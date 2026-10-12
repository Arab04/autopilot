"""Virtual trotuar: skuter, piyodalar, to'siqlar, datchiklar.

Bu fayl faqat simulyator. Skuterning o'z dasturi `autopilot/haydash.py` da.
"""

from dataclasses import dataclass, field
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from autopilot.haydash import (Sozlamalar, Obyekt, Kuzatuvchi, Rejalovchi, XavfsizlikQatlami, KMH,
                               boshqaruv_burchagi, YordamNazoratchisi)  # noqa: E402

DT = 0.05
YORDAM_KUTISH = 30.0  # shuncha soniyada 1 m ham siljimasa operatordan yordam so'raydi


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


@dataclass
class Ssenariy:
    nomi: str
    uzunlik: float = 200.0
    jismlar: list = field(default_factory=list)
    kamera_ochadi: list = field(default_factory=list)  # [(boshlanish, tugash), ...]
    vaqt_chegarasi: float = 400.0
    urug: int = 0


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
    yordam_sorardi: bool    # 30 s qotib qoldi: haqiqiy hayotda operator boshqaruvni oladi
    ortacha_tezlik_kmh: float
    iz: dict


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


def ultratovush(jismlar, sk_s, sk_d, psi, c):
    """Skuter yo'lida (oldinda, o'z kengligi ichida) eng yaqin narsagacha masofa, 2,5 m gacha.

    Soddalashtirish: 8 ta datchik birgalikda narsaning taxminiy yo'nalishini beradi deb olinadi.
    """
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
    rej, xav, kuz = Rejalovchi(c), XavfsizlikQatlami(c), Kuzatuvchi()
    s, d, psi, v = 0.0, 0.0, 0.0, 0.0
    t = 0.0
    oxirgi_kamera, obyektlar = 0.0, []
    buyruq = None
    toqnashuv = tegildi = favq = kam_xato = 0
    tegib_turibdi = set()
    eng_kam = math.inf
    oldingi_holat = None
    iz = {k: [] for k in ("t", "s", "d", "v", "holat")}
    jismlar = [Jism(**vars(j)) for j in sc.jismlar]
    qadam = 0
    nazorat = YordamNazoratchisi(YORDAM_KUTISH)
    yordam = False
    while t < sc.vaqt_chegarasi and s < sc.uzunlik:
        if nazorat.tekshir(t, s):
            yordam = True
            break
        # --- Datchiklar (kamera 10 Hz) ---
        if qadam % 2 == 0:
            ishlaydi = not any(a <= t < b for a, b in sc.kamera_ochadi)
            k = kamera(jismlar, s, d, t, rnd, ishlaydi)
            if k is not None:
                obyektlar, oxirgi_kamera = kuz.yangila(t, k), t
            # --- Skuter dasturi ---
            buyruq = rej.reja(s, d, v, obyektlar)
        uz = ultratovush(jismlar, s, d, psi, c)
        yakuniy = xav.tekshir(buyruq, v, uz, t - oxirgi_kamera)
        if yakuniy.holat != oldingi_holat:
            if yakuniy.holat == "favqulodda":
                favq += 1
            if yakuniy.holat == "kamera_xato":
                kam_xato += 1
            oldingi_holat = yakuniy.holat
        # --- Skuter harakati ---
        if yakuniy.tezlik > v:
            v = min(yakuniy.tezlik, v + c.tezlanish * DT)
        else:
            v = max(yakuniy.tezlik, v - yakuniy.tormoz * DT)
        psi_kerak = boshqaruv_burchagi(d, yakuniy.d_maqsad, v)
        max_burilish = (v / 1.05) * math.tan(math.radians(20)) if v > 0.05 else 0.0
        psi += max(-max_burilish * DT, min(max_burilish * DT, (psi_kerak - psi) * 3 * DT))
        s += v * math.cos(psi) * DT
        d += v * math.sin(psi) * DT
        d = max(-c.yarim_kenglik + c.skuter_r, min(c.yarim_kenglik - c.skuter_r, d))
        # --- Piyodalar ---
        for i, j in enumerate(jismlar):
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
            if abs(j.vd) < 1e-6:
                j.d = max(-c.yarim_kenglik + j.r, min(c.yarim_kenglik - j.r, j.d))
        # --- To'qnashuvni tekshirish ---
        for i, j in enumerate(jismlar):
            m = min(math.hypot(s + k * math.cos(psi) - j.s, d + k * math.sin(psi) - j.d)
                    for k in (-c.skuter_yarim_uzunlik, c.skuter_yarim_uzunlik)) - c.skuter_r - j.r
            if j.turi == "odam" or m < 3:
                eng_kam = min(eng_kam, m)
            if m < 0:
                if i not in tegib_turibdi:
                    if v > 0.2:
                        toqnashuv += 1
                    else:
                        tegildi += 1
                    tegib_turibdi.add(i)
            else:
                tegib_turibdi.discard(i)
        if qadam % 4 == 0:
            for kk, val in zip(iz, (t, s, d, v, yakuniy.holat)):
                iz[kk].append(val)
        t += DT
        qadam += 1
    yetdi = s >= sc.uzunlik
    return Natija(sc.nomi, yetdi, t, toqnashuv, tegildi, eng_kam, favq, kam_xato, yordam,
                  (s / t * 3.6) if t > 0 else 0.0, iz)


def tasodifiy_ssenariy(urug, uzunlik=200.0, odamlar=12, tosiqlar=10, kamera_xato=False):
    """Tasodifiy trotuar: ustunlar, daraxtlar, turli tomonga yuruvchi va kesib o'tuvchi odamlar."""
    rnd = random.Random(urug)
    jismlar = []
    for _ in range(tosiqlar):
        # To'siqlar trotuar chetiga yaqinroq, o'tish uchun joy qoladi
        tomon = rnd.choice((-1, 1))
        jismlar.append(Jism(rnd.uniform(10, uzunlik - 5), tomon * rnd.uniform(0.6, 1.3), r=rnd.uniform(0.15, 0.4),
                            turi="to'siq"))
    for _ in range(odamlar):
        tur = rnd.random()
        if tur < 0.45:      # qarshidan keluvchi
            jismlar.append(Jism(rnd.uniform(20, uzunlik + 60), rnd.uniform(-1.1, 1.1),
                                vs=-rnd.uniform(0.9, 1.5), chetlashadi=rnd.random() < 0.7))
        elif tur < 0.8:     # bir tomonga yuruvchi (skuter quvib o'tadi)
            jismlar.append(Jism(rnd.uniform(10, uzunlik - 20), rnd.uniform(-1.1, 1.1),
                                vs=rnd.uniform(0.6, 1.2), chetlashadi=False))
        else:               # trotuarni kesib o'tuvchi
            yo = rnd.choice((-1, 1))
            jismlar.append(Jism(rnd.uniform(15, uzunlik - 10), -yo * 2.5, vd=yo * rnd.uniform(0.8, 1.4),
                                chetlashadi=False))
    kam = []
    if kamera_xato:
        a = rnd.uniform(20, 80)
        kam = [(a, a + rnd.uniform(1, 5))]
    return Ssenariy(f"tasodifiy-{urug}", uzunlik, jismlar, kam, urug=urug)
