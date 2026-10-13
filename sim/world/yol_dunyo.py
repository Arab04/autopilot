"""Virtual ko'cha: skuter avtomobil yo'lining o'ng chetida (3-bosqich).

Simulyatorda: polosalar bo'ylab mashinalar (IDM haydovchi modeli, skuterni quvib o'tish, polosa
almashtirish, e'tiborsiz haydovchilar), chetda to'xtab turgan mashinalar va avtobuslar, velosipedchilar,
yo'lni noto'g'ri joydan kesib o'tuvchi odamlar (to'xtagan mashinalar orasidan chiqqanlari ham),
chorrahalar (svetofor, kesib o'tuvchi mashinalar, o'ngga buriluvchilar).

Bu fayl faqat simulyator. Skuterning dasturi: `autopilot/yol.py`.
"""

from dataclasses import dataclass, field
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from autopilot.haydash import KMH, boshqaruv_burchagi  # noqa: E402
from autopilot.marshrut import Marshrut, Bolak  # noqa: E402
from autopilot.otish import Mashina as KorilganMashina  # noqa: E402
from autopilot.yol import YolAvtopilot, YolObyekt, YolSozlamalari, yol_tartibi  # noqa: E402
from dunyo import YolMashinasi, mashina_oqimi, mashina_kamera  # noqa: E402

DT = 0.05
OPERATOR_KECHIKISHI = 2.0
OLD_KAMERA, ORQA_KAMERA = 50.0, 60.0
IDM_A, IDM_B, IDM_T, IDM_S0 = 1.5, 2.0, 1.2, 2.0


@dataclass
class Transport:
    """Ko'chadagi transport yoki to'siq (to'rtburchak). s, d: markazi."""
    turi: str              # "mashina", "avtobus", "velosiped", "toxtagan", "tosiq"
    s: float
    d: float
    v: float = 0.0
    v0: float = 0.0        # xohlagan tezligi
    uzunlik: float = 4.5
    eni: float = 1.8
    polosa: int = 0        # mashinalar uchun; -1 = chetda
    burilish: bool = False  # keyingi chorrahada o'ngga buriladi
    signal: bool = True    # burilish chirog'ini yoqadimi
    etiborsiz: bool = False  # skuterni kech ko'radi
    qizilda: bool = False  # qizil chiroqda o'tib ketadi
    paydo: float = 0.0     # shu vaqtdan boshlab yo'lda
    d_maqsad: float = None
    yoq: bool = False      # yo'ldan chiqib ketdi
    id: int = 0


@dataclass
class Piyoda:
    """Yo'lni noto'g'ri joydan kesib o'tuvchi odam."""
    s: float
    tetik: float           # skuter shu joyga yetganda yo'lga chiqadi
    vd: float = 1.4
    etiborli: bool = True
    d: float = -0.6
    yurmoqda: bool = False
    yoq: bool = False
    id: int = 0


@dataclass
class YolSsenariy:
    nomi: str
    marshrut: Marshrut
    transport: list = field(default_factory=list)
    piyodalar: list = field(default_factory=list)
    oqim: float = 0.0               # har polosada mashina/soniya (orqadan keladi)
    burilish_ulushi: float = 0.25   # chorraha oldida o'ngga buriluvchilar ulushi
    etiborsiz_ulushi: float = 0.02
    kesuvchi: list = field(default_factory=list)  # chorrahadagi ko'ndalang mashinalar (dunyo.YolMashinasi)
    svetofor_davri: tuple = (25.0, 25.0)  # (biz uchun yashil, qizil)
    svetofor_siljish: list = field(default_factory=list)  # har chorraha uchun
    kamera_ochadi: list = field(default_factory=list)
    vaqt_chegarasi: float = 600.0
    rejim: str = "yarim"
    urug: int = 0


@dataclass
class YolNatija:
    nomi: str
    yetib_keldi: bool
    vaqt: float
    mashina_toq: int
    odam_toq: int
    velo_toq: int
    tosiq_toq: int
    kesuvchi_toq: int
    yaqin_otish: float        # yonimizdan o'tgan mashinagacha eng kam bo'sh joy (m)
    eshik_zonasi: int         # to'xtagan mashina yonidan 0,8 m dan yaqin o'tishlar
    chetga: int
    favqulodda: int
    yordam: bool
    operator_sorovlari: int
    ortacha_kmh: float
    aylanib_otish: int
    orqa_kutish_s: float
    iz: dict


def svetofor_holati(sc, t, i):
    yashil, qizil = sc.svetofor_davri
    siljish = sc.svetofor_siljish[i] if i < len(sc.svetofor_siljish) else 0.0
    f = (t + siljish) % (yashil + qizil)
    return (True, yashil - f) if f < yashil else (False, yashil + qizil - f)


class Kocha:
    def __init__(self, marshrut: Marshrut, c: YolSozlamalari):
        self.m = marshrut
        self.c = c
        self.otishlar = marshrut.otishlar()
        # Har bo'lak uchun yo'l tartibi (chorraha va burilishda oldingi yo'lniki)
        self._yollar = []
        oxirgi = next((b for b in marshrut.bolaklar if b.turi == "yol"), None)
        for b in marshrut.bolaklar:
            if b.turi == "yol":
                oxirgi = b
            self._yollar.append(oxirgi)
        # Mashinalar to'g'ri o'tadigan chorrahalar (oldidan yo'l keladi) va burilish joylari
        self.togri_otish = set()
        for i, b in enumerate(marshrut.bolaklar):
            if b.turi == "otish" and i > 0 and marshrut.bolaklar[i - 1].turi == "yol":
                self.togri_otish.add(b.boshi)

    def yol(self, s):
        for b, y in zip(self.m.bolaklar, self._yollar):
            if s < b.oxiri:
                return y
        return self._yollar[-1]

    def polosa_markazi(self, s, p):
        y = self.yol(s)
        return y.parkovka + y.velo + (p + 0.5) * y.yol_kengligi

    def mashina_yoli_mi(self, s):
        """Bu joyda mashinalar bizning yo'nalishda harakatlanadimi."""
        b = self.m.bolak(s)
        return b.turi == "yol" or (b.turi == "otish" and b.boshi in self.togri_otish)


def _band(o):
    return o.d - o.eni / 2, o.d + o.eni / 2


def ishga_tushir(sc: YolSsenariy, c: YolSozlamalari = None):
    c = c or YolSozlamalari()
    rnd = random.Random(sc.urug)
    m = sc.marshrut
    kocha = Kocha(m, c)
    ap = YolAvtopilot(m, sc.rejim, c)
    transport = [Transport(**vars(x)) for x in sc.transport]
    piyodalar = [Piyoda(**vars(p)) for p in sc.piyodalar]
    kesuvchi = [YolMashinasi(**vars(x)) for x in sc.kesuvchi]
    keyingi_id = 1000
    for x in transport:
        if not x.id:
            x.id = keyingi_id
            keyingi_id += 1
    for p in piyodalar:
        p.id = keyingi_id
        keyingi_id += 1
    y0 = kocha.yol(0.0)
    s, d, psi, v = 0.0, yol_tartibi(y0, c)[1], 0.0, 0.0
    t = 0.0
    qadam = 0
    buyruq = None
    mash_toq = odam_toq = velo_toq = tosiq_toq = kes_toq = favq = chetga = eshik = aylanish = 0
    yaqin_otish = math.inf
    orqa_kutish = 0.0
    tegib = set()
    eshik_korildi = set()
    chetda = False
    oldingi_holat = None
    oldingi_rejim = "yurish"
    iz = {k: [] for k in ("t", "s", "d", "v", "holat")}
    op_vaqt, op_javob = None, None
    yordam = False

    def yangi_mashina(s0, p, v0):
        nonlocal keyingi_id
        keyingi_id += 1
        avtobus = rnd.random() < 0.06
        return Transport("avtobus" if avtobus else "mashina", s0, kocha.polosa_markazi(s0, p), v0, v0,
                         12.0 if avtobus else 4.5, 2.5 if avtobus else 1.8, p,
                         burilish=rnd.random() < sc.burilish_ulushi, signal=rnd.random() < 0.9,
                         etiborsiz=rnd.random() < sc.etiborsiz_ulushi, qizilda=rnd.random() < 0.02,
                         id=keyingi_id)

    # Boshlang'ich oqim: skuter atrofida polosalarda mashinalar
    if sc.oqim > 0:
        for p in range(y0.yollar):
            x = -200.0
            while x < 250:
                x += rnd.expovariate(sc.oqim / 12.0)  # ~12 m/s tezlikda oqim zichligi
                if kocha.mashina_yoli_mi(max(0.0, x)) and not -40 < x < 15:  # skuterning ustiga emas
                    v0 = rnd.uniform(30, 60) * KMH
                    transport.append(yangi_mashina(x, p, v0))

    while t < sc.vaqt_chegarasi and s < m.uzunlik:
        if ap.yordam_kerakmi(t, s):
            yordam = True
            break
        yol = kocha.yol(s)
        chet, asosiy, _, polosa_boshi = yol_tartibi(yol, c)
        # --- Yangi mashinalar orqadan ---
        if sc.oqim > 0:
            s_paydo = s - 200.0
            if kocha.mashina_yoli_mi(max(0.0, s_paydo)) and s_paydo > -250:
                for p in range(kocha.yol(max(0.0, s_paydo)).yollar):
                    if rnd.random() < sc.oqim * DT:
                        band_bosh = all(abs(x.s - s_paydo) > 25 for x in transport
                                        if x.polosa == p and x.turi in ("mashina", "avtobus") and not x.yoq)
                        if band_bosh:
                            transport.append(yangi_mashina(s_paydo, p, rnd.uniform(30, 60) * KMH))
        # Skuter dasturi ko'rib turgan chorraha (otish.py dagi tanlov bilan bir xil)
        yaqin_otish_b = next((b for b in kocha.otishlar if s - c.skuter_yarim_uzunlik - c.skuter_r < b.oxiri + 0.5
                              and b.boshi - s < 30), None)
        oi = kocha.otishlar.index(yaqin_otish_b) if yaqin_otish_b else -1
        svet = svetofor_holati(sc, t, oi) if yaqin_otish_b is not None and yaqin_otish_b.svetofor else None
        # --- Datchiklar va dastur (10 Hz) ---
        if qadam % 2 == 0:
            ishlaydi = not any(a <= t < b for a, b in sc.kamera_ochadi)
            aniq = None
            if ishlaydi:
                aniq = []
                for x in transport:
                    if x.yoq or t < x.paydo:
                        continue
                    ds = x.s - s
                    if ds > OLD_KAMERA + x.uzunlik / 2 or ds < -ORQA_KAMERA - x.uzunlik / 2:
                        continue
                    if rnd.random() < 0.03:
                        continue
                    m_ = abs(ds)
                    turi = {"avtobus": "mashina", "toxtagan": "mashina", "tosiq": "to'siq"}.get(x.turi, x.turi)
                    burilish = 0
                    if x.burilish and x.signal:
                        b = next((b for b in kocha.otishlar if 0 < b.boshi - x.s < 45 and b.boshi in kocha.togri_otish), None)
                        burilish = 1 if b is not None else 0
                    aniq.append(YolObyekt(x.s + rnd.gauss(0, 0.1 + 0.01 * m_), x.d + rnd.gauss(0, 0.05 + 0.004 * m_),
                                          x.v + rnd.gauss(0, 0.3), rnd.gauss(0, 0.1), x.uzunlik, x.eni, turi,
                                          burilish, x.id))
                for p in piyodalar:
                    if p.yoq or not p.yurmoqda and p.d < -0.3:
                        continue
                    if yol.parkovka > 0 and p.d < yol.parkovka - 0.2 and _parkovka_ortida(p, transport):
                        continue  # to'xtab turgan mashinalar orasida: ko'rinmaydi
                    ds = p.s - s
                    if not -10 < ds < OLD_KAMERA or rnd.random() < 0.05:
                        continue
                    aniq.append(YolObyekt(p.s + rnd.gauss(0, 0.1), p.d + rnd.gauss(0, 0.08), rnd.gauss(0, 0.1),
                                          (p.vd if p.yurmoqda else 0.0) + rnd.gauss(0, 0.1), 0.6, 0.6, "odam",
                                          0, p.id))
            km = []
            if yaqin_otish_b is not None and ishlaydi:
                km = mashina_kamera(kesuvchi, oi, s, yaqin_otish_b, t, rnd, True) if s > yaqin_otish_b.boshi - 15 else []
            javob = None
            if op_vaqt is not None and t >= op_vaqt:
                javob, op_vaqt = op_javob, None
            buyruq = ap.rejalash(t, s, d, v, aniq, km, svet, javob)
            if ap.operator_sorovi and op_vaqt is None and javob is None:
                op_vaqt = t + OPERATOR_KECHIKISHI
                haqiqiy = [KorilganMashina(x.polosa, x.x, x.vx) for x in kesuvchi if x.otish == oi and t >= x.paydo]
                kelajak = [KorilganMashina(x.polosa, x.x + x.vx * OPERATOR_KECHIKISHI, x.vx) for x in haqiqiy]
                op_javob = (ap.otish.bosh_joy_bor(yaqin_otish_b, s, 0.0, haqiqiy, bufer=1.5)
                            and ap.otish.bosh_joy_bor(yaqin_otish_b, s, 0.0, kelajak, bufer=1.5))
            if ap.rej.rejim == "aylanib" and oldingi_rejim != "aylanib":
                aylanish += 1
            oldingi_rejim = ap.rej.rejim
        uz = _ultratovush(transport, piyodalar, s, d, psi, c)
        yakuniy = ap.xavfsizlik(buyruq, v, uz, t)
        if yakuniy.holat != oldingi_holat:
            if yakuniy.holat == "favqulodda":
                favq += 1
            oldingi_holat = yakuniy.holat
        if yakuniy.holat == "orqa_kutish":
            orqa_kutish += DT
        # --- Skuter harakati ---
        if yakuniy.tezlik > v:
            v = min(yakuniy.tezlik, v + c.tezlanish * DT)
        else:
            v = max(yakuniy.tezlik, v - yakuniy.tormoz * DT)
        kappa = m.egrilik(s)
        s_tezlik = v * math.cos(psi) / max(0.3, 1 - kappa * d)
        psi_kerak = boshqaruv_burchagi(d, yakuniy.d_maqsad, v)
        chek = math.atan2(c.yon_otish_tezligi, max(v, 0.5))
        psi_kerak = max(-chek, min(chek, psi_kerak))
        max_omega = (v / 1.05) * math.tan(math.radians(20)) if v > 0.05 else 0.0
        omega = (psi_kerak - psi) * 3 + kappa * s_tezlik
        omega = max(-max_omega, min(max_omega, omega))
        psi += (omega - kappa * s_tezlik) * DT
        s += s_tezlik * DT
        d += v * math.sin(psi) * DT
        if d - c.skuter_r < 0.02:
            if not chetda:
                chetga += 1
            chetda = True
            d = c.skuter_r + 0.02
        else:
            chetda = False
        # --- Transport ---
        _transport_qadam(transport, piyodalar, kocha, sc, s, d, v, t, rnd)
        _piyoda_qadam(piyodalar, transport, kocha, s, d, v, t)
        _kesuvchi_qadam(kesuvchi, kocha.otishlar, sc, s, v, t)
        # --- To'qnashuvlar ---
        cs, sn = math.cos(psi), math.sin(psi)
        doiralar = [(s + k * cs, d + k * sn) for k in (-c.skuter_yarim_uzunlik, c.skuter_yarim_uzunlik)]
        for x in transport:
            if x.yoq or t < x.paydo:
                continue
            ds = x.s - s
            if abs(ds) > 15:
                continue
            masofa = min(math.hypot(max(abs(px - x.s) - x.uzunlik / 2, 0), max(abs(py - x.d) - x.eni / 2, 0))
                         for px, py in doiralar) - c.skuter_r
            if masofa < 0:
                if x.id not in tegib:
                    tegib.add(x.id)
                    if x.turi in ("mashina", "avtobus"):
                        mash_toq += 1
                    elif x.turi == "velosiped":
                        velo_toq += 1
                    else:
                        tosiq_toq += 1
            else:
                tegib.discard(x.id)
            if abs(ds) < x.uzunlik / 2 + 0.3:
                yon = (x.d - x.eni / 2) - (d + c.skuter_r) if x.d > d else (d - c.skuter_r) - (x.d + x.eni / 2)
                if x.turi in ("mashina", "avtobus") and x.v > 1.0 and x.d > d:
                    yaqin_otish = min(yaqin_otish, yon)
                if x.turi == "toxtagan" and x.d < d and yon < 0.8 and x.id not in eshik_korildi and v > 0.5:
                    eshik_korildi.add(x.id)
                    eshik += 1
        for p in piyodalar:
            if p.yoq or not p.yurmoqda:
                continue
            masofa = min(math.hypot(px - p.s, py - p.d) for px, py in doiralar) - c.skuter_r - 0.3
            if masofa < 0:
                if p.id not in tegib and v > 0.2:
                    odam_toq += 1
                tegib.add(p.id)
            else:
                tegib.discard(p.id)
        if yaqin_otish_b is not None:
            d_ref = asosiy
            for i, x in enumerate(kesuvchi):
                if x.otish != oi or t < x.paydo:
                    continue
                markaz = yaqin_otish_b.boshi + (x.polosa + 0.5) * yaqin_otish_b.yol_kengligi
                if abs(s - markaz) < 0.9 + c.skuter_yarim_uzunlik + c.skuter_r:
                    if abs(x.x - (d - d_ref)) - 2.3 - c.skuter_r < 0:
                        if ("k", i) not in tegib:
                            kes_toq += 1
                            tegib.add(("k", i))
                    else:
                        tegib.discard(("k", i))
        if qadam % 4 == 0:
            for kk, val in zip(iz, (t, s, d, v, yakuniy.holat)):
                iz[kk].append(val)
        t += DT
        qadam += 1
    return YolNatija(sc.nomi, s >= m.uzunlik, t, mash_toq, odam_toq, velo_toq, tosiq_toq, kes_toq, yaqin_otish,
                     eshik, chetga, favq, yordam, ap.otish.operator_sorovlari, (s / t * 3.6) if t > 0 else 0.0,
                     aylanish, orqa_kutish, iz)


def _parkovka_ortida(p, transport):
    return any(x.turi == "toxtagan" and abs(x.s - p.s) < x.uzunlik / 2 + 1.5 for x in transport)


def _ultratovush(transport, piyodalar, s, d, psi, c):
    """Oldinga qaragan ultratovush: skuter yo'nalishi bo'ylab 4 m gacha, o'z eni ichida."""
    cs, sn = math.cos(psi), math.sin(psi)
    yaqin = [(x.s, x.d, x.uzunlik / 2, x.eni / 2) for x in transport if not x.yoq and abs(x.s - s) < 10]
    yaqin += [(p.s, p.d, 0.3, 0.3) for p in piyodalar if not p.yoq and p.yurmoqda and abs(p.s - s) < 10]
    if not yaqin:
        return None
    old = c.skuter_yarim_uzunlik + c.skuter_r
    for k in range(0, 41):
        x = old + 0.1 * k
        px, py = s + x * cs, d + x * sn
        for os_, od, yl, ye in yaqin:
            if abs(px - os_) < yl and abs(py - od) < ye + c.skuter_r * 0.8:
                return 0.1 * k
    return None


def _idm(v, v0, oraliq, dv):
    s_star = IDM_S0 + max(0.0, v * IDM_T + v * dv / (2 * math.sqrt(IDM_A * IDM_B)))
    return IDM_A * (1 - (v / max(v0, 0.1)) ** 4 - (s_star / max(oraliq, 0.1)) ** 2)


def _transport_qadam(transport, piyodalar, kocha, sc, s_sk, d_sk, v_sk, t, rnd):
    c = kocha.c
    skuter = Transport("skuter", s_sk, d_sk, v_sk, uzunlik=1.3, eni=0.7, id=-1)
    harakat = [x for x in transport if not x.yoq and t >= x.paydo]
    for x in harakat:
        if x.turi in ("toxtagan", "tosiq"):
            continue
        if x.s > kocha.m.uzunlik + 20 or x.s < s_sk - 260 or x.s > s_sk + 320:
            x.yoq = True
            continue
        if x.turi in ("mashina", "avtobus") and not kocha.mashina_yoli_mi(min(max(0.0, x.s), kocha.m.uzunlik - 0.01)):
            x.yoq = True  # boshqa ko'chaga ketdi
            continue
        y = kocha.yol(max(0.0, x.s))
        if x.turi == "velosiped":
            _velosiped(x, harakat, skuter, piyodalar, y, c)
            continue
        if x.polosa >= y.yollar:
            x.polosa = y.yollar - 1
        markaz = kocha.polosa_markazi(max(0.0, x.s), x.polosa)
        maqsad = markaz
        v0 = x.v0
        # O'ngga burilish
        burilish_b = None
        if x.burilish:
            burilish_b = next((b for b in kocha.otishlar if -4 < b.boshi - x.s < 45 and b.boshi in kocha.togri_otish), None)
            if burilish_b is not None:
                if burilish_b.boshi - x.s < 25:
                    v0 = min(v0, 18 * KMH)
                if x.s > burilish_b.boshi - 6:
                    maqsad = y.parkovka + 1.0
                if x.s > burilish_b.boshi + 3:
                    x.yoq = True
                    continue
        # Polosamizdagi tor (skuter, velosiped) yoki turgan narsani polosa ichida yoki qo'shni polosaga
        # o'tib quvib o'tish
        nomzodlar = harakat + [skuter]
        p_lo, p_hi = markaz - x.eni / 2 - 0.3, markaz + x.eni / 2 + 0.3
        aylanish, ayl_oraliq = None, 50.0
        quvish = []
        for o in nomzodlar:
            if o is x or o.yoq or not (o.turi in ("skuter", "velosiped") or o.v < 0.5):
                continue
            oraliq = (o.s - o.uzunlik / 2) - (x.s + x.uzunlik / 2)
            olo, ohi = _band(o)
            # Quvib o'tgandan keyin ham uning oldiga 5 m chiqmaguncha polosaga qaytmaydi
            if -o.uzunlik - x.uzunlik - 5.0 < oraliq < 50.0 and olo < p_hi and ohi > p_lo:
                if o is skuter and x.etiborsiz:
                    continue  # haydovchi skuterni ko'rmayapti
                quvish.append((oraliq, o))
                if oraliq < ayl_oraliq:
                    aylanish, ayl_oraliq = o, oraliq
        if aylanish is not None and maqsad == markaz:
            chegara = markaz + (y.yol_kengligi - x.eni) / 2 + 0.4
            if y.yollar == 1:
                chegara += 2.5  # bir polosali yo'lda qarama-qarshi polosaga chiqib quvib o'tadi
            zaxira = 1.2 if aylanish.turi in ("skuter", "velosiped") else 0.5
            kerak = aylanish.d + aylanish.eni / 2 + zaxira + x.eni / 2
            # Ketma-ket turganlarni (masalan avtobus orqasidagi velosipedchi) bir yo'la, eng kengiga qarab aylanadi
            for oraliq, o in quvish:
                zaxira = 1.2 if o.turi in ("skuter", "velosiped") else 0.5
                k = o.d + o.eni / 2 + zaxira + x.eni / 2
                if oraliq < ayl_oraliq + 15.0 and kerak < k <= chegara:
                    kerak = k
            if kerak <= chegara:
                maqsad = max(maqsad, kerak)
            elif x.polosa + 1 < y.yollar and _polosa_bosh(harakat, x, x.polosa + 1):
                x.polosa += 1
                maqsad = kocha.polosa_markazi(max(0.0, x.s), x.polosa)
        # IDM lideri: hozirgi va maqsad yon holat orasida bizga to'g'ri keladigan eng yaqin narsa
        lider, lider_oraliq = None, math.inf
        lo, hi = min(x.d, maqsad) - x.eni / 2 - 0.3, max(x.d, maqsad) + x.eni / 2 + 0.3
        if maqsad > x.d + 0.3:
            lo = x.d - x.eni / 2 - 0.3  # chapga chiqyapmiz: hozirgi joyimiz muhim
            hi = x.d + x.eni / 2 + 0.3
        for o in nomzodlar:
            if o is x or o.yoq:
                continue
            oraliq = (o.s - o.uzunlik / 2) - (x.s + x.uzunlik / 2)
            if oraliq < -0.5 or oraliq > 80:
                continue
            olo, ohi = _band(o)
            yonida = olo < hi and ohi > lo
            if o is skuter:
                if x.etiborsiz and oraliq > max(3.0, (x.v - o.v) * 1.2):
                    continue  # haydovchi telefonga qarayapti: skuterni juda kech ko'radi
                if burilish_b is not None and x.s > burilish_b.boshi - 25 and o.s < burilish_b.oxiri + 3:
                    yonida = yonida or (o.d < x.d and not x.etiborsiz)  # burilishda o'ngdagi skuterga yo'l beradi
            if yonida and oraliq < lider_oraliq:
                lider, lider_oraliq = o, oraliq
        for p in piyodalar:
            if p.yoq or not p.yurmoqda:
                continue
            oraliq = p.s - 0.3 - (x.s + x.uzunlik / 2)
            if -0.5 < oraliq < 40:
                pd_kel = p.d + p.vd * 1.5
                if min(p.d, pd_kel) - 0.5 < hi and max(p.d, pd_kel) + 0.5 > lo and oraliq < lider_oraliq:
                    lider, lider_oraliq = Transport("odam", p.s, p.d, 0.0, uzunlik=0.6, eni=0.6), oraliq
        x.d_maqsad = maqsad
        # Svetofor (biz bilan bir yo'nalishda)
        for i, b in enumerate(kocha.otishlar):
            if not b.svetofor or b.boshi not in kocha.togri_otish:
                continue
            oraliq = b.boshi - 1.0 - (x.s + x.uzunlik / 2)
            if 0 < oraliq < 80 and not svetofor_holati(sc, t, i)[0] and not x.qizilda:
                if x.v * x.v / (2 * oraliq) < 4.0 and oraliq < lider_oraliq:
                    lider, lider_oraliq = Transport("chiziq", b.boshi, 0, 0.0, uzunlik=0.0), oraliq
        if lider is None:
            a = _idm(x.v, v0, 1e9, 0.0)
        else:
            a = _idm(x.v, v0, lider_oraliq, x.v - lider.v)
        a = max(-7.0, min(IDM_A, a))
        x.v = max(0.0, x.v + a * DT)
        x.s += x.v * DT
        # Yonidagi narsaga qarab yon tomonga surilmaydi; turgan joyida yonga siljimaydi
        for o in nomzodlar:
            if o is x or o.yoq or abs(o.s - x.s) > (o.uzunlik + x.uzunlik) / 2 + 0.5:
                continue
            olo, ohi = _band(o)
            if olo >= x.d + x.eni / 2 - 0.05 and maqsad > olo - x.eni / 2 - 0.3:
                maqsad = max(min(x.d, maqsad), olo - x.eni / 2 - 0.3)
            elif ohi <= x.d - x.eni / 2 + 0.05 and maqsad < ohi + x.eni / 2 + 0.3:
                maqsad = min(max(x.d, maqsad), ohi + x.eni / 2 + 0.3)
        dd = maqsad - x.d
        yon_v = min(1.5, 0.4 * x.v + 0.1)
        x.d += max(-yon_v * DT, min(yon_v * DT, dd))


def _polosa_bosh(harakat, x, p):
    # To'xtab qolgan mashinani qo'shni polosadagilar o'tkazib yuboradi (orqadagi kichikroq bo'shliq yetadi)
    orqa = 25 if x.v > 1.0 else 10
    for o in harakat:
        if o is x or o.polosa != p or o.turi not in ("mashina", "avtobus"):
            continue
        if -orqa < o.s - x.s < 15:
            return False
    return True


def _velosiped(x, harakat, skuter, piyodalar, y, c):
    lider_oraliq = math.inf
    lider_v = 0.0
    for o in harakat + [skuter]:
        if o is x or o.yoq:
            continue
        oraliq = (o.s - o.uzunlik / 2) - (x.s + x.uzunlik / 2)
        if -0.3 < oraliq < 20 and abs(o.d - x.d) < (o.eni + x.eni) / 2 + 0.2 and oraliq < lider_oraliq:
            lider_oraliq, lider_v = oraliq, o.v
    a = _idm(x.v, x.v0, lider_oraliq, x.v - lider_v) if lider_oraliq < math.inf else _idm(x.v, x.v0, 1e9, 0)
    x.v = max(0.0, x.v + max(-5.0, min(1.0, a)) * DT)
    x.s += x.v * DT
    # Oldida to'xtab turgan mashina/to'siq bo'lsa, chapdan aylanib o'tadi, keyin chetga qaytadi
    if not hasattr(x, "d0"):
        x.d0 = x.d
    maqsad = x.d0
    for o in harakat:
        if o.turi in ("toxtagan", "tosiq") and -o.uzunlik / 2 - 2.0 < o.s - x.s < o.uzunlik / 2 + 10.0:
            olo, ohi = _band(o)
            if olo < x.d0 + x.eni / 2 + 0.3:
                maqsad = max(maqsad, ohi + x.eni / 2 + 0.5)
    if (maqsad > x.d + 0.05 and skuter.v > 0.5 and -10.0 < skuter.s - x.s < 3.0
            and skuter.d - skuter.eni / 2 < maqsad + x.eni / 2 + 0.5):
        maqsad = x.d  # orqa/yonda skuter kelyapti: chapga chiqmay, uni o'tkazib yuboradi
    for o in harakat + [skuter]:
        # Yonidagi narsaga (turgan skuter, mashina) yon tomondan urilmaydi
        if o is not x and not o.yoq and abs(o.s - x.s) < (o.uzunlik + x.uzunlik) / 2 + 0.5 and o.d > x.d:
            maqsad = min(maqsad, max(x.d, o.d - o.eni / 2 - x.eni / 2 - 0.3))
    yon = 0.4 * DT
    x.d += max(-yon, min(yon, maqsad - x.d))
    if x.v < 0.5 and maqsad > x.d + 0.05:
        x.v = 0.5  # sekin yurib chetga chiqadi


def _piyoda_qadam(piyodalar, transport, kocha, s_sk, d_sk, v_sk, t):
    for p in piyodalar:
        if p.yoq:
            continue
        y = kocha.yol(max(0.0, p.s))
        kenglik = y.parkovka + y.velo + y.yollar * y.yol_kengligi
        if not p.yurmoqda:
            if s_sk < p.tetik:
                continue
            if p.etiborli:
                # Yaqinlashib kelayotgan transport 4 s ichida yetib keladigan bo'lsa, kutadi
                xavf = v_sk > 0.5 and 0 < p.s - s_sk < v_sk * 4 + 3
                for x in transport:
                    if not x.yoq and x.turi in ("mashina", "avtobus", "velosiped") and x.v > 0.5 \
                            and 0 < p.s - x.s < x.v * 4 + 5:
                        xavf = True
                if xavf:
                    continue
            p.yurmoqda = True
        yangi = p.d + p.vd * DT
        # Oldida turgan transportga kirib ketmaydi
        tosiq = abs(p.s - s_sk) < 1.0 and abs(yangi - d_sk) < 0.7 and v_sk < 0.3
        if tosiq:
            p.s -= 1.0 * DT  # to'xtab turgan skuterni orqasidan aylanib o'tadi
        for x in transport:
            if x.yoq or x.turi == "toxtagan":
                continue
            if abs(p.s - x.s) < x.uzunlik / 2 + 0.4 and abs(yangi - x.d) < x.eni / 2 + 0.4 and x.v < 0.5:
                tosiq = True
        if not tosiq:
            p.d = yangi
        if p.d > kenglik + 1.0:
            p.yoq = True


def _kesuvchi_qadam(kesuvchi, otishlar, sc, s_sk, v_sk, t):
    for mm in kesuvchi:
        if t < mm.paydo:
            continue
        b = otishlar[mm.otish]
        if b.oxiri < s_sk - 20:
            continue  # o'tib ketgan chorraha: endi ahamiyati yo'q
        oxirgi = getattr(mm, "_t", None)
        if b.boshi - s_sk > 80:
            # Uzoqdagi chorraha: skuter yo'q, mashinalar to'g'ri yuradi. Yaqinlashganda bir yo'la suramiz (tezroq).
            if oxirgi is None:
                mm._t = max(mm.paydo, t - DT)
            continue
        if oxirgi is not None:
            mm.x += mm.vx * (t - DT - oxirgi)
            mm._t = None
        if b.svetofor:
            toxtash = svetofor_holati(sc, t, mm.otish)[0] and not mm.qizilda_otadi  # biz uchun yashil
        else:
            toxtash = mm.yol_beradi and b.boshi - 3.0 < s_sk < b.oxiri + 0.5 and (v_sk < 0.3 or s_sk > b.boshi - 1.0)
        yaqinlashmoqda = mm.x * mm.vx < 0
        tox_chiziq = abs(mm.x) - 2.3 - 4.5
        if toxtash and yaqinlashmoqda and 0 < tox_chiziq:
            kerak = mm.vx ** 2 / (2 * max(0.1, tox_chiziq))
            if kerak < 5.0:
                tez = abs(mm.vx)
                tez = max(0.0, tez - max(kerak, 2.5) * DT) if tox_chiziq > 0.3 else 0.0
                mm.vx = math.copysign(tez, mm.vx) if tez > 0 else 0.0
                mm.x += mm.vx * DT
                continue
        if not toxtash and abs(mm.vx) < 0.1:
            mm.vx = (1 if mm.polosa % 2 == 0 else -1) * 11.0
        mm.x += mm.vx * DT


# ---------------------------------------------------------------- tasodifiy ko'chalar

def tasodifiy_yol_bolagi(rnd, uzunlik):
    tur = rnd.random()
    yollar = rnd.choice((1, 2, 2, 3))
    if tur < 0.3:
        return Bolak("yol", uzunlik, yollar=yollar, velo=1.5)
    if tur < 0.6:
        return Bolak("yol", uzunlik, yollar=yollar, parkovka=2.2)
    return Bolak("yol", uzunlik, yollar=yollar)


def tasodifiy_kocha(urug, rejim="yarim", kamera_xato=False):
    """Tasodifiy ko'cha marshruti: 2-4 ta yo'l bo'lagi, orasida o'ngga, to'g'ri yoki chapga (2 bosqichda) o'tish."""
    rnd = random.Random(urug * 104729 + 7)
    bolaklar = [tasodifiy_yol_bolagi(rnd, rnd.uniform(120, 260))]
    for _ in range(rnd.randint(1, 3)):
        oldingi = bolaklar[-1]
        tur = rnd.choice(("ong", "togri", "togri", "chap"))
        if tur == "ong":
            bolaklar.append(Bolak("burilish", 6.0 * math.pi / 2, egrilik=-1 / 6.0))
        elif tur == "togri":
            p = rnd.choice((2, 4))
            bolaklar.append(Bolak("otish", p * 3.5, yollar=p, svetofor=rnd.random() < 0.7))
        else:
            # Chapga: ko'ndalang ko'chani to'g'ri kesib o'tamiz, burchakda buriliib, o'z ko'chamizni kesib o'tamiz
            p = rnd.choice((2, 4))
            svet = rnd.random() < 0.7
            bolaklar.append(Bolak("otish", p * 3.5, yollar=p, svetofor=svet))
            r = yol_tartibi(oldingi, YolSozlamalari())[1] + 3.5  # burchakdagi kutish joyi: skuter aylana oladigan radius
            bolaklar.append(Bolak("burilish", r * math.pi / 2, egrilik=1 / r))
            p2 = min(4, oldingi.yollar * 2)
            bolaklar.append(Bolak("otish", p2 * 3.5, yollar=p2, svetofor=svet))
        bolaklar.append(tasodifiy_yol_bolagi(rnd, rnd.uniform(100, 220)))
    return kocha_toldir(Marshrut(bolaklar), rnd, f"kocha-{urug}", rejim, kamera_xato, urug)


def kocha_toldir(marshrut, rnd, nomi, rejim="yarim", kamera_xato=False, urug=0):
    """Berilgan marshrut (masalan xaritadan tuzilgan) ko'chalarini tasodifiy transport, odam va oqim bilan to'ldiradi."""
    transport, piyodalar = [], []
    keyingi = 1
    for b in marshrut.bolaklar:
        if b.turi != "yol":
            continue
        x = b.boshi + rnd.uniform(5, 30) + (30 if b.boshi == 0 else 0)
        while x < b.oxiri - 15:
            if b.parkovka > 0:
                # Parkovka: mashinalar qatori, orasida bo'sh joylar
                if rnd.random() < 0.7:
                    transport.append(Transport("toxtagan", x, b.parkovka / 2, uzunlik=4.5, eni=1.8, polosa=-1, id=keyingi))
                    keyingi += 1
                x += rnd.uniform(5.5, 9.0)
                continue
            r = rnd.random()
            # Qoidaga ko'ra chorraha / o'tish joyiga 5 m dan yaqin to'xtash mumkin emas
            yarim = 6.0 if 0.25 <= r < 0.33 else 2.25
            x_toxtash = max(x, b.boshi + 5.0 + yarim)
            if r < 0.33 and x_toxtash + yarim > b.oxiri - 5.0:
                r = 0.4  # bu yerda to'xtab bo'lmaydi: o'rniga kichik to'siq
            if r < 0.25:
                transport.append(Transport("toxtagan", x_toxtash, b.velo + 1.0 if b.velo else 1.0, uzunlik=4.5, eni=1.8,
                                           polosa=-1, id=keyingi))
            elif r < 0.33:
                transport.append(Transport("avtobus", x_toxtash, b.velo + 1.35, 0.0, 0.0, 12.0, 2.5, -1, id=keyingi))
                transport[-1].turi = "toxtagan"
            elif r < 0.55:
                transport.append(Transport("tosiq", x, b.velo / 2 + rnd.uniform(0.3, 1.0) if b.velo else rnd.uniform(0.4, 1.2),
                                           uzunlik=0.6, eni=0.6, polosa=-1, id=keyingi))
            else:
                v0 = rnd.uniform(10, 16) * KMH
                transport.append(Transport("velosiped", x, (b.parkovka + b.velo / 2) if b.velo else 0.7, v0, v0,
                                           1.8, 0.6, -1, id=keyingi))
            keyingi += 1
            x += rnd.uniform(30, 90)
        # Yo'lni kesib o'tuvchi odamlar
        for _ in range(rnd.randint(0, 3) if b.uzunlik > 60 else 0):
            ps = rnd.uniform(b.boshi + 30, b.oxiri - 10)
            piyodalar.append(Piyoda(ps, ps - rnd.uniform(8, 40), vd=rnd.uniform(1.1, 1.6), etiborli=rnd.random() < 0.75))
    kesuvchi = []
    vaqt_chegarasi = max(900, marshrut.uzunlik)
    for i, b in enumerate(marshrut.otishlar()):
        # Xaritadan oqim ma'lum bo'lsa (ko'cha turi bo'yicha), shu atrofida; aks holda katta ko'chadek
        intensivlik = b.oqim * rnd.uniform(0.6, 1.5) if b.oqim > 0 else rnd.uniform(0.04, 0.16) / b.yollar
        kesuvchi += mashina_oqimi(rnd, i, b.yollar, intensivlik, vaqt_chegarasi,
                                  qizilda_ehtimol=0.03 if b.svetofor else 0.0, yol_berish=0.0 if b.svetofor else 0.3)
    kam = []
    if kamera_xato:
        a = rnd.uniform(15, 60)
        kam = [(a, a + rnd.uniform(0.5, 3))]
    return YolSsenariy(nomi, marshrut, transport, piyodalar, oqim=rnd.uniform(0.03, 0.15),
                       kesuvchi=kesuvchi, svetofor_siljish=[rnd.uniform(0, 50) for _ in marshrut.otishlar()],
                       kamera_ochadi=kam, vaqt_chegarasi=vaqt_chegarasi, rejim=rejim, urug=urug)
