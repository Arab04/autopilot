"""Yo'lda yurish sinovlari (3-bosqich). Ishga tushirish: python3 yol_sinovlar.py [tasodifiy_soni]

Asosiy talab: skuter hech kimga (mashina, odam, velosipedchi, to'xtab turgan mashina) tegmasligi
va orqadan kelayotgan mashinalar oldiga to'satdan chiqmasligi kerak.
"""

import math
import sys
from multiprocessing import Pool
from pathlib import Path

from yol_dunyo import (YolSsenariy, Transport, Piyoda, ishga_tushir, tasodifiy_kocha, Marshrut, Bolak, KMH)
from dunyo import YolMashinasi


def _yol(uzunlik, **k):
    return Bolak("yol", uzunlik, **{"yollar": 2, **k})


def _ortacha_d(n, boshi=0.3, oxiri=0.9):
    ds = n.iz["d"]
    qism = ds[int(len(ds) * boshi):int(len(ds) * oxiri)]
    return sum(qism) / len(qism)


def _xavfsiz(n):
    return n.mashina_toq + n.odam_toq + n.velo_toq + n.tosiq_toq + n.kesuvchi_toq == 0 and n.chetga == 0


def _parkovka_qatori(boshi, oxiri, bosh_joylar=()):
    natija, x, i = [], boshi, 0
    while x < oxiri:
        if all(abs(x - b) > 4 for b in bosh_joylar):
            natija.append(Transport("toxtagan", x, 1.1, uzunlik=4.5, eni=1.8, polosa=-1, id=500 + i))
        x += 6.0
        i += 1
    return natija


def _kesuvchilar(otish, polosalar, davr=4.0, tezlik=45):
    return [YolMashinasi(otish, p, -(1 if p % 2 == 0 else -1) * 120, (1 if p % 2 == 0 else -1) * tezlik * KMH, paydo)
            for p in range(polosalar) for paydo in [i * davr + p for i in range(60)]]


ANIQ = [
    (YolSsenariy("1. Bo'sh yo'l: bordyurdan 0,8 m da", Marshrut([_yol(300)])),
     lambda n: n.yetib_keldi and n.ortacha_kmh > 17 and 0.6 < _ortacha_d(n) < 1.0),
    (YolSsenariy("2. Velosiped yo'lagi o'rtasida", Marshrut([_yol(300, velo=1.5)]), oqim=0.1),
     lambda n: n.yetib_keldi and _xavfsiz(n) and 0.55 < _ortacha_d(n) < 0.95),
    (YolSsenariy("3. Zich oqim: mashinalar quvib o'tadi", Marshrut([_yol(400)]), oqim=0.25),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.yaqin_otish > 0.5),
    (YolSsenariy("4. Bir polosali tor yo'l, orqada mashinalar", Marshrut([_yol(300, yollar=1)]), oqim=0.12),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("5. Chetda to'xtagan mashina, orqada hech kim", Marshrut([_yol(200)]),
                 [Transport("toxtagan", 80, 1.0, uzunlik=4.5, eni=1.8, polosa=-1, id=1)]),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.aylanib_otish >= 1),
    (YolSsenariy("6. To'xtagan mashina, orqadan zich oqim", Marshrut([_yol(250, yollar=1)]),
                 [Transport("toxtagan", 80, 1.0, uzunlik=4.5, eni=1.8, polosa=-1, id=1)], oqim=0.2, urug=6),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.yaqin_otish > 0.3),
    (YolSsenariy("7. Bekatda avtobus turibdi", Marshrut([_yol(250)]),
                 [Transport("toxtagan", 100, 1.35, uzunlik=12.0, eni=2.5, polosa=-1, id=1)], oqim=0.1, urug=7),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("8. Sekin velosipedchini quvib o'tish", Marshrut([_yol(300)]),
                 [Transport("velosiped", 40, 0.7, 3.0, 3.0, 1.8, 0.6, -1, id=1)], oqim=0.08, urug=8),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("9. Parkovka, mashinalar orasidan odam chiqadi", Marshrut([_yol(250, parkovka=2.2)]),
                 _parkovka_qatori(20, 230), [Piyoda(121.0, 100.0, vd=1.5, etiborli=False)], urug=9),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.eshik_zonasi == 0),
    (YolSsenariy("10. Chorraha: qizilda kutadi, yashilda o'tadi",
                 Marshrut([_yol(80), Bolak("otish", 14.0, yollar=4, svetofor=True), _yol(60)]),
                 kesuvchi=_kesuvchilar(0, 4), svetofor_davri=(20.0, 30.0), svetofor_siljish=[25.0], oqim=0.08, urug=10),
     lambda n: n.yetib_keldi and _xavfsiz(n) and "bosh_joy_kutish" in n.iz["holat"]),
    (YolSsenariy("11. Oldimizdagi mashina o'ngga burilib, yo'limizni kesadi",
                 Marshrut([_yol(150), Bolak("otish", 7.0, yollar=2, svetofor=True), _yol(60)]),
                 [Transport("mashina", -120, 2.6, 12.5, 12.5, polosa=0, burilish=True, id=1)],
                 svetofor_davri=(300.0, 5.0), urug=11),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("12. Chapga burilish: chorrahani 2 marta kesib o'tadi",
                 Marshrut([_yol(80), Bolak("otish", 7.0, yollar=2, svetofor=True),
                           Bolak("burilish", 4.5 * math.pi / 2, egrilik=1 / 4.5), Bolak("otish", 14.0, yollar=4, svetofor=True),
                           _yol(60)]),
                 kesuvchi=_kesuvchilar(0, 2, 6.0) + _kesuvchilar(1, 4, 6.0), svetofor_davri=(20.0, 20.0),
                 svetofor_siljish=[0.0, 20.0], oqim=0.05, urug=12),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("13. Kamera 2 s o'chadi, oldinda to'xtagan mashina", Marshrut([_yol(200)]),
                 [Transport("toxtagan", 70, 1.0, uzunlik=4.5, eni=1.8, polosa=-1, id=1)],
                 kamera_ochadi=[(9.0, 11.0)], oqim=0.05, urug=13),
     lambda n: n.yetib_keldi and _xavfsiz(n)),
    (YolSsenariy("14. Yo'l ta'mirlanmoqda: o'tib bo'lmaydi", Marshrut([_yol(150, yollar=1)]),
                 [Transport("tosiq", 80, 2.3, uzunlik=3.0, eni=4.6, polosa=-1, id=1)], vaqt_chegarasi=120, urug=14),
     lambda n: n.yordam and _xavfsiz(n)),
]


def _tasodifiy(urug):
    sc = tasodifiy_kocha(urug, rejim="toliq" if urug % 3 == 0 else "yarim", kamera_xato=(urug % 5 == 0))
    n = ishga_tushir(sc)
    n.iz = None
    return n


def main():
    soni = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    xatolar = []
    print(f"{'Ssenariy':55} {'Yetdi':6} {'To`qn.':7} {'Yonidan':8} {'Aylan.':7} Natija")
    natijalar = []
    for sc, shart in ANIQ:
        n = ishga_tushir(sc)
        ok = shart(n)
        natijalar.append((n, ok, sc))
        if not ok:
            xatolar.append(sc.nomi)
        jami = n.mashina_toq + n.odam_toq + n.velo_toq + n.tosiq_toq + n.kesuvchi_toq
        print(f"{sc.nomi[:55]:55} {'ha' if n.yetib_keldi else 'yo`q':6} {jami:<7} "
              f"{min(n.yaqin_otish, 9.9):5.2f} m  {n.aylanib_otish:<7} {'O`TDI' if ok else 'O`TMADI'}")

    print(f"\n{soni} ta tasodifiy ko'cha marshruti (parkovka, velosiped yo'lagi, avtobus, chorrahalar; "
          f"har 3-tasi to'liq avtonom, har 5-tasida kamera o'chadi)...")
    with Pool() as p:
        nat = p.map(_tasodifiy, range(1, soni + 1))
    yetdi = sum(n.yetib_keldi for n in nat)
    yordam = sum(n.yordam for n in nat)
    jami = {k: sum(getattr(n, k) for n in nat) for k in
            ("mashina_toq", "odam_toq", "velo_toq", "tosiq_toq", "kesuvchi_toq", "chetga", "eshik_zonasi")}
    yomon = [n.nomi for n in nat if not _xavfsiz(n)]
    print(f"  Manzilga o'zi yetdi:               {yetdi}/{soni}")
    print(f"  Qotib qolib operator chaqirdi:     {yordam}/{soni}")
    print(f"  Mashina bilan to'qnashuv:          {jami['mashina_toq']}")
    print(f"  Odam bilan to'qnashuv:             {jami['odam_toq']}")
    print(f"  Velosipedchi bilan:                {jami['velo_toq']}")
    print(f"  To'xtagan mashina / to'siq bilan:  {jami['tosiq_toq']}")
    print(f"  Chorrahada ko'ndalang mashina:     {jami['kesuvchi_toq']}")
    print(f"  Bordyurga tegish:                  {jami['chetga']}")
    print(f"  Eshik ochilish zonasidan o'tish:   {jami['eshik_zonasi']}")
    print(f"  Yonidan o'tgan mashina, eng yaqin: {min(n.yaqin_otish for n in nat):.2f} m")
    print(f"  Aylanib o'tishlar (jami):          {sum(n.aylanib_otish for n in nat)}")
    print(f"  Orqani kutish (o'rtacha):          {sum(n.orqa_kutish_s for n in nat) / soni:.1f} s")
    print(f"  Chorrahada operator tasdig'i:      {sum(n.operator_sorovlari for n in nat)} marta")
    print(f"  O'rtacha tezlik:                   {sum(n.ortacha_kmh for n in nat) / soni:.1f} km/soat")
    if yomon:
        xatolar.append(f"tasodifiy: {len(yomon)} ta marshrutda to'qnashuv ({', '.join(yomon[:8])})")
    qolgan = soni - yetdi - yordam
    if qolgan:
        xatolar.append(f"tasodifiy: {qolgan} ta vaqt chegarasida yetmadi")
    if yordam > 0.15 * soni:
        xatolar.append(f"tasodifiy: operator {yordam}/{soni} marta kerak bo'ldi (chegara 15%)")
    chiz(natijalar)
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


def chiz(natijalar):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(len(natijalar), 1, figsize=(12, 1.6 * len(natijalar)))
    for ax, (n, ok, sc) in zip(axes, natijalar):
        y = next(b for b in sc.marshrut.bolaklar if b.turi == "yol")
        kenglik = y.parkovka + y.velo + y.yollar * y.yol_kengligi
        ax.axhspan(0, kenglik, color="#eeeeee")
        if y.parkovka:
            ax.axhspan(0, y.parkovka, color="#dddddd")
        if y.velo:
            ax.axhspan(y.parkovka, y.parkovka + y.velo, color="#d8ecd8")
        for b in sc.marshrut.bolaklar:
            if b.turi == "otish":
                ax.axvspan(b.boshi, b.oxiri, color="#f5e6a8")
        for x in sc.transport:
            ax.add_patch(plt.Rectangle((x.s - x.uzunlik / 2, x.d - x.eni / 2), x.uzunlik, x.eni,
                                       color="#999999" if x.turi in ("toxtagan", "tosiq") else "#6fa8dc"))
        ranglar = {"yurish": "#2ca02c", "aylanib": "#1f77b4", "orqa_kutish": "#ff7f0e", "kutish": "#ff7f0e",
                   "bosh_joy_kutish": "#ff7f0e", "operator_kutish": "#9467bd", "yol_berish": "#e377c2",
                   "favqulodda": "#d62728"}
        for h, rang in ranglar.items():
            xs = [s for s, hh in zip(n.iz["s"], n.iz["holat"]) if hh == h]
            ys = [d for d, hh in zip(n.iz["d"], n.iz["holat"]) if hh == h]
            if xs:
                ax.scatter(xs, ys, s=3, color=rang, label=h)
        ax.set_ylim(-0.5, kenglik + 0.5)
        ax.set_xlim(0, sc.marshrut.uzunlik)
        ax.set_title(f"{n.nomi}  [{'O`TDI' if ok else 'O`TMADI'}]", fontsize=9, loc="left",
                     color="#2ca02c" if ok else "#d62728")
        ax.set_ylabel("d (m)")
    axes[0].legend(fontsize=7, loc="upper right", ncol=4, markerscale=3)
    axes[-1].set_xlabel("marshrut bo'ylab (m); d = bordyurdan masofa. Kulrang = to'xtagan mashina/to'siq, "
                        "yashil yo'lak = velosiped yo'lagi, sariq = chorraha")
    fig.tight_layout()
    out = Path(__file__).with_name("natijalar_yol.png")
    fig.savefig(out, dpi=80)
    print(f"\nGrafik: {out}")


if __name__ == "__main__":
    sys.exit(main())
