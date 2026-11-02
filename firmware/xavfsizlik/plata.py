"""Xavfsizlik platasi dasturini (C) Pythondan chaqirish: simulyatorga ulash va Jetson tomoni uchun protokol.

    from plata import Plata
    p = Plata()                                    # libxavfsizlik.so ni kerak bo'lsa o'zi yig'adi (gcc)
    chiqish = p.qadam(t_ms, tezlik, [d0, d1, ...], buyruq=dict(tezlik=5, tormoz=2.5))
    kadr = p.buyruq_kadri(seq, tezlik=5, tormoz=2.5)  # Jetson UART ga yuboradigan baytlar
"""

import ctypes
import subprocess
from pathlib import Path

PAPKA = Path(__file__).resolve().parent
KUTUBXONA = PAPKA / "libxavfsizlik.so"
ULTRATOVUSH_SONI = 8
HOLATLAR = ["normal", "cheklangan", "toxtash", "favqulodda", "bloklangan"]
SABABLAR = ["ultratovush", "datchik_xato", "jetson_kech", "jetson_yoq", "operator", "radio", "qochish",
            "yiqilish", "batareya", "kritik_batareya", "tezlik_chegara"]

f, b, u8, u32 = ctypes.c_float, ctypes.c_bool, ctypes.c_uint8, ctypes.c_uint32


class Sozlama(ctypes.Structure):
    _fields_ = [(n, f) for n in ("max_tezlik", "reaksiya", "favqulodda_tormoz", "yumshoq_tormoz",
                                 "ultratovush_zaxira", "ultratovush_bosh_vaqt", "datchik_xato_vaqt",
                                 "datchik_xato_tezlik")] + \
               [("jetson_kechikish_ms", u32), ("jetson_uzilish_ms", u32)] + \
               [(n, f) for n in ("qochish_farq", "qochish_vaqt", "yiqilish_qiyalik", "kam_kuchlanish",
                                 "kam_kuchlanish_tezlik", "kritik_kuchlanish", "yigish_tezlik", "yigish_ushlab",
                                 "yigish_max_qiyalik", "ochish_tezlik", "ochish_qiyalik", "keskin_tormoz",
                                 "ochilgach_kutish")] + \
               [("max_qiyalik_hodisa", u8), ("ultratovush_masofa", f)]


class Buyruq(ctypes.Structure):
    _fields_ = [("tezlik", f), ("tormoz", f), ("operator_toxtat", b), ("operator_ochish", b), ("tez_yol", b),
                ("aloqa_bor", b)]


class Kirish(ctypes.Structure):
    _fields_ = [("t_ms", u32), ("tezlik", f), ("ultratovush", f * ULTRATOVUSH_SONI), ("qiyalik", f),
                ("kuchlanish", f), ("tok_bor", b), ("radio_toxtat", b), ("buyruq_yangi", b), ("buyruq", Buyruq)]


class Chiqish(ctypes.Structure):
    _fields_ = [("tezlik_max", f), ("tormoz", f), ("motor_uzish", b), ("yg_qulf", b), ("yg_yigish_motor", b),
                ("signal", b), ("holat", ctypes.c_int), ("sabab", u32)]


def _kutubxona():
    manba = [PAPKA / n for n in ("xavfsizlik.c", "protokol.c", "xavfsizlik.h", "protokol.h")]
    if not KUTUBXONA.exists() or any(m.stat().st_mtime > KUTUBXONA.stat().st_mtime for m in manba):
        subprocess.run(["make", "-s", "-C", str(PAPKA), "libxavfsizlik.so"], check=True)
    lib = ctypes.CDLL(str(KUTUBXONA))
    lib.xv_standart_sozlama.argtypes = [ctypes.c_void_p]
    lib.xv_boshlash.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.xv_qadam.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    lib.xp_buyruq_yoz.argtypes = [u8, ctypes.c_void_p, ctypes.c_void_p]
    lib.xp_buyruq_yoz.restype = ctypes.c_size_t
    return lib


_LIB = None


class Plata:
    def __init__(self, **sozlama):
        global _LIB
        _LIB = _LIB or _kutubxona()
        self.lib = _LIB
        self.sozlama = Sozlama()
        self.lib.xv_standart_sozlama(ctypes.byref(self.sozlama))
        for k, v in sozlama.items():
            setattr(self.sozlama, k, v)
        self._holat = ctypes.create_string_buffer(self.lib.xv_holat_hajmi())
        self.lib.xv_boshlash(self._holat, ctypes.byref(self.sozlama))
        self.k, self.c = Kirish(), Chiqish()
        self.k.kuchlanish, self.k.tok_bor = 50.0, True

    def qadam(self, t_ms, tezlik, ultratovush, buyruq=None, qiyalik=0.0, kuchlanish=None, radio_toxtat=False):
        """ultratovush: metrlar ro'yxati (None yoki manfiy = datchik xato, 99 = aks-sado yo'q); buyruq: dict yoki None (kadr kelmadi)."""
        k = self.k
        k.t_ms = int(t_ms) & 0xFFFFFFFF
        k.tezlik = tezlik
        for i in range(ULTRATOVUSH_SONI):
            x = ultratovush[i] if i < len(ultratovush) else 99.0
            k.ultratovush[i] = -1.0 if x is None else x
        k.qiyalik = qiyalik
        if kuchlanish is not None:
            k.kuchlanish = kuchlanish
        k.radio_toxtat = radio_toxtat
        k.buyruq_yangi = buyruq is not None
        if buyruq is not None:
            k.buyruq = Buyruq(**{"tez_yol": True, "aloqa_bor": True, **buyruq})
        self.lib.xv_qadam(self._holat, ctypes.byref(k), ctypes.byref(self.c))
        c = self.c
        return {"tezlik_max": c.tezlik_max, "tormoz": c.tormoz, "motor_uzish": c.motor_uzish,
                "holat": HOLATLAR[c.holat], "sabab": [s for i, s in enumerate(SABABLAR) if c.sabab >> i & 1],
                "yg_qulf": c.yg_qulf}

    def buyruq_kadri(self, seq, **buyruq):
        kadr = ctypes.create_string_buffer(64)
        n = self.lib.xp_buyruq_yoz(seq & 0xFF, ctypes.byref(Buyruq(**buyruq)), kadr)
        return kadr.raw[:n]


def crc16(data, crc=0xFFFF):
    """Protokol CRC si (Jetson tomonida C kutubxonasisiz ishlatish uchun)."""
    for x in data:
        crc ^= x << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def buyruq_kadri(seq, tezlik, tormoz, operator_toxtat=False, operator_ochish=False, tez_yol=True, aloqa_bor=True):
    """Jetson -> plata buyruq kadri, sof Python (protokol.h dagi format)."""
    sm = max(-32768, min(32767, round(tezlik * 100)))
    bayroq = operator_toxtat | operator_ochish << 1 | tez_yol << 2 | aloqa_bor << 3
    tana = bytes([4, 0x01, seq & 0xFF]) + (sm & 0xFFFF).to_bytes(2, "little") + \
        bytes([max(0, min(255, round(tormoz * 10))), bayroq])
    crc = crc16(tana)
    return bytes([0xA5, 0x5A]) + tana + crc.to_bytes(2, "big")
