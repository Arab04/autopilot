"""drone_video sinovlari. Ishga tushirish: python3 sinovlar.py

Android qurilma tahlili (android_malumot.py) soxta qurilma ma'lumotlarida, pult qidiruvi
(dron_qidiruv.py) soxta RTSP/HTTP/RTMP/xom H.264 serverlarida, server sozlash skripti
(server/ornatish.sh) vaqtinchalik papkada, oqim.sh esa ffmpeg bo'lsa mahalliy SRT
qabul qiluvchiga video yuborib tekshiriladi.
"""

import os
from pathlib import Path
import re
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

from android_malumot import BUYRUQLAR, hex_ip, soketlar, uid_paketlar, trafik, tarmoqlar, tahlil, yig
from dron_qidiruv import qr_ip, xom_oqim, tekshir

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


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def soxta_server(ishlov):
    """127.0.0.1 da TCP server: har bir ulanishda ishlov(soket) chaqiriladi -> (server, port)."""
    class Ulanish(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            try:
                ishlov(self.request)
            except OSError:
                pass
    srv = _Server(("127.0.0.1", 0), Ulanish)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def rtsp_ishlov(s):
    data = s.recv(4096)
    if not data:
        return
    usul, url = data.split(b" ")[:2]
    if usul == b"OPTIONS":
        s.sendall(b"RTSP/1.0 200 OK\r\nCSeq: 1\r\nPublic: OPTIONS, DESCRIBE, SETUP, PLAY\r\n\r\n")
    elif usul == b"DESCRIBE" and url.endswith(b"/live"):
        sdp = b"v=0\r\ns=dron\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n"
        s.sendall(b"RTSP/1.0 200 OK\r\nCSeq: 2\r\nContent-Type: application/sdp\r\n"
                  b"Content-Length: %d\r\n\r\n" % len(sdp) + sdp)
    else:
        s.sendall(b"RTSP/1.0 404 Not Found\r\nCSeq: 2\r\n\r\n")


def mjpeg_ishlov(s):
    data = s.recv(4096)
    if not data:
        return
    yol = data.split(b" ")[1]
    if yol == b"/?action=stream":
        s.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=kadr\r\n\r\n")
        for _ in range(3):
            s.sendall(b"--kadr\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8\xff\xe0" + bytes(200) + b"\xff\xd9\r\n")
    elif yol == b"/":
        tana = b"<html><title>XiL kamera</title></html>"
        s.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n" % len(tana) + tana)
    else:
        s.sendall(b"HTTP/1.0 404 Not Found\r\n\r\n")


def h264_ishlov(baytlar):
    """Ulanish bilanoq xom H.264 yuboradigan pult (arzon Wi-Fi kameralarga o'xshash)."""
    def ishlov(s):
        for i in range(0, len(baytlar), 4096):
            s.sendall(baytlar[i:i + 4096])
            time.sleep(0.002)
    return ishlov


def rtmp_ishlov(s):
    data = s.recv(2048)
    if data[:1] == b"\x03":
        s.sendall(b"\x03" + bytes(3072))


def jim_ishlov(s):
    s.recv(4096)


SOXTA_H264 = bytes.fromhex("00000001674d401fe8802802dd80b501010140000003004000000c83c60c4480"
                           "0000000168ebef20" "0000000165888040") + bytes(3000)


def yopiq_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def qidiruv_sinovi():
    """dron_qidiruv.tekshir: har xil soxta pult serverlarida video manzillarini to'g'ri topadi."""
    serverlar = {nom: soxta_server(f) for nom, f in [
        ("rtsp", rtsp_ishlov), ("mjpeg", mjpeg_ishlov), ("h264", h264_ishlov(SOXTA_H264)),
        ("rtmp", rtmp_ishlov), ("jim", jim_ishlov)]}
    port = {nom: p for nom, (_, p) in serverlar.items()}
    try:
        qatorlar, videolar = tekshir("127.0.0.1", sorted(port.values()) + [yopiq_port()],
                                     kashf=False, tekshirish=False)
    finally:
        for srv, _ in serverlar.values():
            srv.shutdown()
            srv.server_close()
    m = "\n".join(qatorlar)
    kutilgan = {(f"rtsp://127.0.0.1:{port['rtsp']}/live", "video, H264"),
                (f"http://127.0.0.1:{port['mjpeg']}/?action=stream", "MJPEG video oqimi"),
                (f"tcp://127.0.0.1:{port['h264']}", "H.264")}
    if set(videolar) != kutilgan:
        return f"topilgan videolar: {videolar}"
    for kerak in (f"{port['rtmp']}: RTMP", f"{port['jim']}: noma'lum - javob bermadi",
                  "veb sahifa: text/html 'XiL kamera'", "./oqim.sh rele "):
        if kerak not in m:
            return f"hisobotda yo'q: {kerak!r}"
    return f"Ochiq TCP portlar: {', '.join(map(str, sorted(port.values())))}" in m


def rele_tcp_sinovi():
    """oqim.sh rele: dron_qidiruv topgan xom H.264 tcp:// oqimini (KIRISH_FORMAT=h264) SRT orqali uzatadi."""
    if not shutil.which("ffmpeg"):
        return None
    with tempfile.TemporaryDirectory() as t:
        fayl = Path(t, "dron.h264")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                        "-i", "testsrc2=size=640x360:rate=25", "-t", "4", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-f", "h264", str(fayl)], check=True)
        srv, port = soxta_server(h264_ishlov(fayl.read_bytes()))
        chiqish = Path(t, "qabul.ts")
        qabul = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                                  "-i", "srt://127.0.0.1:8890?mode=listener", "-c", "copy", str(chiqish)],
                                 stderr=subprocess.DEVNULL)
        time.sleep(1)
        rele = subprocess.Popen(["bash", str(PAPKA / "oqim.sh"), "rele", f"tcp://127.0.0.1:{port}",
                                 "127.0.0.1", "abc123"], env={**os.environ, "KIRISH_FORMAT": "h264"},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            qabul.wait(timeout=30)
        finally:
            os.killpg(rele.pid, signal.SIGTERM)
            qabul.kill()
            srv.shutdown()
            srv.server_close()
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height",
                               "-of", "csv=p=0", str(chiqish)], capture_output=True, text=True).stdout.split("\n")[0]
        return "" if info == "h264,640,360" else f"qabul qilingan oqim: {info!r}"


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
    ("QR matni: IP:192.168.0.184;TP:MEDIA;",
     lambda: qr_ip("IP:192.168.0.184;TP:MEDIA;") == "192.168.0.184" and qr_ip(" 10.0.0.5 ") == "10.0.0.5"),
    ("Oqim turini baytlardan aniqlash: H.264, H.265, JPEG, TS, FLV",
     lambda: xom_oqim(SOXTA_H264) == "H.264"
     and xom_oqim(bytes.fromhex("0000000140010c01") + bytes(64)) == "H.265"
     and xom_oqim(b"\xff\xd8\xff\xe0" + bytes(64)) == "JPEG (MJPEG)"
     and xom_oqim((b"\x47" + bytes(187)) * 3) == "MPEG-TS"
     and xom_oqim(b"FLV\x01\x05") == "FLV" and xom_oqim(b"salom dunyo") == ""),
    ("dron_qidiruv: RTSP, MJPEG, xom H.264, RTMP, jim va yopiq portlar", qidiruv_sinovi),
    ("oqim.sh rele: xom H.264 (tcp://) SRT orqali serverga yetadi", rele_tcp_sinovi),
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
