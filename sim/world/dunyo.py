"""Virtual shahar: trotuarlar, burilishlar, yo'l o'tish joylari, piyodalar, mashinalar.

Bu fayl faqat simulyator. Skuterning o'z dasturi `autopilot/` papkasida.
"""

from dataclasses import dataclass, field
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from autopilot.haydash import Sozlamalar, Obyekt, KMH, boshqaruv_burchagi  # noqa: E402
from autopilot.marshrut import Marshrut, Bolak  # noqa: E402
from autopilot.otish import Mashina as KorilganMashina  # noqa: E402
from autopilot.avtopilot import Avtopilot  # noqa: E402

DT = 0.05
YORDAM_KUTISH = 30.0  # shuncha soniyada 1 m ham siljimasa operatordan yordam so'raydi
OPERATOR_KECHIKISHI = 2.0  # operator so'rovga shuncha soniyada javob beradi
MASHINA_KORISH = 120.0  # kamera mashinani shu masofadan ko'radi (m)


@dataclass
class Jism:
    s: float
    d: float
    vs: float = 0.0
    vd: float = 0.0
    r: float = 0.3
    turi: str = "odam"          # "odam" yoki "to'siq"
    yashirin_gacha: float = 0.0  # shu vaqtgacha kamera ko'rmaydi (masalan, mashina orqasida)
    chetlashadi: bool = True     # odam skuterni ko'rib yon tomonga o'tadimi
    oraliq: tuple = None         # (boshi, oxiri): odam faqat shu trotuar bo'lagida yuradi, keyin burilib ketadi


@dataclass
class YolMashinasi:
    """Simulyatordagi haqiqiy mashina. x: o'tish joyi markazidan yo'l bo'ylab (m)."""
    otish: int          # qaysi o'tish joyi (marshrutdagi tartib raqami)
    polosa: int
    x: float
    vx: float
    paydo: float = 0.0  # shu vaqtdan boshlab yo'lda
    qizilda_otadi: bool = False
    yol_beradi: bool = False  # svetoforsiz o'tish joyida kutayotgan piyodaga yo'l beradi


@dataclass
class Ssenariy:
    nomi: str
    uzunlik: float = 200.0
    jismlar: list = field(default_factory=list)
    kamera_ochadi: list = field(default_factory=list)  # [(boshlanish, tugash), ...]
    vaqt_chegarasi: float = 400.0
    urug: int = 0
    marshrut: Marshrut = None
    mashinalar: list = field(default_factory=list)
    svetofor_davri: tuple = (20.0, 40.0)  # (piyodaga yashil, qizil) soniya
    svetofor_siljish: float = 0.0
    rejim: str = "yarim"


@dataclass
class Natija:
    nomi: str
    yetib_keldi: bool
    vaqt: float
    toqnashuv: int          # skuter harakatda bo'lganda tegish (asosiy xato)
    tegildi_turganda: int   # skuter turganda odam tegdi
    eng_kam_masofa: float
    favqulodda: int
    kamera_xato: int
    yordam_sorardi: bool    # qotib qoldi: haqiqiy hayotda operator boshqaruvni oladi
    ortacha_tezlik_kmh: float
    iz: dict
    mashina_toqnashuv: int = 0
    mashinagacha_eng_kam: float = math.inf   # skuter yo'lda bo'lganda eng yaqin mashina (m)
    chetga_chiqdi: int = 0                   # trotuar chetidan chiqib ketish
    operator_sorovlari: int = 0
    burilish_max_tezlik: float = 0.0         # burilishdagi eng katta tezlik (km/soat)


def svetofor_holati(sc, t):
    yashil, qizil = sc.svetofor_davri
    f = (t + sc.svetofor_siljish) % (yashil + qizil)
    return (True, yashil - f) if f < yashil else (False, yashil + qizil - f)


def kamera(jismlar, sk_s, sk_d, t, rnd, ishlayapti):
    """Kamera o'rnini bosuvchi model: 12 m ichida, shovqin va ba'zan o'tkazib yuborish bilan."""
    if not ishlayapti:
        return None
    natija = []
    for j in jismlar:
        if t < j.yashirin_gacha:
            continue
        m = math.hypot(j.s - sk_s, j.d - sk_d)
        if m > 12:
            continue
        if rnd.random() < 0.05:  # 5% kadrlarda ko'rmay qoladi
            continue
        xato = 0.05 + 0.02 * m
        natija.append(Obyekt(j.s + rnd.gauss(0, xato), j.d + rnd.gauss(0, xato),
                             j.vs + rnd.gauss(0, 0.1), j.vd + rnd.gauss(0, 0.1), j.r + 0.05, j.turi))
    return natija


def mashina_kamera(mashinalar, otish_tartibi, sk_s, b, t, rnd, ishlayapti):
    """Yon kameralar: o'tish joyiga yaqin bo'lganda mashinalarni 120 m gacha ko'radi."""
    if not ishlayapti or b is None or abs(sk_s - b.boshi) > 15:
        return []
    natija = []
    for m in mashinalar:
        if m.otish != otish_tartibi or t < m.paydo or abs(m.x) > MASHINA_KORISH:
            continue
        if rnd.random() < 0.05:
            continue
        xato = 0.3 + 0.01 * abs(m.x)
        natija.append(KorilganMashina(m.polosa, m.x + rnd.gauss(0, xato), m.vx + rnd.gauss(0, 0.3)))
    return natija


def ultratovush(jismlar, sk_s, sk_d, psi, c):
    """Skuter yo'lida (oldinda, o'z kengligi ichida) eng yaqin narsagacha masofa, 2,5 m gacha."""
    old_s = sk_s + c.skuter_yarim_uzunlik * math.cos(psi)
    old_d = sk_d + c.skuter_yarim_uzunlik * math.sin(psi)
    eng = None
    for j in jismlar:
        ds, dd = j.s - old_s, j.d - old_d
        oldinga = ds * math.cos(psi) + dd * math.sin(psi)
        yonga = -ds * math.sin(psi) + dd * math.cos(psi)
        if oldinga < -0.1 or abs(yonga) > c.skuter_r + j.r + 0.1:
            continue
        m = math.hypot(ds, dd) - j.r - c.skuter_r
        if m > 2.5:
            continue
        eng = m if eng is None else min(eng, m)
    return eng


def ishga_tushir(sc: Ssenariy, c: Sozlamalar = None):
    c = c or Sozlamalar()
    rnd = random.Random(sc.urug)
    marshrut = sc.marshrut or Marshrut.togri(sc.uzunlik)
    otishlar = marshrut.otishlar()
    ap = Avtopilot(marshrut, sc.rejim, c, YORDAM_KUTISH)
    s, d, psi, v = 0.0, 0.0, 0.0, 0.0
    t = 0.0
    buyruq = None
    toqnashuv = tegildi = favq = kam_xato = mashina_toq = chetga = 0
    tegib_turibdi, mashina_tegib = set(), set()
    eng_kam, mashina_eng_kam, burilish_max = math.inf, math.inf, 0.0
    chetda = False
    oldingi_holat = None
    iz = {k: [] for k in ("t", "s", "d", "v", "holat")}
    jismlar = [Jism(**vars(j)) for j in sc.jismlar]
    mashinalar = [YolMashinasi(**vars(m)) for m in sc.mashinalar]
    operator_javob_vaqti, operator_javobi = None, None
    qadam = 0
    yordam = False
    while t < sc.vaqt_chegarasi and s < marshrut.uzunlik:
        if ap.yordam_kerakmi(t, s):
            yordam = True
            break
        b_hozir = marshrut.bolak(s)
        yaqin_otish = next((b for b in otishlar if b.boshi - 15 < s < b.oxiri + 2), None)
        otish_tartibi = otishlar.index(yaqin_otish) if yaqin_otish else -1
        svet = svetofor_holati(sc, t) if yaqin_otish is not None and yaqin_otish.svetofor else None
        # --- Datchiklar va skuter dasturi (10 Hz) ---
        if qadam % 2 == 0:
            ishlaydi = not any(a <= t < b for a, b in sc.kamera_ochadi)
            k = kamera(jismlar, s, d, t, rnd, ishlaydi)
            km = mashina_kamera(mashinalar, otish_tartibi, s, yaqin_otish, t, rnd, ishlaydi)
            javob = None
            if operator_javob_vaqti is not None and t >= operator_javob_vaqti:
                javob, operator_javob_vaqti = operator_javobi, None
            buyruq = ap.rejalash(t, s, d, v, k, km, svet, javob)
            # Operator (simulyatsiya): so'rov kelsa, 2 s dan keyin haqiqiy vaziyatga qarab javob beradi
            if ap.operator_sorovi and operator_javob_vaqti is None and javob is None:
                operator_javob_vaqti = t + OPERATOR_KECHIKISHI
                haqiqiy = [KorilganMashina(m.polosa, m.x, m.vx) for m in mashinalar
                           if m.otish == otish_tartibi and t >= m.paydo]
                kelajak = [KorilganMashina(m.polosa, m.x + m.vx * OPERATOR_KECHIKISHI, m.vx) for m in haqiqiy]
                operator_javobi = (ap.otish.bosh_joy_bor(yaqin_otish, s, 0.0, haqiqiy, bufer=1.5)
                                   and ap.otish.bosh_joy_bor(yaqin_otish, s, 0.0, kelajak, bufer=1.5))
        uz = ultratovush(jismlar, s, d, psi, c)
        yakuniy = ap.xavfsizlik(buyruq, v, uz, t)
        if yakuniy.holat != oldingi_holat:
            if yakuniy.holat == "favqulodda":
                favq += 1
            if yakuniy.holat == "kamera_xato":
                kam_xato += 1
            oldingi_holat = yakuniy.holat
        # --- Skuter harakati (marshrut koordinatalarida, egrilik bilan) ---
        if yakuniy.tezlik > v:
            v = min(yakuniy.tezlik, v + c.tezlanish * DT)
        else:
            v = max(yakuniy.tezlik, v - yakuniy.tormoz * DT)
        kappa = marshrut.egrilik(s)
        s_tezlik = v * math.cos(psi) / max(0.3, 1 - kappa * d)
        psi_kerak = boshqaruv_burchagi(d, yakuniy.d_maqsad, v)
        max_omega = (v / 1.05) * math.tan(math.radians(20)) if v > 0.05 else 0.0
        omega = (psi_kerak - psi) * 3 + kappa * s_tezlik
        omega = max(-max_omega, min(max_omega, omega))
        psi += (omega - kappa * s_tezlik) * DT
        s += s_tezlik * DT
        d += v * math.sin(psi) * DT
        if b_hozir.turi == "burilish":
            burilish_max = max(burilish_max, v * 3.6)
        chegara = c.yarim_kenglik - c.skuter_r + 0.05
        if abs(d) > chegara:
            if not chetda:
                chetga += 1
            chetda = True
            d = max(-chegara, min(chegara, d))
        else:
            chetda = False
        # --- Piyodalar ---
        for j in jismlar:
            if j.turi != "odam":
                continue
            if t < j.yashirin_gacha and abs(j.vd) > 0:
                continue  # mashina orqasida kutib turibdi
            yon_v = j.vd
            # Odamlar turgan skuterni doim aylanib o'tadi; harakatdagini faqat e'tiborlilar
            if j.chetlashadi or v < 0.3:
                oldinda = (s - j.s) * (1 if j.vs >= 0 else -1)
                if 0 < oldinda < 3 and abs(d - j.d) < 1.0:
                    yon_v = 0.6 if j.d >= d else -0.6
            j.s += j.vs * DT
            j.d += yon_v * DT
            if j.oraliq and not (j.oraliq[0] <= j.s <= j.oraliq[1]):
                j.s = -1e6  # trotuar bo'lagidan chiqib, boshqa ko'chaga burilib ketdi
            if abs(j.vd) < 1e-6:
                j.d = max(-c.yarim_kenglik + j.r, min(c.yarim_kenglik - j.r, j.d))
        # --- Mashinalar ---
        for m in mashinalar:
            if t < m.paydo:
                continue
            b = otishlar[m.otish]
            if b.svetofor:
                toxtash = svetofor_holati(sc, t)[0] and not m.qizilda_otadi
            else:
                # Ba'zi haydovchilar o'tish joyi oldida kutayotgan (yoki o'tayotgan) piyodaga yo'l beradi
                toxtash = m.yol_beradi and b.boshi - 3.0 < s < b.oxiri + 0.5 and (v < 0.3 or s > b.boshi - 1.0)
            yaqinlashmoqda = m.x * m.vx < 0
            tox_chiziq = abs(m.x) - 2.3 - 4.5  # to'xtash chizig'i: o'tish joyi markazidan 4,5 m
            if toxtash and yaqinlashmoqda and 0 < tox_chiziq:
                kerak = m.vx ** 2 / (2 * max(0.1, tox_chiziq))
                if kerak < 5.0:  # qulay to'xtay oladi: to'xtaydi
                    tez = abs(m.vx)
                    tez = max(0.0, tez - max(kerak, 2.5) * DT) if tox_chiziq > 0.3 else 0.0
                    m.vx = math.copysign(tez, m.vx) if tez > 0 else 0.0
                    m.x += m.vx * DT
                    continue
            if not toxtash and abs(m.vx) < 0.1:
                m.vx = (1 if m.polosa % 2 == 0 else -1) * 11.0  # yashil yondi / piyoda o'tdi: yo'lga tushadi
            m.x += m.vx * DT
        # --- To'qnashuvni tekshirish ---
        for i, j in enumerate(jismlar):
            mm = min(math.hypot(s + k * math.cos(psi) - j.s, d + k * math.sin(psi) - j.d)
                     for k in (-c.skuter_yarim_uzunlik, c.skuter_yarim_uzunlik)) - c.skuter_r - j.r
            if j.turi == "odam" or mm < 3:
                eng_kam = min(eng_kam, mm)
            if mm < 0:
                if i not in tegib_turibdi:
                    if v > 0.2:
                        toqnashuv += 1
                    else:
                        tegildi += 1
                    tegib_turibdi.add(i)
            else:
                tegib_turibdi.discard(i)
        if yaqin_otish is not None:
            for i, m in enumerate(mashinalar):
                if m.otish != otish_tartibi or t < m.paydo:
                    continue
                polosa_markazi = yaqin_otish.boshi + (m.polosa + 0.5) * yaqin_otish.yol_kengligi
                # Skuter shu polosa ichidami (mashina eni 1,8 m)
                if abs(s - polosa_markazi) < 0.9 + c.skuter_yarim_uzunlik + c.skuter_r:
                    oraliq = abs(m.x - d) - 2.3 - c.skuter_r
                    mashina_eng_kam = min(mashina_eng_kam, oraliq)
                    if oraliq < 0:
                        if i not in mashina_tegib:
                            mashina_toq += 1
                            mashina_tegib.add(i)
                    else:
                        mashina_tegib.discard(i)
        if qadam % 4 == 0:
            for kk, val in zip(iz, (t, s, d, v, yakuniy.holat)):
                iz[kk].append(val)
        t += DT
        qadam += 1
    yetdi = s >= marshrut.uzunlik
    return Natija(sc.nomi, yetdi, t, toqnashuv, tegildi, eng_kam, favq, kam_xato, yordam,
                  (s / t * 3.6) if t > 0 else 0.0, iz, mashina_toq, mashina_eng_kam, chetga,
                  ap.otish.operator_sorovlari, burilish_max)


def tasodifiy_jismlar(rnd, bolaklar, odamlar, tosiqlar):
    """Faqat trotuar bo'laklariga: ustunlar, daraxtlar, turli tomonga yuruvchi va kesib o'tuvchi odamlar."""
    trotuar = [b for b in bolaklar if b.turi == "trotuar" and b.uzunlik > 15]
    jismlar = []

    # Bitta to'g'ri trotuarda odamlar marshrut bo'ylab erkin yuradi (1-bosqich sinovlari bilan bir xil)
    yakka = len(bolaklar) == 1

    def joy(chet=5, siljish=0.0):
        b = rnd.choice(trotuar)
        oraliq = None if yakka else (b.boshi, b.oxiri)
        return rnd.uniform(b.boshi + chet, b.oxiri - chet) + (siljish if yakka else 0.0), oraliq

    for _ in range(tosiqlar):
        tomon = rnd.choice((-1, 1))
        jismlar.append(Jism(joy()[0], tomon * rnd.uniform(0.6, 1.3), r=rnd.uniform(0.15, 0.4), turi="to'siq"))
    for _ in range(odamlar):
        tur = rnd.random()
        if tur < 0.45:      # qarshidan keluvchi
            s0, oraliq = joy(siljish=20)
            jismlar.append(Jism(s0, rnd.uniform(-1.1, 1.1), vs=-rnd.uniform(0.9, 1.5),
                                chetlashadi=rnd.random() < 0.7, oraliq=oraliq))
        elif tur < 0.8:     # bir tomonga yuruvchi (skuter quvib o'tadi)
            s0, oraliq = joy()
            jismlar.append(Jism(s0, rnd.uniform(-1.1, 1.1), vs=rnd.uniform(0.6, 1.2), chetlashadi=False,
                                oraliq=oraliq))
        else:               # trotuarni kesib o'tuvchi
            yo = rnd.choice((-1, 1))
            jismlar.append(Jism(joy()[0], -yo * 2.5, vd=yo * rnd.uniform(0.8, 1.4), chetlashadi=False))
    return jismlar


def tasodifiy_ssenariy(urug, uzunlik=200.0, odamlar=12, tosiqlar=10, kamera_xato=False):
    """Tasodifiy to'g'ri trotuar (1-bosqich sinovlari)."""
    rnd = random.Random(urug)
    m = Marshrut.togri(uzunlik)
    jismlar = tasodifiy_jismlar(rnd, m.bolaklar, odamlar, tosiqlar)
    kam = []
    if kamera_xato:
        a = rnd.uniform(20, 80)
        kam = [(a, a + rnd.uniform(1, 5))]
    return Ssenariy(f"tasodifiy-{urug}", uzunlik, jismlar, kam, urug=urug, marshrut=m)


def mashina_oqimi(rnd, otish_tartibi, polosalar, intensivlik, davomiylik, qizilda_ehtimol=0.0, yol_berish=0.0):
    """Har polosada Puasson oqimi: intensivlik = mashina/soniya."""
    mashinalar = []
    for p in range(polosalar):
        yo = 1 if p % 2 == 0 else -1  # juft polosa +x tomonga, toq polosa -x tomonga
        t = -rnd.expovariate(intensivlik) * 3
        while t < davomiylik:
            t += rnd.expovariate(intensivlik)
            tez = rnd.uniform(30, 60) * KMH
            x0 = -yo * (MASHINA_KORISH + 40)
            # Boshlang'ich vaqti manfiy bo'lsa, mashina allaqachon yo'lda
            if t < 0:
                x0 += yo * tez * (-t)
            mashinalar.append(YolMashinasi(otish_tartibi, p, x0, yo * tez, max(0.0, t),
                                           rnd.random() < qizilda_ehtimol, rnd.random() < yol_berish))
    return mashinalar


def tasodifiy_shahar(urug, rejim="yarim", kamera_xato=False):
    """Tasodifiy shahar marshruti: trotuarlar, 2-4 ta burilish, 1-2 ta yo'l o'tish joyi."""
    rnd = random.Random(urug * 7919 + 1)
    bolaklar = []
    otishlar_soni = rnd.choice((1, 1, 2))
    burilishlar = rnd.randint(2, 4)
    turlar = ["burilish"] * burilishlar + ["otish"] * otishlar_soni
    rnd.shuffle(turlar)
    for tur in turlar:
        bolaklar.append(Bolak("trotuar", rnd.uniform(25, 60)))
        if tur == "burilish":
            r = rnd.uniform(3.0, 5.0)
            bolaklar.append(Bolak("burilish", r * math.pi / 2, egrilik=rnd.choice((-1, 1)) / r))
        else:
            polosa = rnd.choice((2, 2, 4))
            bolaklar.append(Bolak("otish", polosa * 3.5, yollar=polosa, svetofor=rnd.random() < 0.5))
    bolaklar.append(Bolak("trotuar", rnd.uniform(25, 50)))
    m = Marshrut(bolaklar)
    jismlar = tasodifiy_jismlar(rnd, m.bolaklar, odamlar=10, tosiqlar=8)
    mashinalar = []
    for i, b in enumerate(m.otishlar()):
        # Polosa ko'p bo'lsa, har biridagi oqim siyrakroq (jami oqim taxminan bir xil)
        mashinalar += mashina_oqimi(rnd, i, b.yollar, rnd.uniform(0.04, 0.20) / b.yollar, 900,
                                    qizilda_ehtimol=0.05 if b.svetofor else 0.0,
                                    yol_berish=0.0 if b.svetofor else 0.3)
    kam = []
    if kamera_xato:
        a = rnd.uniform(20, 80)
        kam = [(a, a + rnd.uniform(1, 5))]
    return Ssenariy(f"shahar-{urug}", m.uzunlik, jismlar, kam, vaqt_chegarasi=900, urug=urug,
                    marshrut=m, mashinalar=mashinalar, svetofor_siljish=rnd.uniform(0, 60), rejim=rejim)
