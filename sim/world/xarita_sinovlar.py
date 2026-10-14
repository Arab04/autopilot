"""4-bosqich sinovlari: xaritadan marshrut tuzish va uni simulyatorda bosib o'tish.

    python3 xarita_sinovlar.py                      # sun'iy sinov shahri (xarita moduli sinovi)
    python3 xarita_sinovlar.py --osm chirchiq.osm   # haqiqiy OpenStreetMap fayli, 10 ta tasodifiy manzil
    python3 xarita_sinovlar.py --chirchiq [N]       # Chirchiq xaritasi: ombordan 10 manzilga, har biri N marta (3)
    python3 xarita_sinovlar.py --km 1000            # Chirchiqda jami 1000 km (borish va qaytish), to'qnashuvsiz

Sun'iy shahar xarita modulini tekshirish uchun: unda avtomagistral, bir tomonlama ko'cha, svetoforli katta yo'l,
velosiped yo'lagi, parkovka, qiya ko'cha va egilgan ko'cha bor. Bu Chirchiq emas.

Chirchiq xaritasi xaritalar/chirchiq.osm.gz da (OpenStreetMap, overpass-api.de dan 2026-10-12 da yuklangan;
ma'lumotlar (c) OpenStreetMap hissadorlari, ODbL litsenziyasi).
"""

import math
import random
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autopilot.otish import kutish_bahosi  # noqa: E402
from autopilot.xarita import Xarita  # noqa: E402
from autopilot.yol import YolSozlamalari, yol_tartibi  # noqa: E402
from yol_dunyo import ishga_tushir, kocha_toldir  # noqa: E402
from yol_sinovlar import _xavfsiz  # noqa: E402

LAT0, LON0 = 41.47, 69.58  # sun'iy shahar shu nuqta atrofida (koordinatalar uchun)
CHIRCHIQ_OSM = Path(__file__).with_name("xaritalar") / "chirchiq.osm.gz"

# Ombor va 1-5 manzilni Isroil bergan (2026-10-12), 6-10 ni Claude tanlagan. Koordinatalar OSM dan.
# Ombor: "Navoiy bozoriga yetmasdan" - Markaziy bozor (Tsentralniy rinok) dan ~100 m g'arbda deb olingan.
CHIRCHIQ_OMBOR = ("Ombor (Navoiy/Markaziy bozor oldi)", 41.47350, 69.59000)
CHIRCHIQ_MANZILLAR = [
    ("Jismoniy tarbiya instituti (Troitsk)", 41.43607, 69.53586),
    ("O'rmon parki", 41.46567, 69.56722),
    ("Chirchiq bozori", 41.45864, 69.54696),
    ("8-kichik nohiya", 41.46214, 69.55030),
    ("Oktyabr (Oktyabr bozori)", 41.48526, 69.57855),
    ("Pedagogika universiteti", 41.47080, 69.57417),
    ("Shoshilinch tibbiy yordam markazi", 41.48515, 69.58598),
    ("4-kichik nohiya", 41.49342, 69.58493),
    ("Do'stlik mahallasi", 41.49540, 69.60669),
    ("Kimyogar sport majmuasi", 41.46510, 69.58491),
]


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
    ids = sorted(xarita.asosiy)
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


_XARITA = {}
SABAB = {"bosh_joy_kutish": "chorrahada bo'sh joy yo'q", "operator_kutish": "chorrahada bo'sh joy yo'q",
         "aylanib": "to'siqni aylanib o'tolmadi", "kutish": "to'siq oldida kutdi", "orqa_kutish": "to'siq oldida kutdi"}


def _sim(arg):
    k, osm, bosh, manzil, takror = arg
    if osm not in _XARITA:
        _XARITA[osm] = Xarita.osm_dan(osm)
    xm = _XARITA[osm].skuter_marshruti(bosh, manzil, _asosiy)
    rnd = random.Random(k * 7919 + takror * 1000003)
    sc = kocha_toldir(xm.marshrut, rnd, f"manzil-{k}", rejim="toliq" if k % 3 == 0 else "yarim",
                      kamera_xato=k % 5 == 0, urug=k + 100 * takror)
    n = ishga_tushir(sc)
    turlar = [b.turi for b in xm.marshrut.bolaklar]
    sabab = SABAB.get(n.iz["holat"][-1], n.iz["holat"][-1]) if n.yordam else ""
    # Operator chaqirilgan joy (xaritada ko'rsatish uchun): s bo'yicha eng yaqin tugun
    joy = None
    if n.yordam:
        pts = [_XARITA[osm].xy(i) for i in xm.tugunlar]
        s_kerak, jami, joy = n.iz["s"][-1] * xm.uzunlik_xarita / xm.marshrut.uzunlik, 0.0, xm.tugunlar[-1]
        for i in range(1, len(pts)):
            jami += math.dist(pts[i - 1], pts[i])
            if jami >= s_kerak:
                joy = xm.tugunlar[i]
                break
    # Uzoq kutiladigan o'tishlarda (xarita bahosi > 30 s) haqiqatda qancha kutdi: chiziq oldida o'tgan vaqt
    kutishlar = []
    for b in xm.marshrut.otishlar():
        baho = kutish_bahosi(b)
        if baho > 30:
            ts = [t for t, s in zip(n.iz["t"], n.iz["s"]) if b.boshi - 3 < s < b.boshi]
            if ts and n.iz["s"][-1] >= b.boshi:
                kutishlar.append((baho, max(ts) - min(ts)))
    n.iz = {}  # jarayonlar orasida katta ma'lumot uzatmaymiz
    return (k, takror, n, xm.marshrut.uzunlik, turlar.count("otish"),
            sum(1 for b in xm.marshrut.bolaklar if b.turi == "otish" and b.svetofor), sabab, joy, xm.tugunlar,
            kutishlar)


def _rasm(xarita, natijalar, fayl):
    """Chirchiq xaritasi (SVG, qo'shimcha kutubxonasiz): ko'chalar, marshrutlar, ombor, svetoforlar va
    operator chaqirilgan joylar."""
    nuqtalar = [xarita.xy(i) for i in xarita.asosiy]
    x0, x1 = min(p[0] for p in nuqtalar), max(p[0] for p in nuqtalar)
    y0, y1 = min(p[1] for p in nuqtalar), max(p[1] for p in nuqtalar)
    k = 900 / max(x1 - x0, y1 - y0)
    W, H = (x1 - x0) * k + 20, (y1 - y0) * k + 60

    def xy(i):
        x, y = xarita.xy(i)
        return f"{(x - x0) * k + 10:.1f},{(y1 - y) * k + 40:.1f}"

    q = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" font-family="sans-serif">',
         f'<rect width="100%" height="100%" fill="white"/>',
         '<text x="10" y="22" font-size="15">Chirchiq: ombordan 10 manzilga skuter marshrutlari (OpenStreetMap)</text>']
    for y in xarita.yollar:
        if not any(i in xarita.asosiy for i in y.tugunlar):
            continue
        katta = y.turi in ("primary", "secondary", "trunk")
        q.append(f'<polyline points="{" ".join(xy(i) for i in y.tugunlar)}" fill="none" '
                 f'stroke="{"#999" if katta else "#d4d4d4"}" stroke-width="{2.2 if katta else 0.8}"/>')
    ranglar = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#d62728"]
    chizilgan = set()
    for n_ in natijalar:
        m, tugunlar = n_[0], n_[8]
        if m in chizilgan:
            continue
        chizilgan.add(m)
        r = ranglar[(m - 1) % len(ranglar)]
        q.append(f'<polyline points="{" ".join(xy(i) for i in tugunlar)}" fill="none" stroke="{r}" '
                 f'stroke-width="3" stroke-opacity="0.75"/>')
        x, y = xy(tugunlar[-1]).split(",")
        q.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{r}" stroke="black"/>'
                 f'<text x="{float(x) + 7:.1f}" y="{float(y) + 4:.1f}" font-size="11">{m}. {CHIRCHIQ_MANZILLAR[m - 1][0]}</text>')
    for t in xarita.tugunlar.values():
        if t.svetofor and t.id in xarita._yonma:
            x, y = xy(t.id).split(",")
            q.append(f'<rect x="{float(x) - 3:.1f}" y="{float(y) - 3:.1f}" width="6" height="6" fill="#2ca02c"/>')
    for n_ in natijalar:
        if n_[7] is not None:
            x, y = map(float, xy(n_[7]).split(","))
            q.append(f'<path d="M{x - 5},{y - 5}L{x + 5},{y + 5}M{x - 5},{y + 5}L{x + 5},{y - 5}" stroke="red" stroke-width="2.5"/>')
    x, y = xy(xarita.eng_yaqin_tugun(*CHIRCHIQ_OMBOR[1:])).split(",")
    q.append(f'<circle cx="{x}" cy="{y}" r="9" fill="gold" stroke="black" stroke-width="2"/>')
    q.append(f'<text x="10" y="{H - 10:.0f}" font-size="12">Sariq doira = ombor, rangli chiziq = marshrut, '
             'qizil X = operator chaqirilgan joy, yashil kvadrat = xaritadagi svetofor. (c) OpenStreetMap</text>')
    q.append("</svg>")
    Path(fayl).write_text("\n".join(q), encoding="utf-8")


def chirchiq(takror):
    """Chirchiq xaritasi: ombordan 10 ta manzilga, har biri takror marta (har safar boshqa ko'cha holati)."""
    osm = str(CHIRCHIQ_OSM)
    xarita = Xarita.osm_dan(osm)
    print(f"Xarita: Chirchiq (OpenStreetMap): {len(xarita.tugunlar)} tugun, {len(xarita.yollar)} yo'l "
          f"(skuter yura oladigan asosiy tarmoqda {len(xarita.asosiy)} tugun), "
          f"{sum(t.svetofor for t in xarita.tugunlar.values())} ta svetofor belgilangan")
    bosh = CHIRCHIQ_OMBOR[1:]
    juftlar = [(bosh, (lat, lon)) for _, lat, lon in CHIRCHIQ_MANZILLAR]
    print(f"Boshlanish: {CHIRCHIQ_OMBOR[0]}")
    for (lat, lon), n in zip([bosh] + [m for _, m in juftlar], [CHIRCHIQ_OMBOR[0]] + [n for n, *_ in CHIRCHIQ_MANZILLAR]):
        t = xarita.tugunlar[xarita.eng_yaqin_tugun(lat, lon)]
        d = xarita.masofa_ll((lat, lon), (t.lat, t.lon))
        if d > 150:
            print(f"  diqqat: {n} eng yaqin yurish mumkin bo'lgan ko'chadan {d:.0f} m uzoqda")
    xatolar = modul_sinovlari(xarita, juftlar)
    print(f"Xarita moduli sinovlari: {'o`tdi' if not xatolar else '; '.join(xatolar)}")

    with Pool() as p:
        natijalar = p.map(_sim, [(k, osm, b, m, u) for u in range(takror) for k, (b, m) in enumerate(juftlar, 1)])
    print(f"\nHar bir manzil {takror} marta (har safar boshqa mashinalar, odamlar, to'xtagan mashinalar):\n")
    print(f"{'Manzil':34} {'Uzunlik':>8} {'Chorraha':>9} {'O`zi yetdi':>10} {'Operator':>9} {'To`qn.':>7} {'O`rt. vaqt':>10}")
    sabablar = {}
    for k, (nomi, *_) in enumerate(CHIRCHIQ_MANZILLAR, 1):
        r = [x for x in natijalar if x[0] == k]
        yetdi = [x for x in r if x[2].yetib_keldi]
        toq = sum(not _xavfsiz(x[2]) for x in r)
        vaqt = sum(x[2].vaqt for x in yetdi) / len(yetdi) if yetdi else float("nan")
        print(f"{nomi:34} {r[0][3]:7.0f}m {r[0][4]:9} {len(yetdi):>7}/{len(r)} {sum(x[2].yordam for x in r):>9} "
              f"{toq:>7} {vaqt / 60:8.1f}min")
        for x in r:
            if x[6]:
                sabablar[x[6]] = sabablar.get(x[6], 0) + 1
            if not _xavfsiz(x[2]):
                xatolar.append(f"{nomi} ({x[1] + 1}-marta): to'qnashuv")
            elif not x[2].yetib_keldi and not x[2].yordam:
                xatolar.append(f"{nomi} ({x[1] + 1}-marta): vaqt chegarasida yetmadi")
    jami = len(natijalar)
    yordam = sum(x[2].yordam for x in natijalar)
    yetdi = [x for x in natijalar if x[2].yetib_keldi]
    print(f"\nJami: {jami} ta yetkazish. O'zi yetdi: {len(yetdi)}, operator chaqirdi: {yordam}, "
          f"to'qnashuv: {sum(not _xavfsiz(x[2]) for x in natijalar)}")
    if yetdi:
        print(f"O'rtacha tezlik (yetganlar): {sum(x[2].ortacha_kmh for x in yetdi) / len(yetdi):.1f} km/soat")
    kut = sorted(w for x in natijalar for _, w in x[9])
    if kut:
        print(f"Svetoforsiz katta ko'chani kesib o'tishda kutish ({len(kut)} marta): o'rtacha {sum(kut) / len(kut):.0f} s, "
              f"mediana {kut[len(kut) // 2]:.0f} s, eng uzoq {kut[-1]:.0f} s; "
              f"2 daqiqadan uzoq: {sum(w > 120 for w in kut)} marta")
    if sabablar:
        print("Operator chaqirish sabablari: " + ", ".join(f"{s_} - {n_}" for s_, n_ in sorted(sabablar.items(), key=lambda z: -z[1])))
    # Haqiqiy xaritada operator chaqiruvlari ko'p (ombordan g'arbga har yetkazish svetoforsiz Alisher Navoiy
    # ko'chasini kesadi), shuning uchun bu chegara faqat yomonlashishdan himoya: asosiy talab - to'qnashuv yo'q.
    if yordam > 0.65 * jami:
        xatolar.append(f"operator {yordam}/{jami} marta kerak bo'ldi")
    fayl = Path(__file__).with_name("natijalar_chirchiq.svg")
    _rasm(xarita, natijalar, fayl)
    print(f"Rasm: {fayl.name}")
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


def uzoq_sinov(km):
    """'Skuterga tayyor' 1-mezoni: Chirchiqda jami km kilometr yurish, birorta to'qnashuvsiz.

    Ombordan manzilga va manzildan omborga qaytish navbatma-navbat, har safar boshqa ko'cha holati.
    Operator chaqirilgan yetkazishda shu joygacha yurilgan masofa hisoblanadi.
    """
    osm = str(CHIRCHIQ_OSM)
    bosh = CHIRCHIQ_OMBOR[1:]
    vazifalar = []
    for u in range(1000):
        for k, (_, lat, lon) in enumerate(CHIRCHIQ_MANZILLAR, 1):
            vazifalar.append((k, osm, bosh, (lat, lon), 2 * u + 100))
            vazifalar.append((k, osm, (lat, lon), bosh, 2 * u + 101))
    jami_m, natijalar, xatolar = 0.0, [], []
    with Pool() as p:
        for r in p.imap(_sim, vazifalar, chunksize=1):
            n = r[2]
            jami_m += n.ortacha_kmh / 3.6 * n.vaqt
            natijalar.append(r)
            if not _xavfsiz(n):
                xatolar.append(f"{n.nomi} ({r[1]}): to'qnashuv")
                print(f"  TO'QNASHUV: {xatolar[-1]}", flush=True)
            if len(natijalar) % 50 == 0:
                print(f"  {len(natijalar)} ta safar, {jami_m / 1000:.0f} km, to'qnashuv {len(xatolar)}", flush=True)
            if jami_m >= km * 1000:
                p.terminate()
                break
    yetdi = sum(x[2].yetib_keldi for x in natijalar)
    yordam = sum(x[2].yordam for x in natijalar)
    soat = sum(x[2].vaqt for x in natijalar) / 3600
    print(f"\nJami: {jami_m / 1000:.0f} km, {len(natijalar)} ta safar ({soat:.0f} soat), o'zi yetdi {yetdi}, "
          f"operator {yordam}, to'qnashuv {len(xatolar)}")
    print(f"Mashina yonidan o'tishda eng kam oraliq: {min(x[2].yaqin_otish for x in natijalar):.2f} m; "
          f"favqulodda tormoz: {sum(x[2].favqulodda for x in natijalar)}")
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


def main():
    args = sys.argv[1:]
    if "--km" in args:
        return uzoq_sinov(float(args[args.index("--km") + 1]))
    if "--chirchiq" in args:
        i = args.index("--chirchiq")
        takror = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 3
        return chirchiq(takror)
    if "--osm" in args:
        osm = nomi = args[args.index("--osm") + 1]
    else:
        osm, nomi = sinov_shahri_osm(), "sun'iy sinov shahri"
    soni = 10
    xarita = Xarita.osm_dan(osm)
    print(f"Xarita: {nomi}: {len(xarita.tugunlar)} tugun, {len(xarita.yollar)} yo'l "
          f"(asosiy tarmoqda {len(xarita.asosiy)} tugun), {sum(t.svetofor for t in xarita.tugunlar.values())} svetofor")
    juftlar = manzillar(xarita, soni)
    xatolar = modul_sinovlari(xarita, juftlar)
    print(f"Xarita moduli sinovlari: {'o`tdi' if not xatolar else '; '.join(xatolar)}")

    with Pool() as p:
        natijalar = p.map(_sim, [(k, osm, b, m, 0) for k, (b, m) in enumerate(juftlar, 1)])
    print(f"\n{'Manzil':10} {'Uzunlik':>8} {'Chorraha':>9} {'Svetofor':>9} {'Vaqt':>7} {'Yetdi':>6} Xavfsiz")
    for k, _, n, uz, ch, sv, *_ in natijalar:
        print(f"{n.nomi:10} {uz:7.0f}m {ch:9} {sv:9} {n.vaqt:6.0f}s {'ha' if n.yetib_keldi else 'yo`q':>6} "
              f"{'ha' if _xavfsiz(n) else 'YO`Q'}{'  (operator)' if n.yordam else ''}")
        if not _xavfsiz(n):
            xatolar.append(f"{n.nomi}: to'qnashuv")
        elif not n.yetib_keldi and not n.yordam:
            xatolar.append(f"{n.nomi}: vaqt chegarasida yetmadi")
    yordam = sum(x[2].yordam for x in natijalar)
    if yordam > 0.2 * soni:
        xatolar.append(f"operator {yordam}/{soni} marta kerak bo'ldi")
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


if __name__ == "__main__":
    sys.exit(main())
