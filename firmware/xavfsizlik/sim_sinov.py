"""Platadagi C dasturini ko'cha simulyatorida sinash.

Simulyatordagi Python xavfsizlik qatlami (ultratovush bo'yicha favqulodda tormoz) o'rniga shu papkadagi C
dasturi ishlaydi: har 50 ms da Jetson buyrug'i, g'ildirak tezligi va ultratovush unga beriladi, motor esa
platadan chiqqan chegaraga bo'ysunadi. Kamera eskirishi Jetsonning o'z tekshiruvi bo'lib qoladi.
Keyin 3-bosqichning barcha sinovlari (14 aniq ssenariy + N tasodifiy ko'cha) yurgiziladi.

    python3 sim_sinov.py 150
"""

import sys
from pathlib import Path

PAPKA = Path(__file__).resolve().parent
ILDIZ = PAPKA.parents[1]
sys.path.insert(0, str(PAPKA))
sys.path.insert(0, str(ILDIZ / "sim" / "world"))
sys.path.insert(0, str(ILDIZ))

from plata import Plata  # noqa: E402
from autopilot.haydash import Buyruq  # noqa: E402
from autopilot.yol import YolAvtopilot  # noqa: E402

_asl = YolAvtopilot.xavfsizlik


def plata_bilan(self, buyruq, v, ultratovush, t):
    # Jetson tomoni: kamera eskirganini o'zi tekshiradi (ultratovushsiz)
    jetson = _asl(self, buyruq, v, None, t)
    if not hasattr(self, "_plata"):
        self._plata = Plata()
    d = 99.0 if ultratovush is None else ultratovush  # simulyator 4 m gacha ko'radi, None = aks-sado yo'q
    c = self._plata.qadam(round(t * 1000), v, [d, d, d], dict(tezlik=jetson.tezlik, tormoz=jetson.tormoz))
    if c["holat"] == "favqulodda":
        return Buyruq(0.0, jetson.d_maqsad, c["tormoz"], "favqulodda")
    if c["tezlik_max"] < jetson.tezlik:
        return Buyruq(c["tezlik_max"], jetson.d_maqsad, max(jetson.tormoz, c["tormoz"]), "plata_" + c["holat"])
    return jetson


def main():
    YolAvtopilot.xavfsizlik = plata_bilan
    Plata()  # kutubxonani oldindan yig'ish (jarayonlar bo'linishidan oldin)
    import yol_sinovlar
    print("Xavfsizlik qatlami: platadagi C dasturi (firmware/xavfsizlik)\n")
    return yol_sinovlar.main()


if __name__ == "__main__":
    sys.exit(main())
