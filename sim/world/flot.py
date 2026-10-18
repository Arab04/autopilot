"""Flot va dispetcherlik (E bosqich): bir nechta virtual skuter, buyurtmalar navbati, operatorlar.

Har bir skuterni to'liq (piyoda, mashina darajasida) simulyatsiya qilish o'rniga flot darajasidagi model:
skuter Chirchiq xaritasidagi haqiqiy marshrut bo'ylab yuradi, chorrahalarda kutadi. Kutish vaqtlari va
tezlik batafsil simulyatordan (4-bosqich, 1000 km) olingan:
  - yo'lda o'rtacha tezlik YURISH_TEZLIGI (batafsil simulyatordagi safar vaqtlariga moslangan);
  - har chorrahada kutish: o'rtachasi xaritaning kutish_bahosi(), taqsimoti eksponensial;
  - kutish 3 baravar (kamida 2 daqiqa, ko'pi 10 daqiqa) cho'zilsa, skuter operatordan ruxsat so'raydi
    (skuter dasturidagi qoida bilan bir xil); to'siqni aylanib o'tolmaslik ham km ga qarab tasodifiy.
Operatorlar soni cheklangan: bir operator bir paytda bitta so'rovni ko'radi, qolganlar navbatda kutadi.
Shu model bilan "N ta buyurtma/soatga nechta skuter va nechta operator kerak" degan savolga javob olinadi.

Buyurtma hayoti: yangi -> tayinlandi (skuter omborda yuklanmoqda) -> yolda -> yetib_keldi (mijoz PIN bilan
qutini ochadi) -> topshirildi; mijoz 10 daqiqada kelmasa -> qaytarildi (skuter yukni omborga olib qaytadi).

CRM yoki mijoz boti buyurtmani HTTP API orqali beradi (operator_panel.py serverida /api/...), kodga
qarang: Flot.buyurtma_ber, Flot.qutini_och, Flot.buyurtma_json.
"""

import bisect
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from xarita_sinovlar import CHIRCHIQ_MANZILLAR, CHIRCHIQ_OMBOR, CHIRCHIQ_OSM, _asosiy  # sys.path ni ham sozlaydi
from autopilot.xarita import Xarita, kutish_bahosi

YURISH_TEZLIGI = 14 / 3.6         # m/s, chorrahalarda kutishdan tashqari (batafsil simulyatorga moslangan)
SARF_KM = 2.5                     # batareya % / km (48V 25Ah, ~40 km)
ZAHIRA = 15.0                     # % - safardan keyin ham qolishi kerak
ZARYAD_TEZLIGI = 0.5 / 60         # % / s (0 -> 100% taxminan 3,3 soat)
BATAREYA_ALMASHTIRISH = 100 / 1800  # % / s: bo'sh batareyani to'lasiga almashtirish (~30 daq ichida)
ZARYAD_TUGASH = 95.0
YUKLASH = (60, 120)               # omborda qutiga yuklash, s
MIJOZ_KUTISH = 600                # mijoz shuncha kelmasa, yuk omborga qaytadi, s
OPERATOR_VAQTI = (20, 60)         # operator chorrahaga ruxsat berishi, s
YORDAM_VAQTI = (60, 180)          # operator to'siqdan qo'lda olib o'tishi, s
YORDAM_KM = 0.01                  # har km da "qolib ketish" ehtimoli
KUTISH_SIGMA = 1.25               # chorrahada kutish taqsimoti (lognormal) kengligi
YETKAZISH_MAQSADI = 45 * 60       # "o'z vaqtida" chegarasi (buyurtmadan topshirishgacha), s

def operator_ehtimoli(kutilgan):
    """Chorrahada operator chaqirilishi ehtimoli. Batafsil simulyatordan (4-bosqich, 100 ta safar):
    42 ta chaqiruvning 34 tasi Navoiy ko'chasidagi ikki o'tishda (kutish_bahosi ~100-110 s), deyarli
    har safar shulardan biridan o'tadi; qolgan o'rtacha chorrahalarda ~3%."""
    return 0.34 if kutilgan >= 100 else 0.03 if kutilgan > 20 else 0.0


HOLAT_NOMLARI = {
    "omborda": "Omborda, bo'sh", "zaryad": "Zaryadlanmoqda", "yuklash": "Yuklanmoqda",
    "mijozga": "Mijozga ketmoqda", "mijozda": "Mijozni kutmoqda", "qaytish": "Omborga qaytmoqda",
}


@dataclass
class Marshrut:
    """Xaritadagi yo'l: chiziq (x, y metr), chorrahalar (masofa, kutilgan kutish s)."""
    nuqtalar: list
    masofalar: list               # har nuqtagacha jamlangan masofa
    otishlar: list                # [(masofa, kutilgan_kutish)]

    @property
    def uzunlik(self):
        return self.masofalar[-1]

    def xy(self, s):
        i = max(0, min(len(self.nuqtalar) - 2, bisect.bisect_right(self.masofalar, s) - 1))
        (x0, y0), (x1, y1) = self.nuqtalar[i], self.nuqtalar[i + 1]
        l = self.masofalar[i + 1] - self.masofalar[i]
        k = 0.0 if l <= 0 else min(1.0, max(0.0, (s - self.masofalar[i]) / l))
        return x0 + k * (x1 - x0), y0 + k * (y1 - y0)

    def kutilgan_vaqt(self):
        return self.uzunlik / YURISH_TEZLIGI + sum(k for _, k in self.otishlar)

    def teskari(self):
        L = self.uzunlik
        return Marshrut(self.nuqtalar[::-1], [L - m for m in self.masofalar[::-1]],
                        [(L - m, k) for m, k in self.otishlar[::-1]])


@dataclass
class Buyurtma:
    id: int
    nomi: str
    lat: float
    lon: float
    pin: str
    yaratildi: float
    mijoz: str = ""
    tel: str = ""
    izoh: str = ""
    manba: str = "panel"           # panel / crm / avto
    avto_mijoz: bool = True        # True: mijoz qutini o'zi (tasodifiy vaqtda) ochadi; False: PIN API orqali
    holat: str = "yangi"
    skuter: int = None
    tayinlandi: float = None
    yetib_keldi: float = None
    topshirildi: float = None
    mijoz_keladi: float = None     # avto mijoz qachon keladi (sim vaqti)
    pin_urinish: int = 0
    marshrut: Marshrut = field(default=None, repr=False)


@dataclass
class Skuter:
    id: int
    batareya: float = 100.0
    holat: str = "omborda"
    buyurtma: Buyurtma = None
    marshrut: Marshrut = None
    s: float = 0.0                 # marshrut bo'ylab masofa
    keyingi_otish: int = 0
    kutish_tugaydi: float = None   # chorrahada kutish (sim vaqti)
    operator_soradi: bool = False  # operator navbatida
    operator_tugaydi: float = None
    holat_tugaydi: float = None    # yuklash tugashi va h.k.
    km: float = 0.0
    band_vaqt: float = 0.0
    operator_chaqiruv: int = 0


class Flot:
    def __init__(self, skuterlar=5, operatorlar=2, avto_buyurtma=6.0, urug=1, xarita=None, vaqt_tezligi=10.0,
                 zaryad_tezligi=ZARYAD_TEZLIGI):
        self.lock = threading.RLock()
        self.rnd = random.Random(urug)
        self.xarita = xarita or Xarita.osm_dan(str(CHIRCHIQ_OSM))
        self.ombor = CHIRCHIQ_OMBOR[1:]
        self.ombor_xy = self._xy(*self.ombor)
        self.manzillar = [(n, la, lo) for n, la, lo in CHIRCHIQ_MANZILLAR] + self._tasodifiy_manzillar(30)
        self._marshrutlar = {}     # tugun -> Marshrut (ombordan)
        self.t = 0.0
        self.vaqt_tezligi = vaqt_tezligi
        self.zaryad_tezligi = zaryad_tezligi   # %/s; batareya almashtirish uchun BATAREYA_ALMASHTIRISH
        self.pauza = False
        self.avto_buyurtma = avto_buyurtma   # buyurtma / soat (0 = faqat API dan)
        self.skuterlar = [Skuter(i + 1) for i in range(skuterlar)]
        self.operatorlar = operatorlar
        self.operator_band = []    # [(tugash vaqti, skuter id)]
        self.operator_navbat = []  # (so'rov vaqti, skuter id, turi), vaqt bo'yicha tartibda
        self.buyurtmalar = {}
        self.navbat = deque()      # tayinlanmagan buyurtma id lari
        self._keyingi_id = 1
        self._keyingi_avto = self._avto_oraliq()
        self.jurnal = deque(maxlen=200)
        self.jurnal_n = 0
        self.stat = {"operator_kutish": [], "operator_band_s": 0.0, "operator_chaqiruv": 0, "yordam": 0}

    # ---------- xarita ----------
    def _xy(self, lat, lon):
        return self.xarita.xy(self.xarita.eng_yaqin_tugun(lat, lon))

    def _tasodifiy_manzillar(self, soni):
        """Ombordan 0,8-6 km uzoqlikdagi tasodifiy uylar (asosiy tarmoq tugunlari)."""
        x = self.xarita
        ids = sorted(x.asosiy)
        rnd = random.Random(7)
        natija = []
        while len(natija) < soni:
            t = x.tugunlar[rnd.choice(ids)]
            d = Xarita.masofa_ll(self.ombor, (t.lat, t.lon))
            if 800 <= d <= 6000:
                natija.append((f"Uy {len(natija) + 1}", round(t.lat, 5), round(t.lon, 5)))
        return natija

    def marshrut(self, lat, lon):
        """Ombordan (lat, lon) gacha marshrut (keshlanadi). Topilmasa None."""
        tugun = self.xarita.eng_yaqin_tugun(lat, lon)
        if tugun in self._marshrutlar:
            return self._marshrutlar[tugun]
        xm = self.xarita.skuter_marshruti(self.ombor, (lat, lon), _asosiy)
        if xm is None:
            self._marshrutlar[tugun] = None
            return None
        pts = [self.xarita.xy(i) for i in xm.tugunlar]
        mas = [0.0]
        for p, q in zip(pts, pts[1:]):
            mas.append(mas[-1] + math.dist(p, q))
        k = mas[-1] / max(1.0, xm.marshrut.uzunlik)   # marshrut (s) -> xarita chizig'i masofasi
        otishlar = [(b.boshi * k, kutish_bahosi(b)) for b in xm.marshrut.otishlar()]
        m = Marshrut(pts, mas, otishlar)
        self._marshrutlar[tugun] = m
        return m

    # ---------- jurnal ----------
    def yoz(self, matn):
        self.jurnal_n += 1
        self.jurnal.append({"n": self.jurnal_n, "t": round(self.t), "matn": matn})

    # ---------- buyurtmalar (API) ----------
    def buyurtma_ber(self, lat=None, lon=None, manzil=None, nomi="", mijoz="", tel="", izoh="", manba="panel",
                     avto_mijoz=True):
        """Yangi buyurtma. manzil: 1..len(manzillar) yoki lat/lon. Qaytaradi: (Buyurtma, xato)."""
        with self.lock:
            if manzil is not None:
                if not 1 <= int(manzil) <= len(self.manzillar):
                    return None, f"manzil 1..{len(self.manzillar)} bo'lishi kerak"
                nomi, lat, lon = self.manzillar[int(manzil) - 1]
            if lat is None or lon is None:
                return None, "manzil yoki lat/lon kerak"
            lat, lon = float(lat), float(lon)
            if not (math.isfinite(lat) and math.isfinite(lon)):
                return None, "lat/lon noto'g'ri"
            if Xarita.masofa_ll(self.ombor, (lat, lon)) > 15000:
                return None, "manzil xizmat hududidan tashqarida (ombordan 15 km dan uzoq)"
            m = self.marshrut(lat, lon)
            if m is None:
                return None, "bu manzilga skuter yo'li topilmadi"
            if m.uzunlik / 1000 * SARF_KM * 2 + ZAHIRA > 100:
                return None, "manzil juda uzoq: borib-qaytishga batareya yetmaydi"
            b = Buyurtma(self._keyingi_id, str(nomi or f"{lat:.5f}, {lon:.5f}")[:80], lat, lon,
                         f"{self.rnd.randrange(10000):04d}", self.t, str(mijoz)[:80], str(tel)[:30],
                         str(izoh)[:200], manba, bool(avto_mijoz))
            b.marshrut = m
            self._keyingi_id += 1
            self.buyurtmalar[b.id] = b
            self.navbat.append(b.id)
            self.yoz(f"Buyurtma #{b.id}: {b.nomi} ({manba}, {m.uzunlik / 1000:.1f} km)")
            self._dispetcher()
            return b, None

    def qutini_och(self, bid, pin):
        """Mijoz PIN kiritadi. Qaytaradi: xato matni yoki None."""
        with self.lock:
            b = self.buyurtmalar.get(bid)
            if b is None:
                return "buyurtma topilmadi"
            if b.holat != "yetib_keldi":
                return f"skuter hali yetib kelmagan (holat: {b.holat})" if b.holat in ("yangi", "tayinlandi", "yolda") \
                    else f"buyurtma yopilgan (holat: {b.holat})"
            if b.pin_urinish >= 5:
                return "PIN 5 marta xato kiritildi, operatorga murojaat qiling"
            if str(pin) != b.pin:
                b.pin_urinish += 1
                return "PIN noto'g'ri"
            self._topshir(b)
            return None

    def bekor_qil(self, bid):
        with self.lock:
            b = self.buyurtmalar.get(bid)
            if b is None:
                return "buyurtma topilmadi"
            if b.holat != "yangi":
                return "faqat hali skuterga berilmagan buyurtmani bekor qilish mumkin"
            b.holat = "bekor"
            self.navbat.remove(bid)
            self.yoz(f"Buyurtma #{bid} bekor qilindi")
            return None

    # ---------- simulyatsiya ----------
    def _avto_oraliq(self):
        return self.t + (self.rnd.expovariate(self.avto_buyurtma / 3600) if self.avto_buyurtma > 0 else math.inf)

    def qadam(self, dt=1.0):
        with self.lock:
            self.t += dt
            if self.t >= self._keyingi_avto:
                k = self.rnd.randrange(len(self.manzillar)) + 1
                self.buyurtma_ber(manzil=k, manba="avto")
                self._keyingi_avto = self._avto_oraliq()
            self._operatorlar(dt)
            for sk in self.skuterlar:
                self._skuter_qadam(sk, dt)
            self._dispetcher()

    def _kerakli_zaryad(self, m):
        return m.uzunlik / 1000 * SARF_KM * 2 + ZAHIRA

    def _dispetcher(self):
        """Navbatdagi eng eski buyurtmani omborda turgan, zaryadi yetadigan skuterga beradi
        (eng ko'p zaryadlisiga: zaryadlanayotganlar ham, agar yetsa)."""
        while self.navbat:
            b = self.buyurtmalar[self.navbat[0]]
            m = b.marshrut
            bosh = [s for s in self.skuterlar if s.holat in ("omborda", "zaryad")
                    and s.batareya >= self._kerakli_zaryad(m)]
            if not bosh:
                return
            sk = max(bosh, key=lambda s: (s.holat == "omborda", s.batareya))
            self.navbat.popleft()
            b.holat, b.skuter, b.tayinlandi = "tayinlandi", sk.id, self.t
            sk.buyurtma, sk.marshrut, sk.s, sk.keyingi_otish = b, m, 0.0, 0
            sk.holat, sk.holat_tugaydi = "yuklash", self.t + self.rnd.uniform(*YUKLASH)
            self.yoz(f"Buyurtma #{b.id} -> skuter {sk.id} (zaryad {sk.batareya:.0f}%)")

    def _operator_sora(self, sk, turi):
        sk.operator_soradi = True
        sk.operator_chaqiruv += 1
        self.stat["operator_chaqiruv"] += 1
        if turi == "yordam":
            self.stat["yordam"] += 1
        bisect.insort(self.operator_navbat, (self.t, sk.id, turi))

    def _operatorlar(self, dt):
        self.stat["operator_band_s"] += len(self.operator_band) * dt
        tugadi = [x for x in self.operator_band if x[0] <= self.t]
        self.operator_band = [x for x in self.operator_band if x[0] > self.t]
        for _, sid in tugadi:
            sk = self.skuterlar[sid - 1] if sid <= len(self.skuterlar) else None
            if sk is not None:
                if sk.kutish_tugaydi is not None:   # chorrahaga ruxsat berildi: o'tib ketadi
                    sk.keyingi_otish += 1
                sk.operator_soradi, sk.kutish_tugaydi = False, None
        while self.operator_navbat and self.operator_navbat[0][0] <= self.t and len(self.operator_band) < self.operatorlar:
            t0, sid, turi = self.operator_navbat.pop(0)
            self.stat["operator_kutish"].append(self.t - t0)
            dav = self.rnd.uniform(*(YORDAM_VAQTI if turi == "yordam" else OPERATOR_VAQTI))
            self.operator_band.append((self.t + dav, sid))

    def _skuter_qadam(self, sk, dt):
        if sk.holat in ("omborda", "zaryad"):
            # Omborda turgan skuter doim zaryadga ulanadi; zaryadlanayotgani ham buyurtma ola oladi (yetsa)
            if sk.batareya < ZARYAD_TUGASH:
                sk.batareya = min(100.0, sk.batareya + self.zaryad_tezligi * dt)
            sk.holat = "zaryad" if sk.batareya < ZARYAD_TUGASH else "omborda"
            return
        sk.band_vaqt += dt
        if sk.holat == "yuklash":
            if self.t >= sk.holat_tugaydi:
                sk.holat = "mijozga"
                sk.buyurtma.holat = "yolda"
            return
        if sk.holat == "mijozda":
            b = sk.buyurtma
            if b.avto_mijoz and b.mijoz_keladi is not None and self.t >= b.mijoz_keladi:
                self._topshir(b)
            elif self.t - b.yetib_keldi >= MIJOZ_KUTISH:
                b.holat = "qaytarildi"
                self.yoz(f"Buyurtma #{b.id}: mijoz 10 daqiqada kelmadi, yuk omborga qaytmoqda")
                self._qayt(sk)
            return
        # Harakat (mijozga yoki qaytish)
        if sk.operator_soradi:
            return
        m = sk.marshrut
        if sk.kutish_tugaydi is not None:          # chorrahada
            if self.t < sk.kutish_tugaydi:
                return
            sk.kutish_tugaydi = None
            sk.keyingi_otish += 1
        if sk.keyingi_otish < len(m.otishlar) and sk.s >= m.otishlar[sk.keyingi_otish][0]:
            kutilgan = m.otishlar[sk.keyingi_otish][1]
            chegara = min(600.0, max(120.0, 3 * kutilgan))
            if self.rnd.random() < operator_ehtimoli(kutilgan):
                # skuter uzoq kutib qoldi: operatordan ruxsat so'raydi
                sk.kutish_tugaydi = self.t + chegara
                self._operator_sora_keyin(sk, chegara)
            else:
                # Lognormal: batafsil simulyatorda katta ko'chada o'rtacha 87 s, mediana 40 s
                kutish = self.rnd.lognormvariate(math.log(kutilgan) - KUTISH_SIGMA ** 2 / 2, KUTISH_SIGMA) \
                    if kutilgan >= 1 else 0.0
                sk.kutish_tugaydi = self.t + min(kutish, chegara)
            return
        oldingi = sk.s
        chegara_s = m.otishlar[sk.keyingi_otish][0] if sk.keyingi_otish < len(m.otishlar) else m.uzunlik
        sk.s = min(chegara_s, sk.s + YURISH_TEZLIGI * dt)
        yurdi = sk.s - oldingi
        sk.km += yurdi / 1000
        sk.batareya = max(0.0, sk.batareya - yurdi / 1000 * SARF_KM)
        if yurdi > 0 and self.rnd.random() < YORDAM_KM * yurdi / 1000:
            self._operator_sora(sk, "yordam")
            return
        if sk.s >= m.uzunlik - 1e-6:
            if sk.holat == "mijozga":
                b = sk.buyurtma
                sk.holat, b.holat, b.yetib_keldi = "mijozda", "yetib_keldi", self.t
                if b.avto_mijoz:
                    r = self.rnd.random()
                    b.mijoz_keladi = self.t + (self.rnd.uniform(20, 180) if r < 0.7 else
                                               self.rnd.uniform(180, 480) if r < 0.95 else math.inf)
                self.yoz(f"Skuter {sk.id} yetib keldi: buyurtma #{b.id} ({b.nomi}), mijoz PIN bilan ochadi")
            else:
                sk.holat, sk.marshrut, sk.buyurtma = "omborda", None, None
                self.yoz(f"Skuter {sk.id} omborga qaytdi (zaryad {sk.batareya:.0f}%)")

    def _operator_sora_keyin(self, sk, kechikish):
        """Chorrahada `kechikish` s kutgandan keyin operator so'rovi: so'rov vaqtini oldinga suramiz."""
        sk.operator_soradi = True
        sk.operator_chaqiruv += 1
        self.stat["operator_chaqiruv"] += 1
        bisect.insort(self.operator_navbat, (self.t + kechikish, sk.id, "otish"))

    def _topshir(self, b):
        b.holat, b.topshirildi = "topshirildi", self.t
        sk = self.skuterlar[b.skuter - 1]
        self.yoz(f"Buyurtma #{b.id} topshirildi ({(b.topshirildi - b.yaratildi) / 60:.0f} daqiqada)")
        self._qayt(sk)

    def _qayt(self, sk):
        sk.holat = "qaytish"
        sk.marshrut = sk.marshrut.teskari()
        sk.s, sk.keyingi_otish, sk.kutish_tugaydi = 0.0, 0, None

    # ---------- sozlamalar ----------
    def sozla(self, skuterlar=None, operatorlar=None, avto_buyurtma=None, vaqt_tezligi=None, pauza=None):
        with self.lock:
            if skuterlar is not None:
                n = max(1, min(50, int(skuterlar)))
                while len(self.skuterlar) < n:
                    self.skuterlar.append(Skuter(len(self.skuterlar) + 1))
                # Kamaytirish: faqat oxiridagi omborda turganlarini olib tashlaymiz
                while len(self.skuterlar) > n and self.skuterlar[-1].holat in ("omborda", "zaryad"):
                    self.skuterlar.pop()
            if operatorlar is not None:
                self.operatorlar = max(1, min(20, int(operatorlar)))
            if avto_buyurtma is not None:
                self.avto_buyurtma = max(0.0, min(120.0, float(avto_buyurtma)))
                self._keyingi_avto = self._avto_oraliq()
            if vaqt_tezligi is not None:
                self.vaqt_tezligi = max(0.25, min(120.0, float(vaqt_tezligi)))
            if pauza is not None:
                self.pauza = bool(pauza)

    # ---------- natijalar ----------
    def korsatkichlar(self):
        with self.lock:
            tops = [b for b in self.buyurtmalar.values() if b.holat == "topshirildi"]
            vaqtlar = sorted(b.topshirildi - b.yaratildi for b in tops)
            ok = self.stat["operator_kutish"]
            soat = max(self.t, 1) / 3600
            return {
                "vaqt_soat": round(self.t / 3600, 2),
                "buyurtma": len(self.buyurtmalar),
                "topshirildi": len(tops),
                "qaytarildi": sum(b.holat == "qaytarildi" for b in self.buyurtmalar.values()),
                "navbatda": len(self.navbat),
                "ortacha_daq": round(sum(vaqtlar) / len(vaqtlar) / 60, 1) if vaqtlar else None,
                "p90_daq": round(vaqtlar[int(0.9 * (len(vaqtlar) - 1))] / 60, 1) if vaqtlar else None,
                "oz_vaqtida_foiz": round(100 * sum(v <= YETKAZISH_MAQSADI for v in vaqtlar) / len(vaqtlar)) if vaqtlar else None,
                "operator_chaqiruv": self.stat["operator_chaqiruv"],
                "operator_chaqiruv_soat": round(self.stat["operator_chaqiruv"] / soat, 1),
                "operator_bandlik_foiz": round(100 * self.stat["operator_band_s"] / max(1, self.t * max(1, self.operatorlar))),
                "operator_kutish_s": round(sum(ok) / len(ok)) if ok else 0,
                "skuter_bandlik_foiz": round(100 * sum(s.band_vaqt for s in self.skuterlar) / max(1, self.t * len(self.skuterlar))),
                "km": round(sum(s.km for s in self.skuterlar), 1),
            }

    def buyurtma_json(self, b, sirli=False):
        j = {"id": b.id, "nomi": b.nomi, "lat": b.lat, "lon": b.lon, "holat": b.holat, "skuter": b.skuter,
             "manba": b.manba, "mijoz": b.mijoz, "yaratildi": round(b.yaratildi),
             "kutmoqda_daq": round((self.t - b.yaratildi) / 60, 1)}
        if sirli:
            j["pin"] = b.pin
        if b.topshirildi is not None:
            j["yetkazish_daq"] = round((b.topshirildi - b.yaratildi) / 60, 1)
        sk = self.skuterlar[b.skuter - 1] if b.skuter and b.skuter <= len(self.skuterlar) else None
        if sk is not None and sk.buyurtma is b and sk.holat in ("yuklash", "mijozga"):
            m = sk.marshrut
            qolgan = (m.uzunlik - sk.s) / YURISH_TEZLIGI + sum(k for d, k in m.otishlar[sk.keyingi_otish:])
            if sk.holat == "yuklash":
                qolgan += max(0.0, sk.holat_tugaydi - self.t)
            j["eta_daq"] = round(qolgan / 60, 1)
            j["skuter_xy"] = [round(c - o, 1) for c, o in zip(m.xy(sk.s), self.ombor_xy)]
        return j

    def holat_json(self):
        with self.lock:
            sk = []
            for s in self.skuterlar:
                xy = s.marshrut.xy(s.s) if s.marshrut else self.ombor_xy
                sk.append({"id": s.id, "holat": s.holat, "holat_nomi": HOLAT_NOMLARI[s.holat]
                           + (" (operator)" if s.operator_soradi else " (chorrahada)" if s.kutish_tugaydi else ""),
                           "batareya": round(s.batareya), "xy": [round(xy[0] - self.ombor_xy[0], 1),
                                                                round(xy[1] - self.ombor_xy[1], 1)],
                           "buyurtma": s.buyurtma.id if s.buyurtma else None, "km": round(s.km, 1),
                           "operator": s.operator_soradi})
            faol = [b for b in self.buyurtmalar.values() if b.holat in ("yangi", "tayinlandi", "yolda", "yetib_keldi")]
            oxirgi = sorted((b for b in self.buyurtmalar.values() if b not in faol), key=lambda b: -b.id)[:15]
            return {"t": round(self.t), "vaqt_tezligi": self.vaqt_tezligi, "pauza": self.pauza,
                    "avto_buyurtma": self.avto_buyurtma, "operatorlar": self.operatorlar,
                    "operator_band": len(self.operator_band), "operator_navbat": sum(t <= self.t for t, *_ in self.operator_navbat),
                    "skuterlar": sk, "buyurtmalar": [self.buyurtma_json(b, sirli=True) for b in faol + oxirgi],
                    "korsatkich": self.korsatkichlar(), "jurnal": list(self.jurnal)[-30:]}

    def xarita_json(self):
        """Panel uchun ko'chalar (ombor atrofida 7 km, ombor = (0, 0)), manzillar."""
        x = self.xarita
        ox, oy = self.ombor_xy
        kochalar = []
        for y in x.yollar:
            if y.turi not in ("primary", "secondary", "tertiary", "trunk", "residential", "unclassified"):
                continue
            q = [x.xy(i) for i in y.tugunlar]
            if any(abs(a - ox) < 7000 and abs(b - oy) < 7000 for a, b in q):
                kochalar.append([y.turi in ("primary", "secondary", "trunk")] + [[round(a - ox), round(b - oy)] for a, b in q])
        manzillar = [[n, *[round(c - o) for c, o in zip(self._xy(la, lo), (ox, oy))]] for n, la, lo in self.manzillar]
        return {"kochalar": kochalar, "manzillar": manzillar}

    # ---------- real vaqt ----------
    def ishla(self):
        """Server uchun: sim vaqtini devor soatiga vaqt_tezligi marta tezlikda yurgizadi."""
        oxirgi = time.monotonic()
        qoldiq = 0.0
        while True:
            time.sleep(0.1)
            hozir = time.monotonic()
            dt, oxirgi = hozir - oxirgi, hozir
            if self.pauza:
                continue
            qoldiq += min(dt, 1.0) * self.vaqt_tezligi
            while qoldiq >= 1.0:
                self.qadam(1.0)
                qoldiq -= 1.0
