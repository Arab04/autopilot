"""4-bosqich sinovlari: xaritadan marshrut tuzish va uni simulyatorda bosib o'tish.

    python3 xarita_sinovlar.py                      # sun'iy sinov shahri (xarita moduli sinovi)
    python3 xarita_sinovlar.py --osm chirchiq.osm   # haqiqiy OpenStreetMap fayli, 10 ta tasodifiy manzil

Sun'iy shahar xarita modulini tekshirish uchun: unda avtomagistral, bir tomonlama ko'cha, svetoforli katta yo'l,
velosiped yo'lagi, parkovka, qiya ko'cha va egilgan ko'cha bor. Bu Chirchiq emas.
"""

import math
import random
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autopilot.xarita import Xarita  # noqa: E402
from autopilot.yol import YolSozlamalari, yol_tartibi  # noqa: E402
from yol_dunyo import ishga_tushir, kocha_toldir  # noqa: E402
from yol_sinovlar import _xavfsiz  # noqa: E402

LAT0, LON0 = 41.47, 69.58  # sun'iy shahar shu nuqta atrofida (koordinatalar uchun)


def _ll(x, y):
    lat = LAT0 + math.degrees(y / 6371000.0)
    lon = LON0 + math.degrees(x / (6371000.0 * math.cos(math.radians(LAT0))))
    return lat, lon


def sinov_shahri_osm():
    """Sun'iy shahar: 7x6 ko'chalar to'ri (har xil oraliq), turli yo'l turlari va teglar."""
    xs = [0, 110, 230, 330, 460, 560, 690]
    ys = [0, 95, 210, 320, 410, 540]
    tugunlar, yollar = {}, []
    nid = [1]

    def tugun(x, y, **teg):
        i = nid[0]
        nid[0] += 1
        tugunlar[i] = (x, y, teg)
        return i

    panjara = {(i, j): tugun(x, y) for i, x in enumerate(xs) for j, y in enumerate(ys)}
    wid = [1000]

    def yol(ids, **teg):
        wid[0] += 1
        yollar.append((wid[0], ids, teg))

    # Sharq-g'arb ko'chalari (j bo'yicha)
    for j in range(len(ys)):
        ids = [panjara[(i, j)] for i in range(len(xs))]
        if j == 2:
            yol(ids, highway="primary", lanes="4", name="Katta ko'cha")
            for i in (1, 3, 5):
                tugunlar[panjara[(i, j)]][2]["highway"] = "traffic_signals"
        elif j == 4:
            yol(ids, highway="residential", oneway="yes", name="Bir tomonlama")
        elif j == 0:
            yol(ids, highway="trunk", lanes="6", name="Tranzit")  # skuter yurmasligi kerak
        else:
            yol(ids, highway="residential", **({"parking:lane:right": "parallel"} if j == 1 else {}))
    # Shimol-janub ko'chalari
    for i in range(len(xs)):
        ids = [panjara[(i, j)] for j in range(len(ys))]
        if i == 3:
            yol(ids, highway="secondary", lanes="2", **{"cycleway:right": "lane"}, name="Velo ko'cha")
        elif i == 5:
            # Egilgan ko'cha: har oraliqda bitta qo'shimcha nuqta yon tomonga surilgan
            egri = [ids[0]]
            for a, b in zip(ids, ids[1:]):
                (xa, ya, _), (xb, yb, _) = tugunlar[a], tugunlar[b]
                egri += [tugun((xa + xb) / 2 + 12, (ya + yb) / 2), b]
            yol(egri, highway="tertiary")
        else:
            yol(ids, highway="residential")
    # Qiya ko'cha (60 gradusga yaqin burilishlar)
    yol([panjara[(0, 1)], tugun(55, 150), panjara[(1, 3)]], highway="residential", name="Qiya")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<osm version="0.6">']
    for i, (x, y, teg) in tugunlar.items():
        lat, lon = _ll(x, y)
        t = "".join(f'<tag k="{k}" v="{v}"/>' for k, v in teg.items())
        lines.append(f'<node id="{i}" lat="{lat:.7f}" lon="{lon:.7f}">{t}</node>')
    for w, ids, teg in yollar:
        nd = "".join(f'<nd ref="{i}"/>' for i in ids)
        t = "".join(f'<tag k="{k}" v="{v}"/>' for k, v in teg.items())
        lines.append(f'<way id="{w}">{nd}{t}</way>')
    lines.append("</osm>")
    return "\n".join(lines)


def _asosiy(bolak):
    return yol_tartibi(bolak, YolSozlamalari())[1]


def manzillar(xarita, soni, urug=1, min_masofa=500.0):
    """Tasodifiy (boshlanish, manzil) juftlari, bir-biridan kamida min_masofa uzoqda."""
    rnd = random.Random(urug)
    ids = sorted(xarita.qoshni)
    juftlar = []
    while len(juftlar) < soni:
        a, b = rnd.sample(ids, 2)
        if xarita.masofa(a, b) >= min_masofa:
            ta, tb = xarita.tugunlar[a], xarita.tugunlar[b]
            juftlar.append(((ta.lat, ta.lon), (tb.lat, tb.lon)))
    return juftlar


def modul_sinovlari(xarita, juftlar):
    """Xarita moduli: yo'l qoidalari va marshrut geometriyasi."""
    xatolar = []
    trunk = {y.id for y in xarita.yollar if y.turi in ("trunk", "motorway")}
    bir_tomon = {}
    for y in xarita.yollar:
        if y.bir_tomonlama and not y.velo_teskari:
            for a, b in zip(y.tugunlar, y.tugunlar[1:]):
                bir_tomon[(b, a)] = y.id  # taqiqlangan yo'nalish
    for k, (bosh, manzil) in enumerate(juftlar, 1):
        xm = xarita.skuter_marshruti(bosh, manzil, _asosiy)
        if xm is None:
            xatolar.append(f"{k}: yo'l topilmadi")
            continue
        t = xm.tugunlar
        for a, b in zip(t, t[1:]):
            if (a, b) in bir_tomon:
                xatolar.append(f"{k}: bir tomonlama ko'chaga teskari kirdi")
            yollar = {y.id for j, y, _ in xarita.qoshni.get(a, ()) if j == b}
            if yollar and yollar <= trunk:
                xatolar.append(f"{k}: tranzit yo'lga chiqdi")
        nisbat = xm.marshrut.uzunlik / xm.uzunlik_xarita
        if not 0.75 < nisbat < 1.05:
            xatolar.append(f"{k}: marshrut uzunligi xaritadan juda farq qiladi ({nisbat:.2f})")
        if xm.marshrut.bolaklar[0].turi != "yol" or xm.marshrut.bolaklar[-1].turi != "yol":
            xatolar.append(f"{k}: marshrut yo'l bo'lagi bilan boshlanib tugashi kerak")
        turlar = [b.turi for b in xm.marshrut.bolaklar]
        chap = sum(1 for br in xm.burilishlar if br.chorraha and br.burchak > math.radians(30))
        ikki_bosqich = sum(1 for i in range(len(turlar) - 2)
                           if turlar[i:i + 3] == ["otish", "burilish", "otish"])
        if ikki_bosqich != chap:
            xatolar.append(f"{k}: {chap} ta chap burilishdan {ikki_bosqich} tasi ikki bosqichli")
    return xatolar


def _sim(arg):
    k, osm_matn, bosh, manzil = arg
    xarita = Xarita.osm_dan(osm_matn)
    xm = xarita.skuter_marshruti(bosh, manzil, _asosiy)
    rnd = random.Random(k * 7919)
    sc = kocha_toldir(xm.marshrut, rnd, f"manzil-{k}", rejim="toliq" if k % 3 == 0 else "yarim",
                      kamera_xato=k % 5 == 0, urug=k)
    n = ishga_tushir(sc)
    turlar = [b.turi for b in xm.marshrut.bolaklar]
    return k, n, xm.marshrut.uzunlik, turlar.count("otish"), sum(1 for b in xm.marshrut.bolaklar
                                                                  if b.turi == "otish" and b.svetofor)


def main():
    args = sys.argv[1:]
    if "--osm" in args:
        osm_matn = Path(args[args.index("--osm") + 1]).read_text(encoding="utf-8")
        nomi = args[args.index("--osm") + 1]
    else:
        osm_matn = sinov_shahri_osm()
        nomi = "sun'iy sinov shahri"
    soni = 10
    xarita = Xarita.osm_dan(osm_matn)
    print(f"Xarita: {nomi}: {len(xarita.tugunlar)} tugun, {len(xarita.yollar)} yo'l, "
          f"{sum(t.svetofor for t in xarita.tugunlar.values())} svetofor")
    juftlar = manzillar(xarita, soni)
    xatolar = modul_sinovlari(xarita, juftlar)
    print(f"Xarita moduli sinovlari: {'o`tdi' if not xatolar else '; '.join(xatolar)}")

    with Pool() as p:
        natijalar = p.map(_sim, [(k, osm_matn, b, m) for k, (b, m) in enumerate(juftlar, 1)])
    print(f"\n{'Manzil':10} {'Uzunlik':>8} {'Chorraha':>9} {'Svetofor':>9} {'Vaqt':>7} {'Yetdi':>6} Xavfsiz")
    for k, n, uz, ch, sv, in natijalar:
        print(f"{n.nomi:10} {uz:7.0f}m {ch:9} {sv:9} {n.vaqt:6.0f}s {'ha' if n.yetib_keldi else 'yo`q':>6} "
              f"{'ha' if _xavfsiz(n) else 'YO`Q'}{'  (operator)' if n.yordam else ''}")
        if not _xavfsiz(n):
            xatolar.append(f"{n.nomi}: to'qnashuv")
        elif not n.yetib_keldi and not n.yordam:
            xatolar.append(f"{n.nomi}: vaqt chegarasida yetmadi")
    yordam = sum(n.yordam for _, n, *_ in natijalar)
    if yordam > 0.2 * soni:
        xatolar.append(f"operator {yordam}/{soni} marta kerak bo'ldi")
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


if __name__ == "__main__":
    sys.exit(main())
