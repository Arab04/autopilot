"""Marshrut xaritasi: trotuar bo'laklari, burilishlar va yo'lni kesib o'tish joylari.

Skuter marshrutni oldindan biladi (xaritadan). Har bir bo'lak uchun:
- "trotuar": to'g'ri trotuar;
- "burilish": aylana yoy (egrilik > 0 = chapga, < 0 = o'ngga);
- "otish": avtomobil yo'lini piyodalar o'tish joyidan (yoki chorrahani) kesib o'tish;
- "yol": avtomobil yo'lining o'ng cheti (3-bosqich): polosalar, velosiped yo'lagi, parkovka.
"""

from dataclasses import dataclass, field
import math


@dataclass
class Bolak:
    turi: str                     # "trotuar", "burilish", "otish"
    uzunlik: float                # m (otish uchun = yo'llar soni * yo'l kengligi)
    egrilik: float = 0.0          # 1/m, faqat burilish uchun
    yollar: int = 0               # otish: avtomobil yo'llari (polosalari) soni
    yol_kengligi: float = 3.5     # otish: bitta polosa kengligi (m)
    svetofor: bool = False        # otish: svetofor bormi (trotuarda piyodalar, yo'lda o'z yo'nalishimiz uchun)
    velo: float = 0.0             # yol: velosiped yo'lagi kengligi (m), 0 = yo'q
    parkovka: float = 0.0         # yol: chetda mashina to'xtash joyi kengligi (m), 0 = yo'q
    oqim: float = 0.0             # otish: kesib o'tiladigan yo'ldagi kutilgan oqim (mashina/s, bitta polosada), 0 = noma'lum
    tugunlar: tuple = ()          # otish: xaritadagi chorraha tugun(lar)i (marshrut variantlarini solishtirish uchun)
    boshi: float = 0.0            # marshrut boshidan masofa (avtomatik hisoblanadi)

    @property
    def oxiri(self):
        return self.boshi + self.uzunlik


class Marshrut:
    def __init__(self, bolaklar):
        self.bolaklar = bolaklar
        s = 0.0
        for b in bolaklar:
            b.boshi = s
            s += b.uzunlik
        self.uzunlik = s

    @staticmethod
    def togri(uzunlik):
        return Marshrut([Bolak("trotuar", uzunlik)])

    def bolak(self, s):
        for b in self.bolaklar:
            if s < b.oxiri:
                return b
        return self.bolaklar[-1]

    def egrilik(self, s):
        b = self.bolak(s)
        return b.egrilik if b.turi == "burilish" else 0.0

    def otishlar(self):
        return [b for b in self.bolaklar if b.turi == "otish"]

    def tezlik_chegarasi(self, s, max_tezlik, yon_tezlanish, tormoz, oldinga=8.0):
        """Burilishdan oldin sekinlashish: yon tezlanish chegaradan oshmasin."""
        v = max_tezlik
        x = 0.0
        while x <= oldinga:
            k = abs(self.egrilik(s + x))
            if k > 1e-6:
                v_burilish = math.sqrt(yon_tezlanish / k)
                v = min(v, math.sqrt(v_burilish ** 2 + 2 * tormoz * x))
            x += 0.5
        return v

    def dekart(self, s, d=0.0):
        """Marshrut koordinatasini (s, d) xaritadagi (x, y) ga aylantiradi (grafik uchun)."""
        x = y = th = 0.0
        qolgan = s
        for b in self.bolaklar:
            l = min(qolgan, b.uzunlik)
            if b.turi == "burilish" and abs(b.egrilik) > 1e-9:
                r = 1 / b.egrilik
                x += r * (math.sin(th + l / r) - math.sin(th))
                y += -r * (math.cos(th + l / r) - math.cos(th))
                th += l / r
            else:
                x += l * math.cos(th)
                y += l * math.sin(th)
            qolgan -= l
            if qolgan <= 1e-9:
                break
        return x - d * math.sin(th), y + d * math.cos(th)
