"""Joylashuv datchiklari simulyatori (5-bosqich): GPS, odometr, giroskop, kamera (yo'l cheti, chorraha cheti).

Bu fayl faqat simulyator: datchiklar haqiqiy joydan xato bilan o'lchaydi. Skuter dasturi
(`autopilot/joylashuv.py`) haqiqiy joyni bilmaydi, faqat shu o'lchovlarni oladi.
"""

from dataclasses import dataclass, field
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from autopilot.joylashuv import marshrut_belgilari  # noqa: E402


@dataclass
class JoylashuvSharoiti:
    """Ko'chadagi datchiklar sharoiti. Masofalar marshrut bo'ylab (s, m)."""
    gps_shovqin: float = 0.7        # har o'lchovdagi tasodifiy xato (m)
    gps_xato: float = 1.5           # sekin o'zgaruvchi xato (m): atmosfera, binolardan qaytish
    gps_xato_vaqt: float = 60.0     # (s)
    gps_yoq: list = field(default_factory=list)      # [(s1, s2)]: signal yo'q (daraxtlar, ko'prik osti)
    gps_sakrash: list = field(default_factory=list)  # [(s1, s2, dx, dy)]: GPS shu qadar noto'g'ri joyni ko'rsatadi
    kanyon: list = field(default_factory=list)       # [(s1, s2, xato)]: baland binolar orasi, xato kattaroq
    odometr_xato: float = 0.0       # g'ildirak masshtabi xatosi (0,03 = 3%)
    giro_xato: float = 0.0          # giroskopning boshlang'ich xatosi (rad/s)
    chet_korinish: float = 0.92     # kadrda yo'l cheti (bordyur yoki parkovka chizig'i) ko'rinish ehtimoli
    chet_yoq: list = field(default_factory=list)     # [(s1, s2)]: yo'l cheti ko'rinmaydi (qor, loy, ta'mir)
    chiziq_korinish: float = 0.8    # chorraha cheti ko'rinish ehtimoli (20 m ichida)
    burilish_korinish: float = 0.6  # o'ngga burilishda bordyur egilishi boshi (15 m ichida)
    yanglish: float = 0.02          # kameraning noto'g'ri o'lchov ulushi


def _ichida(s, oraliqlar):
    return any(a <= s < b for a, b, *_ in oraliqlar)


class Datchiklar:
    def __init__(self, sh: JoylashuvSharoiti, marshrut, chiziq, yol_tartibi, urug=0):
        """yol_tartibi(s) -> bu joydagi "yol" bo'lagi (parkovka kengligini bilish uchun)."""
        self.sh = sh
        self.m = marshrut
        self.chiziq = chiziq
        self.yol = yol_tartibi
        self.rnd = random.Random(urug * 7919 + 13)
        self.k = 1.0 + sh.odometr_xato   # haqiqiy tezlik = k * g'ildirak ko'rsatgan tezlik
        self.bg = sh.giro_xato
        self.bx = self.rnd.gauss(0, sh.gps_xato)
        self.by = self.rnd.gauss(0, sh.gps_xato)
        self.t_gps = None
        self.belgilar = marshrut_belgilari(marshrut)

    def odometr(self, v):
        if v < 1e-3:
            return 0.0
        return max(0.0, v / self.k + self.rnd.gauss(0, 0.02))

    def giro(self, omega, dt):
        self.bg += self.rnd.gauss(0, 1e-4) * math.sqrt(dt)
        return omega + self.bg + self.rnd.gauss(0, 0.01)

    def gps(self, t, s, d):
        """GPS: (x, y, aniqlik) yoki None (signal yo'q)."""
        sh = self.sh
        dt = 0.0 if self.t_gps is None else t - self.t_gps
        self.t_gps = t
        xato, tau = sh.gps_xato, sh.gps_xato_vaqt
        for a, b, x in sh.kanyon:
            if a <= s < b:
                xato, tau = x, 20.0
        if dt > 0:
            a = math.exp(-dt / tau)
            q = xato * math.sqrt(1 - a * a)
            self.bx = a * self.bx + self.rnd.gauss(0, q)
            self.by = a * self.by + self.rnd.gauss(0, q)
        if _ichida(s, sh.gps_yoq):
            return None
        x, y = self.chiziq.xy(s, d)
        x += self.bx + self.rnd.gauss(0, sh.gps_shovqin)
        y += self.by + self.rnd.gauss(0, sh.gps_shovqin)
        for a, b, dx, dy in sh.gps_sakrash:
            if a <= s < b:
                x, y = x + dx, y + dy  # qaytgan signal: qabul qilgich buni sezmaydi
        # Qabul qilgich aytadigan aniqlik: haqiqiy xatoga bog'liq, lekin odatda kamaytirib aytiladi
        aniqlik = math.hypot(xato, sh.gps_shovqin) * self.rnd.uniform(0.6, 1.0)
        return x, y, aniqlik

    def chet(self, s, d):
        """Yo'l chetigacha yon masofa: (masofa, turi) yoki None."""
        sh, rnd = self.sh, self.rnd
        b = self.m.bolak(s)
        if b.turi == "otish" or (b.turi == "burilish" and b.egrilik > 0) or _ichida(s, sh.chet_yoq):
            return None  # chorraha ichida va chap burilishda (chorraha burchagida) bordyur yo'q
        if rnd.random() > sh.chet_korinish:
            return None
        yol = self.yol(s)
        if b.turi == "yol" and yol.parkovka > 0:
            turi, asos = "parkovka", yol.parkovka
        else:
            turi, asos = "bordyur", 0.0
        masofa = d - asos
        if rnd.random() < sh.yanglish:
            return masofa + rnd.choice((-1, 1)) * rnd.uniform(0.3, 1.2), turi
        return masofa + rnd.gauss(0, 0.02 + 0.015 * abs(masofa)), turi

    def belgi(self, s, old=0.3):
        """Oldimizdagi eng yaqin belgigacha masofa (skuter markazidan) va turi, yoki None."""
        sh, rnd = self.sh, self.rnd
        oldinda = [(e - s, tr) for e, tr in self.belgilar if 2.0 + old < e - s < (15.0 if tr == "burilish" else 20.0)]
        if not oldinda:
            return None
        masofa, turi = min(oldinda)
        if rnd.random() > (sh.burilish_korinish if turi == "burilish" else sh.chiziq_korinish):
            return None
        if rnd.random() < sh.yanglish:
            return masofa + rnd.uniform(-4, 4), turi
        if turi == "burilish":
            return masofa + rnd.gauss(0, 0.15 + 0.025 * masofa), turi
        return masofa + rnd.gauss(0, 0.08 + 0.015 * masofa), turi


def tasodifiy_sharoit(rnd, uzunlik):
    """Tasodifiy ko'cha uchun datchik sharoiti: GPS yo'qolishi, sakrashi, binolar orasi, yeyilgan g'ildirak."""
    sh = JoylashuvSharoiti(gps_shovqin=rnd.uniform(0.5, 1.0), gps_xato=rnd.uniform(1.0, 2.0),
                           odometr_xato=rnd.gauss(0, 0.02), giro_xato=rnd.gauss(0, 0.005),
                           chet_korinish=rnd.uniform(0.85, 0.95))

    def oraliq(eng_kam, eng_kop):
        a = rnd.uniform(20, max(30, uzunlik - eng_kam))
        return a, a + rnd.uniform(eng_kam, eng_kop)

    if rnd.random() < 0.4:
        sh.gps_yoq.append(oraliq(40, 200))
    if rnd.random() < 0.25:
        sh.gps_sakrash.append((*oraliq(20, 80), rnd.uniform(-25, 25), rnd.uniform(-25, 25)))
    if rnd.random() < 0.25:
        sh.kanyon.append((*oraliq(80, 250), rnd.uniform(3.0, 6.0)))
    if rnd.random() < 0.3:
        sh.chet_yoq.append(oraliq(5, 25))
    return sh
