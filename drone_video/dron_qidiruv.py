"""Pult Wi-Fi tarmog'ida qanday video xizmatlar berayotganini aniqlaydi.

Pult APP Flight rejimida QR kod ko'rsatadi, masalan `IP:192.168.0.184;TP:MEDIA;`.
Ya'ni pult Wi-Fi tarmoqqa oddiy qurilma bo'lib ulangan va video shu IP manzilda.
Shu Wi-Fi'ga ulangan kompyuterda (Windows, Linux yoki Mac, faqat Python kerak):

    python3 dron_qidiruv.py 192.168.0.184
    python3 dron_qidiruv.py "IP:192.168.0.184;TP:MEDIA;"     # QR matnini ham qabul qiladi
    python3 dron_qidiruv.py 192.168.0.184 --portlar 80,554    # faqat shu portlar

Barcha TCP portlar tekshiriladi. Ochiq portlarda RTSP, HTTP (MJPEG, HLS, FLV), RTMP
yoki to'g'ridan-to'g'ri H.264/JPEG oqimi qidiriladi, SSDP va ONVIF so'rovlari
yuboriladi. Natija ekranga va dron_qidiruv_<sana>.txt fayliga yoziladi.
Pultga faqat so'rov yuboriladi, uning sozlamalari o'zgartirilmaydi.
"""

from concurrent.futures import ThreadPoolExecutor
import datetime
import re
import shutil
import socket
import subprocess
import sys

RTSP_YOLLAR = ["", "live", "stream", "stream0", "stream1", "main", "main.264", "h264", "H264Video",
               "video", "media", "MEDIA", "live.sdp", "ch0", "ch01", "ch0_0.h264", "11", "12", "av0_0",
               "live/ch00_0", "live/main", "fpv_stream", "webcam", "unicast", "0", "1"]
HTTP_YOLLAR = ["/", "/?action=stream", "/stream", "/video", "/mjpeg", "/video.mjpg", "/mjpg/video.mjpg",
               "/live", "/live.flv", "/live.m3u8", "/index.m3u8", "/media", "/MEDIA", "/snapshot.jpg"]
CHEGARA = 64 * 1024


def qr_ip(matn):
    """'IP:192.168.0.184;TP:MEDIA;' yoki oddiy manzil -> '192.168.0.184'."""
    m = re.search(r"IP:\s*([\w.-]+)", matn, re.I)
    return m.group(1) if m else matn.strip()


def xom_oqim(b):
    """Baytlarga qarab oqim turini aniqlaydi, aniqlanmasa ''."""
    if b.startswith(b"FLV"):
        return "FLV"
    if b[:1] == b"\x47" and len(b) >= 377 and b[188:189] == b[376:377] == b"\x47":
        return "MPEG-TS"
    if b"\xff\xd8\xff" in b[:4096]:
        return "JPEG (MJPEG)"
    for m in re.finditer(rb"\x00\x00\x01(.)", b[:CHEGARA], re.S):
        nal = m.group(1)[0]
        if nal & 0x80 == 0 and nal & 0x1F in (5, 7, 8):
            return "H.264"
        if nal & 0x81 == 0 and (nal >> 1) & 0x3F in (19, 20, 32, 33, 34):
            return "H.265"
    return ""


def _javob(sarlavha):
    """Javob sarlavhalari -> (kod, {kalit: qiymat})."""
    qatorlar = sarlavha.decode("latin-1").split("\r\n")
    kod = int(qatorlar[0].split()[1]) if len(qatorlar[0].split()) > 1 and qatorlar[0].split()[1].isdigit() else 0
    maydon = {}
    for q in qatorlar[1:]:
        if ":" in q:
            k, v = q.split(":", 1)
            maydon[k.strip().lower()] = v.strip()
    return kod, maydon


def sora(ip, port, sorov=b"", kutish=1.5, chegara=CHEGARA):
    """So'rov yuborib javobni o'qiydi: sarlavha va Content-Length bo'yicha tana, yoki chegara/vaqt tugaguncha."""
    try:
        s = socket.create_connection((ip, port), timeout=kutish)
    except OSError:
        return b""
    olingan = b""
    try:
        s.settimeout(kutish)
        if sorov:
            s.sendall(sorov)
        while len(olingan) < chegara:
            qism = s.recv(8192)
            if not qism:
                break
            olingan += qism
            if b"\r\n\r\n" in olingan and olingan[:5] in (b"RTSP/", b"HTTP/"):
                sarlavha, tana = olingan.split(b"\r\n\r\n", 1)
                uzunlik = _javob(sarlavha)[1].get("content-length")
                if uzunlik is not None and len(tana) >= int(uzunlik):
                    break
    except OSError:
        pass
    finally:
        s.close()
    return olingan


def ochiq_portlar(ip, portlar, oqimlar=128, kutish=0.5):
    def ochiqmi(p):
        try:
            with socket.create_connection((ip, p), timeout=kutish):
                return p
        except OSError:
            return None
    with ThreadPoolExecutor(oqimlar) as ex:
        return sorted(p for p in ex.map(ochiqmi, portlar) if p)


def rtsp_tekshir(ip, port):
    """DESCRIBE bilan video yo'llarini qidiradi -> [(url, izoh)]."""
    topildi = []
    for yol in RTSP_YOLLAR:
        url = f"rtsp://{ip}:{port}/{yol}"
        javob = sora(ip, port, f"DESCRIBE {url} RTSP/1.0\r\nCSeq: 2\r\nAccept: application/sdp\r\n\r\n".encode())
        if not javob.startswith(b"RTSP/"):
            continue
        kod, _ = _javob(javob.split(b"\r\n\r\n", 1)[0])
        if kod == 200 and b"m=video" in javob:
            kodek = re.search(rb"a=rtpmap:\d+ ([\w-]+)/", javob)
            topildi.append((url, "video, " + (kodek.group(1).decode() if kodek else "kodek noma'lum")))
        elif kod == 401:
            topildi.append((url, "parol so'rayapti (401)"))
            break
    return topildi


def http_tekshir(ip, port):
    """Ma'lum yo'llarni GET qiladi -> [(url, izoh, video_bormi)]."""
    natija = []
    for yol in HTTP_YOLLAR:
        javob = sora(ip, port, f"GET {yol} HTTP/1.0\r\nHost: {ip}\r\n\r\n".encode())
        if not javob.startswith(b"HTTP/"):
            continue
        sarlavha, _, tana = javob.partition(b"\r\n\r\n")
        kod, maydon = _javob(sarlavha)
        if kod != 200:
            continue
        turi = maydon.get("content-type", "")
        oqim = xom_oqim(tana)
        url = f"http://{ip}:{port}{yol}"
        if "multipart/x-mixed-replace" in turi:
            natija.append((url, "MJPEG video oqimi", True))
        elif "mpegurl" in turi:
            natija.append((url, "HLS video", True))
        elif turi.startswith("image/"):
            natija.append((url, f"rasm ({turi}), bitta kadr", False))
        elif oqim:
            natija.append((url, f"{oqim} oqimi ({turi or 'turi yozilmagan'})", True))
        elif yol == "/":
            sarlavha_m = re.search(rb"<title>(.*?)</title>", tana, re.I | re.S)
            nomi = sarlavha_m.group(1).decode("utf-8", "replace").strip() if sarlavha_m else ""
            natija.append((url, f"veb sahifa: {turi} {nomi!r}".strip(), False))
    return natija


def port_tekshir(ip, port):
    """Bitta ochiq portda nima ishlayotganini aniqlaydi -> {turi, izoh, videolar: [(url, izoh)]}."""
    banner = sora(ip, port, b"", kutish=1.0)
    oqim = xom_oqim(banner)
    if oqim:
        return {"turi": f"xom {oqim}", "izoh": "ulanish bilanoq video yuboradi",
                "videolar": [(f"tcp://{ip}:{port}", oqim)]}
    javob = sora(ip, port, f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode())
    if javob.startswith(b"RTSP/"):
        yollar = rtsp_tekshir(ip, port)
        return {"turi": "RTSP", "izoh": "" if yollar else "video yo'li topilmadi",
                "videolar": [(u, i) for u, i in yollar if i.startswith("video")], "yollar": yollar}
    if javob.startswith(b"HTTP/") or sora(ip, port, b"GET / HTTP/1.0\r\n\r\n").startswith(b"HTTP/"):
        sahifalar = http_tekshir(ip, port)
        izoh = "; ".join(f"{u} -> {i}" for u, i, v in sahifalar if not v)
        videolar = [(u, i) for u, i, v in sahifalar if v]
        return {"turi": "HTTP", "izoh": izoh or ("" if videolar else "video yo'li topilmadi"),
                "videolar": videolar}
    rtmp = sora(ip, port, b"\x03" + bytes(1536), chegara=1537)
    if rtmp[:1] == b"\x03" and len(rtmp) > 1:
        return {"turi": "RTMP", "izoh": "RTMP server (yo'li noma'lum)", "videolar": []}
    namuna = (banner or javob)[:32]
    return {"turi": "noma'lum", "izoh": f"javob: {namuna.hex(' ')}" if namuna else "javob bermadi",
            "videolar": []}


def kashfiyot(ip, kutish=2.0):
    """SSDP va ONVIF (WS-Discovery) so'rovlariga javoblar -> [qator]."""
    sorovlar = [
        (1900, b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\n'
               b"MX: 1\r\nST: ssdp:all\r\n\r\n"),
        (3702, b'<?xml version="1.0" encoding="UTF-8"?><e:Envelope '
               b'xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
               b'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
               b'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"><e:Header>'
               b"<w:MessageID>uuid:2f1c7c1e-0d6b-4f58-9a3e-6b1f0c1d2e3f</w:MessageID>"
               b"<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>"
               b"<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>"
               b"</e:Header><e:Body><d:Probe/></e:Body></e:Envelope>"),
    ]
    javoblar = []
    for port, sorov in sorovlar:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(kutish)
        try:
            s.sendto(sorov, (ip, port))
            while True:
                data, _ = s.recvfrom(65535)
                matn = data.decode("utf-8", "replace")
                server = re.search(r"^SERVER:\s*(.+)$", matn, re.I | re.M)
                xaddr = re.search(r"XAddrs>([^<]+)<", matn)
                javoblar.append(f"{'SSDP' if port == 1900 else 'ONVIF'}: "
                                + (server.group(1).strip() if server else xaddr.group(1) if xaddr else matn[:120]))
        except OSError:
            pass
        finally:
            s.close()
    return javoblar


def mac_manzil(ip):
    """ARP jadvalidan MAC manzil (ishlab chiqaruvchini aniqlash uchun)."""
    for buyruq in (["arp", "-a", ip], ["arp", "-n", ip], ["ip", "neigh", "show", ip]):
        if not shutil.which(buyruq[0]):
            continue
        try:
            chiqish = subprocess.run(buyruq, capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.search(r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", chiqish)
        if m:
            return m.group(0).lower().replace("-", ":")
    return ""


def kirish_formati(url, izoh):
    """ffmpeg uchun -f qiymati: xom TCP oqimda format avtomatik aniqlanmasligi mumkin."""
    if not url.startswith("tcp://"):
        return ""
    return "hevc" if "H.265" in izoh else "mjpeg" if "JPEG" in izoh else "mpegts" if "TS" in izoh else \
        "flv" if "FLV" in izoh else "h264"


def ffprobe(url, izoh):
    if not shutil.which("ffprobe"):
        return ""
    buyruq = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,avg_frame_rate",
              "-of", "csv=p=0"]
    if url.startswith("rtsp://"):
        buyruq += ["-rtsp_transport", "tcp"]
    if kirish_formati(url, izoh):
        buyruq += ["-f", kirish_formati(url, izoh)]
    try:
        r = subprocess.run(buyruq + [url], capture_output=True, text=True, timeout=20)
        return (r.stdout.strip().splitlines() or [r.stderr.strip()[-150:]])[0]
    except subprocess.TimeoutExpired:
        return "ffprobe javob kutib qoldi"


def tekshir(ip, portlar=range(1, 65536), kashf=True, tekshirish=True):
    """Hamma bosqichlar -> hisobot qatorlari va topilgan video manzillar."""
    qatorlar = [f"Manzil: {ip}"]
    ochiq = ochiq_portlar(ip, portlar)
    mac = mac_manzil(ip)
    qatorlar.append(f"MAC: {mac or 'aniqlanmadi'}")
    qatorlar.append("Ochiq TCP portlar: " + (", ".join(map(str, ochiq)) or "yo'q"))
    videolar = []
    for p in ochiq:
        n = port_tekshir(ip, p)
        qatorlar.append(f"  {p}: {n['turi']}" + (f" - {n['izoh']}" if n["izoh"] else ""))
        for url, izoh in n.get("yollar", []):
            if not izoh.startswith("video"):
                qatorlar.append(f"      {url}: {izoh}")
        for url, izoh in n["videolar"]:
            qatorlar.append(f"      VIDEO: {url} ({izoh})")
            videolar.append((url, izoh))
    if kashf:
        javoblar = kashfiyot(ip)
        qatorlar.append("SSDP/ONVIF: " + ("; ".join(javoblar) if javoblar else "javob yo'q"))

    qatorlar += ["", "-- Xulosa --"]
    if videolar:
        for url, izoh in videolar:
            sinov = ffprobe(url, izoh) if tekshirish else ""
            qatorlar.append(f"* Video topildi: {url} ({izoh})" + (f"\n  ffprobe: {sinov}" if sinov else ""))
        url, izoh = videolar[0]
        fmt = kirish_formati(url, izoh)
        qatorlar += [f"* Ko'rish: ffplay -f {fmt} {url}" if fmt else
                     f"* VLC'da ko'rish: Media -> Open Network Stream -> {url}",
                     "* Serverga uzatish (shu kompyuterdan): " + (f"KIRISH_FORMAT={fmt} " if fmt else "")
                     + f"./oqim.sh rele {url} SERVER <PULT_PAROLI>"]
    elif ochiq:
        qatorlar.append("* Portlar ochiq, lekin ma'lum video formati topilmadi. Shu faylni jamoaga yuboring: "
                        "protokolni javoblar bo'yicha aniqlaymiz.")
    elif mac:
        qatorlar.append("* Pult tarmoqda bor (MAC javob berdi), lekin TCP portlari yopiq: video UDP orqali "
                        "va faqat ilova so'raganda yuborilishi mumkin. Shu faylni jamoaga yuboring.")
    else:
        qatorlar.append("* Pult topilmadi. Kompyuter pult bilan bir Wi-Fi'dami? Pult yoqilgan va APP Flight "
                        "rejimidami? Routerda 'mijozlarni ajratish' (AP/client isolation) o'chiqmi?")
    return qatorlar, videolar


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ip = qr_ip(sys.argv[1])
    portlar = range(1, 65536)
    if "--portlar" in sys.argv:
        portlar = [int(p) for p in sys.argv[sys.argv.index("--portlar") + 1].split(",")]
    print(f"{ip} tekshirilmoqda ({len(portlar)} ta port, bir necha daqiqa olishi mumkin)...")
    qatorlar, _ = tekshir(ip, portlar)
    vaqt = datetime.datetime.now()
    hisobot = [f"=== Pult tarmoq tekshiruvi ({vaqt:%Y-%m-%d %H:%M}) ==="] + qatorlar
    print("\n".join(hisobot))
    fayl = f"dron_qidiruv_{vaqt:%Y%m%d_%H%M%S}.txt"
    with open(fayl, "w", encoding="utf-8") as f:
        f.write("\n".join(hisobot) + "\n")
    print(f"\nNatija: {fayl} (shu faylni jamoaga yuboring)")


if __name__ == "__main__":
    main()
