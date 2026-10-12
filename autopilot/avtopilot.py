"""Skuter dasturining yuqori qatlami: barcha modullarni birlashtiradi.

Skuterda ikki tezlikda ishlaydi:
- `rejalash` (10 Hz, asosiy kompyuter): kuzatish, yo'l tanlash, burilish, yo'lni kesib o'tish;
- `xavfsizlik` (20 Hz, mikrokontroller): ultratovush va kamera nazorati.
"""

import math

from .haydash import Buyruq, Kuzatuvchi, Rejalovchi, Sozlamalar, XavfsizlikQatlami, YordamNazoratchisi
from .marshrut import Marshrut
from .otish import YolOtishBoshqaruvi

# Yo'lni kesib o'tishda bo'sh joy kutish odatiy hol: operatorni kechroq chaqiramiz
OTISH_KUTISH_CHEGARASI = 120.0


class Avtopilot:
    def __init__(self, marshrut: Marshrut, rejim="yarim", c: Sozlamalar = None, yordam_kutish=30.0):
        self.c = c or Sozlamalar()
        self.marshrut = marshrut
        self.kuz = Kuzatuvchi()
        self.rej = Rejalovchi(self.c)
        self.otish = YolOtishBoshqaruvi(rejim=rejim)
        self.xav = XavfsizlikQatlami(self.c)
        self.nazorat = YordamNazoratchisi(yordam_kutish)
        self.oxirgi_kamera = 0.0
        self.obyektlar = []
        self.otish_holati = None

    @property
    def operator_sorovi(self):
        return self.otish.sorov is not None

    def rejalash(self, t, s, d, v, aniqlashlar, mashinalar=(), svetofor=None, operator_javobi=None):
        c = self.c
        if aniqlashlar is not None:
            self.obyektlar = self.kuz.yangila(t, aniqlashlar)
            self.oxirgi_kamera = t
        b = self.rej.reja(s, d, v, self.obyektlar)
        # Burilishdan oldin sekinlashish
        v_egri = self.marshrut.tezlik_chegarasi(s, c.max_tezlik, c.yon_tezlanish, c.tormoz)
        # Yo'lni kesib o'tish
        yol_ochiq = b.holat == "yurish" and b.tezlik >= c.max_tezlik - 1e-6
        yol_tezligi = math.inf if yol_ochiq else (b.tezlik if b.holat == "yurish" else 0.0)
        v_otish, holat = self.otish.qadam(t, s, v, self.marshrut, list(mashinalar), svetofor, operator_javobi,
                                          yol_tezligi)
        if holat == "otish" and self.otish_holati != "otish":
            self.nazorat.boshlanish = (t, s)  # yo'lga chiqish boshlandi: kutish vaqtini qayta sanaymiz
        self.otish_holati = holat
        if holat == "otish":
            # Yo'lda biroz tezroq yuramiz, agar oldimizda odam yoki to'siq cheklovi bo'lmasa
            tezlik = v_otish if yol_ochiq else b.tezlik
        else:
            tezlik = min(b.tezlik, v_otish, v_egri)
        yangi_holat = b.holat if holat in (None, "otish", "otishga_yaqinlashish") else holat
        return Buyruq(tezlik, b.d_maqsad, b.tormoz, yangi_holat)

    def xavfsizlik(self, buyruq, v, ultratovush, t):
        return self.xav.tekshir(buyruq, v, ultratovush, t - self.oxirgi_kamera)

    def yordam_kerakmi(self, t, s):
        kutish = OTISH_KUTISH_CHEGARASI if self.otish_holati in ("bosh_joy_kutish", "operator_kutish") else None
        return self.nazorat.tekshir(t, s, kutish)
