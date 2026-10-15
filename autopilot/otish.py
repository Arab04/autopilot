"""Avtomobil yo'lini piyodalar o'tish joyidan kesib o'tish.

Qoidalar:
1. Skuter o'tish joyi oldidagi chiziqda to'xtaydi.
2. Svetofor bo'lsa: piyodalar uchun yashil va qolgan vaqt yetarli bo'lsa o'tadi.
   Baribir mashinalarni tekshiradi (qizilda o'tib ketadigan haydovchilar).
3. Svetofor bo'lmasa: har bir polosadagi mashinalar yetib kelguncha skuter shu polosadan
   chiqib ulgurishi va yana `bufer` soniya zaxira qolishi kerak.
4. Yarim avtonom rejimda svetoforsiz joyda o'tishdan oldin operator tasdiqlaydi.
5. Yo'lga chiqqandan keyin to'xtamaydi: oxirigacha o'tib ketadi (yo'l o'rtasida to'xtash xavfliroq).

Mashina koordinatasi: x = o'tish joyi markazidan yo'l bo'ylab masofa (m), vx = tezligi.
"""

from dataclasses import dataclass
import math

from .marshrut import Bolak


@dataclass
class Mashina:
    """Kamera aniqlagan mashina."""
    polosa: int
    x: float
    vx: float


@dataclass
class OtishSozlamalari:
    otish_tezligi: float = 8 / 3.6     # yo'lda biroz tezroq (yon g'ildiraklar hali ochiq, < 9 km/soat)
    tezlanish: float = 0.8
    tormoz: float = 2.0
    bufer: float = 2.5                 # mashina kelguncha qo'shimcha zaxira vaqt (s)
    joy_zaxira: float = 2.0            # mashina joylashuvi xatosi uchun (m)
    zona_yarim: float = 2.0            # o'tish joyi yarim kengligi + zaxira (m)
    mashina_yarim_uzunlik: float = 2.3
    svetofor_zaxira: float = 3.0       # yashil tugashiga kamida shuncha vaqt qolsin (s)
    chiziqdan: float = 0.6             # o'tish joyi boshidan oldin to'xtash (m)
    operator_qayta: float = 3.0        # operator rad etsa, qayta so'rashdan oldin kutish (s)
    operator_kechikishi: float = 2.0   # operator javob bergunicha o'tadigan vaqt: shu vaqtdan keyin ham bo'sh joy
                                       # qolsagina so'raymiz (aks holda ruxsat kelganda joy yopilgan bo'ladi)
    skuter_old: float = 0.65           # skuter markazidan old chetigacha (m)
    skuter_orqa: float = 0.65
    min_tezlik: float = 0.8            # yo'lni bundan sekin kesib o'tmaymiz (m/s)
    toxtamasdan: bool = False          # yo'lda: svetofor yashil va xavfsiz bo'lsa chiziqda to'xtamay o'tadi


SVETOFOR_KUTISH = 30.0   # svetoforda o'rtacha kutish (s)


def kutish_bahosi(b: Bolak, oc: OtishSozlamalari = None):
    """O'tish joyida bo'sh joy kutishning taxminiy o'rtacha vaqti (s), xaritadagi oqimdan.

    Mashinalar har polosada Puasson oqimi (b.oqim mashina/s) deb olinadi. Skuter chiziqdan qo'zg'alib i-polosadan
    chiqib ulgurguncha (T_i + zaxira) shu polosaga mashina kelmasligi kerak: P = exp(-D), D = sum(oqim * T_i).
    O'rtacha kutish (Adams formulasi): (1/P - 1 - D) / jami_oqim. Svetoforda - o'rtacha qizil chiroq vaqti.
    Simulyatorda o'lchangan kutishga yaqin; oqim kun davomida o'zgarsa, haqiqiy o'rtacha kattaroq bo'ladi.
    """
    oc = oc or OtishSozlamalari()
    if b.svetofor:
        return SVETOFOR_KUTISH
    if b.oqim <= 0 or b.yollar <= 0:
        return 0.0
    v, a = oc.otish_tezligi, oc.tezlanish
    x_tez = v * v / (2 * a)
    daraja = 0.0
    for p in range(b.yollar):
        x = (p + 1) * b.yol_kengligi + oc.skuter_orqa
        t = math.sqrt(2 * x / a) if x <= x_tez else v / a + (x - x_tez) / v
        daraja += b.oqim * (t + oc.bufer + 0.5)
    return (math.exp(min(daraja, 50.0)) - 1.0 - daraja) / (b.oqim * b.yollar)


class YolOtishBoshqaruvi:
    def __init__(self, oc: OtishSozlamalari = None, rejim="yarim"):
        self.oc = oc or OtishSozlamalari()
        self.rejim = rejim               # "yarim" yoki "toliq"
        self.ruxsat = {}                 # bolak.boshi -> True
        self.sorov = None                # operatorga yuborilgan so'rov (bolak.boshi) yoki None
        self.rad_vaqti = -1e9
        self.operator_sorovlari = 0
        self.v_otish = self.oc.otish_tezligi  # oldinda odam bo'lsa, undan sekinroq o'tamiz

    # --- yordamchi hisoblar ---
    def _vaqt(self, masofa, v):
        """v tezlikdan o'tish tezligigacha tezlanib, masofani bosib o'tish vaqti."""
        oc = self.oc
        vt = max(self.v_otish, v)
        x_tez = max(0.0, (vt ** 2 - v ** 2) / (2 * oc.tezlanish))
        if masofa <= x_tez:
            return (-v + math.sqrt(v * v + 2 * oc.tezlanish * masofa)) / oc.tezlanish
        return (vt - v) / oc.tezlanish + (masofa - x_tez) / vt

    def bosh_joy_bor(self, b: Bolak, s, v, mashinalar, bufer=None):
        """Hozir yo'lga chiqsak, hamma polosalardan mashina yetib kelguncha chiqib ulguramizmi."""
        oc = self.oc
        bufer = oc.bufer if bufer is None else bufer
        for m in mashinalar:
            if m.polosa >= b.yollar:
                continue
            polosa_oxiri = b.boshi + (m.polosa + 1) * b.yol_kengligi
            if s - oc.skuter_orqa > polosa_oxiri:
                continue  # bu polosadan allaqachon chiqdik
            t_chiqish = self._vaqt(max(0.0, polosa_oxiri - s + oc.skuter_orqa), v)
            oraliq = abs(m.x) - oc.mashina_yarim_uzunlik - oc.zona_yarim  # mashina old qismidan zonagacha
            uzoqlashmoqda = m.x * m.vx > 0
            turibdi = abs(m.vx) < 1.0
            if turibdi and oraliq > -oc.joy_zaxira / 2:
                continue  # to'xtash chizig'ida turibdi (yo'l bergan). Qo'zg'alsa, tezligidan bilamiz.
            if oraliq < 0:
                if uzoqlashmoqda and not turibdi:
                    continue  # o'tish joyidan chiqib ketyapti
                return False  # mashina o'tish joyida turibdi yoki kiryapti
            if uzoqlashmoqda:
                continue
            yetib_kelish = max(0.0, oraliq - oc.joy_zaxira) / abs(m.vx)
            if yetib_kelish < t_chiqish + bufer:
                return False
        return True

    def _toliq_otish_vaqti(self, b, s, v):
        return self._vaqt(max(0.0, b.oxiri - s + self.oc.skuter_orqa), v)

    # --- asosiy qadam ---
    def qadam(self, t, s, v, marshrut, mashinalar, svetofor=None, operator_javobi=None, yol_tezligi=math.inf):
        """Qaytaradi: (tezlik_chegarasi, holat). holat None bo'lsa, o'tish joyi yaqin emas.

        svetofor: (yashil: bool, qolgan_vaqt: float) yoki None.
        operator_javobi: None, True (tasdiq) yoki False (rad).
        yol_tezligi: oldimizdagi odam/to'siq tufayli rejalovchi ruxsat bergan tezlik. Oldinda sekin
        yuruvchi odam bo'lsa, yo'lni shu tezlikda o'tamiz, shuning uchun mashinalar oralig'i kattaroq kerak.
        """
        oc = self.oc
        self.v_otish = min(oc.otish_tezligi, yol_tezligi)
        yaqin = [b for b in marshrut.otishlar() if s - oc.skuter_orqa < b.oxiri + 0.5 and b.boshi - s < 10]
        b = yaqin[0] if yaqin else None
        # Chapga ikki bosqichli burilish: birinchisini o'tib, ikkinchisining chizig'iga yetdik - endi u hal qiladi
        if (b is not None and self.ruxsat.get(b.boshi) and len(yaqin) > 1
                and s >= yaqin[1].boshi - oc.chiziqdan - oc.skuter_old - 0.4):
            b = yaqin[1]
        if b is None:
            return math.inf, None
        if self.ruxsat.get(b.boshi):
            # Yo'lga chiqqanmizmi? Chiqmagan bo'lsak va vaziyat o'zgargan bo'lsa, to'xtaymiz.
            ichkarida = s + oc.skuter_old > b.boshi - 0.1
            chiziq = b.boshi - oc.chiziqdan - oc.skuter_old
            # To'xtay olmaydigan darajada yaqin bo'lsak (sariq chiroq "dilemmasi"), o'tib ketamiz
            toxtay_oladi = not oc.toxtamasdan or chiziq - s >= v * v / (2 * oc.tormoz * 1.5)
            # Mashina xavfi bo'lsa, yo'lga chiqmagunimizcha har doim to'xtaymiz. Faqat chiroq o'zgarsa
            # (sariq "dilemma"), qulay to'xtay olmasak, o'tib ketamiz.
            mashina_xavfi = self.v_otish >= oc.min_tezlik and not self.bosh_joy_bor(b, s, v, mashinalar)
            if not ichkarida and (mashina_xavfi or (toxtay_oladi and not self._xavfsiz(b, s, v, mashinalar, svetofor))):
                self.ruxsat[b.boshi] = False
            else:
                return oc.otish_tezligi, "otish"
        chiziq = b.boshi - oc.chiziqdan - oc.skuter_old
        tezlik = math.sqrt(2 * oc.tormoz * max(0.0, chiziq - s))
        if (oc.toxtamasdan and b.svetofor and v > 0.1
                and chiziq - s <= v * v / (2 * oc.tormoz) + 2.0 and self._xavfsiz(b, s, v, mashinalar, svetofor)):
            # Yashil yonib turibdi, mashinalar yo'q: velosipedchidek to'xtamasdan o'tamiz
            self.ruxsat[b.boshi] = True
            return max(oc.otish_tezligi, v), "otish"
        if chiziq - s > 0.4 or v > 0.1:
            return tezlik, "otishga_yaqinlashish"
        # Chiziqda turibmiz
        if operator_javobi is not None and self.sorov == b.boshi:
            self.sorov = None
            if operator_javobi and self._xavfsiz(b, s, v, mashinalar, svetofor):
                self.ruxsat[b.boshi] = True
                return oc.otish_tezligi, "otish"
            self.rad_vaqti = t
        if self.sorov == b.boshi:
            return 0.0, "operator_kutish"
        if not self._xavfsiz(b, s, v, mashinalar, svetofor):
            return 0.0, "bosh_joy_kutish"
        if self.rejim == "yarim" and not b.svetofor:
            if t - self.rad_vaqti < oc.operator_qayta:
                return 0.0, "bosh_joy_kutish"
            kelajak = [Mashina(m.polosa, m.x + m.vx * oc.operator_kechikishi, m.vx) for m in mashinalar]
            if not self.bosh_joy_bor(b, s, v, kelajak):
                return 0.0, "bosh_joy_kutish"
            self.sorov = b.boshi
            self.operator_sorovlari += 1
            return 0.0, "operator_kutish"
        self.ruxsat[b.boshi] = True
        return oc.otish_tezligi, "otish"

    def _xavfsiz(self, b, s, v, mashinalar, svetofor):
        if self.v_otish < self.oc.min_tezlik:
            return False  # oldimiz to'siq: yo'lga chiqmaymiz, yo'l bo'shashini kutamiz
        if b.svetofor:
            if svetofor is None:
                return False
            yashil, qolgan = svetofor
            if not yashil or qolgan < self._toliq_otish_vaqti(b, s, v) + self.oc.svetofor_zaxira:
                return False
        # Svetofor bo'lsa ham mashinalarni tekshiramiz (qizilda o'tib ketadiganlar uchun)
        return self.bosh_joy_bor(b, s, v, mashinalar)
