"""Ko'cha xaritasi: manzilgacha yo'l topish va uni skuter marshrutiga (Marshrut bo'laklariga) aylantirish.

Xarita manbaga bog'lanmagan: ichki model (Tugun, Yol, Xarita) har qanday manbadan to'ldiriladi. Hozir
OpenStreetMap (.osm XML) o'qiladi; Yandex (tijorat litsenziyasi bilan) yoki boshqa manba uchun faqat
o'quvchi funksiya qo'shiladi.

Skuter yo'lning o'ng chetida yuradi, shuning uchun:
- avtomagistral va tranzit yo'llar (motorway, trunk) ishlatilmaydi, katta yo'llar (primary) qimmatroq;
- bir tomonlama yo'lga teskari kirilmaydi (velosipedga ruxsat bo'lmasa);
- chorrahada o'ngga oddiy burilish, chapga ikki bosqichda (ko'ndalang ko'chani, keyin o'z ko'chamizni kesib o'tish);
- svetofor, polosalar soni, velosiped yo'lagi va parkovka teglardan olinadi.
"""

from dataclasses import dataclass, field
import heapq
import math
import xml.etree.ElementTree as ET

from .marshrut import Bolak, Marshrut

YER_RADIUSI = 6371000.0
POLOSA_KENGLIGI = 3.5

# Yo'l turi -> narx ko'paytiruvchisi (None = skuter yurmaydi)
YOL_NARXI = {
    "residential": 1.0, "living_street": 1.0, "unclassified": 1.0, "service": 1.3,
    "tertiary": 1.1, "tertiary_link": 1.1, "secondary": 1.4, "secondary_link": 1.4,
    "primary": 2.5, "primary_link": 2.5, "cycleway": 0.8,
    "motorway": None, "motorway_link": None, "trunk": None, "trunk_link": None,
}
# Teg bo'lmasa, ikki tomonlama yo'ldagi jami polosalar soni
STANDART_POLOSALAR = {"secondary": 4, "secondary_link": 2, "primary": 4, "primary_link": 2}


@dataclass
class Tugun:
    id: int
    lat: float
    lon: float
    svetofor: bool = False
    otish_joyi: bool = False


@dataclass
class Yol:
    id: int
    tugunlar: list
    turi: str
    polosalar: int = 0            # jami polosalar (ikki tomonga), 0 = noma'lum
    bir_tomonlama: bool = False
    velo_teskari: bool = False    # bir tomonlama, lekin velosipedga teskari yurish mumkin
    velo_yolak: bool = False      # o'ng tomonda velosiped yo'lagi
    parkovka: bool = False        # o'ng chetda mashina to'xtaydi
    nomi: str = ""

    def bizning_polosalar(self):
        """Biz yuradigan yo'nalishdagi polosalar soni."""
        jami = self.polosalar or STANDART_POLOSALAR.get(self.turi, 2)
        if self.bir_tomonlama:
            return max(1, self.polosalar or 1)
        return max(1, jami // 2)

    def jami_polosalar(self):
        """Ko'ndalang kesib o'tganda yo'lning to'liq kengligi (polosalarda)."""
        if self.bir_tomonlama:
            return max(1, self.polosalar or 1)
        return max(2, self.polosalar or STANDART_POLOSALAR.get(self.turi, 2))


@dataclass
class Burilish:
    """Marshrutdagi tugun: qanday burilamiz va u chorrahami."""
    tugun: int
    burchak: float                # rad, chapga musbat
    chorraha: bool
    svetofor: bool
    kesuvchi_polosalar: int       # ko'ndalang yo'lning jami polosalari


@dataclass
class XaritaMarshruti:
    tugunlar: list                # yo'l bo'ylab tugun id lari
    marshrut: Marshrut            # skuter dasturi uchun bo'laklar
    uzunlik_xarita: float         # xaritadagi chiziq uzunligi (m)
    burilishlar: list = field(default_factory=list)


class Xarita:
    def __init__(self, tugunlar, yollar):
        self.tugunlar = tugunlar          # id -> Tugun
        self.yollar = [y for y in yollar if YOL_NARXI.get(y.turi, "yoq") != "yoq"]
        self.qoshni = {}                  # id -> [(qo'shni id, Yol, uzunlik)]
        self.tugun_yollari = {}           # id -> {Yol id, ...} (chorrahani aniqlash uchun)
        for y in self.yollar:
            for a in y.tugunlar:
                self.tugun_yollari.setdefault(a, set()).add(y.id)
            if YOL_NARXI.get(y.turi) is None:
                continue
            for a, b in zip(y.tugunlar, y.tugunlar[1:]):
                l = self.masofa(a, b)
                self.qoshni.setdefault(a, []).append((b, y, l))
                if not y.bir_tomonlama or y.velo_teskari:
                    self.qoshni.setdefault(b, []).append((a, y, l))
        self.yol_id = {y.id: y for y in self.yollar}
        lat0 = sum(t.lat for t in tugunlar.values()) / max(1, len(tugunlar))
        self._cos = math.cos(math.radians(lat0))

    # --- o'qish ---
    @classmethod
    def osm_dan(cls, manba):
        """OpenStreetMap XML (.osm) fayl yo'li yoki matnidan xarita."""
        if manba.lstrip().startswith("<"):
            ildiz = ET.fromstring(manba)
        else:
            ildiz = ET.parse(manba).getroot()
        tugunlar, yollar = {}, []
        for n in ildiz.iter("node"):
            teg = {t.get("k"): t.get("v") for t in n.iter("tag")}
            hw = teg.get("highway", "")
            tugunlar[int(n.get("id"))] = Tugun(
                int(n.get("id")), float(n.get("lat")), float(n.get("lon")),
                svetofor=hw == "traffic_signals" or teg.get("crossing") == "traffic_signals",
                otish_joyi=hw == "crossing")
        for w in ildiz.iter("way"):
            teg = {t.get("k"): t.get("v") for t in w.iter("tag")}
            if "highway" not in teg:
                continue
            ids = [int(nd.get("ref")) for nd in w.iter("nd") if int(nd.get("ref")) in tugunlar]
            if len(ids) < 2:
                continue
            ow = teg.get("oneway", "no")
            if ow == "-1":
                ids, ow = ids[::-1], "yes"
            try:
                polosalar = int(teg.get("lanes", "0").split(";")[0])
            except ValueError:
                polosalar = 0
            velo = any(teg.get(k, "") in ("lane", "track", "shared_lane")
                       for k in ("cycleway", "cycleway:right", "cycleway:both"))
            park = any(teg.get(k, "") in ("parallel", "diagonal", "perpendicular", "lane", "street_side", "yes")
                       for k in ("parking:lane:right", "parking:lane:both", "parking:right", "parking:both"))
            yollar.append(Yol(int(w.get("id")), ids, teg["highway"], polosalar,
                              bir_tomonlama=ow in ("yes", "true", "1"),
                              velo_teskari=teg.get("oneway:bicycle") == "no", velo_yolak=velo,
                              parkovka=park, nomi=teg.get("name", "")))
        return cls(tugunlar, yollar)

    # --- geometriya ---
    def xy(self, i):
        """Tugun koordinatasi metrda (mahalliy tekislik: x = sharq, y = shimol)."""
        t = self.tugunlar[i]
        return (math.radians(t.lon) * YER_RADIUSI * self._cos, math.radians(t.lat) * YER_RADIUSI)

    def masofa(self, a, b):
        ta, tb = self.tugunlar[a], self.tugunlar[b]
        dx = math.radians(tb.lon - ta.lon) * YER_RADIUSI * math.cos(math.radians((ta.lat + tb.lat) / 2))
        dy = math.radians(tb.lat - ta.lat) * YER_RADIUSI
        return math.hypot(dx, dy)

    def eng_yaqin_tugun(self, lat, lon):
        """Manzilga eng yaqin, skuter yura oladigan tugun."""
        eng, m = None, math.inf
        for i in self.qoshni:
            t = self.tugunlar[i]
            d = (t.lat - lat) ** 2 + ((t.lon - lon) * self._cos) ** 2
            if d < m:
                eng, m = i, d
        return eng

    # --- yo'l topish ---
    def yol_top(self, boshi, manzil):
        """Dijkstra: tugunlar ro'yxati va har qadamdagi Yol. Topilmasa None."""
        navbat = [(0.0, boshi)]
        narx = {boshi: 0.0}
        oldingi = {}
        while navbat:
            n, i = heapq.heappop(navbat)
            if i == manzil:
                break
            if n > narx.get(i, math.inf):
                continue
            for j, y, l in self.qoshni.get(i, ()):
                yangi = n + l * YOL_NARXI[y.turi]
                if yangi < narx.get(j, math.inf):
                    narx[j] = yangi
                    oldingi[j] = (i, y)
                    heapq.heappush(navbat, (yangi, j))
        if manzil not in narx:
            return None
        tugunlar, yollar = [manzil], []
        while tugunlar[-1] != boshi:
            i, y = oldingi[tugunlar[-1]]
            tugunlar.append(i)
            yollar.append(y)
        return tugunlar[::-1], yollar[::-1]

    def _chorrahami(self, i):
        return len(self.tugun_yollari.get(i, ())) >= 2 and len(self._tarmoqlar(i)) >= 3

    def _tarmoqlar(self, i):
        """Tugundan chiqadigan yo'nalishlar (qo'shni tugunlar, yo'l yo'nalishidan qat'i nazar)."""
        q = set()
        for y in self.yollar:
            t = y.tugunlar
            for k, a in enumerate(t):
                if a == i:
                    if k > 0:
                        q.add(t[k - 1])
                    if k + 1 < len(t):
                        q.add(t[k + 1])
        return q

    def _svetofor_yaqinmi(self, i, radius=25.0):
        if self.tugunlar[i].svetofor:
            return True
        for j in self._tarmoqlar(i):
            if self.tugunlar[j].svetofor and self.masofa(i, j) < radius:
                return True
        return False

    def _kesuvchi_polosalar(self, i, kiruvchi, chiquvchi):
        boshqa = [self.yol_id[k] for k in self.tugun_yollari.get(i, ()) if k not in (kiruvchi.id, chiquvchi.id)]
        if not boshqa:
            boshqa = [chiquvchi if chiquvchi.id != kiruvchi.id else kiruvchi]
        return min(4, max(y.jami_polosalar() for y in boshqa))

    # --- skuter marshruti ---
    def skuter_marshruti(self, boshi, manzil, asosiy_d=None):
        """Ikki nuqta (lat, lon) orasida skuter marshruti. Topilmasa None.

        asosiy_d(Bolak) -> skuterning bordyurdan masofasi (chap burilish radiusi uchun); berilmasa 0,8 m.
        """
        a = self.eng_yaqin_tugun(*boshi)
        b = self.eng_yaqin_tugun(*manzil)
        topildi = self.yol_top(a, b) if a is not None and b is not None and a != b else None
        if topildi is None:
            return None
        tugunlar, yollar = topildi
        return self.marshrutga_aylantir(tugunlar, yollar, asosiy_d or (lambda bolak: 0.8))

    def marshrutga_aylantir(self, tugunlar, yollar, asosiy_d):
        """Tugunlar zanjirini to'g'ri yo'l bo'laklari, burilishlar va chorrahalarga aylantiradi."""
        pts = [self.xy(i) for i in tugunlar]
        uzunlik_xarita = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        # Har bir oraliq tugundagi burilish burchagi
        burilishlar = []
        for k in range(1, len(tugunlar) - 1):
            h1 = math.atan2(pts[k][1] - pts[k - 1][1], pts[k][0] - pts[k - 1][0])
            h2 = math.atan2(pts[k + 1][1] - pts[k][1], pts[k + 1][0] - pts[k][0])
            burchak = (h2 - h1 + math.pi) % (2 * math.pi) - math.pi
            i = tugunlar[k]
            chorraha = self._chorrahami(i)
            burilishlar.append(Burilish(i, burchak, chorraha,
                                        chorraha and self._svetofor_yaqinmi(i),
                                        self._kesuvchi_polosalar(i, yollar[k - 1], yollar[k]) if chorraha else 0))

        # Har bir tugunda nima qo'yiladi: (kirishdan oldin qisqartirish, chiqishdan keyin qisqartirish, bo'laklar)
        def yol_bolagi(y, uzunlik):
            return Bolak("yol", max(1.0, uzunlik), yollar=y.bizning_polosalar(),
                         velo=1.5 if y.velo_yolak else 0.0, parkovka=2.2 if y.parkovka else 0.0)

        tugun_qismlari = []
        for k, br in enumerate(burilishlar, start=1):
            kir = yollar[k - 1]
            th = br.burchak
            if br.chorraha and abs(th) < math.radians(30):
                # To'g'ri kesib o'tish
                w = br.kesuvchi_polosalar * POLOSA_KENGLIGI
                tugun_qismlari.append((w / 2, w / 2, [Bolak("otish", w, yollar=br.kesuvchi_polosalar,
                                                              svetofor=br.svetofor)]))
            elif br.chorraha and th > 0:
                # Chapga: ko'ndalang ko'chani, burchakda burilib, o'z (eski) ko'chamizni kesib o'tamiz
                w1 = br.kesuvchi_polosalar * POLOSA_KENGLIGI
                p2 = min(4, kir.jami_polosalar())
                w2 = p2 * POLOSA_KENGLIGI
                r = asosiy_d(yol_bolagi(kir, 10.0)) + 3.5
                tugun_qismlari.append((w2 / 2, w1 / 2, [
                    Bolak("otish", w1, yollar=br.kesuvchi_polosalar, svetofor=br.svetofor),
                    Bolak("burilish", r * th, egrilik=1 / r),
                    Bolak("otish", w2, yollar=p2, svetofor=br.svetofor)]))
            elif abs(th) > math.radians(3):
                # O'ngga burilish (chorrahada r = 6 m) yoki ko'chaning egilishi
                r = 6.0 if br.chorraha else 20.0
                kesish = r * math.tan(abs(th) / 2)
                tugun_qismlari.append((kesish, kesish, [Bolak("burilish", r * abs(th),
                                                                egrilik=math.copysign(1 / r, th))]))
            else:
                tugun_qismlari.append((0.0, 0.0, []))

        bolaklar = []
        for k, y in enumerate(yollar):
            uz = math.dist(pts[k], pts[k + 1])
            if k > 0:
                uz -= tugun_qismlari[k - 1][1]
            if k < len(tugun_qismlari):
                uz -= tugun_qismlari[k][0]
            bolaklar.append(yol_bolagi(y, uz))
            if k < len(tugun_qismlari):
                bolaklar.extend(tugun_qismlari[k][2])
        # Bir xil tartibdagi qo'shni yo'l bo'laklarini birlashtiramiz
        birlashgan = []
        for b in bolaklar:
            o = birlashgan[-1] if birlashgan else None
            if (o is not None and o.turi == b.turi == "yol" and (o.yollar, o.velo, o.parkovka) == (b.yollar, b.velo, b.parkovka)):
                o.uzunlik += b.uzunlik
            else:
                birlashgan.append(b)
        return XaritaMarshruti(tugunlar, Marshrut(birlashgan), uzunlik_xarita, burilishlar)
