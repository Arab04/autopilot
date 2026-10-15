"""Operatorlar uchun Telegram bot: skuter so'rovlarini telefonga yuboradi va javobni qabul qiladi.

operator_panel.py ichidan ishga tushadi (muhit o'zgaruvchilari):
    TELEGRAM_TOKEN     @BotFather bergan token
    OPERATOR_CHATLAR   ruxsat etilgan operatorlar chat raqamlari, vergul bilan (botga /start yuborsangiz
                       raqamingizni aytadi); ro'yxatda yo'q odam hech narsani boshqara olmaydi
    PANEL_URL          panel manzili (xabardagi "Panelni ochish" tugmasi uchun), masalan http://1.2.3.4:8765

Xabarlar:
- chorrahadan o'tishga ruxsat so'rovi: [Ruxsat] [Rad] tugmalari;
- yordam so'rovi (skuter qolib ketdi): [Avtonom davom] [To'xtatish] tugmalari, qo'lda boshqarish panelda;
- so'rov yopilsa yoki boshqa operator javob bersa, tugmalar olib tashlanadi.
Buyruqlar: /start, /holat, /toxtat, /davom.

Faqat Python standart kutubxonasi (urllib, uzun so'rov - long polling).
"""

import json
import threading
import time
import urllib.error
import urllib.request

API = "https://api.telegram.org/bot{}/{}"


class OperatorBot:
    def __init__(self, token, panel, chatlar, panel_url=""):
        self.token, self.panel, self.chatlar, self.panel_url = token, panel, set(chatlar), panel_url
        self.xabarlar = {}   # so'rov kaliti -> [(chat_id, message_id), ...]
        self.lock = threading.Lock()
        panel.tinglovchilar.append(self.hodisa)

    # --- Telegram API ---
    def api(self, usul, kutish=15, **param):
        so = urllib.request.Request(API.format(self.token, usul), json.dumps(param).encode(),
                                    {"Content-Type": "application/json"})
        with urllib.request.urlopen(so, timeout=kutish) as r:
            j = json.load(r)
        if not j.get("ok"):
            raise RuntimeError(j.get("description", "Telegram xatosi"))
        return j["result"]

    def _tugmalar(self, qatorlar):
        q = [[{"text": m, "callback_data": d} for m, d in qator] for qator in qatorlar]
        if self.panel_url.startswith(("http://", "https://")):
            q.append([{"text": "Panelni ochish", "url": self.panel_url}])
        return {"inline_keyboard": q}

    def yubor(self, matn, tugmalar=None, kalit=None):
        for chat in sorted(self.chatlar):
            try:
                m = self.api("sendMessage", chat_id=chat, text=matn,
                             **({"reply_markup": self._tugmalar(tugmalar)} if tugmalar else {}))
            except (urllib.error.URLError, RuntimeError, OSError):
                continue
            if kalit:
                with self.lock:
                    self.xabarlar.setdefault(kalit, []).append((chat, m["message_id"]))

    def yop(self, kalit, izoh):
        with self.lock:
            royxat = self.xabarlar.pop(kalit, [])
        for chat, mid in royxat:
            try:
                self.api("editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup={"inline_keyboard": []})
                self.api("sendMessage", chat_id=chat, text=izoh, reply_to_message_id=mid)
            except (urllib.error.URLError, RuntimeError, OSError):
                pass

    # --- Paneldan kelgan hodisalar ---
    def hodisa(self, turi, malumot, t):
        # Telegramga yuborish sekin bo'lishi mumkin: simulyatorni kutdirmaslik uchun alohida oqimda
        threading.Thread(target=self._hodisa, args=(turi, malumot, t), daemon=True).start()

    def _safar_matni(self):
        s = self.panel.safar or {}
        h = self.panel.surat or {}
        yol = f"{s.get('nomi', '')} -> ombor" if s.get("qaytish") else f"ombor -> {s.get('nomi', '')}"
        return f"Safar: {yol}, {h.get('s', 0) / 1000:.2f}/{s.get('uzunlik', 0) / 1000:.2f} km"

    def _hodisa(self, turi, malumot, t):
        if turi == "otish":
            svet = "svetoforli" if malumot.get("svetofor") else "svetoforsiz"
            self.yubor(f"Chorrahani kesib o'tishga ruxsat so'rayapti: {malumot.get('polosalar')} polosali, {svet} "
                       f"yo'l ({malumot.get('kenglik')} m).\n{self._safar_matni()}\n"
                       "Ruxsatdan keyin ham skuter mashinalarni o'zi tekshiradi.",
                       [[("Ruxsat", f"tasdiq:{t}"), ("Rad", f"rad:{t}")]], kalit=("otish", t))
        elif turi == "yordam":
            from operator_panel import holat_nomi
            self.yubor(f"YORDAM: skuter qolib ketdi ({holat_nomi(malumot.get('sabab'))}).\n{self._safar_matni()}\n"
                       "Qo'lda boshqarish uchun panelni oching.",
                       [[("Avtonom davom", f"avtonom:{t}"), ("To'xtatish", f"toxtat:{t}")]], kalit=("yordam", t))
        elif turi == "skuter_rad":
            self.yubor("Skuter o'tmadi: o'zi yaqinlashayotgan mashina ko'rdi, bo'sh joy bo'lganda yana so'raydi.")
        elif turi == "yopildi":
            qaysi = "yordam" if malumot.get("sorov") == "yordam" else "otish"
            with self.lock:
                kalitlar = [k for k in self.xabarlar if k[0] == qaysi]
            for k in kalitlar:
                self.yop(k, "So'rov yopildi.")

    # --- Operatordan kelgan javoblar ---
    def _callback(self, q):
        chat = q["message"]["chat"]["id"]
        ism = q["from"].get("first_name", "operator")
        if chat not in self.chatlar:
            return self.api("answerCallbackQuery", callback_query_id=q["id"], text="Siz operator ro'yxatida yo'qsiz")
        amal, _, t = q.get("data", "").partition(":")
        p = self.panel
        with p.lock:
            hozir = p.sorov_otish if amal in ("tasdiq", "rad") else p.sorov_yordam
            dolzarb = hozir is not None and f"{hozir['t']}" == t
        if amal != "toxtat" and not dolzarb:
            self.api("answerCallbackQuery", callback_query_id=q["id"], text="Bu so'rov allaqachon yopilgan")
            return self.yop(("otish" if amal in ("tasdiq", "rad") else "yordam", float(t)), "So'rov eskirgan.")
        p.yoz(f"Telegram: {ism}")
        p.buyruq(amal)
        javob = {"tasdiq": "Ruxsat berildi", "rad": "Rad etildi", "avtonom": "Avtonom davom etadi",
                 "toxtat": "To'xtatildi (davom ettirish: /davom)"}.get(amal, "Bajarildi")
        self.api("answerCallbackQuery", callback_query_id=q["id"], text=javob)
        self.yop(("otish" if amal in ("tasdiq", "rad") else "yordam", float(t)), f"{ism}: {javob}.")

    def _xabar(self, m):
        chat, matn = m["chat"]["id"], (m.get("text") or "").strip().split("@")[0]
        operator = chat in self.chatlar
        if matn == "/start":
            return self.api("sendMessage", chat_id=chat, text=(
                f"Chat raqamingiz: {chat}.\n" + ("Siz operatorsiz: skuter so'rovlari shu yerga keladi."
                                                 if operator else "Operator bo'lish uchun bu raqamni administratorga yuboring.")))
        if not operator:
            return None
        if matn == "/holat":
            h = self.panel.holat_json()
            if "t" not in h:
                return self.api("sendMessage", chat_id=chat, text="Simulyator hali boshlanmadi.")
            return self.api("sendMessage", chat_id=chat, text=(
                f"{self._safar_matni()}\nHolat: {h['holat_nomi']}, {h['v'] * 3.6:.0f} km/soat, "
                f"{'qo`lda' if h['qolda'] else 'avtonom'}{', TO`XTATILGAN' if h['toxtat'] else ''}\n"
                f"To'qnashuv: {h['toqnashuv']}"))
        if matn in ("/toxtat", "/davom"):
            self.panel.yoz(f"Telegram: {m['from'].get('first_name', 'operator')}")
            self.panel.buyruq(matn[1:])
            return self.api("sendMessage", chat_id=chat, text="To'xtatildi." if matn == "/toxtat" else "Davom etmoqda.")
        return None

    def ishla(self):
        offset = None
        while True:
            try:
                yangilar = self.api("getUpdates", kutish=40, timeout=30, allowed_updates=["message", "callback_query"],
                                    **({"offset": offset} if offset else {}))
            except (urllib.error.URLError, RuntimeError, OSError):
                time.sleep(5)
                continue
            for u in yangilar:
                offset = u["update_id"] + 1
                try:
                    if "callback_query" in u:
                        self._callback(u["callback_query"])
                    elif "message" in u:
                        self._xabar(u["message"])
                except (urllib.error.URLError, RuntimeError, OSError, KeyError, ValueError):
                    pass
