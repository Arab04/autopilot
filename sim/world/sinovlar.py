"""Virtual trotuar sinovlari. Ishga tushirish: python3 sinovlar.py [tasodifiy_soni]

Asosiy talab: skuter harakatda bo'lganda hech kimga tegmasligi kerak.
"""

import sys
from multiprocessing import Pool
from pathlib import Path

import math

from dunyo import (Jism, Ssenariy, YolMashinasi, ishga_tushir, tasodifiy_ssenariy, tasodifiy_shahar,
                   KMH, Marshrut, Bolak)


def _burilish(r, chapga=True):
    return Bolak("burilish", r * math.pi / 2, egrilik=(1 if chapga else -1) / r)


def _otish(polosa=2, svetofor=False):
    return Bolak("otish", polosa * 3.5, yollar=polosa, svetofor=svetofor)


def _mashinalar(polosa0, polosa1, otish=0):
    """Har polosa uchun (paydo_vaqti, tezlik_kmh) ro'yxati. 0-polosa +x ga, 1-polosa -x ga."""
    m = []
    for p, oqim in ((0, polosa0), (1, polosa1)):
        yo = 1 if p == 0 else -1
        for paydo, kmh in oqim:
            m.append(YolMashinasi(otish, p, -yo * 160, yo * kmh * KMH, paydo))
    return m

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

# 2-bosqich: burilishlar va yo'lni kesib o'tish
IKKINCHI = [
    (Ssenariy("9. Chapga 90° burilish (r=3 m)", marshrut=Marshrut([Bolak("trotuar", 30), _burilish(3.0),
                                                                     Bolak("trotuar", 30)])),
     lambda n: n.yetib_keldi and n.chetga_chiqdi == 0 and n.burilish_max_tezlik < 6.5),
    (Ssenariy("10. O'ngga burilish, burilishda qarshidan odam", marshrut=Marshrut(
        [Bolak("trotuar", 30), _burilish(4.0, False), Bolak("trotuar", 30)]),
        jismlar=[Jism(42, 0.0, vs=-1.2, chetlashadi=False)]),
     lambda n: n.yetib_keldi and n.toqnashuv == 0 and n.chetga_chiqdi == 0),
    (Ssenariy("11. O'ng tomonda yurish: bo'sh trotuar", 60),
     lambda n: n.yetib_keldi and sum(n.iz["d"][len(n.iz["d"]) // 3:]) / len(n.iz["d"][len(n.iz["d"]) // 3:]) < -0.2),
    (Ssenariy("12. Svetoforsiz o'tish, mashina yo'q (operator tasdiqlaydi)",
              marshrut=Marshrut([Bolak("trotuar", 30), _otish(2), Bolak("trotuar", 20)])),
     lambda n: n.yetib_keldi and n.operator_sorovlari == 1 and n.mashina_toqnashuv == 0),
    (Ssenariy("13. Svetoforsiz o'tish, mashinalar ketma-ket o'tadi",
              marshrut=Marshrut([Bolak("trotuar", 30), _otish(2), Bolak("trotuar", 20)]),
              mashinalar=_mashinalar([(0, 50), (4, 45), (9, 55)], [(2, 40), (7, 50), (12, 45)])),
     lambda n: n.yetib_keldi and n.mashina_toqnashuv == 0 and n.mashinagacha_eng_kam > 5.0),
    (Ssenariy("14. To'liq avtonom rejim: operatorsiz o'tadi",
              marshrut=Marshrut([Bolak("trotuar", 30), _otish(2), Bolak("trotuar", 20)]),
              mashinalar=_mashinalar([(3, 50)], [(6, 50)]), rejim="toliq"),
     lambda n: n.yetib_keldi and n.operator_sorovlari == 0 and n.mashina_toqnashuv == 0),
    (Ssenariy("15. Svetofor: qizilda kutadi, yashilda o'tadi",
              marshrut=Marshrut([Bolak("trotuar", 30), _otish(4, svetofor=True), Bolak("trotuar", 20)]),
              mashinalar=[YolMashinasi(0, p, -(1 if p % 2 == 0 else -1) * 100, (1 if p % 2 == 0 else -1) * 45 * KMH,
                                       paydo) for p in range(4) for paydo in (0, 6, 12, 18, 24, 30, 36)],
              svetofor_davri=(20.0, 30.0), svetofor_siljish=25.0),
     lambda n: n.yetib_keldi and n.mashina_toqnashuv == 0 and n.mashinagacha_eng_kam > 3.0),
    (Ssenariy("16. Svetofor yashil, lekin mashina qizilda o'tib ketadi",
              marshrut=Marshrut([Bolak("trotuar", 30), _otish(2, svetofor=True), Bolak("trotuar", 20)]),
              mashinalar=[YolMashinasi(0, 0, -160, 60 * KMH, p, qizilda_otadi=True) for p in (11.0, 13.0)],
              svetofor_davri=(40.0, 20.0)),
     lambda n: n.yetib_keldi and n.mashina_toqnashuv == 0 and n.mashinagacha_eng_kam > 3.0),
]


def _tasodifiy(urug):
    sc = tasodifiy_ssenariy(urug, kamera_xato=(urug % 4 == 0))
    n = ishga_tushir(sc)
    n.iz = None
    return n


def _shahar(urug):
    sc = tasodifiy_shahar(urug, rejim="toliq" if urug % 3 == 0 else "yarim", kamera_xato=(urug % 5 == 0))
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

    print("\n2-bosqich: burilish va yo'lni kesib o'tish")
    print(f"{'Ssenariy':60} {'Yetdi':6} {'Odam':5} {'Mashina':8} {'Mash.gacha':11} {'Oper.':6} Natija")
    ikkinchi_natijalar = []
    for sc, shart in IKKINCHI:
        n = ishga_tushir(sc)
        ok = shart(n)
        ikkinchi_natijalar.append((n, ok, sc))
        if not ok:
            xatolar.append(sc.nomi)
        print(f"{sc.nomi[:60]:60} {'ha' if n.yetib_keldi else 'yo`q':6} {n.toqnashuv:<5} {n.mashina_toqnashuv:<8} "
              f"{min(n.mashinagacha_eng_kam, 99):6.1f} m   {n.operator_sorovlari:<6} {'O`TDI' if ok else 'O`TMADI'}")

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
    # O'ng tomonda yurish qoidasi qo'shilgach ~13%: ko'pi ikki tomondan to'siq bilan haqiqatan to'silgan joylar
    if yordam > 0.15 * soni:
        xatolar.append(f"tasodifiy: operator {yordam}/{soni} marta kerak bo'ldi (chegara 15%)")

    shahar_soni = max(10, soni // 2)
    print(f"\n{shahar_soni} ta tasodifiy shahar marshruti (2-4 burilish, 1-2 yo'l o'tish joyi, mashinalar, "
          f"svetoforlar; har 3-tasi to'liq avtonom)...")
    with Pool() as p:
        sh = p.map(_shahar, range(1, shahar_soni + 1))
    sh_yetdi = sum(n.yetib_keldi for n in sh)
    sh_yordam = sum(n.yordam_sorardi for n in sh)
    sh_toq = sum(n.toqnashuv for n in sh)
    sh_mtoq = sum(n.mashina_toqnashuv for n in sh)
    sh_chet = sum(n.chetga_chiqdi for n in sh)
    print(f"  Manzilga o'zi yetdi:             {sh_yetdi}/{shahar_soni}")
    print(f"  Qotib qolib operator chaqirdi:   {sh_yordam}/{shahar_soni}")
    print(f"  Odam bilan to'qnashuv:           {sh_toq}")
    print(f"  Mashina bilan to'qnashuv:        {sh_mtoq}")
    print(f"  Yo'lda mashinagacha eng yaqin:   {min(n.mashinagacha_eng_kam for n in sh):.1f} m")
    print(f"  Trotuar chetidan chiqish:        {sh_chet}")
    print(f"  Burilishda eng katta tezlik:     {max(n.burilish_max_tezlik for n in sh):.1f} km/soat")
    print(f"  O'tish joyida operator tasdig'i: {sum(n.operator_sorovlari for n in sh)} marta")
    print(f"  O'rtacha tezlik:                 {sum(n.ortacha_tezlik_kmh for n in sh) / shahar_soni:.1f} km/soat")
    if sh_toq or sh_mtoq:
        xatolar.append(f"shahar: {sh_toq} odam, {sh_mtoq} mashina to'qnashuvi")
    if sh_chet:
        xatolar.append(f"shahar: {sh_chet} marta trotuardan chiqdi")
    if shahar_soni - sh_yetdi - sh_yordam:
        xatolar.append(f"shahar: {shahar_soni - sh_yetdi - sh_yordam} ta vaqt chegarasida yetmadi")
    if sh_yordam > 0.15 * shahar_soni:
        xatolar.append(f"shahar: operator {sh_yordam}/{shahar_soni} marta kerak bo'ldi (chegara 15%)")

    chiz(aniq_natijalar)
    chiz_shahar(ikkinchi_natijalar)
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


def chiz_shahar(natijalar):
    """2-bosqich ssenariylari xaritada (yuqoridan ko'rinish)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    ustun = 4
    qator = (len(natijalar) + ustun - 1) // ustun
    fig, axes = plt.subplots(qator, ustun, figsize=(4 * ustun, 3.6 * qator))
    for ax, (n, ok, sc) in zip(axes.flat, natijalar):
        m = sc.marshrut or Marshrut.togri(sc.uzunlik)
        for b in m.bolaklar:
            ss = [b.boshi + b.uzunlik * i / 30 for i in range(31)]
            rang = "#bbbbbb" if b.turi != "otish" else "#f5d76e"
            for d in (-1.5, 1.5):
                xy = [m.dekart(s, d) for s in ss]
                ax.plot([p[0] for p in xy], [p[1] for p in xy], color=rang, lw=1)
        xy = [m.dekart(s, d) for s, d in zip(n.iz["s"], n.iz["d"])]
        kutish = [p for p, h in zip(xy, n.iz["holat"]) if h not in ("yurish", "sekin_aylanish")]
        ax.plot([p[0] for p in xy], [p[1] for p in xy], color="#2ca02c", lw=1.5)
        if kutish:
            ax.scatter([p[0] for p in kutish], [p[1] for p in kutish], s=8, color="#ff7f0e", zorder=3)
        ax.set_aspect("equal")
        ax.set_title(f"{n.nomi[:38]}\n[{'O`TDI' if ok else 'O`TMADI'}]", fontsize=8,
                     color="#2ca02c" if ok else "#d62728")
        ax.tick_params(labelsize=6)
    for ax in list(axes.flat)[len(natijalar):]:
        ax.axis("off")
    fig.suptitle("Yashil = skuter izi, to'q sariq = kutish/to'xtash, sariq = yo'l o'tish joyi", fontsize=9)
    fig.tight_layout()
    out = Path(__file__).with_name("natijalar_shahar.png")
    fig.savefig(out, dpi=85)
    print(f"Grafik: {out}")


if __name__ == "__main__":
    sys.exit(main())
