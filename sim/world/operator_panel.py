"""Operator paneli (B bosqich): virtual skuterni brauzerdan kuzatish va masofadan boshqarish.

Ishga tushirish:
    python3 operator_panel.py            # keyin brauzerda http://localhost:8765
    python3 operator_panel.py --port 9000 --manzil 3 --tezlik 2

Simulyator Chirchiq xaritasida ombordan tanlangan manzilga real vaqtda yuradi. Operator:
  - svetoforsiz chorrahada skuterning "kesib o'taymi?" so'roviga tasdiq/rad beradi;
  - skuter qolib ketsa (yordam so'rovi), boshqaruvni oladi: tezlik va bordyurdan masofani beradi,
    keyin avtonomga qaytaradi;
  - istalgan payt favqulodda to'xtatadi.
Operator buyrug'i ham skuterning xavfsizlik qatlamidan o'tadi (ultratovush, kamera), chorrahaga ruxsat
berilsa ham skuter mashinalarni o'zi yana tekshiradi.

Faqat Python standart kutubxonasi. Server faqat shu kompyuterdan ochiladi (127.0.0.1); tarmoqqa ochish
uchun --host 0.0.0.0 (parolsiz, faqat ishonchli tarmoqda).
"""

import argparse
import base64
import bisect
import hmac
import os
import sys
import json
import math
import random
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from xarita_sinovlar import CHIRCHIQ_MANZILLAR, CHIRCHIQ_OMBOR, CHIRCHIQ_OSM, Xarita, _asosiy
from yol_dunyo import Kocha, Operator, ishga_tushir, kocha_toldir
from autopilot.yol import YolSozlamalari
from kamera import MAX_KADR, Kamera

HTML = Path(__file__).with_name("operator_panel.html")
FLOT_HTML = Path(__file__).with_name("flot.html")
KAMERA_HTML = Path(__file__).with_name("kamera.html")
QOLDA_MAX_TEZLIK = 20 / 3.6


class Geometriya:
    """Marshrut koordinatasi (s, d) -> tekislik (x, y) va yo'nalish; Marshrut.dekart ning tez varianti."""

    def __init__(self, marshrut):
        self.m = marshrut
        self.boshlar, self.pozalar = [], []
        x = y = th = 0.0
        for b in marshrut.bolaklar:
            self.boshlar.append(b.boshi)
            self.pozalar.append((x, y, th, b))
            x, y, th = self._oldinga(x, y, th, b, b.uzunlik)

    @staticmethod
    def _oldinga(x, y, th, b, l):
        if b.turi == "burilish" and abs(b.egrilik) > 1e-9:
            r = 1 / b.egrilik
            return (x + r * (math.sin(th + l / r) - math.sin(th)), y - r * (math.cos(th + l / r) - math.cos(th)),
                    th + l / r)
        return x + l * math.cos(th), y + l * math.sin(th), th

    def poza(self, s):
        i = max(0, bisect.bisect_right(self.boshlar, s) - 1)
        x, y, th, b = self.pozalar[i]
        return self._oldinga(x, y, th, b, min(max(0.0, s - b.boshi), b.uzunlik))

    def xy(self, s, d=0.0):
        x, y, th = self.poza(s)
        return x - d * math.sin(th), y + d * math.cos(th), th


class SafarBekor(Exception):
    pass


class PanelOperator(Operator):
    """Brauzerdagi operator: HTTP so'rovlaridan buyruqlarni oladi, simulyatordan holatni oladi."""

    def __init__(self, vaqt_tezligi=1.0):
        self.lock = threading.Lock()
        self.vaqt_tezligi = vaqt_tezligi
        self.pauza = False
        self.safar = None          # marshrut, xarita ma'lumotlari (panel bir marta oladi)
        self.safar_raqami = 0
        self.geo = None
        self.surat = None
        self.jurnal = deque(maxlen=200)
        self.jurnal_n = 0
        self.tinglovchilar = []    # f(turi, malumot, t): so'rovlar haqida xabar (masalan Telegram bot)
        self._yangi_safar_tozala()

    def _yangi_safar_tozala(self):
        self.sorov_otish = None    # {"t", "s", ...}
        self.sorov_yordam = None
        self.javob = None
        self.qolda = False
        self.qv, self.qd = 0.0, 0.8
        self.toxtat = False
        self.yordam_yop = False
        self.bekor = False
        self._t0 = None

    def yoz(self, matn, t=None):
        with self.lock:
            self.jurnal_n += 1
            self.jurnal.append({"n": self.jurnal_n, "t": round(t, 1) if t is not None else None,
                                "vaqt": time.strftime("%H:%M:%S"), "matn": matn})

    # --- Simulyator tomoni (Operator interfeysi) ---
    def sorov(self, t, turi, malumot):
        yopilgan = None
        with self.lock:
            if turi == "otish":
                self.sorov_otish = dict(malumot, t=t)
            elif turi == "yordam":
                self.sorov_yordam = dict(malumot, t=t)
            elif turi == "yopildi":
                qaysi = "sorov_yordam" if malumot.get("sorov") == "yordam" else "sorov_otish"
                yopilgan = getattr(self, qaysi)
                setattr(self, qaysi, None)
        if turi == "otish":
            q = "svetofor bor" if malumot.get("svetofor") else "svetoforsiz"
            self.yoz(f"So'rov: chorrahani kesib o'tishga ruxsat ({malumot.get('polosalar')} polosa, {q})", t)
        elif turi == "yordam":
            self.yoz(f"YORDAM: skuter qolib ketdi ({holat_nomi(malumot.get('sabab'))})", t)
        elif turi == "skuter_rad":
            self.yoz("Skuter o'tmadi: o'zi yaqinlashayotgan mashina ko'rdi, bo'sh joy bo'lganda yana so'raydi", t)
        elif yopilgan:
            self.yoz("Yordam so'rovi yopildi" if malumot.get("sorov") == "yordam" else "Chorraha so'rovi yopildi", t)
        for f in self.tinglovchilar:
            try:
                f(turi, malumot, t)
            except Exception as e:  # bot xatosi simulyatorni to'xtatmasin
                self.yoz(f"Xabar yuborilmadi: {e}", t)

    def otish_javobi(self, t):
        with self.lock:
            j, self.javob = self.javob, None
            return j

    def boshqaruv(self, t):
        with self.lock:
            return (self.qv, self.qd) if self.qolda else None

    def yordam_yopildimi(self, t):
        with self.lock:
            j, self.yordam_yop = self.yordam_yop, False
            if j:
                self.sorov_yordam = None
            return j

    def toxtatildimi(self, t):
        return self.toxtat

    def kuzat(self, t, holat):
        with self.lock:
            self.surat = holat
            if not self.qolda:
                self.qd = holat["d"]  # qo'lda boshqarish shu joydan boshlanadi
        if holat.get("tugadi"):
            return
        # Real vaqt: simulyator soati devordagi soatdan (vaqt_tezligi marta) oldinga o'tib ketmasin
        while True:
            if self.bekor:
                raise SafarBekor()
            if not self.pauza:
                break
            time.sleep(0.05)
            self._t0 = None
        hozir = time.monotonic()
        if self._t0 is None:
            self._t0 = (t, hozir, self.vaqt_tezligi)
        t0, w0, k = self._t0
        if k != self.vaqt_tezligi:
            self._t0 = (t, hozir, self.vaqt_tezligi)
            return
        kerak = w0 + (t - t0) / k
        if kerak > hozir:
            time.sleep(kerak - hozir)
        elif hozir - kerak > 1.0:
            self._t0 = (t, hozir, k)  # kompyuter ulgurmayapti: orqada qolmaslik uchun qayta boshlaymiz

    # --- Panel tomoni ---
    def buyruq(self, amal, qiymat=None):
        with self.lock:
            v = (self.surat or {}).get("v", 0.0)
            if amal == "tasdiq" and self.sorov_otish:
                self.javob, self.sorov_otish = True, None
                matn = "Operator: chorrahadan o'tishga RUXSAT berdi (skuter mashinalarni o'zi ham tekshiradi)"
            elif amal == "rad" and self.sorov_otish:
                self.javob, self.sorov_otish = False, None
                matn = "Operator: RAD etdi, skuter kutadi va keyinroq yana so'raydi"
            elif amal == "qolda":
                self.qolda, self.qv = True, min(v, 1.0)
                self.sorov_yordam = None
                matn = "Operator boshqaruvni oldi (qo'lda)"
            elif amal == "avtonom":
                self.qolda = False
                self.yordam_yop = True
                matn = "Avtonom rejimga qaytarildi"
            elif amal == "toxtat":
                self.toxtat = True
                matn = "FAVQULODDA TO'XTATISH"
            elif amal == "davom":
                self.toxtat = False
                matn = "To'xtatish bekor qilindi"
            elif amal == "tezlik" and self.qolda:
                self.qv = min(QOLDA_MAX_TEZLIK, max(0.0, self.qv + float(qiymat)))
                return None
            elif amal == "yon" and self.qolda:
                self.qd = min(12.0, max(0.4, self.qd + float(qiymat)))
                return None
            elif amal == "vaqt_tezligi":
                self.vaqt_tezligi = min(20.0, max(0.25, float(qiymat)))
                return None
            elif amal == "pauza":
                self.pauza = bool(qiymat)
                return None
            else:
                return f"noma'lum yoki hozir mumkin bo'lmagan buyruq: {amal}"
        self.yoz(matn, (self.surat or {}).get("t"))
        return None

    def holat_json(self):
        with self.lock:
            h, geo = self.surat, self.geo
            jav = {"safar": self.safar_raqami, "vaqt_tezligi": self.vaqt_tezligi, "pauza": self.pauza,
                   "qolda": self.qolda, "qv": self.qv, "qd": self.qd, "toxtat": self.toxtat,
                   "sorov_otish": self.sorov_otish, "sorov_yordam": self.sorov_yordam,
                   "jurnal": list(self.jurnal)[-40:]}
        if h is None or geo is None:
            return jav
        x, y, th = geo.xy(h["s"], h["d"])
        jav.update({k: h[k] for k in ("t", "s", "d", "v", "holat", "rejim", "otish_holati", "toqnashuv",
                                      "svetofor", "otish", "otish_sorovi")})
        jav["tugadi"], jav["yetib_keldi"] = h.get("tugadi", False), h.get("yetib_keldi", False)
        jav["holat_nomi"] = holat_nomi(h["holat"] if h["holat"] not in ("yurish", "") else h["otish_holati"] or h["rejim"])
        jav["skuter"] = [round(x, 2), round(y, 2), round(th + h["psi"], 3), round(geo.poza(h["s"])[2], 3)]
        tr = []
        for turi, s, d, l, w, v in h["transport"]:
            x_, y_, a = geo.xy(s, d)
            tr.append([turi, round(x_, 2), round(y_, 2), round(a, 3), l, w])
        jav["transport"] = tr
        jav["odamlar"] = [[round(c, 2) for c in geo.xy(s, d)[:2]] for s, d in h["odamlar"]]
        ke = []
        for s, d, vx in h["kesuvchi"]:
            x_, y_, a = geo.xy(s, d)
            ke.append([round(x_, 2), round(y_, 2), round(a + (math.pi / 2 if vx >= 0 else -math.pi / 2), 3)])
        jav["kesuvchi"] = ke
        return jav


HOLAT_NOMLARI = {
    "yurish": "Yo'lda", "otishga_yaqinlashish": "Chorrahaga yaqinlashmoqda",
    "operator_kutish": "Operator ruxsatini kutmoqda", "bosh_joy_kutish": "Mashinalar o'tishini kutmoqda",
    "otish": "Chorrahani kesib o'tmoqda", "favqulodda": "Favqulodda tormoz (ultratovush)",
    "kamera_xato": "Kamera xatosi: to'xtadi", "operator": "Operator boshqaryapti",
    "operator_toxtatdi": "Operator to'xtatdi", "kutish": "To'siq oldida kutmoqda",
    "aylanib": "To'siqni aylanib o'tmoqda", "orqa_kutish": "Orqadan mashina o'tishini kutmoqda",
}


def holat_nomi(h):
    return HOLAT_NOMLARI.get(h, h or "")


class Simulyator:
    """Safarlarni navbat bilan yurgizadi (alohida oqimda)."""

    def __init__(self, panel: PanelOperator, davomli=False):
        self.panel = panel
        self.davomli = davomli  # serverda: safar tugasa, keyingisi o'zi boshlanadi
        self.xarita = Xarita.osm_dan(str(CHIRCHIQ_OSM))
        self.c = YolSozlamalari()
        self.navbat = deque()
        self.hodisa = threading.Event()
        self.manzillar = [n for n, *_ in CHIRCHIQ_MANZILLAR]

    def boshla(self, manzil, qaytish=False, urug=None):
        self.navbat.append((manzil, qaytish, urug if urug is not None else random.randrange(10 ** 6)))
        self.panel.bekor = True
        self.hodisa.set()

    def ishla(self):
        while True:
            self.hodisa.wait()
            self.hodisa.clear()
            while self.navbat:
                manzil, qaytish, urug = self.navbat.pop()
                self.navbat.clear()
                tugadi = self._safar(manzil, qaytish, urug)
                if self.davomli and tugadi and not self.navbat:
                    # Ombordan manzilga, keyin omborga qaytish; keyin keyingi manzil
                    keyingi = (manzil, True) if not qaytish else (manzil % len(self.manzillar) + 1, False)
                    time.sleep(10)
                    if not self.navbat:
                        self.navbat.append((*keyingi, random.randrange(10 ** 6)))

    def _safar(self, k, qaytish, urug):
        ombor = CHIRCHIQ_OMBOR[1:]
        nomi, lat, lon = CHIRCHIQ_MANZILLAR[k - 1]
        bosh, oxir = ((lat, lon), ombor) if qaytish else (ombor, (lat, lon))
        xm = self.xarita.skuter_marshruti(bosh, oxir, _asosiy)
        sc = kocha_toldir(xm.marshrut, random.Random(urug), nomi, rejim="yarim", urug=urug)
        sc.vaqt_chegarasi = 4 * 3600.0
        p = self.panel
        with p.lock:
            p._yangi_safar_tozala()
            p.safar_raqami += 1
            p.geo = Geometriya(xm.marshrut)
            p.surat = None
            p.safar = self._safar_json(xm, k, qaytish, p.safar_raqami)
        p.yoz(f"Yangi safar: {'qaytish: ' + nomi + ' -> ombor' if qaytish else 'ombor -> ' + nomi} "
              f"({xm.marshrut.uzunlik / 1000:.1f} km, {len(xm.marshrut.otishlar())} ta chorraha)")
        try:
            n = ishga_tushir(sc, self.c, operator=p)
        except SafarBekor:
            p.yoz("Safar bekor qilindi")
            return False
        p.yoz(f"Safar tugadi: {'yetib keldi' if n.yetib_keldi else 'yetmadi'}, {n.vaqt / 60:.1f} daqiqa, "
              f"to'qnashuv {n.mashina_toq + n.odam_toq + n.velo_toq + n.tosiq_toq + n.kesuvchi_toq}")
        return True

    def _safar_json(self, xm, k, qaytish, raqam):
        m = xm.marshrut
        geo = Geometriya(m)
        kocha = Kocha(m, self.c)
        yol = []
        s = 0.0
        while s <= m.uzunlik:
            x, y, th = geo.xy(s)
            b = m.bolak(s)
            y_ = kocha.yol(s)
            turi = {"yol": 0, "burilish": 1, "otish": 2}.get(b.turi, 0)
            yol.append([round(s, 1), round(x, 2), round(y, 2), round(th, 4), turi, y_.parkovka, y_.velo,
                        y_.yol_kengligi, y_.yollar])
            s += 2.0
        otishlar = []
        for b in m.otishlar():
            p0, p1 = geo.xy(b.boshi + 1e-6), geo.xy(b.oxiri - 1e-6)
            otishlar.append([round(b.boshi, 2), round(b.oxiri, 2), b.svetofor, b.yollar,
                             [round(b.boshi, 2)] + [round(v, 4) for v in p0], [round(b.oxiri, 2)] + [round(v, 4) for v in p1]])
        # Kichik xarita: marshrut tugunlari va atrofdagi ko'chalar (xarita tekisligida, metr)
        pts = [self.xarita.xy(i) for i in xm.tugunlar]
        x0, x1 = min(p[0] for p in pts) - 300, max(p[0] for p in pts) + 300
        y0, y1 = min(p[1] for p in pts) - 300, max(p[1] for p in pts) + 300
        kochalar = []
        for y in self.xarita.yollar:
            if y.turi not in ("primary", "secondary", "tertiary", "trunk", "residential", "unclassified"):
                continue
            q = [self.xarita.xy(i) for i in y.tugunlar]
            if any(x0 < a < x1 and y0 < b < y1 for a, b in q):
                kochalar.append([[round(a - x0), round(b - y0)] for a, b in q])
        return {"raqam": raqam, "manzil": k, "nomi": CHIRCHIQ_MANZILLAR[k - 1][0], "qaytish": qaytish,
                "uzunlik": round(m.uzunlik, 1), "yol": yol, "otishlar": otishlar,
                "xarita": {"w": round(x1 - x0), "h": round(y1 - y0), "marshrut": [[round(a - x0), round(b - y0)] for a, b in pts],
                           "kochalar": kochalar}}


def server_yasa(sim: Simulyator, host="127.0.0.1", port=8765, parol=None, login="operator", flot=None,
                api_kalit=None):
    """parol berilsa, har bir so'rov HTTP Basic bilan himoyalanadi (foydalanuvchi: login).

    flot berilsa: /flot sahifasi va /api/... (buyurtmalar). api_kalit berilsa, CRM /api/buyurtma... yo'llariga
    parolsiz, "X-API-Kalit" sarlavhasi bilan kira oladi (boshqa sahifalarga emas).
    """
    panel = sim.panel
    kamera = Kamera()
    kalit = "Basic " + base64.b64encode(f"{login}:{parol}".encode()).decode() if parol else None
    flot_xarita = {}  # bir marta hisoblanadi

    class Ishlovchi(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _javob(self, kod, tana, turi="application/json"):
            data = tana if isinstance(tana, bytes) else json.dumps(tana, ensure_ascii=False).encode()
            self.send_response(kod)
            self.send_header("Content-Type", turi + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _ruxsatmi(self):
            self.crm = False
            if kalit is None or hmac.compare_digest(self.headers.get("Authorization", ""), kalit):
                return True
            if api_kalit and self.path.startswith("/api/buyurtma") \
                    and hmac.compare_digest(self.headers.get("X-API-Kalit", ""), api_kalit):
                self.crm = True
                return True
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Skuter operator paneli", charset="UTF-8"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False

        def do_GET(self):
            if not self._ruxsatmi():
                return
            if self.path in ("/", "/index.html"):
                self._javob(200, HTML.read_bytes(), "text/html")
            elif self.path == "/holat":
                self._javob(200, panel.holat_json())
            elif self.path == "/safar":
                with panel.lock:
                    s = panel.safar
                self._javob(200, {"safar": s, "manzillar": sim.manzillar})
            elif self.path == "/kamera":
                self._javob(200, KAMERA_HTML.read_bytes(), "text/html")
            elif self.path == "/kamera/holat":
                self._javob(200, kamera.holat())
            elif self.path.startswith("/kamera/oqim"):
                self._oqim()
            elif flot is not None and (self.path == "/flot" or self.path.startswith("/api/")):
                self._flot_get()
            else:
                self._javob(404, {"xato": "topilmadi"})

        def _flot_get(self):
            yol = self.path.split("?")[0].rstrip("/")
            if yol == "/flot":
                return self._javob(200, FLOT_HTML.read_bytes(), "text/html")
            if yol == "/api/flot/holat":
                return self._javob(200, flot.holat_json())
            if yol == "/api/flot/xarita":
                if not flot_xarita:
                    flot_xarita.update(flot.xarita_json())
                return self._javob(200, flot_xarita)
            if yol == "/api/manzillar":
                return self._javob(200, [{"raqam": i + 1, "nomi": n, "lat": la, "lon": lo}
                                         for i, (n, la, lo) in enumerate(flot.manzillar)])
            q = yol.split("/")
            if len(q) == 4 and q[2] == "buyurtma" and q[3].isdigit():
                with flot.lock:
                    b = flot.buyurtmalar.get(int(q[3]))
                    if b is None:
                        return self._javob(404, {"xato": "buyurtma topilmadi"})
                    return self._javob(200, flot.buyurtma_json(b))
            self._javob(404, {"xato": "topilmadi"})

        def _flot_post(self):
            if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
                return self._javob(411, {"xato": "Content-Length sarlavhasi kerak (chunked tana o'qilmaydi)"})
            try:
                n = int(self.headers.get("Content-Length", 0))
                b = json.loads(self.rfile.read(min(n, 10000)) or b"{}")
                if not isinstance(b, dict):
                    raise ValueError("JSON obyekt kerak")
            except ValueError as e:
                return self._javob(400, {"xato": f"noto'g'ri JSON: {e}"})
            yol = self.path.split("?")[0].rstrip("/")
            q = yol.split("/")
            try:
                if yol == "/api/buyurtma":
                    bu, xato = flot.buyurtma_ber(
                        lat=b.get("lat"), lon=b.get("lon"), manzil=b.get("manzil"), nomi=b.get("nomi", ""),
                        mijoz=b.get("mijoz", ""), tel=b.get("tel", ""), izoh=b.get("izoh", ""),
                        manba="crm" if self.crm else "panel", avto_mijoz=b.get("avto_mijoz", not self.crm))
                    if xato:
                        return self._javob(400, {"xato": xato})
                    with flot.lock:
                        return self._javob(201, flot.buyurtma_json(bu, sirli=True))
                if len(q) == 5 and q[2] == "buyurtma" and q[3].isdigit() and q[4] in ("och", "bekor"):
                    bid = int(q[3])
                    xato = flot.qutini_och(bid, str(b.get("pin", ""))) if q[4] == "och" else flot.bekor_qil(bid)
                    return self._javob(400 if xato else 200, {"xato": xato} if xato else {"ok": True})
                if yol == "/api/flot/sozlama" and not self.crm:
                    flot.sozla(**{k: b[k] for k in ("skuterlar", "operatorlar", "avto_buyurtma", "vaqt_tezligi",
                                                    "pauza") if k in b})
                    return self._javob(200, {"ok": True})
            except (ValueError, TypeError) as e:
                return self._javob(400, {"xato": f"noto'g'ri qiymat: {e}"})
            self._javob(404, {"xato": "topilmadi"})

        def _oqim(self):
            """MJPEG: har yangi kadr multipart bo'lagi bo'lib ketadi; brauzer <img> da video kabi ko'rsatadi."""
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=kadr")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            raqam = -1
            try:
                while True:
                    raqam, jpeg = kamera.kut(raqam)
                    if jpeg is None:
                        continue
                    self.wfile.write(b"--kadr\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg))
                    self.wfile.write(jpeg + b"\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass

        def _kadr_qabul(self):
            n = int(self.headers.get("Content-Length", 0))
            if not 0 < n <= MAX_KADR:
                return self._javob(413, {"xato": f"kadr hajmi 1..{MAX_KADR} bayt bo'lishi kerak"})
            try:
                rtt = self.headers.get("X-Rtt")
                raqam = kamera.qabul(self.rfile.read(n), float(rtt) if rtt else None,
                                     self.headers.get("User-Agent", ""))
            except ValueError as e:
                return self._javob(400, {"xato": str(e)})
            self._javob(200, {"ok": True, "raqam": raqam})

        def do_POST(self):
            if not self._ruxsatmi():
                return
            if self.path == "/kamera/kadr":
                return self._kadr_qabul()
            if flot is not None and self.path.startswith("/api/"):
                return self._flot_post()
            if self.path != "/buyruq":
                return self._javob(404, {"xato": "topilmadi"})
            try:
                n = int(self.headers.get("Content-Length", 0))
                b = json.loads(self.rfile.read(min(n, 10000)) or b"{}")
                amal = b.get("amal")
                if amal == "safar":
                    sim.boshla(int(b["manzil"]), bool(b.get("qaytish")))
                    xato = None
                else:
                    xato = panel.buyruq(amal, b.get("qiymat"))
            except (ValueError, KeyError, TypeError) as e:
                xato = f"noto'g'ri so'rov: {e}"
            self._javob(400 if xato else 200, {"xato": xato} if xato else {"ok": True})

    srv = ThreadingHTTPServer((host, port), Ishlovchi)
    srv.kamera = kamera
    return srv


def main():
    ap = argparse.ArgumentParser(description="Skuter operator paneli (simulyator bilan)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--manzil", type=int, default=1, help=f"1..{len(CHIRCHIQ_MANZILLAR)}")
    ap.add_argument("--tezlik", type=float, default=1.0, help="simulyator vaqti tezligi (1 = real vaqt)")
    ap.add_argument("--davomli", action="store_true", help="safar tugasa keyingisini o'zi boshlaydi (server uchun)")
    ap.add_argument("--skuterlar", type=int, default=5, help="flot: virtual skuterlar soni")
    ap.add_argument("--operatorlar", type=int, default=2, help="flot: operatorlar soni")
    ap.add_argument("--buyurtma", type=float, default=6.0, help="flot: avtomatik buyurtmalar / soat (0 = faqat API)")
    ap.add_argument("--flot-tezlik", type=float, default=10.0, help="flot: vaqt tezligi")
    a = ap.parse_args()
    parol = os.environ.get("OPERATOR_PAROL") or None
    if a.host not in ("127.0.0.1", "localhost", "::1") and not parol:
        sys.exit("Tarmoqqa ochishdan oldin OPERATOR_PAROL muhit o'zgaruvchisida parol bering.")
    sim = Simulyator(PanelOperator(a.tezlik), davomli=a.davomli)
    threading.Thread(target=sim.ishla, daemon=True).start()
    sim.boshla(a.manzil)
    from flot import Flot
    flot = Flot(a.skuterlar, a.operatorlar, a.buyurtma, urug=random.randrange(10 ** 6), xarita=sim.xarita,
                vaqt_tezligi=a.flot_tezlik)
    threading.Thread(target=flot.ishla, daemon=True).start()
    srv = server_yasa(sim, a.host, a.port, parol, os.environ.get("OPERATOR_LOGIN") or "operator", flot=flot,
                      api_kalit=os.environ.get("FLOT_API_KALIT") or None)
    if os.environ.get("TELEGRAM_TOKEN"):
        from operator_bot import OperatorBot
        chatlar = {int(x) for x in os.environ.get("OPERATOR_CHATLAR", "").replace(",", " ").split()}
        bot = OperatorBot(os.environ["TELEGRAM_TOKEN"], sim.panel, chatlar, os.environ.get("PANEL_URL", ""))
        threading.Thread(target=bot.ishla, daemon=True).start()
        print(f"Telegram bot ishga tushdi, operatorlar: {sorted(chatlar) or 'hali yo`q (/start yuborib chat raqamini bilib oling)'}")
    print(f"Operator paneli: http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{srv.server_port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
