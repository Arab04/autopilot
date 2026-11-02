"""Mijoz Telegram boti sinovlari (Telegram o'rniga soxta API, flot haqiqiy).

    python mijoz_bot_sinovlar.py

1. Havola: noto'g'ri kod bilan ulanib bo'lmaydi; to'g'ri havola ulaydi; flot javobida kuzatish havolasi bor.
2. To'liq yo'l: mijozga tayinlandi, yo'lda (ETA va joylashuv), yetib keldi (PIN va tugma) xabarlari keladi;
   [Qutini ochish] tugmasi buyurtmani topshiradi; takroriy xabar yo'q.
3. PIN ni yozish: noto'g'ri PIN ochmaydi, to'g'risi ochadi.
4. Begona chat: boshqa odamning buyurtmasini ko'rmaydi va qutisini ocholmaydi.
5. Mijoz kelmasa: "yuk omborga qaytarildi" xabari.
6. Skuter joylashuvi (lat/lon) xaritadagi nuqtaga mos.
"""

import math
import sys

from flot import MIJOZ_KUTISH, Flot
from mijoz_bot import MijozBot
from xarita_sinovlar import CHIRCHIQ_OSM
from autopilot.xarita import Xarita

XARITA = Xarita.osm_dan(str(CHIRCHIQ_OSM))
MIJOZ, BEGONA = 111, 222


class SoxtaBot(MijozBot):
    def __init__(self, flot):
        super().__init__("soxta", flot)
        self.yuborilgan = []   # (usul, param)

    def api(self, usul, kutish=15, **param):
        self.yuborilgan.append((usul, param))
        if usul == "getMe":
            return {"username": "skuter_sinov_bot"}
        return {"message_id": len(self.yuborilgan)}

    def matnlar(self, chat=MIJOZ):
        return [p["text"] for u, p in self.yuborilgan if u == "sendMessage" and p["chat_id"] == chat]

    def yoz_xabar(self, chat, matn):
        self._xabar({"chat": {"id": chat}, "text": matn})

    def bos(self, chat, data):
        self._callback({"id": "q", "message": {"chat": {"id": chat}}, "data": data})


def _tayyor(manzil=6):
    f = Flot(skuterlar=2, avto_buyurtma=0, xarita=XARITA, urug=5)
    bot = SoxtaBot(f)
    bot.boshlash()
    b, _ = f.buyurtma_ber(manzil=manzil, manba="crm", avto_mijoz=False)
    return f, bot, b


def _yur(f, bot, shart, chegara=4 * 3600):
    for i in range(chegara):
        if shart():
            break
        f.qadam(1.0)
        if i % 5 == 0:
            bot.tekshir()
    bot.tekshir()
    return shart()


def sinov_havola():
    f, bot, b = _tayyor()
    with f.lock:
        j = f.buyurtma_json(b, sirli=True)
    havola_ok = j.get("kuzatish_havola") == f"https://t.me/skuter_sinov_bot?start={b.id}_{b.kuzatish}"
    bot.yoz_xabar(MIJOZ, f"/start {b.id}_notogri")
    bot.yoz_xabar(MIJOZ, f"/start {b.id + 1}_{b.kuzatish}")
    rad = not bot._mening(MIJOZ)
    bot.yoz_xabar(MIJOZ, "/start " + j["kuzatish"])
    ulandi = bot._mening(MIJOZ) == [b.id] and "omborda yuklanmoqda" in bot.matnlar()[-1]
    return havola_ok and rad and ulandi, f"havola {havola_ok}, noto'g'ri kod rad {rad}, ulandi {ulandi}"


def sinov_toliq_yol():
    f, bot, b = _tayyor()
    bot.yoz_xabar(MIJOZ, f"/start {b.id}_{b.kuzatish}")
    yolda = _yur(f, bot, lambda: b.holat == "yolda")
    joy = [p for u, p in bot.yuborilgan if u == "sendLocation"]
    keldi = _yur(f, bot, lambda: b.holat == "yetib_keldi")
    oxirgi = [(u, p) for u, p in bot.yuborilgan if u == "sendMessage"][-1][1]
    pin_bor = b.pin in oxirgi["text"] and oxirgi["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == f"och:{b.id}"
    bot.bos(MIJOZ, f"och:{b.id}")
    topshirildi = b.holat == "topshirildi" and "Quti ochildi" in bot.matnlar()[-1]
    n = len(bot.matnlar())
    for _ in range(20):
        f.qadam(1.0)
        bot.tekshir()
    takror_yoq = len(bot.matnlar()) == n
    ok = yolda and len(joy) == 1 and keldi and pin_bor and topshirildi and takror_yoq
    return ok, (f"yo'lda {yolda}, joylashuv {len(joy)}, yetib keldi {keldi}, PIN+tugma {pin_bor}, "
                f"topshirildi {topshirildi}, takrorsiz {takror_yoq}, xabarlar {n}")


def sinov_pin_yozish():
    f, bot, b = _tayyor()
    bot.yoz_xabar(MIJOZ, f"/start {b.id}_{b.kuzatish}")
    bot.yoz_xabar(MIJOZ, b.pin)
    erta = "kutayotgan skuter yo'q" in bot.matnlar()[-1]
    _yur(f, bot, lambda: b.holat == "yetib_keldi")
    notogri = "0000" if b.pin != "0000" else "1111"
    bot.yoz_xabar(MIJOZ, notogri)
    rad = b.holat == "yetib_keldi" and "PIN noto'g'ri" in bot.matnlar()[-1]
    bot.yoz_xabar(MIJOZ, b.pin)
    return erta and rad and b.holat == "topshirildi", f"erta rad {erta}, xato PIN rad {rad}, holat {b.holat}"


def sinov_begona():
    f, bot, b = _tayyor()
    bot.yoz_xabar(MIJOZ, f"/start {b.id}_{b.kuzatish}")
    _yur(f, bot, lambda: b.holat == "yetib_keldi")
    bot.bos(BEGONA, f"och:{b.id}")
    bot.yoz_xabar(BEGONA, b.pin)
    bot.yoz_xabar(BEGONA, "/holat")
    begona_xabar = bot.matnlar(BEGONA)
    javob = [p for u, p in bot.yuborilgan if u == "answerCallbackQuery"][-1].get("text", "")
    ok = b.holat == "yetib_keldi" and "ulanmagan" in javob and all("ulangan buyurtma yo'q" in m for m in begona_xabar) \
        and not any(b.pin in m for m in begona_xabar)
    return ok, f"holat {b.holat}, tugma javobi: {javob!r}, begonaga {len(begona_xabar)} xabar (PIN yo'q)"


def sinov_kelmadi():
    f, bot, b = _tayyor()
    bot.yoz_xabar(MIJOZ, f"/start {b.id}_{b.kuzatish}")
    _yur(f, bot, lambda: b.holat == "yetib_keldi")
    qaytdi = _yur(f, bot, lambda: b.holat == "qaytarildi", chegara=MIJOZ_KUTISH + 60)
    ok = qaytdi and "omborga qaytarildi" in bot.matnlar()[-1] and not bot.obunalar
    return ok, f"holat {b.holat}, obuna yopildi {not bot.obunalar}"


def sinov_joylashuv():
    f = Flot(skuterlar=1, avto_buyurtma=0, xarita=XARITA)
    xato = 0.0
    for i in list(XARITA.asosiy)[:200]:
        t = XARITA.tugunlar[i]
        la, lo = f.ll(*XARITA.xy(i))
        xato = max(xato, Xarita.masofa_ll((la, lo), (t.lat, t.lon)))
    return xato < 1.0 and math.isfinite(xato), f"eng katta farq {xato:.2f} m"


SINOVLAR = [
    ("Havola va ulanish", sinov_havola),
    ("To'liq yo'l va tugma", sinov_toliq_yol),
    ("PIN ni yozish", sinov_pin_yozish),
    ("Begona chat", sinov_begona),
    ("Mijoz kelmadi", sinov_kelmadi),
    ("Skuter joylashuvi", sinov_joylashuv),
]


def main():
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
