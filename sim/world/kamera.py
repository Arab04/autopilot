"""Sinov kamerasi: telefon brauzeri kadrlarni (JPEG) serverga yuboradi, operator paneli ularni ko'radi.

Skuter yig'ilguncha telefon "skuter kamerasi" o'rnida turadi: Chirchiqda 4G orqali video qancha kechikishini
skutersiz o'lchash uchun. Telefon har kadrni POST /kamera/kadr bilan yuboradi va javob kelishini kutadi
(shuning uchun sekin aloqada navbat yig'ilmaydi, kadrlar tushib qoladi). Panel GET /kamera/oqim dan MJPEG
oqimini oladi.

Kechikish: telefon yuborish vaqtini (aylanib kelish, RTT) o'lchab keyingi kadr bilan aytadi; server kadr
qachon kelganini biladi. Ko'rsatkich = RTT/2 (telefon -> server) + kadrning serverdagi yoshi.
"""

import threading
import time
from collections import deque

MAX_KADR = 2_000_000  # bayt; 1280x720 JPEG odatda 50-200 KB


class Kamera:
    def __init__(self):
        self.shart = threading.Condition()
        self.kadr = None  # oxirgi JPEG
        self.raqam = 0
        self.keldi = 0.0  # time.monotonic()
        self.rtt_ms = None  # telefon o'lchagan yuborish vaqti
        self.qurilma = ""
        self._tarix = deque(maxlen=60)  # (vaqt, hajm)

    def qabul(self, jpeg: bytes, rtt_ms=None, qurilma=""):
        if not jpeg.startswith(b"\xff\xd8"):
            raise ValueError("JPEG emas")
        hozir = time.monotonic()
        with self.shart:
            self.kadr, self.keldi = jpeg, hozir
            self.raqam += 1
            if rtt_ms is not None and 0 <= rtt_ms <= 60_000:  # NaN ham shu yerda o'tmaydi
                self.rtt_ms = round(rtt_ms)
            self.qurilma = qurilma[:80]
            self._tarix.append((hozir, len(jpeg)))
            self.shart.notify_all()
        return self.raqam

    def kut(self, oxirgi, kutish=5.0):
        """oxirgi raqamdan yangi kadr kelguncha kutadi. (raqam, jpeg) yoki kadr kelmasa (oxirgi, None)."""
        with self.shart:
            self.shart.wait_for(lambda: self.raqam != oxirgi, timeout=kutish)
            if self.raqam == oxirgi:
                return oxirgi, None
            return self.raqam, self.kadr

    def holat(self):
        hozir = time.monotonic()
        with self.shart:
            if self.kadr is None:
                return {"bor": False}
            oyna = [(t, n) for t, n in self._tarix if hozir - t <= 3.0]
            dt = max(1e-3, hozir - oyna[0][0]) if len(oyna) > 1 else None
            yosh = (hozir - self.keldi) * 1000
            return {
                "bor": True,
                "faol": yosh < 3000,
                "yosh_ms": round(yosh),
                "rtt_ms": self.rtt_ms,
                "kechikish_ms": round(self.rtt_ms / 2 + yosh) if self.rtt_ms is not None else None,
                "fps": round((len(oyna) - 1) / dt, 1) if dt else 0.0,
                "kbit_s": round(sum(n for _, n in oyna[1:]) * 8 / 1000 / dt) if dt else 0,
                "hajm_kb": round(len(self.kadr) / 1024, 1),
                "kadrlar": self.raqam,
                "qurilma": self.qurilma,
            }
