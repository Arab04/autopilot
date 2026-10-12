"""Skuterning "miyasi": marshrut rejalash va xavfsizlik qatlami.

Bu kod keyinchalik skuterning o'ziga o'rnatiladi, shuning uchun u simulyatorga
bog'liq emas: faqat datchiklardan kelgan ma'lumotni oladi va buyruq qaytaradi.

Koordinatalar marshrut bo'ylab: s = marshrut bo'ylab masofa (m), d = markaz
chiziqdan yon tomonga siljish (m, chap +). Burilishlar va yo'lni kesib o'tish
`marshrut.py` va `otish.py` da; hammasini `Avtopilot` klassi birlashtiradi.
"""

from dataclasses import dataclass, field
import math

KMH = 1 / 3.6


@dataclass
class Sozlamalar:
    max_tezlik: float = 6 * KMH       # trotuarda
    tezlanish: float = 0.8            # m/s^2
    tormoz: float = 2.0               # oddiy tormoz, m/s^2
    favqulodda_tormoz: float = 3.5    # m/s^2
    yarim_kenglik: float = 1.5        # trotuar yarim kengligi (m)
    skuter_r: float = 0.35            # skuterni ifodalovchi doira radiusi (2 ta doira)
    skuter_yarim_uzunlik: float = 0.3
    xavfsiz_masofa: float = 0.4       # odamgacha minimal bo'sh joy (m)
    tosiq_masofa: float = 0.15        # ustun, daraxt kabi turg'un narsagacha (m)
    kamera_xato_0: float = 0.05       # kamera joylashuv xatosi: 0,05 m + masofaning 2%
    kamera_xato_m: float = 0.02
    devordan: float = 0.15            # trotuar chetidan bo'sh joy (m)
    gorizont: float = 3.0             # oldinga necha soniya bashorat qilinadi
    oldinga_korish: float = 10.0      # turg'un to'siqlar uchun rejalash masofasi (m)
    yon_otish_masofasi: float = 4.0   # bir yo'lakdan boshqasiga o'tish uchun kerakli yo'l (m)
    sekin_otish_masofasi: float = 2.5  # juda sekin, rul to'liq burilganda (m)
    sekin_tezlik: float = 0.3         # m/s
    ergashish_masofa: float = 1.5     # oldimizdagi odamgacha saqlanadigan masofa (m)
    qadam: float = 0.5
    kamera_eskirdi: float = 0.3       # kameradan shuncha vaqt ma'lumot kelmasa = xato (s)
    reaksiya: float = 0.15            # buyruq bajarilish kechikishi (s)
    afzal_d: float = -0.4             # o'ng tomonda yurish qoidasi: markazdan o'ngroq (m)
    yon_tezlanish: float = 0.8        # burilishda maksimal yon tezlanish (m/s^2)


@dataclass
class Obyekt:
    """Kamera aniqlagan obyekt (odam, ustun, velosiped...)."""
    s: float
    d: float
    vs: float
    vd: float
    r: float
    turi: str = "odam"   # kamera beradigan sinf: "odam" yoki "to'siq"


@dataclass
class Buyruq:
    tezlik: float          # kerakli tezlik (m/s)
    d_maqsad: float        # kerakli yon holat (m)
    tormoz: float          # ruxsat etilgan sekinlashish (m/s^2)
    holat: str             # "yurish", "kutish", "favqulodda", "kamera_xato"


class Kuzatuvchi:
    """Kameradan kelgan shovqinli aniqlashlarni kuzatib boradi (alpha-beta filtr).

    Har bir kadrda obyekt joyi biroz sakraydi; kuzatuvchi ularni silliqlaydi,
    tezligini baholaydi va bir necha kadrda ko'rinmay qolgan obyektni 1 s eslab turadi.
    """

    def __init__(self, alfa=0.35, beta=0.1, eslash=1.0, darvoza=1.2):
        self.alfa, self.beta, self.eslash, self.darvoza = alfa, beta, eslash, darvoza
        self.izlar = []  # [Obyekt, oxirgi_korilgan_vaqt]
        self.t = None

    def yangila(self, t, aniqlashlar):
        dt = 0.0 if self.t is None else t - self.t
        self.t = t
        for iz in self.izlar:
            o = iz[0]
            o.s += o.vs * dt
            o.d += o.vd * dt
        ishlatilgan = set()
        for a in aniqlashlar:
            eng, eng_m = None, self.darvoza
            for i, iz in enumerate(self.izlar):
                # Faqat bir xil sinfdagi obyektlarni bog'laymiz (ustun odamga "aylanib" qolmasin)
                if i in ishlatilgan or iz[0].turi != a.turi:
                    continue
                m = math.hypot(iz[0].s - a.s, iz[0].d - a.d)
                if m < eng_m:
                    eng, eng_m = i, m
            if eng is None:
                self.izlar.append([Obyekt(a.s, a.d, a.vs, a.vd, a.r, a.turi), t, 1])
                ishlatilgan.add(len(self.izlar) - 1)
                continue
            ishlatilgan.add(eng)
            o = self.izlar[eng][0]
            rs, rd = a.s - o.s, a.d - o.d
            self.izlar[eng][2] += 1
            if o.turi != "odam":
                # Turg'un narsa: barcha o'lchovlarning o'rtachasi (vaqt o'tgan sari aniqlashadi)
                k = max(0.05, 1.0 / self.izlar[eng][2])
                o.s += k * rs
                o.d += k * rd
                o.vs = o.vd = 0.0
                o.r = max(o.r, a.r)
                self.izlar[eng][1] = t
                continue
            o.s += self.alfa * rs
            o.d += self.alfa * rd
            if dt > 0:
                o.vs += self.beta * rs / dt
                o.vd += self.beta * rd / dt
            o.r = max(o.r, a.r)
            self.izlar[eng][1] = t
        self.izlar = [iz for iz in self.izlar if t - iz[1] <= self.eslash]
        return [iz[0] for iz in self.izlar]


def boshqaruv_burchagi(d, d_maqsad, v):
    """Pure pursuit: maqsad yo'lagiga qaysi burchak bilan borish kerak (rad)."""
    oldinga = max(1.0, 1.2 * v + 0.5)
    return math.atan2(d_maqsad - d, oldinga)


class Rejalovchi:
    """Bir necha yon yo'lakni sinab ko'rib, eng xavfsiz va qulayini tanlaydi."""

    def __init__(self, c: Sozlamalar):
        self.c = c
        self.oldingi_d = 0.0
        # Sinab ko'riladigan yon holatlar (12,5 sm qadam bilan)
        lim = c.yarim_kenglik - c.skuter_r - c.devordan
        n = 17
        self.variantlar = [-lim + 2 * lim * i / (n - 1) for i in range(n)]

    def _bosh_joy(self, s0, d0, yol, v, obyektlar, otish=None):
        """Berilgan yo'l bo'yicha v tezlikda yurilsa, eng kichik bo'sh joy (zaxiradan keyin, m).

        yol = (d1, x, d2): avval d1 yo'lagiga o'tadi, x metrdan keyin d2 ga o'tadi.
        """
        c = self.c
        d1, x_otish, d2 = yol
        otish = otish or c.yon_otish_masofasi
        eng_kam = math.inf
        birinchi_xato = math.inf
        # Agar biror narsa hozirning o'zida zaxira masofadan yaqin bo'lsa (masalan, odam yonimizga
        # kelib to'xtagan), undan uzoqlashmasak ham bo'ladi, faqat yaqinlashmaslik kerak.
        chegara = {}
        t = 0.0
        # Harakatlanuvchilar uchun 3 s bashorat; turg'un to'siqlar uchun kamida 10 m oldinga
        t_max = max(c.gorizont, c.oldinga_korish / v)
        while t <= t_max + 1e-9:
            x = v * t
            ss = s0 + x
            dd = d0 + (d1 - d0) * min(1.0, x / otish)
            if x > x_otish:
                dd += (d2 - d1) * min(1.0, (x - x_otish) / otish)
            for i, o in enumerate(obyektlar):
                harakatda = o.turi == "odam"
                if t > c.gorizont and harakatda:
                    continue
                vs, vd = (o.vs, o.vd) if harakatda else (0.0, 0.0)  # ustun joyidan qimirlamaydi
                os_, od = o.s + vs * t, o.d + vd * t
                # Kamera uzoqdagi narsani kamroq aniq ko'radi: noaniqlikni hisobga olamiz
                # (o'sha paytdagi masofa bo'yicha: yaqinlashganda baho aniqlashadi)
                noaniq = c.kamera_xato_0 + c.kamera_xato_m * abs(os_ - ss)
                gap = min(math.hypot(ss + k - os_, dd - od)
                          for k in (-c.skuter_yarim_uzunlik, c.skuter_yarim_uzunlik))
                gap -= c.skuter_r + o.r + (c.xavfsiz_masofa if o.turi == "odam" else c.tosiq_masofa) + noaniq
                if i not in chegara:
                    chegara[i] = min(0.0, gap) - 0.02
                ortiqcha = gap - chegara[i]
                if ortiqcha < eng_kam:
                    eng_kam = ortiqcha
                if ortiqcha < 0 and x < birinchi_xato:
                    birinchi_xato = x
            t += c.qadam
        return eng_kam, birinchi_xato

    def _narx(self, d1, d2, gap, tosiq_oldinda):
        af = self.c.afzal_d
        narx = (abs(d1 - af) + 0.5 * abs(d2 - af) + abs(d1 - self.oldingi_d) * 1.5
                + max(0.0, 1.0 - gap) * 2.0)
        # Oldinda to'siq bo'lsa va bir tomonni tanlagan bo'lsak, boshqa tomonga sakramaymiz
        # (kamera shovqinidan tebranish bo'lmasin). Yo'l bo'sh bo'lsa, o'ng tomonga qaytamiz.
        if tosiq_oldinda and abs(self.oldingi_d - af) > 0.2 and (d1 - af) * (self.oldingi_d - af) < 0:
            narx += 5.0
        return narx

    def _tanla(self, s, d, v, yaqin, otish=None):
        """Eng arzon xavfsiz yo'lni qaytaradi: (narx, (d1, x, d2)) yoki None.

        Avval bitta yo'lakli variantlar; topilmasa, ikki bosqichli (ilon izi) variantlar.
        """
        eng_yaxshi = None
        tosiq_oldinda = any(-1 < o.s - s < 12 and abs(o.d - d) < 2.0 for o in yaqin)
        for dv in self.variantlar:
            yol = (dv, math.inf, dv)
            gap = self._bosh_joy(s, d, yol, v, yaqin, otish)[0]
            if gap < 0:
                continue
            narx = self._narx(dv, dv, gap, tosiq_oldinda)
            if eng_yaxshi is None or narx < eng_yaxshi[0]:
                eng_yaxshi = (narx, yol)
        if eng_yaxshi is not None:
            return eng_yaxshi
        for d1 in self.variantlar[::2]:
            for x in (1.5, 3.0, 5.0, 7.0):
                for d2 in self.variantlar[::2]:
                    if d2 == d1:
                        continue
                    yol = (d1, x, d2)
                    gap = self._bosh_joy(s, d, yol, v, yaqin, otish)[0]
                    if gap < 0:
                        continue
                    narx = self._narx(d1, d2, gap, tosiq_oldinda) + 1.0
                    if eng_yaxshi is None or narx < eng_yaxshi[0]:
                        eng_yaxshi = (narx, yol)
        return eng_yaxshi

    def _ergashish(self, s, d, d_maqsad, yaqin):
        """Oldimizda bir tomonga ketayotgan odam bo'lsa, 1,5 m masofa saqlab orqasidan boramiz."""
        c = self.c
        lo, hi = min(d, d_maqsad), max(d, d_maqsad)
        tezlik = c.max_tezlik
        for o in yaqin:
            oldinda = o.s - s - c.skuter_yarim_uzunlik - c.skuter_r - o.r
            yon = max(0.0, lo - o.d, o.d - hi)
            if o.turi == "odam" and oldinda > -0.2 and yon < c.skuter_r + o.r + c.xavfsiz_masofa:
                tezlik = min(tezlik, max(0.0, max(0.0, o.vs) + 0.6 * (oldinda - c.ergashish_masofa)))
        return tezlik

    def reja(self, s, d, v, obyektlar):
        c = self.c
        yaqin = [o for o in obyektlar if -3 < o.s - s < 15]
        eng_yaxshi = self._tanla(s, d, max(v, 0.5), yaqin)
        sekin = False
        if eng_yaxshi is None and v < 0.3:
            # Turgan joydan juda sekin, keskin burilib aylanib o'tishga harakat
            eng_yaxshi = self._tanla(s, d, 0.3, yaqin, otish=c.sekin_otish_masofasi)
            sekin = eng_yaxshi is not None
        if eng_yaxshi is None:
            # Hech qaysi yo'l xavfsiz emas: eng ko'p bo'sh joy qoladigan yo'lakka buriladi (yaqinlashganda
            # kamera aniqroq ko'radi va yo'l ochilishi mumkin), xavfli nuqtadan oldin to'xtaymiz
            eng = None
            for dv in self.variantlar:
                gap, xato_x = self._bosh_joy(s, d, (dv, math.inf, dv), 0.5, yaqin)
                if eng is None or (xato_x, gap) > (eng[1], eng[2]):
                    eng = (dv, xato_x, gap)
            d_m, xato_x, _ = eng
            odam_yonda = any(o.turi == "odam" and abs(o.s - s) < 2.5 for o in yaqin)
            if xato_x < 3.0 or odam_yonda:
                d_m = d  # xavf yaqin yoki yonda odam: burilmaymiz (burilsak orqa qismi yonga suriladi)
                xato_x = self._bosh_joy(s, d, (d, math.inf, d), 0.5, yaqin)[1]
            masofa = max(0.0, xato_x - 0.3)
            tezlik = min(c.max_tezlik, math.sqrt(2 * c.tormoz * masofa), self._ergashish(s, d, d_m, yaqin))
            self.oldingi_d = d_m
            return Buyruq(tezlik if tezlik > 0.05 else 0.0, d_m, c.tormoz, "kutish")
        yol = eng_yaxshi[1]
        self.oldingi_d = yol[0]
        # Odam zaxira masofadan yaqin turgan bo'lsa (yonimizdan o'tayotgan bo'lsa), u o'tib ketguncha kutamiz:
        # burilganda skuterning orqasi yon tomonga suriladi va odamga tegib ketishi mumkin.
        for o in yaqin:
            if o.turi == "odam" and abs(o.s - s) < 1.5:
                yaqinlik = (math.hypot(o.s - s, o.d - d) - c.skuter_yarim_uzunlik - c.skuter_r - o.r
                            - c.xavfsiz_masofa)
                if yaqinlik < 0:
                    return Buyruq(0.0, d, c.tormoz, "kutish")
        if sekin:
            return Buyruq(c.sekin_tezlik, yol[0], c.tormoz, "sekin_aylanish")
        # Tezlik: tanlangan yo'l shu tezlikda ham xavfsiz bo'lgan eng katta qiymat
        tezlik = 0.5
        for nomzod in (c.max_tezlik, 4.5 * KMH, 3.5 * KMH, 2.5 * KMH):
            if nomzod <= 0.5 or self._bosh_joy(s, d, yol, nomzod, yaqin)[0] >= 0:
                tezlik = nomzod
                break
        tezlik = min(tezlik, self._ergashish(s, d, yol[0], yaqin))
        # Odam yaqin bo'lsa baribir sekinlashamiz (qulaylik va ishonch uchun)
        for o in yaqin:
            if o.turi == "odam" and abs(o.s - s) < 4 and abs(o.d - yol[0]) < 1.5:
                tezlik = min(tezlik, 3.5 * KMH)
        return Buyruq(tezlik, yol[0], c.tormoz, "yurish")


class XavfsizlikQatlami:
    """Mikrokontrollerda ishlaydigan qatlam: kameraga ishonmaydi.

    - Ultratovush oldinda juda yaqin narsani ko'rsa: favqulodda tormoz.
    - Kameradan ma'lumot eskirsa: to'xtash.
    """

    def __init__(self, c: Sozlamalar):
        self.c = c

    def tekshir(self, buyruq: Buyruq, v, ultratovush_oldinda, kamera_yoshi):
        c = self.c
        to_xtash_yoli = v * c.reaksiya + v * v / (2 * c.favqulodda_tormoz)
        if ultratovush_oldinda is not None and ultratovush_oldinda < to_xtash_yoli + 0.3:
            return Buyruq(0.0, buyruq.d_maqsad, c.favqulodda_tormoz, "favqulodda")
        if kamera_yoshi > c.kamera_eskirdi:
            return Buyruq(0.0, buyruq.d_maqsad, c.favqulodda_tormoz, "kamera_xato")
        return buyruq


class YordamNazoratchisi:
    """Skuter uzoq vaqt oldinga siljimasa, operatordan yordam so'raydi (yarim avtonom rejim)."""

    def __init__(self, kutish=30.0, min_siljish=1.0):
        self.kutish, self.min_siljish = kutish, min_siljish
        self.boshlanish = None  # (vaqt, s)

    def tekshir(self, t, s, kutish=None):
        if self.boshlanish is None or s - self.boshlanish[1] >= self.min_siljish:
            self.boshlanish = (t, s)
            return False
        return t - self.boshlanish[0] > (kutish or self.kutish)
