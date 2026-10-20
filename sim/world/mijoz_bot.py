"""Mijozlar uchun Telegram bot: buyurtmani kuzatish va skuter qutisini PIN bilan ochish.

operator_panel.py ichidan ishga tushadi (muhit o'zgaruvchisi MIJOZ_TELEGRAM_TOKEN, @BotFather dan;
operator botidan ALOHIDA bot bo'lishi kerak).

Qanday ishlaydi:
1. CRM (yoki panel) buyurtma beradi; flot javobida "kuzatish_havola" bor: https://t.me/<bot>?start=<id>_<kod>.
   CRM bu havolani mijozga SMS/xabar bilan yuboradi. Kod tasodifiy sir: havolasiz boshqa buyurtmani ko'rib bo'lmaydi.
2. Mijoz havolani bosadi -> bot buyurtmaga ulanadi va holatini ko'rsatadi.
3. Holat o'zgarganda bot o'zi xabar beradi: skuter tayinlandi, yo'lga chiqdi (taxminiy vaqt va joylashuv),
   yetib keldi (PIN va [Qutini ochish] tugmasi), topshirildi yoki qaytarildi.
4. Mijoz [Qutini ochish] ni bosadi yoki 4 xonali PIN ni yozadi -> quti ochiladi.

Buyruqlar: /start, /holat, /joy (skuter qayerda).
Faqat Python standart kutubxonasi (urllib, long polling).
"""

import hmac
import json
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org/bot{}/{}"
TARMOQ_XATOLARI = (urllib.error.URLError, RuntimeError, OSError)
YAKUNIY = ("topshirildi", "qaytarildi", "bekor")


class MijozBot:
    def __init__(self, token, flot, kuzatish_oraligi=5.0):
        self.token, self.flot, self.oraliq = token, flot, kuzatish_oraligi
        self.obunalar = {}   # buyurtma id -> {chat_id, ...}
        self.oxirgi = {}     # buyurtma id -> oxirgi xabar qilingan holat
        self.lock = threading.Lock()

    # --- Telegram API ---
    def api(self, usul, kutish=15, **param):
        so = urllib.request.Request(API.format(self.token, usul), json.dumps(param).encode(),
                                    {"Content-Type": "application/json"})
        with urllib.request.urlopen(so, timeout=kutish) as r:
            j = json.load(r)
        if not j.get("ok"):
            raise RuntimeError(j.get("description", "Telegram xatosi"))
        return j["result"]

    def yoz(self, chat, matn, tugmalar=None):
        try:
            return self.api("sendMessage", chat_id=chat, text=matn,
                            **({"reply_markup": {"inline_keyboard": [[{"text": m, "callback_data": d}
                                                                      for m, d in qator] for qator in tugmalar]}}
                               if tugmalar else {}))
        except TARMOQ_XATOLARI:
            return None

    def boshlash(self):
        """Bot nomini oladi va flotga aytadi (kuzatish havolasi uchun)."""
        self.flot.mijoz_bot_nomi = self.api("getMe")["username"]
        return self.flot.mijoz_bot_nomi

    # --- buyurtma ma'lumoti ---
    def _buyurtma(self, bid):
        with self.flot.lock:
            b = self.flot.buyurtmalar.get(bid)
            return (b, self.flot.buyurtma_json(b)) if b else (None, None)

    def _matn(self, b, j):
        h = b.holat
        if h == "yangi":
            return f"Buyurtma #{b.id} ({b.nomi}) qabul qilindi, bo'sh skuter kutilmoqda."
        if h == "tayinlandi":
            return f"Buyurtma #{b.id}: skuter #{b.skuter} omborda yuklanmoqda."
        if h == "yolda":
            eta = f", taxminan {max(1, round(j['eta_daq']))} daqiqada yetib keladi" if "eta_daq" in j else ""
            return f"Buyurtma #{b.id}: skuter #{b.skuter} yo'lda{eta}. Qayerdaligini ko'rish: /joy"
        if h == "yetib_keldi":
            return (f"Skuter #{b.skuter} yetib keldi: {b.nomi}.\nQuti PIN kodi: {b.pin}\n"
                    "Qutini ochish uchun tugmani bosing yoki PIN ni yozing. Skuter 10 daqiqa kutadi.")
        if h == "topshirildi":
            return f"Buyurtma #{b.id} topshirildi. Rahmat!"
        if h == "qaytarildi":
            return f"Buyurtma #{b.id}: 10 daqiqada hech kim qutini ochmadi, yuk omborga qaytarildi. Do'konga murojaat qiling."
        if h == "bekor":
            return f"Buyurtma #{b.id} bekor qilindi."
        return f"Buyurtma #{b.id}: {h}"

    def _tugmalar(self, b):
        if b.holat == "yetib_keldi":
            return [[("Qutini ochish", f"och:{b.id}")]]
        if b.holat in ("tayinlandi", "yolda"):
            return [[("Holat", f"holat:{b.id}"), ("Skuter qayerda", f"joy:{b.id}")]]
        return None

    def _xabar_ber(self, chat, bid):
        b, j = self._buyurtma(bid)
        if b is None:
            return self.yoz(chat, "Buyurtma topilmadi.")
        return self.yoz(chat, self._matn(b, j), self._tugmalar(b))

    def _joy(self, chat, bid):
        b, j = self._buyurtma(bid)
        if b is None or "skuter_ll" not in j:
            return self.yoz(chat, "Skuter hozir yo'lda emas." if b else "Buyurtma topilmadi.")
        lat, lon = j["skuter_ll"]
        try:
            self.api("sendLocation", chat_id=chat, latitude=lat, longitude=lon)
        except TARMOQ_XATOLARI:
            pass
        return self.yoz(chat, f"Skuter #{b.skuter}, taxminan {max(1, round(j['eta_daq']))} daqiqa qoldi.")

    def _och(self, chat, bid, pin=None):
        b, _ = self._buyurtma(bid)
        if b is None:
            return "Buyurtma topilmadi."
        xato = self.flot.qutini_och(bid, b.pin if pin is None else pin)
        if xato:
            return f"Quti ochilmadi: {xato}."
        self.oxirgi[bid] = "topshirildi"
        return "Quti ochildi. Yukingizni oling va qopqoqni yoping. Rahmat!"

    # --- obuna ---
    def _mening(self, chat):
        with self.lock:
            return sorted(bid for bid, ch in self.obunalar.items() if chat in ch)

    def _ulash(self, chat, param):
        bid, _, kod = param.partition("_")
        b = self.flot.buyurtmalar.get(int(bid)) if bid.isdigit() else None
        if b is None or not hmac.compare_digest(kod.encode(), b.kuzatish.encode()):
            return self.yoz(chat, "Havola noto'g'ri yoki eskirgan. Do'kondan kelgan havolani qaytadan oching.")
        with self.lock:
            self.obunalar.setdefault(b.id, set()).add(chat)
            self.oxirgi.setdefault(b.id, b.holat)
        return self._xabar_ber(chat, b.id)

    # --- Telegramdan kelganlar ---
    def _xabar(self, m):
        chat = m["chat"]["id"]
        matn = (m.get("text") or "").strip()
        buyruq, _, param = matn.partition(" ")
        buyruq = buyruq.split("@")[0]
        mening = self._mening(chat)
        if buyruq == "/start":
            if param:
                return self._ulash(chat, param.strip())
            return self.yoz(chat, "Salom! Bu avtonom skuter yetkazib berish boti. Buyurtmani kuzatish uchun "
                                  "do'kondan kelgan havolani oching.")
        if not mening:
            return self.yoz(chat, "Sizga ulangan buyurtma yo'q. Do'kondan kelgan havolani oching.")
        if buyruq == "/holat":
            for bid in mening:
                self._xabar_ber(chat, bid)
            return None
        if buyruq == "/joy":
            faol = [bid for bid in mening if self.flot.buyurtmalar[bid].holat in ("tayinlandi", "yolda")]
            return self._joy(chat, faol[-1]) if faol else self.yoz(chat, "Hozir yo'ldagi skuter yo'q.")
        if matn.isdigit() and len(matn) == 4:
            kutayotgan = [bid for bid in mening if self.flot.buyurtmalar[bid].holat == "yetib_keldi"]
            if not kutayotgan:
                return self.yoz(chat, "Hozir sizni kutayotgan skuter yo'q.")
            return self.yoz(chat, self._och(chat, kutayotgan[-1], matn))
        return self.yoz(chat, "Buyruqlar: /holat, /joy. Skuter yetib kelganda PIN ni yozsangiz quti ochiladi.")

    def _callback(self, q):
        chat = q["message"]["chat"]["id"]
        amal, _, bid = q.get("data", "").partition(":")
        bid = int(bid) if bid.isdigit() else -1
        if bid not in self._mening(chat):
            return self.api("answerCallbackQuery", callback_query_id=q["id"], text="Bu buyurtma sizga ulanmagan")
        self.api("answerCallbackQuery", callback_query_id=q["id"])
        if amal == "och":
            return self.yoz(chat, self._och(chat, bid))
        if amal == "joy":
            return self._joy(chat, bid)
        return self._xabar_ber(chat, bid)

    # --- holat o'zgarishini kuzatish ---
    def tekshir(self):
        """Obuna bo'lingan buyurtmalar holati o'zgargan bo'lsa, mijozlarga xabar beradi."""
        with self.lock:
            royxat = [(bid, set(ch)) for bid, ch in self.obunalar.items()]
        for bid, chatlar in royxat:
            b = self.flot.buyurtmalar.get(bid)
            if b is not None and self.oxirgi.get(bid) != b.holat:
                self.oxirgi[bid] = b.holat
                for chat in chatlar:
                    self._xabar_ber(chat, bid)
                    if b.holat == "yolda":
                        self._joy(chat, bid)
            if b is None or b.holat in YAKUNIY:
                with self.lock:
                    self.obunalar.pop(bid, None)

    def _kuzat(self):
        while True:
            time.sleep(self.oraliq)
            try:
                self.tekshir()
            except Exception:   # kuzatuvchi oqim to'xtab qolmasin
                pass

    def ishla(self):
        threading.Thread(target=self._kuzat, daemon=True).start()
        offset = None
        while True:
            try:
                yangilar = self.api("getUpdates", kutish=40, timeout=30, allowed_updates=["message", "callback_query"],
                                    **({"offset": offset} if offset else {}))
            except TARMOQ_XATOLARI:
                time.sleep(5)
                continue
            for u in yangilar:
                offset = u["update_id"] + 1
                try:
                    if "callback_query" in u:
                        self._callback(u["callback_query"])
                    elif "message" in u:
                        self._xabar(u["message"])
                except (*TARMOQ_XATOLARI, KeyError, ValueError):
                    pass
