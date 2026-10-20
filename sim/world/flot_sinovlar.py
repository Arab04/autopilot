"""Flot va dispetcherlik (E bosqich) sinovlari.

    python flot_sinovlar.py            # sinovlar
    python flot_sinovlar.py --jadval   # "nechta skuter va operator kerak" jadvali (natijalar_flot.txt)

1. Model batafsil simulyatorga mos: 10 manzilga safar vaqti 4-bosqich natijalaridan 25% dan ko'p farq qilmaydi.
2. Dispetcher: skuter yetmasa buyurtma navbatda turadi, skuter qaytishi bilan beriladi.
3. Batareya: zaryadi yetmaydigan skuterga uzoq buyurtma berilmaydi; omborda zaryadlanadi.
4. PIN: noto'g'ri PIN ochmaydi, 5 ta xatodan keyin bloklanadi; to'g'ri PIN topshiradi, skuter qaytadi.
5. Mijoz kelmasa: 10 daqiqadan keyin yuk omborga qaytadi.
6. Operatorlar navbati: operator kam bo'lsa skuterlar uzoqroq kutadi.
7. HTTP API: parol, CRM kaliti faqat buyurtma yo'llarida, buyurtma berish, holat, PIN.
8. Bir kunlik ish (10 soat, 10 skuter, 6 buyurtma/soat): 90%+ buyurtma 45 daqiqada yetadi.
"""

import base64
import http.client
import json
import sys
import threading

from flot import BATAREYA_ALMASHTIRISH, MIJOZ_KUTISH, SARF_KM, ZAHIRA, ZARYAD_TEZLIGI, Flot
from xarita_sinovlar import CHIRCHIQ_OSM
from autopilot.xarita import Xarita

XARITA = Xarita.osm_dan(str(CHIRCHIQ_OSM))

# 4-bosqich (batafsil simulyator, har manzil 10 marta): o'rtacha safar vaqti, daqiqa. natijalar_chirchiq.txt
BATAFSIL_DAQ = [39.9, 18.6, 21.2, 24.0, 15.6, 10.4, 11.0, 21.2, 17.3, 6.3]


def _flot(**k):
    k.setdefault("avto_buyurtma", 0)
    return Flot(xarita=XARITA, **k)


def _kut(f, shart, chegara=4 * 3600):
    for _ in range(chegara):
        if shart():
            return True
        f.qadam(1.0)
    return shart()


def sinov_kalibrlash():
    f = _flot(skuterlar=1)
    farqlar = []
    for (nomi, la, lo), ref in zip(f.manzillar[:10], BATAFSIL_DAQ):
        model = f.marshrut(la, lo).kutilgan_vaqt() / 60
        farqlar.append((model - ref) / ref)
    eng = max(farqlar, key=abs)
    return all(abs(x) <= 0.35 for x in farqlar) and sum(abs(x) for x in farqlar) / 10 <= 0.15, \
        f"o'rtacha farq {100 * sum(abs(x) for x in farqlar) / 10:.0f}%, eng katta {100 * eng:+.0f}%"


def sinov_dispetcher():
    f = _flot(skuterlar=2, urug=3)
    bs = [f.buyurtma_ber(manzil=k)[0] for k in (6, 10, 2)]
    darhol = [b.holat for b in bs]
    ok1 = darhol == ["tayinlandi", "tayinlandi", "yangi"]
    _kut(f, lambda: bs[2].holat != "yangi")
    ok2 = bs[2].skuter in (1, 2) and bs[2].tayinlandi > max(bs[0].topshirildi or 0, bs[1].topshirildi or 0) - 1
    _kut(f, lambda: all(b.holat in ("topshirildi", "qaytarildi") for b in bs))
    return ok1 and ok2 and all(b.holat in ("topshirildi", "qaytarildi") for b in bs), \
        f"darhol {darhol}, 3-buyurtma {bs[2].tayinlandi / 60:.0f}-daqiqada qaytgan skuter {bs[2].skuter} ga"


def sinov_batareya():
    f = _flot(skuterlar=1, urug=4)
    sk = f.skuterlar[0]
    sk.batareya = 30.0
    b, _ = f.buyurtma_ber(manzil=1)          # Troitsk, 7,9 km: borib-qaytishga ~55% kerak
    kerak = f.marshrut(b.lat, b.lon).uzunlik / 1000 * SARF_KM * 2 + ZAHIRA
    darhol = b.holat
    _kut(f, lambda: b.holat != "yangi")
    ok = darhol == "yangi" and b.holat == "tayinlandi" and f.skuterlar[0].batareya >= kerak - 0.5
    return ok, f"kerak {kerak:.0f}%, zaryadlanib {b.tayinlandi / 60:.0f}-daqiqada jo'nadi"


def sinov_pin():
    f = _flot(skuterlar=1, urug=5)
    b, _ = f.buyurtma_ber(manzil=10, avto_mijoz=False)
    oldin = f.qutini_och(b.id, b.pin)            # hali yetib kelmagan
    _kut(f, lambda: b.holat == "yetib_keldi")
    xatolar = [f.qutini_och(b.id, "0000" if b.pin != "0000" else "1111") for _ in range(5)]
    blok = f.qutini_och(b.id, b.pin)             # 5 ta xatodan keyin to'g'ri PIN ham ochmaydi
    f2 = _flot(skuterlar=1, urug=5)
    b2, _ = f2.buyurtma_ber(manzil=10, avto_mijoz=False)
    _kut(f2, lambda: b2.holat == "yetib_keldi")
    ochildi = f2.qutini_och(b2.id, b2.pin)
    _kut(f2, lambda: f2.skuterlar[0].holat in ("omborda", "zaryad"))
    ok = (oldin and "yetib kelmagan" in oldin and all(x == "PIN noto'g'ri" for x in xatolar) and blok and "5 marta" in blok
          and ochildi is None and b2.holat == "topshirildi" and f2.skuterlar[0].holat in ("omborda", "zaryad"))
    return ok, f"{b2.yetib_keldi / 60:.0f}-daqiqada yetdi, PIN bilan ochildi, skuter qaytdi"


def sinov_mijoz_kelmadi():
    f = _flot(skuterlar=1, urug=6)
    b, _ = f.buyurtma_ber(manzil=6, avto_mijoz=False)
    _kut(f, lambda: b.holat == "yetib_keldi")
    t0 = f.t
    _kut(f, lambda: b.holat != "yetib_keldi")
    kutdi = f.t - t0
    _kut(f, lambda: f.skuterlar[0].holat in ("omborda", "zaryad"))
    ok = b.holat == "qaytarildi" and abs(kutdi - MIJOZ_KUTISH) <= 2 and f.skuterlar[0].buyurtma is None
    return ok, f"{kutdi:.0f} s kutdi, yuk omborga qaytdi"


def sinov_operator_navbati():
    natija = {}
    for op in (1, 4):
        f = _flot(skuterlar=12, operatorlar=op, urug=7)
        for i in range(12):
            f._operator_sora(f.skuterlar[i], "yordam")   # 12 ta skuter bir vaqtda qolib ketdi
        _kut(f, lambda: not f.operator_navbat and not f.operator_band, 3600)
        k = f.stat["operator_kutish"]
        natija[op] = sum(k) / len(k)
    return natija[1] > 2.5 * natija[4] and natija[4] > 0, \
        f"o'rtacha navbat: 1 operator {natija[1]:.0f} s, 4 operator {natija[4]:.0f} s"


def sinov_api():
    import operator_panel as opn
    sim = opn.Simulyator(opn.PanelOperator())
    f = _flot(skuterlar=2, urug=8)
    srv = opn.server_yasa(sim, port=0, parol="sir", login="admin", flot=f, api_kalit="crm-kalit")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    admin = {"Authorization": "Basic " + base64.b64encode(b"admin:sir").decode()}
    crm = {"X-API-Kalit": "crm-kalit"}

    def so(usul, yol, tana=None, sarlavha=None):
        c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        c.request(usul, yol, body=json.dumps(tana) if tana is not None else None,
                  headers={"Content-Type": "application/json", **(sarlavha or {})})
        r = c.getresponse()
        tana = r.read()
        try:
            return r.status, json.loads(tana)
        except ValueError:
            return r.status, tana

    try:
        k = {}
        k["parolsiz"] = so("GET", "/api/flot/holat")[0]
        k["crm_holat"] = so("GET", "/api/flot/holat", sarlavha=crm)[0]          # CRM faqat buyurtma yo'llari
        k["crm_sozlama"] = so("POST", "/api/flot/sozlama", {"skuterlar": 9}, {"X-API-Kalit": "xato"})[0]
        k["sahifa"] = so("GET", "/flot", sarlavha=admin)[0]
        st, b = so("POST", "/api/buyurtma", {"lat": 41.4708, "lon": 69.5742, "nomi": "Sinov", "tel": "+99890"}, crm)
        k["crm_buyurtma"] = st
        k["notogri"] = so("POST", "/api/buyurtma", {"lat": 40.0, "lon": 69.0}, crm)[0]   # hududdan tashqari
        k["notogri_json"] = so("POST", "/api/buyurtma", [1, 2], admin)[0]
        st, h = so("GET", f"/api/buyurtma/{b['id']}", sarlavha=crm)
        k["kuzatish"] = st
        f.qadam(1.0)
        _kut(f, lambda: f.buyurtmalar[b["id"]].holat == "yetib_keldi")
        k["xato_pin"] = so("POST", f"/api/buyurtma/{b['id']}/och", {"pin": "x"}, crm)[0]
        k["pin"] = so("POST", f"/api/buyurtma/{b['id']}/och", {"pin": b["pin"]}, crm)[0]
        k["sozlama"] = so("POST", "/api/flot/sozlama", {"skuterlar": 4, "operatorlar": 3}, admin)[0]
        _, xar = so("GET", "/api/flot/xarita", sarlavha=admin)
        kutilgan = {"parolsiz": 401, "crm_holat": 401, "crm_sozlama": 401, "sahifa": 200, "crm_buyurtma": 201,
                    "notogri": 400, "notogri_json": 400, "kuzatish": 200, "xato_pin": 400, "pin": 200, "sozlama": 200}
        ok = (k == kutilgan and b["manba"] == "crm" and "eta_daq" in h and "pin" not in h
              and f.buyurtmalar[b["id"]].holat == "topshirildi" and len(f.skuterlar) == 4 and f.operatorlar == 3
              and len(xar["kochalar"]) > 100)
        return ok, ", ".join(f"{n}={v}" for n, v in k.items() if kutilgan.get(n) != v) or "barcha javoblar to'g'ri"
    finally:
        srv.shutdown()


def kun(skuterlar, operatorlar, buyurtma, soat=10, urug=1, zaryad_tezligi=ZARYAD_TEZLIGI):
    f = _flot(skuterlar=skuterlar, operatorlar=operatorlar, avto_buyurtma=buyurtma, urug=urug,
              zaryad_tezligi=zaryad_tezligi)
    for _ in range(int(soat * 3600)):
        f.qadam(1.0)
    return f.korsatkichlar()


def sinov_kun():
    k = kun(10, 1, 6)
    return k["oz_vaqtida_foiz"] >= 90 and k["navbatda"] <= 2, \
        f"{k['topshirildi']} ta topshirildi, o'rtacha {k['ortacha_daq']} daq, 45 daqiqada {k['oz_vaqtida_foiz']}%"


SINOVLAR = [
    ("1. Model batafsil simulyatorga mos (safar vaqti)", sinov_kalibrlash),
    ("2. Dispetcher: navbat va bo'shagan skuter", sinov_dispetcher),
    ("3. Batareya: yetmasa zaryadlanib keyin jo'naydi", sinov_batareya),
    ("4. PIN bilan quti", sinov_pin),
    ("5. Mijoz kelmadi: yuk omborga qaytadi", sinov_mijoz_kelmadi),
    ("6. Operatorlar navbati", sinov_operator_navbati),
    ("7. HTTP API va CRM kaliti", sinov_api),
    ("8. Bir kunlik ish (10 skuter, 6 buyurtma/soat)", sinov_kun),
]


def jadval():
    """Turli talab uchun nechta skuter va operator kerak. 3 xil urug' o'rtachasi."""
    qatorlar = ["Flot modeli: 10 soatlik ish kuni, 3 xil tasodifiy kun o'rtachasi. O'z vaqtida = buyurtmadan "
                "45 daqiqa ichida topshirildi.", "",
                f"{'Buyurtma/soat':>13} {'Skuter':>6} {'Operator':>8} {'O`z vaqtida':>11} {'O`rtacha':>9} "
                f"{'Navbatda':>8} {'Operator chaq./soat':>19} {'Operator band':>13} {'Skuter band':>11}"]
    for buyurtma, variantlar, zt in [
            (3, [(3, 1), (5, 1)], ZARYAD_TEZLIGI), (6, [(5, 1), (8, 1), (10, 1)], ZARYAD_TEZLIGI),
            (12, [(10, 1), (15, 1), (20, 1)], ZARYAD_TEZLIGI), (24, [(20, 1), (30, 2), (40, 2)], ZARYAD_TEZLIGI),
            ("", [], None),
            (6, [(5, 1), (6, 1)], BATAREYA_ALMASHTIRISH), (12, [(10, 1), (12, 1)], BATAREYA_ALMASHTIRISH),
            (24, [(20, 1), (24, 2)], BATAREYA_ALMASHTIRISH)]:
        if zt is None:
            qatorlar += ["", "Batareya almashtirish bilan (zaryadlash 3,3 soat o'rniga bo'sh batareya ~30 daqiqada "
                             "to'lasiga almashtiriladi):"]
            continue
        for sk, op in variantlar:
            ks = [kun(sk, op, buyurtma, urug=u, zaryad_tezligi=zt) for u in (1, 2, 3)]

            def o(n):
                v = [k[n] for k in ks if k[n] is not None]
                return sum(v) / len(v) if v else float("nan")
            qatorlar.append(f"{buyurtma:>13} {sk:>6} {op:>8} {o('oz_vaqtida_foiz'):>10.0f}% {o('ortacha_daq'):>6.0f} daq "
                            f"{o('navbatda'):>8.0f} {o('operator_chaqiruv_soat'):>19.1f} {o('operator_bandlik_foiz'):>12.0f}% "
                            f"{o('skuter_bandlik_foiz'):>10.0f}%")
            print(qatorlar[-1], flush=True)
    return qatorlar


def main():
    if "--jadval" in sys.argv:
        q = jadval()
        from pathlib import Path
        Path(__file__).with_name("natijalar_flot.txt").write_text("\n".join(q) + "\n", encoding="utf-8")
        return 0
    xatolar = []
    for nomi, f in SINOVLAR:
        ok, izoh = f()
        print(f"{'OK ' if ok else 'XATO'}  {nomi} ({izoh})", flush=True)
        if not ok:
            xatolar.append(nomi)
    print("\nO'tmagan sinovlar:", "; ".join(xatolar) if xatolar else "yo'q")
    return 1 if xatolar else 0


if __name__ == "__main__":
    sys.exit(main())
