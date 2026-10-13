"""Joylashuvni aniqlash (5-bosqich): skuter marshrutning qayerida ekanini o'zi baholaydi.

Oldingi bosqichlarda simulyator skuterga uning aniq joyini (s, d) berardi. Haqiqiy skuterda buni
hech kim bermaydi: joy datchiklardan baholanadi.

Datchiklar:
- GPS (5 Hz): 1-3 m xato; daraxtlar va binolar orasida yo'qoladi yoki ko'p metrga "sakraydi".
  Qabul qilgich o'z aniqligini ham aytadi (odatda kamaytirib): binolar orasida u kattalashadi;
- g'ildirak odometri: tezlik (g'ildirak yeyilsa, bir necha foiz xato);
- giroskop: burilish tezligi (o'zining sekin o'zgaruvchi xatosi bor);
- kamera: yo'l chetigacha (bordyur yoki parkovka chizig'i) yon masofa va oldindagi belgigacha masofa
  (chorrahaga kirish yoki chiqish cheti, o'ngga burilishda bordyur egilishining boshi). Bular xaritadagi
  aniq joyga nisbatan o'lchanadi, shuning uchun eng aniq manba.

Yon o'lchov (bordyur) faqat yon holatni (d, psi, bg), bo'ylama belgi faqat bo'ylama holatni (s, k, GPS xatosi)
tuzatadi. Aks holda filtr, masalan, aylanib o'tishdagi yon xatoni odometr xatosi deb, joyini o'nlab metrga
noto'g'ri surardi (simulyatsiya shuni ko'rsatdi).

Usul: kengaytirilgan Kalman filtri (EKF) marshrut koordinatalarida. Holat:
    s, d       marshrut bo'ylab masofa va yon siljish (m), haydash dasturidagi bilan bir xil
    psi        skuter yo'nalishining marshrutga nisbatan burchagi (rad)
    bg         giroskop xatosi (rad/s)
    k          odometr masshtabi: haqiqiy tezlik = k * g'ildirak tezligi
    bx, by     GPS ning sekin o'zgaruvchi xatosi (xarita tekisligida, m)

Har bir o'lchov filtr kutgan qiymatdan juda uzoq bo'lsa (chi-kvadrat darvozasi), rad etiladi:
GPS "sakrashi" va kamera yanglishishi shu bilan to'xtatiladi. Agar kamera bir necha kadr ketma-ket bir xil
narsani ko'rsatib, filtr uni rad etaversa, filtrning o'zi adashgan (masalan, GPS kutilganidan ko'p xato
qilgan): shu o'lchovga qayta ishonamiz.

Ehtiyot qoidalari (filtr o'z noaniqligini biladi):
- Rejalashda skuter o'zini taxminiy joyidan 2 sigma oldinroq deb hisoblaydi: chorraha va burilish
  "yaqinroq" ko'rinadi, demak to'xtash chizig'idan o'tib ketmaydi.
- Yonda ham o'zini bordyurga 2 sigma yaqinroq deb hisoblaydi: bordyurdan shuncha uzoqroq yuradi.
- Yon noaniqlik katta bo'lsa (bordyur uzoq ko'rinmasa) sekinlashadi, juda katta bo'lsa to'xtaydi
  va operatorni chaqiradi. Lekin faqat oddiy yo'lda: chorrahaga kirgan bo'lsa, uni oxirigacha kesib o'tadi
  (chorraha ichida to'xtash eng xavfli; birinchi sinovda 40 marshrutdan 15 tasida shunday bo'lgan).
"""

from dataclasses import dataclass
import math

import numpy as np

from .haydash import KMH
from .marshrut import Marshrut

S, D, PSI, BG, K, BX, BY = range(7)


@dataclass
class JoylashuvSozlamalari:
    # Filtr modeli (haqiqiy datchiklardan biroz yomonroq olinadi: filtr o'ziga ortiqcha ishonmasin)
    gps_shovqin: float = 1.0          # GPS ning har o'lchovdagi tasodifiy xatosi (m)
    gps_xato: float = 2.0             # GPS ning sekin o'zgaruvchi xatosi (m)
    gps_xato_vaqt: float = 60.0       # shu xatoning o'zgarish vaqti (s)
    odometr_shovqin: float = 0.02     # m/sqrt(s)
    odometr_ozgarish: float = 1e-4    # masshtab o'zgarishi, 1/sqrt(s)
    giro_shovqin: float = 0.004       # rad/sqrt(s)
    giro_xato_ozgarish: float = 2e-4  # rad/s/sqrt(s)
    yon_shovqin: float = 0.01         # g'ildirak sirpanishi va h.k., m/sqrt(s)
    egrilik_noaniq: float = 0.1       # burilish boshlanish joyining noaniqligi (xarita, bordyur shakli), m
    chet_shovqin: float = 0.03        # kamera: yo'l chetigacha (m), + 2% masofa
    chiziq_shovqin: float = 0.10      # kamera: chorraha chetigacha (m), + 2% masofa
    burilish_shovqin: float = 0.20    # kamera: burilishda bordyur egilishi boshigacha (m), + 3% masofa
    darvoza_1: float = 10.8           # chi-kvadrat, 1 o'lchov (99,9%)
    darvoza_2: float = 13.8           # chi-kvadrat, 2 o'lchov (99,9%)
    tiklash_kadr: int = 5             # shuncha kadr ketma-ket izchil rad etilsa, filtr adashgan
    # Boshlang'ich noaniqlik (ombordan chiqishda joy ma'lum)
    boshida_s: float = 0.5
    boshida_d: float = 0.1
    boshida_psi: float = 0.03
    boshida_bg: float = 0.01          # rad/s (~0,6 grad/s)
    boshida_k: float = 0.03
    # Ehtiyot qoidalari
    ehtiyot_sigma: float = 2.0        # rejalashda o'zimizni shuncha sigma oldinroq deb hisoblaymiz
    sigma_d_sekin: float = 0.20       # m: bundan katta bo'lsa sekinlashadi
    sigma_d_toxta: float = 0.50       # m: to'xtaydi va operatorni chaqiradi (bordyurdan 2 sigma uzoq yursa ham
                                      # 3 sigma xatoda bordyurga tegishi mumkin)
    sigma_s_sekin: float = 4.0        # m
    sekin_tezlik: float = 10 * KMH


class MarshrutChizigi:
    """Marshrutning xaritadagi chizig'i: (s, d) <-> (x, y). Har 0,25 m da oldindan hisoblanadi."""

    def __init__(self, marshrut: Marshrut, qadam=0.25):
        self.m = marshrut
        self.q = qadam
        n = int(marshrut.uzunlik / qadam) + 2
        xs, ys, ths = [0.0], [0.0], [0.0]
        x = y = th = 0.0
        for i in range(1, n):
            k = marshrut.egrilik(min((i - 0.5) * qadam, marshrut.uzunlik - 1e-6))
            if abs(k) > 1e-9:
                x += (math.sin(th + k * qadam) - math.sin(th)) / k
                y += -(math.cos(th + k * qadam) - math.cos(th)) / k
                th += k * qadam
            else:
                x += qadam * math.cos(th)
                y += qadam * math.sin(th)
            xs.append(x)
            ys.append(y)
            ths.append(th)
        self.xs, self.ys, self.ths = xs, ys, ths

    def nuqta(self, s):
        """Marshrut chizig'idagi nuqta va yo'nalish (marshrutdan tashqarida to'g'ri davom etadi)."""
        n = len(self.xs) - 1
        u = s / self.q
        i = min(max(int(math.floor(u)), 0), n - 1)
        f = u - i
        th = self.ths[i] + (self.ths[i + 1] - self.ths[i]) * min(max(f, 0.0), 1.0)
        if f < 0 or f > 1:
            j = 0 if f < 0 else n
            ortiq = s - j * self.q
            return self.xs[j] + ortiq * math.cos(self.ths[j]), self.ys[j] + ortiq * math.sin(self.ths[j]), self.ths[j]
        return (self.xs[i] + (self.xs[i + 1] - self.xs[i]) * f, self.ys[i] + (self.ys[i + 1] - self.ys[i]) * f, th)

    def xy(self, s, d):
        x, y, th = self.nuqta(s)
        return x - d * math.sin(th), y + d * math.cos(th)


def marshrut_belgilari(marshrut: Marshrut):
    """Kamera taniy oladigan, xaritada joyi aniq belgilar: [(s, turi)]."""
    belgilar = []
    for b in marshrut.bolaklar:
        if b.turi == "otish":
            belgilar += [(b.boshi, "kirish"), (b.oxiri, "chiqish")]
        elif b.turi == "burilish" and b.egrilik < 0:
            belgilar.append((b.boshi, "burilish"))
    return belgilar


class Joylashuv:
    """Skuter joyini baholovchi filtr (EKF) va ehtiyot qoidalari."""

    def __init__(self, marshrut: Marshrut, s0, d0, c: JoylashuvSozlamalari = None, chiziq: MarshrutChizigi = None):
        self.c = c = c or JoylashuvSozlamalari()
        self.m = marshrut
        self.chiziq = chiziq or MarshrutChizigi(marshrut)
        self.x = np.array([s0, d0, 0.0, 0.0, 1.0, 0.0, 0.0])
        self.P = np.diag([c.boshida_s, c.boshida_d, c.boshida_psi, c.boshida_bg, c.boshida_k,
                          c.gps_xato, c.gps_xato]) ** 2
        self.belgilar = marshrut_belgilari(marshrut)
        self.rad = {"gps": 0, "chet": 0, "belgi": 0}
        self.tiklash = 0
        self._rad_etilgan = {"chet": [], "belgi": []}  # ketma-ket rad etilgan o'lchovlar (yangilik)
        self._tuzatish = np.zeros(2)  # oxirgi rejalashdan beri joy tuzatishlari (s, d)
        self._oldingi_ehtiyot = (0.0, 0.0)

    # --- holat ---
    @property
    def s(self):
        return float(self.x[S])

    @property
    def d(self):
        return float(self.x[D])

    @property
    def psi(self):
        return float(self.x[PSI])

    @property
    def k(self):
        return float(self.x[K])

    @property
    def sigma_s(self):
        return math.sqrt(self.P[S, S])

    @property
    def sigma_d(self):
        return math.sqrt(self.P[D, D])

    def tezlik(self, v_odometr):
        return self.k * v_odometr

    # --- bashorat: odometr va giroskop (20 Hz) ---
    def bashorat(self, dt, v_odometr, omega):
        c, x = self.c, self.x
        q = np.zeros(7)
        q[BG] = c.giro_xato_ozgarish ** 2
        q[BX] = q[BY] = 2 * c.gps_xato ** 2 / c.gps_xato_vaqt
        F = np.eye(7)
        F[BX, BX] = F[BY, BY] = 1 - dt / c.gps_xato_vaqt
        x[BX] *= F[BX, BX]
        x[BY] *= F[BY, BY]
        if abs(v_odometr) < 1e-3:
            # Skuter turibdi: joyi va yo'nalishi o'zgarmaydi, giroskop esa faqat o'z xatosini ko'rsatadi
            self.P = F @ self.P @ F.T + np.diag(q) * dt
            self._yangila(np.eye(7)[[BG]], np.array([omega - x[BG]]), np.array([[c.giro_shovqin ** 2 / max(dt, 1e-3)]]),
                          c.darvoza_1)
            return
        kap = self._egrilik(x[S])
        v = x[K] * v_odometr
        f = max(0.3, 1 - kap * x[D])
        cs, sn = math.cos(x[PSI]), math.sin(x[PSI])
        sd = v * cs / f
        dsd = (v * cs * kap / f ** 2, -v * sn / f, v_odometr * cs / f)  # d, psi, k bo'yicha hosilalar
        F[S, D], F[S, PSI], F[S, K] = dsd[0] * dt, dsd[1] * dt, dsd[2] * dt
        F[D, PSI], F[D, K] = v * cs * dt, v_odometr * sn * dt
        F[PSI, D] = -kap * dsd[0] * dt
        F[PSI, PSI] = 1 - kap * dsd[1] * dt
        F[PSI, BG] = -dt
        F[PSI, K] = -kap * dsd[2] * dt
        x[S] += sd * dt
        x[D] += v * sn * dt
        x[PSI] += (omega - x[BG] - kap * sd) * dt
        # Burilish boshi yoki oxiridan o'tdik: s xatosi yo'nalish xatosiga aylanadi (burilishni ertaroq/kechroq
        # boshladikmi, bilmaymiz). Burilish chegarasining o'zi ham aniq emas.
        dk = self._egrilik(x[S]) - kap
        F[PSI, S] = -dk
        if dk:
            q[PSI] += (dk * max(abs(sd) * dt, c.egrilik_noaniq)) ** 2 / dt
        q[S] = c.odometr_shovqin ** 2
        q[D] = c.yon_shovqin ** 2
        q[PSI] = c.giro_shovqin ** 2 + q[PSI]
        q[K] = c.odometr_ozgarish ** 2
        self.P = F @ self.P @ F.T + np.diag(q) * dt

    # --- o'lchovlar ---
    def _egrilik(self, s):
        return self.m.egrilik(min(max(s, 0.0), self.m.uzunlik - 1e-6))

    def _yangila(self, H, y, R, darvoza, faqat=None):
        """Umumiy Kalman yangilanishi. O'lchov darvozadan tashqarida bo'lsa, rad etadi (False).

        faqat: shu holatlargina tuzatiladi (qolganlari uchun kuchaytirish 0; Joseph shakli kovariatsiyani
        shunga mos hisoblaydi).
        """
        P = self.P
        PHt = P @ H.T
        Sm = H @ PHt + R
        Si = np.linalg.inv(Sm)
        if float(y @ Si @ y) > darvoza:
            return False
        Kg = PHt @ Si
        if faqat is not None:
            niqob = np.zeros((7, 1))
            niqob[faqat] = 1.0
            Kg = Kg * niqob
        dx = Kg @ y
        self.x += dx
        self._tuzatish += dx[[S, D]]
        I_KH = np.eye(7) - Kg @ H
        self.P = I_KH @ P @ I_KH.T + Kg @ R @ Kg.T
        return True

    def gps(self, gx, gy, aniqlik=None):
        """GPS o'lchovi (xarita tekisligida, m) va qabul qilgich aytgan aniqlik (m). Qaytaradi: qabul qilindimi."""
        c, x = self.c, self.x
        if aniqlik is not None and aniqlik > c.gps_xato:
            # Qabul qilgich aniqlik yomonlashganini aytyapti (binolar orasi): GPS xatosi shunchalik bo'lishi mumkin,
            # shuning uchun joyni GPS ga emas, ko'proq odometrga va kamera belgilariga qarab baholaymiz
            for i in (BX, BY):
                self.P[i, i] = max(self.P[i, i], aniqlik ** 2)
        px, py, th = self.chiziq.nuqta(x[S])
        kap = self._egrilik(x[S])
        tx, ty, nx, ny = math.cos(th), math.sin(th), -math.sin(th), math.cos(th)
        H = np.zeros((2, 7))
        f = 1 - kap * x[D]
        H[0, S], H[1, S] = f * tx, f * ty
        H[0, D], H[1, D] = nx, ny
        H[0, BX] = H[1, BY] = 1.0
        y = np.array([gx - (px + x[D] * nx + x[BX]), gy - (py + x[D] * ny + x[BY])])
        ok = self._yangila(H, y, np.eye(2) * c.gps_shovqin ** 2, c.darvoza_2)
        if not ok:
            self.rad["gps"] += 1
        return ok

    def chet(self, masofa, turi):
        """Kamera: yo'l chetigacha yon masofa. turi: "bordyur" (d = 0) yoki "parkovka" (to'xtagan mashinalar chizig'i)."""
        if turi == "bordyur":
            asos = 0.0
        else:
            b = self.m.bolak(self.s)
            if b.turi != "yol" or b.parkovka <= 0:
                return False  # xaritada bu yerda parkovka yo'q: nimani ko'rganimizni bilmaymiz
            asos = b.parkovka
        R = (self.c.chet_shovqin + 0.02 * abs(masofa)) ** 2
        return self._kamera("chet", D, masofa - (self.x[D] - asos), 1.0, R, [D, PSI, BG])

    def belgi(self, masofa, turi):
        """Kamera: oldimizdagi belgigacha masofa. turi: "kirish" (chorrahaga kirish: to'xtash chizig'i),
        "chiqish" (chorrahadan chiqish: qarshi tomon bordyuri) yoki "burilish" (o'ngga burilishda bordyur egilishi)."""
        c, s = self.c, self.x[S]
        nomzodlar = sorted((e for e, tr in self.belgilar if tr == turi), key=lambda e: abs((e - s) - masofa))
        if not nomzodlar:
            return False
        e = nomzodlar[0]
        R = ((c.burilish_shovqin + 0.03 * masofa) if turi == "burilish" else (c.chiziq_shovqin + 0.02 * masofa)) ** 2
        if len(nomzodlar) > 1:
            # Ikkita bir xil belgi filtr darvozasiga tushsa, qaysi biri ekanini bilmaymiz: o'lchovni ishlatmaymiz
            yangilik2 = masofa - (nomzodlar[1] - s)
            if yangilik2 ** 2 / (self.P[S, S] + R) < c.darvoza_1:
                return False
            if abs(yangilik2) < 2 * abs(masofa - (e - s)) + 2.0:
                self._rad_etilgan["belgi"] = []  # tiklash uchun ham ishonchsiz
                return self._yangila(self._H(S, -1.0), np.array([masofa - (e - s)]), np.array([[R]]), c.darvoza_1,
                                     [S, K, BX, BY])
        return self._kamera("belgi", S, masofa - (e - s), -1.0, R, [S, K, BX, BY])

    @staticmethod
    def _H(i, belgi):
        H = np.zeros((1, 7))
        H[0, i] = belgi
        return H

    def _kamera(self, nomi, i, yangilik, belgi, R, faqat):
        """Kamera o'lchovi (bitta holat bo'yicha). Ketma-ket izchil rad etilsa, filtr adashgan: tiklaymiz."""
        H = self._H(i, belgi)
        if self._yangila(H, np.array([yangilik]), np.array([[R]]), self.c.darvoza_1, faqat):
            self._rad_etilgan[nomi] = []
            return True
        self.rad[nomi] += 1
        r = self._rad_etilgan[nomi]
        r.append(yangilik)
        if len(r) >= self.c.tiklash_kadr:
            oxirgi = r[-self.c.tiklash_kadr:]
            if max(oxirgi) - min(oxirgi) < 6 * math.sqrt(R) + 0.2:
                # Kamera bir xil narsani ko'rsatyapti: bu holat bo'yicha filtr noaniqligini kattalashtirib, qabul qilamiz
                self.P[i, :] = 0.0
                self.P[:, i] = 0.0
                self.P[i, i] = yangilik ** 2 + 4 * R
                self.tiklash += 1
                self._rad_etilgan[nomi] = []
                return self._yangila(H, np.array([yangilik]), np.array([[R]]), math.inf, faqat)
        return False

    # --- rejalash uchun ---
    def rejalash_joyi(self):
        """Rejalovchi va rul boshqaruviga beriladigan joy: (s, d). Ehtiyot uchun s 2 sigma oldinga (chorraha va
        burilish yaqinroq), d 2 sigma bordyur tomonga (bordyurdan uzoqroq yuradi) surilgan."""
        k = self.c.ehtiyot_sigma
        return self.s + k * self.sigma_s, self.d - k * self.sigma_d

    def tuzatishni_ol(self):
        """Oxirgi chaqiruvdan beri joy qancha tuzatildi (s, d). Kuzatuvchidagi obyektlar ham shuncha suriladi:
        ular kameradan skuterga nisbatan o'lchangan, skuter joyi tuzatilsa, ularniki ham tuzatiladi."""
        ehtiyot = (self.c.ehtiyot_sigma * self.sigma_s, -self.c.ehtiyot_sigma * self.sigma_d)
        ds = float(self._tuzatish[0]) + ehtiyot[0] - self._oldingi_ehtiyot[0]
        dd = float(self._tuzatish[1]) + ehtiyot[1] - self._oldingi_ehtiyot[1]
        self._oldingi_ehtiyot = ehtiyot
        self._tuzatish[:] = 0.0
        return ds, dd

    def cheklov(self, max_tezlik):
        """Joy noaniqligiga qarab tezlik chegarasi va sabab."""
        c = self.c
        if self.sigma_d > c.sigma_d_toxta:
            return 0.0, "joylashuv_xato"
        if self.sigma_d > c.sigma_d_sekin or self.sigma_s > c.sigma_s_sekin:
            return min(max_tezlik, c.sekin_tezlik), "joylashuv_sekin"
        return max_tezlik, None
