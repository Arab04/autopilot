"""Virtual trotuar sinovlari. Ishga tushirish: python3 sinovlar.py [tasodifiy_soni]

Asosiy talab: skuter harakatda bo'lganda hech kimga tegmasligi kerak.
"""

import sys
from multiprocessing import Pool
from pathlib import Path

from dunyo import Jism, Ssenariy, ishga_tushir, tasodifiy_ssenariy, KMH

ANIQ = [
    (Ssenariy("1. Bo'sh trotuar", 100),
     lambda n: n.yetib_keldi and n.ortacha_tezlik_kmh > 5.0),
    (Ssenariy("2. Markazda ustun", 60, [Jism(30, 0.0, r=0.3, turi="to'siq")]),
     lambda n: n.yetib_keldi and n.toqnashuv == 0),
    (Ssenariy("3. Qarshidan odam to'g'ri keladi (chetlashmaydi)", 60,
              [Jism(50, 0.0, vs=-1.3, chetlashadi=False)]),
     lambda n: n.yetib_keldi and n.toqnashuv == 0),
    (Ssenariy("4. Sekin yuruvchi odamni quvib o'tish", 80,
              [Jism(15, 0.2, vs=0.8, chetlashadi=False)]),
     lambda n: n.yetib_keldi and n.toqnashuv == 0),
    (Ssenariy("5. Mashina orqasidan to'satdan chiqqan odam (3 m oldinda)", 60,
              [Jism(23, -2.2, vd=1.2, yashirin_gacha=12.0, chetlashadi=False)]),
     lambda n: n.toqnashuv == 0),
    (Ssenariy("6. Trotuar to'liq to'silgan: 3 kishi yonma-yon turibdi", 40,
              [Jism(25, -1.1, chetlashadi=False), Jism(25, 0.0, chetlashadi=False),
               Jism(25, 1.1, chetlashadi=False)], vaqt_chegarasi=60),
     lambda n: n.yordam_sorardi and n.toqnashuv == 0),
    (Ssenariy("7. Kamera 4 soniya o'chadi, oldinda ustun", 80,
              [Jism(32, 0.0, r=0.3, turi="to'siq")], kamera_ochadi=[(15.0, 19.0)]),
     lambda n: n.yetib_keldi and n.toqnashuv == 0 and n.kamera_xato >= 1),
    (Ssenariy("8. Kamera ustunni umuman ko'rmaydi: faqat ultratovush qutqaradi", 60,
              [Jism(35, 0.0, r=0.3, turi="to'siq", yashirin_gacha=1e9)], vaqt_chegarasi=60),
     lambda n: n.toqnashuv == 0 and n.favqulodda >= 1),
]


def _tasodifiy(urug):
    sc = tasodifiy_ssenariy(urug, kamera_xato=(urug % 4 == 0))
    n = ishga_tushir(sc)
    n.iz = None
    return n


def main():
    soni = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    xatolar = []
    print(f"{'Ssenariy':60} {'Yetdi':6} {'Tegish':7} {'Eng yaqin':10} {'Favq.':6} Natija")
    aniq_natijalar = []
    for sc, shart in ANIQ:
        n = ishga_tushir(sc)
        ok = shart(n)
        aniq_natijalar.append((n, ok, sc))
        if not ok:
            xatolar.append(sc.nomi)
        print(f"{sc.nomi[:60]:60} {'ha' if n.yetib_keldi else 'yo`q':6} {n.toqnashuv:<7} "
              f"{n.eng_kam_masofa:6.2f} m   {n.favqulodda:<6} {'O`TDI' if ok else 'O`TMADI'}")

    print(f"\n{soni} ta tasodifiy trotuar (har biri 200 m, 12 odam, 10 to'siq; har 4-tasida kamera o'chadi)...")
    with Pool() as p:
        nat = p.map(_tasodifiy, range(1, soni + 1))
    toq = [n for n in nat if n.toqnashuv]
    yetdi = sum(n.yetib_keldi for n in nat)
    teg = sum(n.tegildi_turganda for n in nat)
    yordam = sum(n.yordam_sorardi for n in nat)
    print(f"  Manzilga o'zi yetdi:             {yetdi}/{soni}")
    print(f"  Qotib qolib operator chaqirdi:   {yordam}/{soni}")
    print(f"  Harakatda to'qnashuv:            {sum(n.toqnashuv for n in nat)}  "
          f"({', '.join(n.nomi for n in toq[:10])})")
    print(f"  Turganda odam tegib ketdi:       {teg}")
    print(f"  Odamgacha eng yaqin masofa:      {min(n.eng_kam_masofa for n in nat):.2f} m")
    print(f"  O'rtacha tezlik:                 {sum(n.ortacha_tezlik_kmh for n in nat) / soni:.1f} km/soat")
    print(f"  Favqulodda tormoz (jami):        {sum(n.favqulodda for n in nat)}")
    if toq:
        xatolar.append(f"tasodifiy: {len(toq)} ta to'qnashuv")
    qolgan = soni - yetdi - yordam
    if qolgan:
        xatolar.append(f"tasodifiy: {qolgan} ta vaqt chegarasida yetmadi")
    if yordam > 0.10 * soni:
        xatolar.append(f"tasodifiy: operator {yordam}/{soni} marta kerak bo'ldi (chegara 10%)")
    chiz(aniq_natijalar)
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


def chiz(natijalar):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    ranglar = {"yurish": "#2ca02c", "kutish": "#ff7f0e", "favqulodda": "#d62728", "kamera_xato": "#9467bd", "sekin_aylanish": "#1f77b4"}
    fig, axes = plt.subplots(len(natijalar), 1, figsize=(11, 1.9 * len(natijalar)))
    for ax, (n, ok, sc) in zip(axes, natijalar):
        iz = n.iz
        ax.axhspan(-1.5, 1.5, color="#eeeeee")
        for j in sc.jismlar:
            if j.turi == "odam":
                ax.scatter([j.s], [j.d], marker="o", s=40, facecolors="none", edgecolors="#333333")
                if j.vs or j.vd:
                    ax.annotate("", xy=(j.s + 3 * j.vs, j.d + 1.5 * j.vd), xytext=(j.s, j.d),
                                arrowprops=dict(arrowstyle="->", color="#333333", lw=0.8))
            else:
                ax.add_patch(plt.Circle((j.s, j.d), j.r, color="#555555"))
        for h, rang in ranglar.items():
            xs = [s for s, hh in zip(iz["s"], iz["holat"]) if hh == h]
            ys = [d for d, hh in zip(iz["d"], iz["holat"]) if hh == h]
            if xs:
                ax.scatter(xs, ys, s=3, color=rang, label=h)
        ax.set_ylim(-2, 2)
        ax.set_xlim(0, max(iz["s"]) + 5)
        ax.set_title(f"{n.nomi}  [{'O`TDI' if ok else 'O`TMADI'}]  tegish={n.toqnashuv}, "
                     f"eng yaqin={n.eng_kam_masofa:.2f} m", fontsize=9, loc="left",
                     color="#2ca02c" if ok else "#d62728")
        ax.set_ylabel("d (m)")
    axes[0].legend(fontsize=7, loc="upper right", ncol=4, markerscale=3)
    axes[-1].set_xlabel("marshrut bo'ylab masofa (m)   (kulrang doira = ustun/daraxt, halqa = odamning boshlang'ich joyi, strelka = yo'nalishi)")
    fig.tight_layout()
    out = Path(__file__).with_name("natijalar.png")
    fig.savefig(out, dpi=85)
    print(f"\nGrafik: {out}")


if __name__ == "__main__":
    sys.exit(main())
