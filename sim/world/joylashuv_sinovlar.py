"""Joylashuvni aniqlash sinovlari (5-bosqich). Ishga tushirish: python3 joylashuv_sinovlar.py [tasodifiy_soni]

Skuter endi o'z joyini bilmaydi: GPS, odometr, giroskop va kameradan baholaydi.
Asosiy talablar: GPS yo'qolsa, sakrasa yoki ko'p xato qilsa ham skuter hech kimga tegmaydi, bordyurga
urilmaydi va chorraha ichida to'xtab qolmaydi. Joyini bilmasa, to'xtab operatorni chaqiradi.
"""

import math
import random
import sys
from multiprocessing import Pool
from pathlib import Path

from joylashuv_dunyo import JoylashuvSharoiti, tasodifiy_sharoit
from yol_dunyo import YolSsenariy, Bolak, Marshrut, ishga_tushir, tasodifiy_kocha
from yol_sinovlar import _kesuvchilar, _parkovka_qatori, _xavfsiz, _yol

GRAD = math.pi / 180


def _chorrahali(boshi=250, keyin=150, polosa=4):
    return Marshrut([_yol(boshi), Bolak("otish", polosa * 3.5, yollar=polosa, svetofor=True), _yol(keyin)])


def _sc(nomi, marshrut, sh, **k):
    return YolSsenariy(nomi, marshrut, joylashuv=sh, **k)


def _chorraha_ssenariy(nomi, sh, boshi=250, urug=0):
    return _sc(nomi, _chorrahali(boshi), sh, kesuvchi=_kesuvchilar(0, 4), svetofor_davri=(20.0, 30.0),
               svetofor_siljish=[10.0], oqim=0.06, urug=urug)


def _yaxshi(n, chiziq=0.6):
    return n.yetib_keldi and _xavfsiz(n) and n.chorraha_ichida == 0 and n.joy_chiziq < chiziq


ANIQ = [
    (_chorraha_ssenariy("1. Oddiy GPS, svetoforli chorraha", JoylashuvSharoiti(), urug=1),
     lambda n: _yaxshi(n, 0.5) and n.joy_max_d < 0.15 and n.joy_izchil > 0.95),
    (_chorraha_ssenariy("2. GPS 200 m yo'q (daraxtlar ostida), keyin chorraha",
                        JoylashuvSharoiti(gps_yoq=[(30, 240)], odometr_xato=0.03), urug=2),
     lambda n: _yaxshi(n) and n.joy_max_d < 0.15),
    (_chorraha_ssenariy("3. GPS 25 m ga sakraydi (80 m davomida)",
                        JoylashuvSharoiti(gps_sakrash=[(60, 140, 18.0, -17.0)]), urug=3),
     lambda n: _yaxshi(n) and n.joy_max_s < 3.0 and n.joy_rad >= 50),
    (_chorraha_ssenariy("4. Baland binolar orasi: GPS xatosi 6 m gacha",
                        JoylashuvSharoiti(kanyon=[(20, 420, 6.0)]), urug=4),
     lambda n: _yaxshi(n)),
    (_sc("5. G'ildirak yeyilgan (odometr 6% xato), oxirida GPS yo'q", _chorrahali(500, 100),
         JoylashuvSharoiti(odometr_xato=0.06, gps_yoq=[(380, 500)]), kesuvchi=_kesuvchilar(0, 4),
         svetofor_davri=(20.0, 30.0), urug=5),
     lambda n: _yaxshi(n) and n.joy_k_xato < 0.015),
    (_sc("6. Giroskop xatosi 1 grad/s, o'ngga burilish",
         Marshrut([_yol(150), Bolak("burilish", 6.0 * math.pi / 2, egrilik=-1 / 6.0), _yol(150)]),
         JoylashuvSharoiti(giro_xato=1.0 * GRAD), urug=6),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.joy_max_d < 0.2),
    (_sc("7. Parkovka: bordyur o'rniga mashinalar chizig'i ko'rinadi", Marshrut([_yol(250, parkovka=2.2)]),
         JoylashuvSharoiti(), transport=_parkovka_qatori(20, 230), urug=7),
     lambda n: n.yetib_keldi and _xavfsiz(n) and n.eshik_zonasi == 0 and n.joy_max_d < 0.2),
    (_sc("8. Bordyur 40 m ko'rinmaydi va GPS yo'q", Marshrut([_yol(250)]),
         JoylashuvSharoiti(chet_yoq=[(80, 120)], gps_yoq=[(60, 140)]), urug=8),
     lambda n: _xavfsiz(n) and n.joy_izchil > 0.95),
    (_sc("9. Tun: yo'l cheti umuman ko'rinmaydi (faqat GPS)", Marshrut([_yol(250)]),
         JoylashuvSharoiti(chet_korinish=0.0), vaqt_chegarasi=120, urug=9),
     lambda n: n.yordam and _xavfsiz(n) and "joylashuv_xato" in n.iz["holat"]),
    (_sc("10. Chapga burilish (2 chorraha), GPS yo'q",
         Marshrut([_yol(150), Bolak("otish", 7.0, yollar=2, svetofor=True),
                   Bolak("burilish", 4.5 * math.pi / 2, egrilik=1 / 4.5), Bolak("otish", 14.0, yollar=4, svetofor=True),
                   _yol(80)]),
         JoylashuvSharoiti(gps_yoq=[(40, 250)], odometr_xato=-0.03), kesuvchi=_kesuvchilar(0, 2, 6.0) + _kesuvchilar(1, 4, 6.0),
         svetofor_davri=(20.0, 20.0), svetofor_siljish=[0.0, 20.0], oqim=0.05, urug=10),
     lambda n: _yaxshi(n)),
]


def _tasodifiy(urug, joylashuv=True):
    sc = tasodifiy_kocha(urug, rejim="toliq" if urug % 3 == 0 else "yarim", kamera_xato=(urug % 5 == 0))
    if joylashuv:
        sc.joylashuv = tasodifiy_sharoit(random.Random(urug * 31 + 5), sc.marshrut.uzunlik)
    n = ishga_tushir(sc)
    n.joy_toxtadi = "joylashuv_xato" in n.iz["holat"]
    n.iz = None
    return n


def _asos(urug):
    return _tasodifiy(urug, joylashuv=False)


def main():
    soni = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    xatolar = []
    print(f"{'Ssenariy':58} {'Yetdi':6} {'To`qn.':7} {'Xato s':7} {'Xato d':7} {'Chorr.':7} Natija")
    natijalar = []
    for sc, shart in ANIQ:
        n = ishga_tushir(sc)
        ok = shart(n)
        natijalar.append((n, ok, sc))
        if not ok:
            xatolar.append(sc.nomi)
        jami = n.mashina_toq + n.odam_toq + n.velo_toq + n.tosiq_toq + n.kesuvchi_toq
        print(f"{sc.nomi[:58]:58} {'ha' if n.yetib_keldi else 'yo`q':6} {jami:<7} {n.joy_max_s:5.2f} m {n.joy_max_d:5.2f} m "
              f"{n.joy_chiziq:5.2f} m {'O`TDI' if ok else 'O`TMADI'}")

    print(f"\n{soni} ta tasodifiy ko'cha (3-bosqichdagi ko'chalar) + tasodifiy datchik sharoiti: GPS yo'qolishi (40%), "
          f"sakrashi (25%), binolar orasi (25%), bordyur ko'rinmasligi (30%), odometr va giroskop xatosi...")
    with Pool() as p:
        nat = p.map(_tasodifiy, range(1, soni + 1))
        asos = p.map(_asos, range(1, soni + 1))
    yetdi, yordam = sum(n.yetib_keldi for n in nat), sum(n.yordam for n in nat)
    a_yetdi, a_yordam = sum(n.yetib_keldi for n in asos), sum(n.yordam for n in asos)
    yomon = [n.nomi for n in nat if not _xavfsiz(n)]
    a_yomon = [n.nomi for n in asos if not _xavfsiz(n)]
    ichida = sum(n.chorraha_ichida for n in nat)
    a_ichida = sum(n.chorraha_ichida for n in asos)
    joy_toxtadi = sum(n.yordam and n.joy_toxtadi for n in nat)
    max_s = sorted(n.joy_max_s for n in nat)
    print(f"  {'':38} {'aniq joy':>10} {'joylashuv filtri':>18}")
    print(f"  {'Manzilga o`zi yetdi':38} {a_yetdi:>10} {yetdi:>18}")
    print(f"  {'Qotib qolib operator chaqirdi':38} {a_yordam:>10} {yordam:>18}")
    print(f"  {'  shundan joyini bilmagani uchun':38} {'-':>10} {joy_toxtadi:>18}")
    print(f"  {'To`qnashuv yoki bordyurga tegish':38} {len(a_yomon):>10} {len(yomon):>18}")
    print(f"  {'Eshik ochilish zonasidan o`tish':38} {sum(n.eshik_zonasi for n in asos):>10} "
          f"{sum(n.eshik_zonasi for n in nat):>18}")
    print(f"  {'Chorraha ichida to`xtab qolish':38} {a_ichida:>10} {ichida:>18}")
    print(f"  {'O`rtacha tezlik (km/soat)':38} {sum(n.ortacha_kmh for n in asos) / soni:>10.1f} "
          f"{sum(n.ortacha_kmh for n in nat) / soni:>18.1f}")
    print(f"  Joy xatosi, marshrut bo'ylab: o'rtacha marshrutda eng kattasi {max_s[len(max_s) // 2]:.2f} m, "
          f"eng yomon marshrutda {max_s[-1]:.2f} m")
    print(f"  Joy xatosi, yon tomonga: eng yomon marshrutda {max(n.joy_max_d for n in nat):.2f} m")
    print(f"  Chorrahaga 15 m qolganda, marshrut bo'ylab: eng yomon {max(n.joy_chiziq for n in nat):.2f} m")
    print(f"  Filtr o'z xatosini to'g'ri bilgan vaqt (3 sigma ichida): eng yomon marshrutda "
          f"{100 * min(n.joy_izchil for n in nat):.1f}%")
    print(f"  Rad etilgan o'lchovlar (GPS sakrashi, kamera yanglishishi): {sum(n.joy_rad for n in nat)}; "
          f"filtr qayta tiklandi: {sum(n.joy_tiklash for n in nat)} marta")
    if yomon:
        xatolar.append(f"tasodifiy: {len(yomon)} ta marshrutda to'qnashuv ({', '.join(yomon[:8])})")
    if ichida > a_ichida:
        xatolar.append(f"tasodifiy: chorraha ichida to'xtash {ichida} (aniq joy bilan {a_ichida})")
    qolgan = soni - yetdi - yordam
    if qolgan:
        xatolar.append(f"tasodifiy: {qolgan} ta vaqt chegarasida yetmadi")
    if yordam > 0.15 * soni:
        xatolar.append(f"tasodifiy: operator {yordam}/{soni} marta kerak bo'ldi (chegara 15%)")
    chiz(natijalar[:6])
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


def chiz(natijalar):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, axes = plt.subplots(len(natijalar), 2, figsize=(12, 1.9 * len(natijalar)))
    for (ax_s, ax_d), (n, ok, sc) in zip(axes, natijalar):
        iz = n.iz
        for ax, haq, tax, sig, nomi in ((ax_s, iz["s"], iz["s_tax"], iz["sig_s"], "s"),
                                        (ax_d, iz["d"], iz["d_tax"], iz["sig_d"], "d")):
            xato = [a - b for a, b in zip(haq, tax)]
            ax.fill_between(iz["s"], [-3 * x for x in sig], [3 * x for x in sig], color="#cfe2f3", label="3 sigma")
            ax.plot(iz["s"], xato, color="#d62728", lw=0.8, label="haqiqiy xato")
            for a, b in sc.joylashuv.gps_yoq:
                ax.axvspan(a, b, color="#eeeeee", zorder=0)
            for b in sc.marshrut.bolaklar:
                if b.turi == "otish":
                    ax.axvspan(b.boshi, b.oxiri, color="#f5e6a8", zorder=0)
            ax.set_ylabel(f"{nomi} xatosi (m)", fontsize=8)
            ax.tick_params(labelsize=7)
        ax_s.set_title(f"{n.nomi}  [{'O`TDI' if ok else 'O`TMADI'}]", fontsize=9, loc="left",
                       color="#2ca02c" if ok else "#d62728")
    axes[0][0].legend(fontsize=7, loc="upper left")
    for ax in axes[-1]:
        ax.set_xlabel("marshrut bo'ylab (m). Kulrang = GPS yo'q, sariq = chorraha", fontsize=8)
    fig.tight_layout()
    out = Path(__file__).with_name("natijalar_joylashuv.png")
    fig.savefig(out, dpi=80)
    print(f"\nGrafik: {out}")


if __name__ == "__main__":
    sys.exit(main())
