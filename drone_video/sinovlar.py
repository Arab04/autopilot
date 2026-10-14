"""drone_video sinovlari. Ishga tushirish: python3 sinovlar.py

Android qurilma tahlili (android_malumot.py) soxta qurilma ma'lumotlarida, server sozlash skripti
(server/ornatish.sh) vaqtinchalik papkada, oqim.sh esa ffmpeg bo'lsa mahalliy SRT
qabul qiluvchiga sinov tasvirini yuborib tekshiriladi.
"""

import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

from android_malumot import BUYRUQLAR, hex_ip, soketlar, uid_paketlar, trafik, tarmoqlar, tahlil, yig

PAPKA = Path(__file__).resolve().parent
SARLAVHA = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"


def tcp_qator(lip, lport, rip, rport, holat, uid):
    def h(ip):
        return bytes(int(x) for x in ip.split("."))[::-1].hex().upper()
    return (f"   0: {h(lip)}:{lport:04X} {h(rip)}:{rport:04X} {holat} 00000000:00000000 "
            f"00:00000000 00000000 {uid:5}        0 12345 1 0000000000000000 100 0 0 10 0\n")


def dev(qatorlar):
    bosh = ("Inter-|   Receive                                                |  Transmit\n"
            " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets\n")
    return bosh + "".join(f"{nom:>6}: {q} 0 0 0 0 0 0 0 {y} 0 0 0 0 0 0 0\n" for nom, q, y in qatorlar)


def pult(**ozgartir):
    """Soxta qurilma: APP Flight rejimidagi telefon, video dronning Wi-Fi'si orqali, internet SIM orqali."""
    x = {
        "ishlab_chiqaruvchi": "XiL", "model": "RC-019", "android": "10", "sdk": "29", "platforma": "rk3326",
        "ekran": "Physical size: 1920x1080", "sim": "READY", "mobil_internet": "1",
        "oldingi_ilova": "  mResumedActivity: ActivityRecord{1a2b u0 com.xil.pro/.FpvActivity t12}",
        "ilovalar_3": "package:com.xil.pro\npackage:com.wmspanel.larix_screencaster",
        "uidlar": "package:com.xil.pro uid:10123\npackage:android uid:1000\npackage:com.wmspanel.larix_screencaster uid:10124",
        "manzillar": "1: lo    inet 127.0.0.1/8 scope host lo\n"
                     "30: wlan0    inet 192.168.0.100/24 brd 192.168.0.255 scope global wlan0",
        "yollar": "default via 192.168.0.1 dev wlan0 table wlan0 proto static",
        "wifi": 'mWifiInfo SSID: "XiL-019-5G", BSSID: 02:00:00:00:00:00, Frequency: 5745MHz',
        "tarmoqlar": (
            'NetworkAgentInfo{network{100} lp{{InterfaceName: wlan0 LinkAddresses: [192.168.0.100/24]}} '
            'nc{[ Transports: WIFI Capabilities: NOT_METERED&INTERNET&NOT_RESTRICTED&TRUSTED&NOT_VPN '
            'SSID: "XiL-019-5G"]}}\n'
            'NetworkAgentInfo{network{101} lp{{InterfaceName: rmnet_data0 LinkAddresses: [10.12.0.5/30]}} '
            'nc{[ Transports: CELLULAR Capabilities: INTERNET&NOT_RESTRICTED&TRUSTED&NOT_VPN&VALIDATED&NOT_ROAMING]}}'),
        "hdmi": "0",
        "tcp": SARLAVHA + tcp_qator("127.0.0.1", 5037, "0.0.0.0", 0, "0A", 2000),
        "tcp6": "", "udp6": "",
        "udp": SARLAVHA + tcp_qator("192.168.0.100", 7070, "0.0.0.0", 0, "07", 10123)
                        + tcp_qator("192.168.0.100", 40000, "192.168.0.1", 7060, "01", 10123),
        "trafik_soniya": 3.0,
        "trafik": {"wlan0": (8.4, 0.2), "rmnet_data0": (0.0, 0.0)},
    }
    x.update(ozgartir)
    return x


def ornatish_sinovi():
    """server/ornatish.sh: parollar yaratiladi, shablonda o'rinbosar qolmaydi, qayta ishga tushirish parolni saqlaydi."""
    with tempfile.TemporaryDirectory() as t:
        nusxa = Path(t, "server")
        shutil.copytree(PAPKA / "server", nusxa)
        for f in ("mediamtx.local.yml", "parollar.txt"):
            (nusxa / f).unlink(missing_ok=True)

        def run(*a):
            return subprocess.run(["bash", str(nusxa / "ornatish.sh"), *a], capture_output=True, text=True)

        if run("203.0.113.10/../x").returncode == 0:
            return "noto'g'ri manzil qabul qilindi"
        r = run("203.0.113.10")
        if r.returncode != 0:
            return r.stderr
        sozlama = (nusxa / "mediamtx.local.yml").read_text()
        parollar = (nusxa / "parollar.txt").read_text()
        if re.search(r"PULT_PAROLI|OPERATOR_PAROLI|SERVER_MANZILI", sozlama):
            return "shablonda o'rinbosar qoldi"
        pult_p = re.search(r"- user: pult\n\s+pass: ([0-9a-f]{24})\n", sozlama)
        oper_p = re.search(r"- user: operator\n\s+pass: ([0-9a-f]{24})\n", sozlama)
        if not (pult_p and oper_p) or pult_p.group(1) == oper_p.group(1):
            return "parollar yaratilmadi"
        if f"publish:dron:pult:{pult_p.group(1)}" not in parollar or \
                f"rtsp://operator:{oper_p.group(1)}@203.0.113.10:8554/dron" not in parollar:
            return "parollar.txt sozlamaga mos emas"
        if "webrtcAdditionalHosts: [203.0.113.10]" not in sozlama:
            return "server manzili yozilmadi"
        try:
            import yaml
            s = yaml.safe_load(sozlama)
            if s["paths"]["dron"]["record"] is not True or len(s["authInternalUsers"]) != 3:
                return "YAML tuzilishi noto'g'ri"
        except ImportError:
            pass
        run("203.0.113.10")
        if (nusxa / "mediamtx.local.yml").read_text() != sozlama:
            return "qayta ishga tushirganda parollar o'zgardi"
        run("203.0.113.10", "--qayta")
        if (nusxa / "mediamtx.local.yml").read_text() == sozlama:
            return "--qayta yangi parol yaratmadi"
    return ""


def oqim_sinovi():
    """oqim.sh sinov: mahalliy SRT qabul qiluvchiga 3 s sinov tasviri yuboriladi va qabul qilingani tekshiriladi."""
    r = subprocess.run(["bash", "-n", str(PAPKA / "oqim.sh")], capture_output=True, text=True)
    if r.returncode != 0:
        return r.stderr
    if not shutil.which("ffmpeg"):
        return None  # ffmpeg yo'q: faqat sintaksis tekshirildi
    with tempfile.TemporaryDirectory() as t:
        chiqish = Path(t, "qabul.ts")
        qabul = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                                  "-i", "srt://127.0.0.1:8890?mode=listener", "-c", "copy", str(chiqish)],
                                 stderr=subprocess.DEVNULL)
        time.sleep(1)  # qabul qiluvchi portni ochib ulgursin
        try:
            r = subprocess.run(["bash", str(PAPKA / "oqim.sh"), "sinov", "127.0.0.1", "abc123"],
                               capture_output=True, text=True, timeout=60,
                               env={**os.environ, "DAVOMIYLIK": "3"})
            qabul.wait(timeout=20)
        finally:
            qabul.kill()
        if r.returncode != 0:
            return r.stderr[-500:]
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height",
                               "-of", "csv=p=0", str(chiqish)], capture_output=True, text=True).stdout.split("\n")[0]
        if info != "h264,1280,720":
            return f"qabul qilingan oqim: {info!r}"
    return ""


def proc_net_sinovi():
    """Haqiqiy /proc/net/tcp: ochilgan tinglovchi soket to'g'ri o'qiladi (faqat Linux)."""
    if not Path("/proc/net/tcp").exists():
        return None
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        topildi = [k for k in soketlar(Path("/proc/net/tcp").read_text(), "tcp")
                   if k.lokal_port == port and k.lokal_ip == "127.0.0.1" and k.holat == "LISTEN"]
    finally:
        s.close()
    return "" if topildi and topildi[0].uid == os.getuid() else "soket topilmadi"


def yig_sinovi():
    """yig: har bir buyruq qurilmaga yuboriladi, /proc/net/dev ikki marta o'qiladi."""
    soxta = pult()
    buyruqlar = {v: k for k, v in BUYRUQLAR.items()}
    devlar = iter([dev([("wlan0", 0, 0)]), dev([("wlan0", 10 ** 6, 0)])])

    def adb(buyruq):
        return next(devlar) if buyruq == "cat /proc/net/dev" else soxta[buyruqlar[buyruq]]

    x = yig(adb, kutish=0.0)
    return set(x["trafik"]) == {"wlan0"} and x["trafik"]["wlan0"][0] > 0 and "Qurilma: XiL RC-019" in matn(x)


def matn(x):
    return "\n".join(tahlil(x))


SINOVLAR = [
    ("hex IP: IPv4, IPv6, IPv4-mapped",
     lambda: hex_ip("0100A8C0") == "192.168.0.1"
     and hex_ip("00000000000000000000000001000000") == "::1"
     and hex_ip("0000000000000000FFFF00000100A8C0") == "192.168.0.1"),
    ("/proc/net/tcp qatorlari, buzuq qator tashlab ketiladi",
     lambda: [(k.lokal_ip, k.lokal_port, k.holat, k.uid) for k in soketlar(
         SARLAVHA + tcp_qator("0.0.0.0", 8554, "0.0.0.0", 0, "0A", 10050) + "buzuq qator\n", "tcp")]
     == [("0.0.0.0", 8554, "LISTEN", 10050)]),
    ("uid -> paket, ikkinchi foydalanuvchi profili",
     lambda: uid_paketlar("package:com.a uid:10050\npackage:com.b uid:10051,1010051\npackage:com.c uid:10050")
     == {10050: "com.a, com.c", 10051: "com.b", 1000: "android (tizim)"}),
    ("trafik tezligi (Mbit/s), lo hisobga olinmaydi",
     lambda: trafik(dev([("lo", 0, 0), ("wlan0", 1000, 0)]),
                    dev([("lo", 10 ** 9, 0), ("wlan0", 1000 + 3 * 10 ** 6 // 8 * 2, 125000)]), 2.0)
     == {"wlan0": (3.0, 0.5)}),
    ("dumpsys connectivity: transport, interfeys, internet, SSID",
     lambda: tarmoqlar(pult()["tarmoqlar"])
     == [("WIFI", "wlan0", False, "XiL-019-5G"), ("CELLULAR", "rmnet_data0", True, "")]),
    ("APP Flight telefon: video Wi-Fi orqali, internet SIM orqali",
     lambda: (lambda m: "Video wlan0 orqali kelyapti (8.4" in m
              and "Wi-Fi dronga ulangan" in m
              and "Qurilmada hozir internet yo'q" not in m
              and "Internetga chiqadigan tarmoqlar: CELLULAR (rmnet_data0)" in m
              and "Ekrandagi ilova: com.xil.pro" in m
              and "192.168.0.100:40000 -> 192.168.0.1:7060" in m and "com.xil.pro" in m
              and "RTSP" not in m)(matn(pult()))),
    ("Android pult: unda RTSP server, Wi-Fi'da internet bor",
     lambda: (lambda m: "Qurilmada RTSP server bor (port 8554)" in m
              and "<- RTSP bo'lishi mumkin" in m and "Wi-Fi dronga ulangan" not in m
              and "Video eth0 orqali" in m)(matn(pult(
                  tcp=SARLAVHA + tcp_qator("0.0.0.0", 8554, "0.0.0.0", 0, "0A", 1000),
                  tarmoqlar='NetworkAgentInfo{ lp{{InterfaceName: wlan0 }} nc{[ Transports: WIFI '
                            'Capabilities: INTERNET&VALIDATED ]}}',
                  trafik={"eth0": (12.0, 0.1), "wlan0": (0.1, 0.1)})))),
    ("Video IP tarmoqsiz, internet yo'q, soketlar o'qilmadi",
     lambda: (lambda m: "Hech bir IP tarmoqda katta oqim" in m and "Qurilmada hozir internet yo'q" in m
              and "Soketlar ro'yxatini o'qib bo'lmadi" in m)(matn(pult(
                  tarmoqlar="", trafik={"wlan0": (0.05, 0.01)}, tcp="", udp="")))),
    ("yig: soxta qurilmadan ma'lumot yig'ish va trafik o'lchash", yig_sinovi),
    ("haqiqiy /proc/net/tcp o'qiladi", proc_net_sinovi),
    ("server/ornatish.sh: parollar va sozlama", ornatish_sinovi),
    ("oqim.sh sinov: SRT orqali H.264 1280x720 yetib boradi", oqim_sinovi),
]


def main():
    xatolar = []
    print(f"{'Sinov':60} Natija")
    for nomi, f in SINOVLAR:
        try:
            r = f()
        except Exception as e:  # noqa: BLE001 - sinov xatosi natijada ko'rsatiladi
            r = f"{type(e).__name__}: {e}"
        ok = r is True or r == "" or r is None
        izoh = "O`TKAZIB YUBORILDI (ffmpeg yoki /proc yo'q)" if r is None else "O`TDI" if ok else "O`TMADI"
        print(f"{nomi[:60]:60} {izoh}" + ("" if ok or r is False else f"  {r}"))
        if not ok:
            xatolar.append(nomi)
    print(f"\n{len(SINOVLAR) - len(xatolar)}/{len(SINOVLAR)} sinov o'tdi")
    sys.exit(1 if xatolar else 0)


if __name__ == "__main__":
    main()
