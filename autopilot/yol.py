"""Avtomobil yo'lining o'ng chetida yurish (3-bosqich).

Koordinatalar: s = marshrut bo'ylab masofa (m), d = yo'lning o'ng chetidan (bordyurdan) chapga
masofa (m). Yo'l o'ngdan chapga: [parkovka][velosiped yo'lagi][1-polosa][2-polosa]...

Qoidalar:
1. Velosiped yo'lagi bo'lsa, uning o'rtasida; bo'lmasa bordyurdan 0,8 m da yuradi.
   Parkovka bo'lsa, to'xtab turgan mashinalardan 1 m chapda (eshik ochilishi mumkin).
2. Oldida to'xtab turgan mashina, avtobus, to'siq yoki sekin velosipedchi bo'lsa, chapdan
   aylanib o'tadi, lekin faqat orqadan kelayotgan mashinalar xavfsiz tormoz bera oladigan bo'lsa.
   Aks holda to'siq orqasida to'xtab, yo'l bo'shashini kutadi.
3. Aylanib o'tishni boshlagach, oxirigacha tugatadi va o'z joyiga qaytadi.
4. Oldidagi sekin transportga 1,5 s oraliq bilan ergashadi; yo'lga chiqqan odam oldida to'xtaydi.
5. Chorrahada: o'ngga burilish chirog'ini yoqqan mashina orqada yoki yonda bo'lsa, unga yo'l beradi
   ("o'ngga burilish tuzog'i"). Chapga mashinalar orasidan burilmaydi: chorrahani ikki marta
   to'g'ri kesib o'tadi (marshrut shunday tuziladi).
6. Chorrahani kesib o'tish `otish.py` qoidalari bilan: svetofor yashil va mashinalar xavfsiz bo'lsa.
"""

from dataclasses import dataclass
import math

from .haydash import Buyruq, KMH, Sozlamalar, XavfsizlikQatlami, YordamNazoratchisi
from .marshrut import Marshrut
from .otish import Mashina, OtishSozlamalari, YolOtishBoshqaruvi

OTISH_KUTISH_CHEGARASI = 120.0


@dataclass
class YolSozlamalari:
    max_tezlik: float = 20 * KMH
    tezlanish: float = 1.2
    tormoz: float = 2.5
    favqulodda_tormoz: float = 4.0
    skuter_r: float = 0.35
    skuter_yarim_uzunlik: float = 0.3
    bordyurdan: float = 0.8           # velosiped yo'lagi bo'lmasa, bordyurdan masofa (m)
    eshikdan: float = 1.0             # to'xtab turgan mashinadan bo'sh joy (eshik ochilishi) (m)
    zaxira_odam: float = 0.8
    zaxira_velosiped: float = 0.8
    zaxira_mashina: float = 1.0
    zaxira_tosiq: float = 0.3
    oldinga: float = 50.0             # rejalash masofasi (m)
    qaror_masofa: float = 25.0        # aylanib o'tish qarori shu masofadan qabul qilinadi (m)
    toxtash_oraliq: float = 4.0       # to'siq orqasida to'xtash masofasi: joyidan aylanib chiqa olishi uchun (m)
    ergashish_vaqt: float = 1.5       # oldingi transportgacha vaqt oralig'i (s)
    ergashish_min: float = 3.0        # (m)
    orqa_reaksiya: float = 1.5        # orqadagi haydovchi reaksiyasi (s)
    orqa_tormoz: float = 2.0          # orqadagi haydovchidan kutiladigan qulay tormoz (m/s^2)
    orqa_zaxira: float = 8.0          # (m)
    yon_otish_tezligi: float = 1.0    # yon tomonga siljish tezligi (m/s)
    yon_tezlanish: float = 1.5        # burilishda (m/s^2)
    toxtagan_vaqt: float = 2.0        # mashina shuncha turib qolsa, "to'xtab turgan" deb hisoblanadi (s)
    otish_tezligi: float = 15 * KMH   # chorrahani kesib o'tish tezligi
    burilish_kuzatish: float = 3.0    # o'ngga buriluvchi mashinaga yo'l berish zaxirasi (s)
    parkovka_tezligi: float = 12 * KMH  # to'xtagan mashinalar yonida (orasidan odam chiqishi mumkin)


@dataclass
class YolObyekt:
    """Kamera aniqlagan yo'ldagi obyekt (to'rtburchak)."""
    s: float
    d: float
    vs: float
    vd: float
    uzunlik: float
    eni: float
    turi: str                 # "mashina", "velosiped", "odam", "to'siq"
    burilish: int = 0         # +1 = o'ngga burilish chirog'i yoniq
    iz: int = -1              # kuzatuvchi raqami (kamera dasturi beradi)
    toxtagan: bool = False    # kuzatuvchi to'ldiradi: uzoq vaqt qimirlamay turibdi


class YolKuzatuvchi:
    """Kamera kuzatuvchisi raqamlari bo'yicha joy va tezlikni silliqlaydi (alpha-beta)."""

    def __init__(self, alfa=0.4, beta=0.15, eslash=1.0, c: YolSozlamalari = None):
        self.alfa, self.beta, self.eslash = alfa, beta, eslash
        self.c = c or YolSozlamalari()
        self.izlar = {}  # iz -> [obyekt, oxirgi_vaqt, turgan_boshlanishi, yurgan_boshlanishi]
        self.t = None

    def yangila(self, t, aniqlashlar):
        dt = 0.0 if self.t is None else t - self.t
        self.t = t
        for o, *_ in self.izlar.values():
            o.s += o.vs * dt
            o.d += o.vd * dt
        for a in aniqlashlar:
            iz = self.izlar.get(a.iz)
            if iz is None:
                self.izlar[a.iz] = [YolObyekt(a.s, a.d, a.vs, a.vd, a.uzunlik, a.eni, a.turi, a.burilish, a.iz),
                                    t, t if abs(a.vs) < 0.8 else None, None]
                continue
            o = iz[0]
            rs, rd = a.s - o.s, a.d - o.d
            o.s += self.alfa * rs
            o.d += self.alfa * rd
            if dt > 0:
                o.vs += self.beta * rs / dt + 0.3 * (a.vs - o.vs)
                o.vd += self.beta * rd / dt + 0.3 * (a.vd - o.vd)
            o.burilish = a.burilish
            o.uzunlik, o.eni = max(o.uzunlik, a.uzunlik), max(o.eni, a.eni)
            iz[1] = t
            # Gisterezis: kamera shovqini "turibdi/yuryapti" ni almashtirib turmasin
            # (to'xtagan mashina faqat 0,5 s davomida aniq yursa "yuryapti" bo'ladi)
            if abs(o.vs) < 0.8:
                iz[2] = iz[2] if iz[2] is not None else t
                iz[3] = None
            elif abs(o.vs) > 1.5:
                iz[3] = iz[3] if iz[3] is not None else t
                if t - iz[3] >= 0.5 or abs(o.vs) > 3.0:
                    iz[2] = None
            else:
                iz[3] = None
        self.izlar = {k: v for k, v in self.izlar.items() if t - v[1] <= self.eslash}
        natija = []
        for o, _, turgan, _ in self.izlar.values():
            o.toxtagan = turgan is not None and t - turgan >= self.c.toxtagan_vaqt
            natija.append(o)
        return natija


def yol_tartibi(b, c: YolSozlamalari):
    """Yo'l bo'lagi uchun: (o'ng chegara, asosiy d, aylanib o'tishda eng chap d, 1-polosa boshi)."""
    chet = b.parkovka
    polosa_boshi = b.parkovka + b.velo
    if b.velo > 0:
        asosiy = b.parkovka + b.velo / 2
    elif b.parkovka > 0:
        asosiy = b.parkovka + c.eshikdan + c.skuter_r
    else:
        asosiy = c.bordyurdan
    eng_chap = polosa_boshi + b.yol_kengligi + 0.6
    return chet, asosiy, eng_chap, polosa_boshi


class YolRejalovchi:
    def __init__(self, c: YolSozlamalari = None):
        self.c = c or YolSozlamalari()
        self.rejim = "yurish"        # "yurish", "aylanib"
        self.d_aylanish = None
        self.s_oxir = None
        self.yol = None              # oxirgi "yol" bo'lagi (chorrahada ham shu tartib)

    def _zaxira(self, o):
        c = self.c
        if o.turi == "odam":
            return c.zaxira_odam
        if o.turi == "velosiped":
            return c.zaxira_velosiped
        if o.turi == "mashina":
            return c.eshikdan if o.toxtagan else c.zaxira_mashina
        return c.zaxira_tosiq

    def _chegaralar(self, o):
        """Obyekt egallagan yon oraliq, zaxira va skuter yarim eni bilan: skuter markazi shu oraliqda bo'lmasin."""
        z = self._zaxira(o) + self.c.skuter_r
        return o.d - o.eni / 2 - z, o.d + o.eni / 2 + z

    def _tosuvchi(self, o, polosa_boshi):
        """Aylanib o'tish kerak bo'lgan obyektmi: to'siq, chetda to'xtab turgan mashina, sekin velosiped."""
        if o.turi == "to'siq":
            return True
        if o.turi == "mashina":
            # Faqat chetda turgan mashina (navbatda turganini emas)
            return o.toxtagan and o.d - o.eni / 2 < polosa_boshi + 0.8
        if o.turi == "velosiped":
            return o.vs < 0.7 * self.c.max_tezlik
        return False

    def orqa_xavfsiz(self, s, v, d_yangi, obyektlar, d=None, yon_zaxira=1.0):
        """Chapga d_yangi ga chiqsak, orqadan kelayotgan mashinalar bemalol sekinlasha oladimi.

        d berilsa, hozirgi joydan d_yangi gacha bo'lgan butun yo'lak tekshiriladi.
        """
        c = self.c
        d = d_yangi if d is None else d
        y_lo, y_hi = min(d, d_yangi), max(d, d_yangi)
        for o in obyektlar:
            if o.turi not in ("mashina", "velosiped"):
                continue
            if o.s - o.uzunlik / 2 > s + c.skuter_yarim_uzunlik + 0.5:
                continue  # oldimizda
            lo, hi = o.d - o.eni / 2, o.d + o.eni / 2
            if hi < y_lo - c.skuter_r - yon_zaxira or lo > y_hi + c.skuter_r + yon_zaxira:
                continue  # boshqa polosada, bizga xalaqit bermaydi
            oraliq = s - c.skuter_yarim_uzunlik - c.skuter_r - (o.s + o.uzunlik / 2)
            if oraliq < 0:
                return False  # yonimizda (tezligidan qat'i nazar)
            if o.vs <= v + 0.5:
                continue
            kerak = o.vs * c.orqa_reaksiya + (o.vs - v) ** 2 / (2 * c.orqa_tormoz) + c.orqa_zaxira
            if oraliq < kerak:
                return False
        return True

    def _yon_cheklov(self, s, d, maqsad, obyektlar):
        """Yonimizda turgan narsaga qarab yon tomonga burilmaymiz: maqsadni cheklaymiz."""
        c = self.c
        for o in obyektlar:
            if abs(o.s - s) > o.uzunlik / 2 + c.skuter_yarim_uzunlik + 1.0:
                continue
            lo, hi = o.d - o.eni / 2, o.d + o.eni / 2
            z = c.skuter_r + 0.3
            if lo >= d and maqsad > lo - z:
                maqsad = max(min(d, maqsad), lo - z)
            elif hi <= d and maqsad < hi + z:
                maqsad = min(max(d, maqsad), hi + z)
        return maqsad

    def reja(self, t, s, d, v, obyektlar, marshrut: Marshrut):
        c = self.c
        b = marshrut.bolak(s)
        if b.turi == "yol":
            self.yol = b
        elif b.oxiri - s < 15:
            keyingi = marshrut.bolak(b.oxiri + 0.5)
            if keyingi.turi == "yol":
                self.yol = keyingi  # chorrahadan chiqyapmiz: keyingi ko'chaning tartibiga o'tamiz
        if self.yol is None:
            self.yol = next((x for x in marshrut.bolaklar if x.turi == "yol"), b)
        _, asosiy, eng_chap, polosa_boshi = yol_tartibi(self.yol, c)
        old = s + c.skuter_yarim_uzunlik
        holat = "yurish"

        tosuvchilar = [o for o in obyektlar if self._tosuvchi(o, polosa_boshi)
                       and o.s + o.uzunlik / 2 > s - c.skuter_yarim_uzunlik and o.s - s < c.oldinga]

        def tosadi(o, dd):
            lo, hi = self._chegaralar(o)
            return lo < dd < hi

        # --- Aylanib o'tish ---
        if self.rejim == "aylanib" and s > self.s_oxir:
            self.rejim = "yurish"
        if self.rejim == "aylanib":
            # Yo'lda yangi to'siq chiqsa, aylanish oralig'ini uzaytiramiz
            for o in tosuvchilar:
                if tosadi(o, self.d_aylanish) or tosadi(o, asosiy):
                    if o.s - o.uzunlik / 2 - self.s_oxir < 12:
                        self.s_oxir = max(self.s_oxir, o.s + o.uzunlik / 2 + 3.0)
                        _, hi = self._chegaralar(o)
                        if hi > self.d_aylanish and hi <= eng_chap:
                            self.d_aylanish = hi
            maqsad = self.d_aylanish
            holat = "aylanib"
            if maqsad > d + 0.1 and not self.orqa_xavfsiz(s, v, maqsad, obyektlar, d, yon_zaxira=0.3):
                maqsad = d  # orqadan/yondan mashina o'tyapti: o'tib ketguncha joyimizda qolamiz
        else:
            maqsad = asosiy
            oldindagi = sorted((o for o in tosuvchilar if tosadi(o, asosiy)), key=lambda o: o.s)
            if oldindagi:
                birinchi = oldindagi[0]
                guruh = [birinchi]
                d_ayl = self._chegaralar(birinchi)[1]
                oxir = birinchi.s + birinchi.uzunlik / 2
                for o in tosuvchilar:
                    if o in guruh:
                        continue
                    if o.s - o.uzunlik / 2 - oxir < 12 and (tosadi(o, asosiy) or tosadi(o, d_ayl)):
                        guruh.append(o)
                        d_ayl = max(d_ayl, self._chegaralar(o)[1])
                        oxir = max(oxir, o.s + o.uzunlik / 2)
                masofa = birinchi.s - birinchi.uzunlik / 2 - old
                # Aylanib o'tish chorrahaga yetmasdan tugashi kerak (chorrahaga yon tomonda kirmaymiz)
                chorraha = next((x.boshi for x in marshrut.otishlar() if x.boshi > s), math.inf)
                # Joyimizga qaytish uchun yon farqqa qarab 5-15 m kerak
                qaytish = min(15.0, max(5.0, 3.0 * (d_ayl - asosiy)))
                sigadi = oxir + c.skuter_yarim_uzunlik + 3.0 + qaytish < chorraha
                if masofa < c.qaror_masofa and b.turi == "otish":
                    holat = "kutish"  # chorraha ichida aylanib o'tishni boshlamaymiz
                elif masofa < c.qaror_masofa:
                    if d_ayl <= eng_chap and sigadi and self.orqa_xavfsiz(s, v, d_ayl, obyektlar):
                        self.rejim = "aylanib"
                        self.d_aylanish = d_ayl
                        self.s_oxir = oxir + c.skuter_yarim_uzunlik + 3.0
                        maqsad = d_ayl
                        holat = "aylanib"
                    else:
                        holat = "orqa_kutish" if d_ayl <= eng_chap and sigadi else "kutish"

        maqsad = self._yon_cheklov(s, d, maqsad, obyektlar)

        # --- Tezlik ---
        tezlik = c.max_tezlik
        lo_y, hi_y = min(d, maqsad), max(d, maqsad)
        for o in obyektlar:
            if o.s + o.uzunlik / 2 < old - 0.2 or o.s - s > c.oldinga:
                continue
            olo, ohi = self._chegaralar(o)
            if o.turi == "odam":
                # Odamning keyingi 3 soniyadagi yo'li bizning yo'lagimizni kesib o'tadimi
                yetish = max(0.0, o.s - old) / max(v, 1.0)
                kesadi = False
                tau = 0.0
                while tau <= min(yetish + 1.5, 4.0):
                    od = o.d + o.vd * tau
                    if od - c.zaxira_odam - c.skuter_r < hi_y and od + c.zaxira_odam + c.skuter_r > lo_y:
                        kesadi = True
                        break
                    tau += 0.25
                if not kesadi:
                    continue
                oraliq = o.s - old - 1.5
                tezlik = min(tezlik, math.sqrt(2 * c.tormoz * max(0.0, oraliq)))
                continue
            # Bizning yo'lagimizda (zaxirasiz) bo'lgan oldingi obyekt
            yon_lo, yon_hi = o.d - o.eni / 2 - c.skuter_r - 0.2, o.d + o.eni / 2 + c.skuter_r + 0.2
            bizda = yon_lo < hi_y and yon_hi > lo_y
            if self.rejim == "aylanib" and self._tosuvchi(o, polosa_boshi) and not tosadi(o, maqsad):
                # Chapga chiqyapmiz: unga yetguncha yon tomonga chiqib ulguradigan tezlikda boramiz.
                # Boshqaruv (pure pursuit) yon farqni taxminan L = 1.2 v + 0.5 masofada e marta kamaytiradi.
                oraliq = o.s - o.uzunlik / 2 - old
                qolgan = self._chegaralar(o)[1] - 0.1 - d
                if qolgan > 0 and oraliq < 30:
                    farq = max(maqsad - d, qolgan + 0.05)
                    L_kerak = max(0.0, oraliq) / math.log(farq / (farq - qolgan))
                    if L_kerak >= 1.0:
                        tezlik = min(tezlik, max(0.3, 0.8 * (L_kerak - 0.5) / 1.2))
                    else:
                        # Juda yaqin: allaqachon yonidan bemalol o'tsak, sekin davom etamiz
                        bosh = d - c.skuter_r - (o.d + o.eni / 2)
                        tezlik = min(tezlik, 0.3 if bosh > 0.1 or oraliq > 0.3 else 0.0)
                continue
            if not bizda and not (self._tosuvchi(o, polosa_boshi) and tosadi(o, maqsad)):
                continue
            if o.s - o.uzunlik / 2 < old - 0.2:
                continue
            oraliq = o.s - o.uzunlik / 2 - old
            harakatda = o.vs > 0.5 and not (o.turi == "mashina" and o.toxtagan)
            if harakatda:
                kerak = c.ergashish_min + c.ergashish_vaqt * v
                tezlik = min(tezlik, max(0.0, o.vs + 0.5 * (oraliq - kerak)),
                             math.sqrt(2 * c.tormoz * max(0.0, oraliq - c.ergashish_min)) + o.vs)
            else:
                # Turgan narsa oldida to'xtaymiz: keyin joyidan chapga aylanib chiqa oladigan masofada
                kerak = c.toxtash_oraliq
                if self._tosuvchi(o, polosa_boshi):
                    kerak = max(kerak, 1.5 + 1.5 * (self._chegaralar(o)[1] - d))
                    # Chorrahadan keyin turgan bo'lsa, chorraha ichida to'xtamaymiz (yaqinroq to'xtab, sekin aylanamiz)
                    chorraha_oxiri = max((x.oxiri for x in marshrut.otishlar() if x.oxiri < o.s), default=-math.inf)
                    joy = o.s - o.uzunlik / 2 - (chorraha_oxiri + 2 * c.skuter_yarim_uzunlik + 0.5)
                    if joy < kerak:
                        kerak = max(c.toxtash_oraliq, joy)
                tezlik = min(tezlik, math.sqrt(2 * c.tormoz * max(0.0, oraliq - kerak)))
        # To'xtab turgan mashinalar qatori yonida: ular orasidan odam chiqishi mumkin, sekinroq
        for o in obyektlar:
            if o.turi == "mashina" and o.toxtagan and -3 < o.s - s < 15 and o.d < d:
                if d - c.skuter_r - (o.d + o.eni / 2) < 1.8:
                    tezlik = min(tezlik, c.parkovka_tezligi)
                    break
        # Burilish
        tezlik = min(tezlik, marshrut.tezlik_chegarasi(s, c.max_tezlik, c.yon_tezlanish, c.tormoz, oldinga=25.0))
        if holat in ("orqa_kutish", "kutish") and tezlik >= 0.1:
            holat = "yurish"  # hali yetib kelmadik: yaqinlashyapmiz
        return Buyruq(tezlik if tezlik > 0.05 else 0.0, maqsad, c.tormoz, holat)

    def burilishga_yol_berish(self, s, v, obyektlar, marshrut):
        """O'ngga burilayotgan mashina orqada/yonda bo'lsa, chorraha oldida unga yo'l beramiz.

        Qaytaradi: tezlik chegarasi (math.inf = cheklov yo'q).
        """
        c = self.c
        b = next((x for x in marshrut.otishlar() if 0 < x.boshi - s < 30), None)
        if b is None:
            return math.inf
        chiziq = b.boshi - 1.0 - c.skuter_yarim_uzunlik
        t_biz = max(0.0, chiziq - s) / max(v, 1.0)
        for o in obyektlar:
            if o.turi != "mashina" or o.burilish != 1 or o.vs < 0.5:
                continue
            if o.s - o.uzunlik / 2 > b.boshi:
                continue  # allaqachon burilgan
            if o.vs < 1.5 and o.s + o.uzunlik / 2 < s - c.skuter_yarim_uzunlik:
                continue  # orqamizda to'xtab, bizga yo'l beryapti
            t_u = max(0.0, b.boshi - (o.s + o.uzunlik / 2)) / max(o.vs, 1.0)
            if t_u < t_biz + c.burilish_kuzatish:
                return math.sqrt(2 * c.tormoz * max(0.0, chiziq - s))
        return math.inf


class YolAvtopilot:
    """Yo'lda yuruvchi skuterning to'liq dasturi (rejalash 10 Hz + xavfsizlik qatlami)."""

    def __init__(self, marshrut: Marshrut, rejim="yarim", c: YolSozlamalari = None, yordam_kutish=30.0):
        self.c = c or YolSozlamalari()
        self.marshrut = marshrut
        self.kuz = YolKuzatuvchi(c=self.c)
        self.rej = YolRejalovchi(self.c)
        oc = OtishSozlamalari(otish_tezligi=self.c.otish_tezligi, tezlanish=self.c.tezlanish,
                              tormoz=self.c.tormoz, chiziqdan=1.0, toxtamasdan=True)
        self.otish = YolOtishBoshqaruvi(oc, rejim=rejim)
        self.xav = XavfsizlikQatlami(Sozlamalar(favqulodda_tormoz=self.c.favqulodda_tormoz, reaksiya=0.15))
        self.nazorat = YordamNazoratchisi(yordam_kutish)
        self.oxirgi_kamera = 0.0
        self.obyektlar = []
        self.otish_holati = None
        self.kesuvchi_xotira = []  # [(Mashina, oxirgi ko'rilgan vaqt)]
        self.oxirgi_t = None

    @property
    def operator_sorovi(self):
        return self.otish.sorov is not None

    def rejalash(self, t, s, d, v, aniqlashlar, kesuvchi_mashinalar=(), svetofor=None, operator_javobi=None):
        c = self.c
        if aniqlashlar is not None:
            self.obyektlar = self.kuz.yangila(t, aniqlashlar)
            self.oxirgi_kamera = t
        # Ichki tomondan burilishda s bo'yicha tezlik haqiqiy tezlikdan katta: v_s = v / (1 - k d).
        # Rejalash s bo'yicha masofalar bilan ishlaydi, shuning uchun v_s bilan hisoblab, buyruqni qaytaramiz.
        f = min(1.0, max(0.3, 1 - self.marshrut.egrilik(s) * d))
        v = v / f
        b = self.rej.reja(t, s, d, v, self.obyektlar, self.marshrut)
        yol_ochiq = b.tezlik >= c.max_tezlik - 1e-6
        yol_tezligi = math.inf if yol_ochiq else b.tezlik
        if self._chorraha_tiqilgan(s):
            yol_tezligi = 0.0  # chorrahadan keyin joy yo'q: chorrahaga kirib, uni to'sib qo'ymaymiz
        kesuvchilar = self._kesuvchilarni_eslash(t, list(kesuvchi_mashinalar))
        v_otish, holat = self.otish.qadam(t, s, v, self.marshrut, kesuvchilar, svetofor,
                                          operator_javobi, yol_tezligi)
        if holat == "otish" and self.otish_holati != "otish":
            self.nazorat.boshlanish = (t, s)
        self.otish_holati = holat
        tezlik = b.tezlik
        if holat is not None and holat != "otish":
            tezlik = min(tezlik, v_otish)
        if holat != "otish":
            v_burilish = self.rej.burilishga_yol_berish(s, v, self.obyektlar, self.marshrut)
            if v_burilish < tezlik:
                tezlik = v_burilish
                if v_burilish < 0.1:
                    holat = "yol_berish"
        yangi_holat = b.holat if holat in (None, "otish", "otishga_yaqinlashish") else holat
        return Buyruq(tezlik * f, b.d_maqsad, b.tormoz, yangi_holat)

    def _kesuvchilarni_eslash(self, t, korilgan, eslash=0.6):
        """Kamera bir-ikki kadrda mashinani ko'rmay qolsa ham, uni qisqa vaqt eslab, harakatini davom ettiramiz."""
        dt = 0.0 if self.oxirgi_t is None else t - self.oxirgi_t
        self.oxirgi_t = t
        yangi = [(m, t) for m in korilgan]
        for m, tk in self.kesuvchi_xotira:
            if t - tk > eslash:
                continue
            taxmin = Mashina(m.polosa, m.x + m.vx * dt, m.vx)
            if any(k.polosa == m.polosa and abs(k.x - taxmin.x) < 3.0 + 0.05 * abs(k.x) for k in korilgan):
                continue  # hozir ham ko'rinyapti
            yangi.append((taxmin, tk))
        self.kesuvchi_xotira = yangi
        return [m for m, _ in yangi]

    def _chorraha_tiqilgan(self, s):
        """Oldimizdagi chorrahadan keyin bizga joy bormi (u yerda turgan mashina/to'siq yo'qmi)."""
        c = self.c
        b = next((x for x in self.marshrut.otishlar() if 0 < x.boshi - s < 15), None)
        if b is None:
            return False
        keyingi = self.marshrut.bolak(b.oxiri + 0.5)
        yol = keyingi if keyingi.turi == "yol" else self.rej.yol
        if yol is None:
            return False
        _, asosiy, _, polosa_boshi = yol_tartibi(yol, c)
        for o in self.obyektlar:
            if o.turi == "odam" or (o.vs > 1.5 and not o.toxtagan) or o.s + o.uzunlik / 2 < b.boshi:
                continue
            if self.rej._tosuvchi(o, polosa_boshi):
                lo, hi = self.rej._chegaralar(o)
                if not lo < asosiy < hi:
                    continue
                kerak = c.toxtash_oraliq  # chorrahadan chiqib, shu masofada to'xtab aylanamiz
            elif o.d - o.eni / 2 - c.skuter_r - 0.3 < asosiy < o.d + o.eni / 2 + c.skuter_r + 0.3:
                kerak = c.toxtash_oraliq
            else:
                continue
            # Uning oldida to'xtasak, chorrahadan to'liq chiqib ulguramizmi
            if o.s - o.uzunlik / 2 - kerak - 2 * c.skuter_yarim_uzunlik < b.oxiri + 0.5:
                return True
        return False

    def xavfsizlik(self, buyruq, v, ultratovush, t):
        return self.xav.tekshir(buyruq, v, ultratovush, t - self.oxirgi_kamera)

    def yordam_kerakmi(self, t, s):
        kutish = None
        if self.otish_holati in ("bosh_joy_kutish", "operator_kutish"):
            kutish = OTISH_KUTISH_CHEGARASI
        return self.nazorat.tekshir(t, s, kutish)
