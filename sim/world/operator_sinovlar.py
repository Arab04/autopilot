"""Operator paneli (B bosqich) sinovlari: brauzersiz, dastur operator rolini o'ynaydi.

    python operator_sinovlar.py

1-5: simulyatorning operator interfeysi (chorrahaga ruxsat, rad, qo'lda boshqarish, favqulodda to'xtatish,
yordam so'rovida boshqaruvni olish). 6: qo'lda boshqarishda ham to'siqqa urilmaydi. 7: HTTP server.
10: sinov kamerasi (telefon kadr yuboradi, panel MJPEG oqimini oladi).
"""

import json
import sys
import threading
import time
import urllib.request

from yol_dunyo import Operator, Transport, YolSsenariy, ishga_tushir
from yol_sinovlar import _kesuvchilar, _xavfsiz, _yol
from autopilot.marshrut import Bolak, Marshrut


def _chorraha(oqim_kesuvchi=True, **k):
    m = Marshrut([_yol(80), Bolak("otish", 7.0, yollar=2), _yol(60)])
    return YolSsenariy("chorraha", m, kesuvchi=_kesuvchilar(0, 2, 9.0) if oqim_kesuvchi else [], urug=3, **k)


class Dastur(Operator):
    """Ssenariy bo'yicha ishlaydigan operator. Har bir hodisani yozib boradi."""

    def __init__(self, javoblar=(), kechikish=2.0):
        self.javoblar = list(javoblar)  # navbatdagi so'rovlarga javoblar; tugasa - tasdiq
        self.kechikish = kechikish
        self.sorovlar, self.kutilmoqda = [], None
        self.qolda, self.toxtat, self.yop = None, False, False
        self.izlar = []

    def sorov(self, t, turi, malumot):
        self.sorovlar.append((t, turi))
        if turi == "otish":
            self.kutilmoqda = t
        elif turi == "yopildi":
            self.kutilmoqda = None

    def otish_javobi(self, t):
        if self.kutilmoqda is None or t < self.kutilmoqda + self.kechikish:
            return None
        self.kutilmoqda = None
        return self.javoblar.pop(0) if self.javoblar else True

    def boshqaruv(self, t):
        return self.qolda

    def yordam_yopildimi(self, t):
        j, self.yop = self.yop, False
        return j

    def toxtatildimi(self, t):
        return self.toxtat

    def kuzat(self, t, holat):
        self.izlar.append(holat)


def sinov_tasdiq():
    op = Dastur()
    n = ishga_tushir(_chorraha(oqim_kesuvchi=False), operator=op)
    otish = sum(1 for _, x in op.sorovlar if x == "otish")
    return n.yetib_keldi and _xavfsiz(n) and otish == 1 and op.izlar[-1].get("tugadi"), f"so'rov {otish}"


def sinov_oqim():
    """Ko'ndalang oqim bor, operator har doim ruxsat beradi: skuter baribir o'zi tekshiradi."""
    op = Dastur()
    n = ishga_tushir(_chorraha(), operator=op)
    otish = sum(1 for _, x in op.sorovlar if x == "otish")
    rad = sum(1 for _, x in op.sorovlar if x == "skuter_rad")
    return n.yetib_keldi and _xavfsiz(n), f"so'rov {otish}, skuter o'zi to'xtadi {rad}"


def sinov_rad():
    op = Dastur(javoblar=[False, False])
    n = ishga_tushir(_chorraha(oqim_kesuvchi=False), operator=op)
    otish = sum(1 for _, x in op.sorovlar if x == "otish")
    # Rad etilganda o'tmaydi: kutib, yana so'raydi; uchinchi so'rovga ruxsat
    return n.yetib_keldi and _xavfsiz(n) and otish == 3, f"so'rov {otish}"


def sinov_qolda():
    class Op(Dastur):
        def boshqaruv(self, t):
            return (3.0, 2.0) if 5.0 <= t < 20.0 else None

    op = Op()
    n = ishga_tushir(YolSsenariy("qolda", Marshrut([_yol(200)]), urug=4), operator=op)
    h = next(x for x in op.izlar if x["t"] >= 19.5)
    return (n.yetib_keldi and _xavfsiz(n) and abs(h["d"] - 2.0) < 0.15 and abs(h["v"] - 3.0) < 0.2 and h["qolda"]
            and not op.izlar[-1]["qolda"]), f"20-s da d={h['d']:.2f} m, v={h['v']:.1f} m/s"


def sinov_toxtatish():
    class Op(Dastur):
        def toxtatildimi(self, t):
            return 5.0 <= t < 12.0

    op = Op()
    n = ishga_tushir(YolSsenariy("to'xtatish", Marshrut([_yol(200)]), urug=5), operator=op)
    h = next(x for x in op.izlar if x["t"] >= 11.5)
    return n.yetib_keldi and h["v"] == 0.0 and h["holat"] == "operator_toxtatdi", f"11,5 s da v={h['v']}"


def sinov_yordam():
    """Operator chorraha so'roviga javob bermaydi -> skuter yordam so'raydi (safar to'xtamaydi) ->
    operator boshqaruvni olib chorrahadan o'tkazadi -> avtonom davom etib manzilga yetadi."""
    class Op(Dastur):
        def otish_javobi(self, t):
            return None

        def sorov(self, t, turi, malumot):
            super().sorov(t, turi, malumot)
            if turi == "yordam":
                self.qolda = (2.0, 0.8)

        def kuzat(self, t, holat):
            super().kuzat(t, holat)
            if self.qolda and holat["s"] > 95:
                self.qolda = None

    op = Op()
    n = ishga_tushir(_chorraha(oqim_kesuvchi=False), operator=op)
    yordam = sum(1 for _, x in op.sorovlar if x == "yordam")
    return n.yordam and n.yetib_keldi and _xavfsiz(n) and yordam == 1, f"yordam {yordam}, {n.vaqt:.0f} s"


def sinov_qolda_tosiq():
    """Operator to'xtagan mashinaga qarab to'liq tezlikda boshqaradi: kamera himoyasi to'xtatadi."""
    class Op(Dastur):
        def boshqaruv(self, t):
            return (5.5, 1.0)

    op = Op()
    sc = YolSsenariy("qo'lda to'siq", Marshrut([_yol(200)]),
                     [Transport("toxtagan", 80, 1.0, uzunlik=4.5, eni=1.8, polosa=-1, id=1)], vaqt_chegarasi=40, urug=6)
    n = ishga_tushir(sc, operator=op)
    return _xavfsiz(n) and 70 < op.izlar[-1]["s"] < 78, f"to'xtadi s={op.izlar[-1]['s']:.1f} m"


def sinov_http():
    import operator_panel as opn
    sim = opn.Simulyator(opn.PanelOperator(vaqt_tezligi=20.0))
    threading.Thread(target=sim.ishla, daemon=True).start()
    srv = opn.server_yasa(sim, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"

    def ol(yol):
        return json.load(urllib.request.urlopen(url + yol, timeout=5))

    def yubor(**b):
        r = urllib.request.Request(url + "/buyruq", json.dumps(b).encode(), {"Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(r, timeout=5))
        except urllib.error.HTTPError as e:
            return json.load(e)

    try:
        sahifa = urllib.request.urlopen(url + "/", timeout=5).read().decode()
        yubor(amal="safar", manzil=2)
        for _ in range(100):
            h = ol("/holat")
            if h.get("t", 0) > 3 and h.get("v", 0) > 1:
                break
            time.sleep(0.1)
        safar = ol("/safar")["safar"]
        yubor(amal="toxtat")
        time.sleep(1.0)
        h2 = ol("/holat")
        yubor(amal="davom")
        xato = yubor(amal="yoq_buyruq")
        ok = ("Skuter operator paneli" in sahifa and safar["manzil"] == 2 and len(safar["yol"]) > 100
              and h2["v"] == 0.0 and h2["holat"] == "operator_toxtatdi" and "skuter" in h2 and xato.get("xato"))
        return ok, f"safar {safar['uzunlik'] / 1000:.1f} km, to'xtatilganda v={h2['v']}"
    finally:
        srv.shutdown()


def sinov_parol():
    import base64
    import operator_panel as opn
    sim = opn.Simulyator(opn.PanelOperator())
    srv = opn.server_yasa(sim, port=0, parol="sir123")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/holat"
    try:
        kodlar = []
        for kalit in (None, "operator:xato", "operator:sir123"):
            so = urllib.request.Request(url)
            if kalit:
                so.add_header("Authorization", "Basic " + base64.b64encode(kalit.encode()).decode())
            try:
                kodlar.append(urllib.request.urlopen(so, timeout=5).status)
            except urllib.error.HTTPError as e:
                kodlar.append(e.code)
        return kodlar == [401, 401, 200], f"javoblar {kodlar}"
    finally:
        srv.shutdown()


def sinov_bot():
    """Telegram bot (Telegram serverisiz): so'rov xabari tugmalar bilan faqat operatorlarga ketadi,
    begona odam tugma bossa ham hech narsa bo'lmaydi, operator bossa ruxsat panelga yetadi."""
    import operator_panel as opn
    from operator_bot import OperatorBot
    panel = opn.PanelOperator()
    bot = OperatorBot("TOKEN", panel, {111}, "http://panel")
    yuborilgan = []

    def api(usul, kutish=15, **p):
        yuborilgan.append((usul, p))
        return {"message_id": len(yuborilgan)} if usul == "sendMessage" else True

    bot.api = api
    panel.sorov(5.0, "otish", {"s": 80, "otish": 91, "svetofor": False, "polosalar": 2, "kenglik": 7.0})
    bot._hodisa("otish", {"polosalar": 2, "svetofor": False, "kenglik": 7.0}, 5.0)
    xabar = yuborilgan[0]
    tugmalar = [b["callback_data"] for q in xabar[1]["reply_markup"]["inline_keyboard"] for b in q if "callback_data" in b]
    msg = {"chat": {"id": 222}, "message_id": 1}
    bot._callback({"id": "a", "from": {"first_name": "Begona"}, "message": msg, "data": "tasdiq:5.0"})
    begona = panel.javob
    msg = {"chat": {"id": 111}, "message_id": 1}
    bot._callback({"id": "b", "from": {"first_name": "Ali"}, "message": msg, "data": "tasdiq:5.0"})
    eski = len(yuborilgan)
    bot._callback({"id": "c", "from": {"first_name": "Ali"}, "message": msg, "data": "rad:5.0"})  # endi eskirgan
    ok = (xabar[1]["chat_id"] == 111 and tugmalar == ["tasdiq:5.0", "rad:5.0"] and begona is None
          and panel.javob is True and panel.sorov_otish is None
          and any(u == "answerCallbackQuery" and "allaqachon" in p.get("text", "") for u, p in yuborilgan[eski:]))
    return ok, f"{len(yuborilgan)} ta API chaqiruv"


def sinov_kamera():
    """Telefon kadrni POST qiladi (parol bilan), panel uni MJPEG oqimidan oladi; parolsiz va JPEG bo'lmagan
    kadr qabul qilinmaydi."""
    import base64
    import http.client
    import operator_panel as opn
    sim = opn.Simulyator(opn.PanelOperator())
    srv = opn.server_yasa(sim, port=0, parol="sir", login="admin")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auth = {"Authorization": "Basic " + base64.b64encode(b"admin:sir").decode()}

    def sorov(usul, yol, tana=None, sarlavha=None):
        c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        c.request(usul, yol, body=tana, headers=sarlavha or {})
        r = c.getresponse()
        return r.status, r.read()

    kadr1 = b"\xff\xd8" + b"birinchi" * 100 + b"\xff\xd9"
    kadr2 = b"\xff\xd8" + b"ikkinchi" * 100 + b"\xff\xd9"
    try:
        sahifa, _ = sorov("GET", "/kamera", sarlavha=auth)
        bosh = json.loads(sorov("GET", "/kamera/holat", sarlavha=auth)[1])
        parolsiz, _ = sorov("POST", "/kamera/kadr", kadr1, {"Content-Type": "image/jpeg"})
        notogri, _ = sorov("POST", "/kamera/kadr", b"salom", auth)
        ok1, _ = sorov("POST", "/kamera/kadr", kadr1, {**auth, "X-Rtt": "84"})
        # Oqim: ulanish paytidagi oxirgi kadrni darhol, keyingisini kelishi bilan beradi
        c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        c.request("GET", "/kamera/oqim", headers=auth)
        r = c.getresponse()
        turi = r.getheader("Content-Type")
        olingan = b""
        while kadr1 not in olingan:
            olingan += r.read1(65536)
        sorov("POST", "/kamera/kadr", kadr2, {**auth, "X-Rtt": "nan"})
        while kadr2 not in olingan:
            olingan += r.read1(65536)
        c.close()
        h = json.loads(sorov("GET", "/kamera/holat", sarlavha=auth)[1])
        ok = (sahifa == 200 and bosh == {"bor": False} and parolsiz == 401 and notogri == 400 and ok1 == 200
              and turi.startswith("multipart/x-mixed-replace") and h["bor"] and h["kadrlar"] == 2
              and h["rtt_ms"] == 84 and h["kechikish_ms"] >= 42)
        return ok, f"javoblar {sahifa}/{parolsiz}/{notogri}/{ok1}, kechikish {h.get('kechikish_ms')} ms"
    finally:
        srv.shutdown()


SINOVLAR = [
    ("1. Chorrahada operator ruxsat beradi", sinov_tasdiq),
    ("1b. Ko'ndalang oqim: ruxsatdan keyin ham skuter o'zi tekshiradi", sinov_oqim),
    ("2. Operator rad etadi: skuter kutib, qayta so'raydi", sinov_rad),
    ("3. Qo'lda boshqarish va avtonomga qaytish", sinov_qolda),
    ("4. Favqulodda to'xtatish", sinov_toxtatish),
    ("5. Yordam so'rovi: operator boshqaruvni olib o'tkazadi", sinov_yordam),
    ("6. Qo'lda boshqarishda ham to'siq oldida to'xtaydi", sinov_qolda_tosiq),
    ("7. HTTP server: sahifa, holat, buyruqlar", sinov_http),
    ("8. Server paroli (HTTP Basic)", sinov_parol),
    ("9. Telegram bot: so'rov, operator javobi, begona odam", sinov_bot),
    ("10. Sinov kamerasi: kadr yuborish va MJPEG oqimi", sinov_kamera),
]


def main():
    xatolar = []
    for nomi, f in SINOVLAR:
        ok, izoh = f()
        print(f"{'OK ' if ok else 'XATO'}  {nomi} ({izoh})", flush=True)
        if not ok:
            xatolar.append(nomi)
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


if __name__ == "__main__":
    sys.exit(main())
