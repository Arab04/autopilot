"""Dron videosini ko'rsatayotgan Android qurilma ("APP Flight" rejimidagi telefon yoki
Android pult) haqida ma'lumot yig'adi: qurilma, ilovalar, tarmoqlar, internet va video
qaysi IP/port orqali kelayotgani. Shunga qarab videoni serverga uzatishning eng yaxshi
yo'li tanlanadi (README, 4-5-bo'limlar).

Tayyorgarlik: qurilmada "Dasturchi sozlamalari" -> "USB orqali nosozliklarni tuzatish"
(USB debugging) yoqiladi, qurilma kompyuterga USB bilan ulanadi, kompyuterda `adb` bor.
Dron yoqilgan va dron ilovasida video ko'rinib turgan paytda ishga tushiring:

    python3 android_malumot.py

Natija ekranga chiqadi va android_malumot_<sana>.txt fayliga yoziladi. Bir nechta
qurilma ulangan bo'lsa: ANDROID_SERIAL=<seriya> python3 android_malumot.py
Root kerak emas, qurilmada hech narsa o'zgartirilmaydi.
"""

from dataclasses import dataclass
import datetime
import ipaddress
import re
import shutil
import subprocess
import sys
import time

BUYRUQLAR = {
    "ishlab_chiqaruvchi": "getprop ro.product.manufacturer",
    "model": "getprop ro.product.model",
    "android": "getprop ro.build.version.release",
    "sdk": "getprop ro.build.version.sdk",
    "platforma": "getprop ro.board.platform",
    "ekran": "wm size",
    "sim": "getprop gsm.sim.state",
    "mobil_internet": "settings get global mobile_data",
    "oldingi_ilova": "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' | head -2",
    "ilovalar_3": "pm list packages -3",
    "uidlar": "pm list packages -U",
    "manzillar": "ip -o -4 addr show",
    "yollar": "ip -4 route show table all | grep -E '^default'",
    "wifi": "dumpsys wifi | grep -m2 'mWifiInfo'",
    "tarmoqlar": "dumpsys connectivity | grep 'NetworkAgentInfo{'",
    "hdmi": "dumpsys display | grep -ci hdmi",
    "tcp": "cat /proc/net/tcp",
    "tcp6": "cat /proc/net/tcp6",
    "udp": "cat /proc/net/udp",
    "udp6": "cat /proc/net/udp6",
}

TCP_HOLAT = {"01": "ESTABLISHED", "02": "SYN_SENT", "06": "TIME_WAIT", "08": "CLOSE_WAIT", "0A": "LISTEN"}
RTSP_PORTLAR = {554, 8554}
VIDEO_CHEGARA = 0.5  # Mbit/s: bundan ko'p qabul qilayotgan interfeys orqali video kelyapti deb hisoblanadi


@dataclass
class Soket:
    protokol: str
    lokal_ip: str
    lokal_port: int
    uzoq_ip: str
    uzoq_port: int
    holat: str
    uid: int


def hex_ip(h):
    """/proc/net dagi IP: IPv4 teskari tartibda, IPv6 to'rtta teskari 32-bitli so'z."""
    b = bytes.fromhex(h)
    if len(b) == 4:
        return str(ipaddress.IPv4Address(b[::-1]))
    b = b"".join(b[i:i + 4][::-1] for i in range(0, 16, 4))
    ip = ipaddress.IPv6Address(b)
    return str(ip.ipv4_mapped or ip)


def soketlar(matn, protokol):
    natija = []
    for qator in matn.splitlines()[1:]:
        q = qator.split()
        try:
            lip, lport = q[1].split(":")
            rip, rport = q[2].split(":")
            natija.append(Soket(protokol, hex_ip(lip), int(lport, 16), hex_ip(rip), int(rport, 16),
                                TCP_HOLAT.get(q[3], q[3]) if protokol.startswith("tcp") else "", int(q[7])))
        except (IndexError, ValueError):
            continue
    return natija


def uid_paketlar(matn):
    """`pm list packages -U` -> {uid: "paket1, paket2"}."""
    paketlar = {}
    for m in re.finditer(r"package:(\S+)\s+uid:([\d,]+)", matn):
        for uid in {int(u) % 100000 for u in m.group(2).split(",")}:  # boshqa profillar: 10xxxxx
            paketlar.setdefault(uid, []).append(m.group(1))
    natija = {uid: ", ".join(p) for uid, p in paketlar.items()}
    natija.setdefault(1000, "android (tizim)")
    return natija


def trafik(dev1, dev2, soniya):
    """Ikki /proc/net/dev o'qishi orasidagi qabul/yuborish tezligi, Mbit/s."""
    def oqi(matn):
        d = {}
        for qator in matn.splitlines():
            if ":" in qator and "|" not in qator:
                nom, qolgan = qator.split(":", 1)
                f = qolgan.split()
                if len(f) >= 9:
                    d[nom.strip()] = (int(f[0]), int(f[8]))
        return d
    a, b = oqi(dev1), oqi(dev2)
    return {nom: ((b[nom][0] - a[nom][0]) * 8 / soniya / 1e6, (b[nom][1] - a[nom][1]) * 8 / soniya / 1e6)
            for nom in b if nom in a and nom != "lo"}


def tarmoqlar(matn):
    """`dumpsys connectivity` -> [(transport, interfeys, internet_bormi, ssid)]."""
    natija = []
    for qator in matn.splitlines():
        transport = re.search(r"Transports: ([A-Z_|]+)", qator)
        interfeys = re.search(r"InterfaceName: (\S+)", qator)
        ssid = re.search(r'SSID: "([^"]*)"', qator)
        natija.append((transport.group(1) if transport else "?", interfeys.group(1) if interfeys else "?",
                       bool(re.search(r"\bVALIDATED\b", qator)), ssid.group(1) if ssid else ""))
    return natija


def mahalliy(ip):
    a = ipaddress.ip_address(ip)
    return a.is_private and not a.is_loopback and not a.is_unspecified and not a.is_link_local


def tahlil(x):
    """Yig'ilgan xom ma'lumotdan (`yig` natijasi) hisobot qatorlarini tuzadi."""
    uidlar = uid_paketlar(x["uidlar"])
    nomi = lambda uid: uidlar.get(uid % 100000, f"uid {uid}")
    hammasi = [s for p in ("tcp", "tcp6", "udp", "udp6") for s in soketlar(x[p], p)]
    oldingi = re.search(r"\s([\w.]+)/", x["oldingi_ilova"])
    oldingi = oldingi.group(1) if oldingi else "aniqlanmadi"
    qatorlar = [
        f"Qurilma: {x['ishlab_chiqaruvchi']} {x['model']}, Android {x['android']} (SDK {x['sdk']}), "
        f"platforma {x['platforma']}",
        f"Ekran: {x['ekran'].replace('Physical size: ', '')}",
        f"Ekrandagi ilova: {oldingi}",
        "Qo'shimcha ilovalar: " + (", ".join(sorted(re.findall(r"package:(\S+)", x["ilovalar_3"]))) or "yo'q"),
        f"SIM: {x['sim'] or 'yo`q'}, mobil internet: {'yoqilgan' if x['mobil_internet'] == '1' else 'o`chiq'}",
        f"HDMI chiqish belgilari: {'bor' if x['hdmi'] not in ('', '0') else 'yo`q'}",
        "",
        "-- Tarmoqlar --",
    ]
    qatorlar += [q.strip() for q in x["manzillar"].splitlines() if " lo " not in q]
    qatorlar += [q.strip() for q in x["yollar"].splitlines()]
    if x["wifi"]:
        qatorlar.append(x["wifi"].splitlines()[0].strip()[:300])
    tarm = tarmoqlar(x["tarmoqlar"])
    internetli = sorted({f"{t} ({i})" for t, i, v, _ in tarm if v})
    qatorlar.append("Internetga chiqadigan tarmoqlar: " + (", ".join(internetli) or "YO'Q"))

    qatorlar += ["", f"-- Trafik ({x['trafik_soniya']:.0f} s davomida, Mbit/s) --"]
    tezlik = sorted(x["trafik"].items(), key=lambda kv: -kv[1][0])
    qatorlar += [f"{nom:14} qabul {q:6.2f}   yuborish {y:6.2f}" for nom, (q, y) in tezlik if q + y > 0.01]

    tinglovchilar = [s for s in hammasi if s.holat == "LISTEN" and not ipaddress.ip_address(s.lokal_ip).is_loopback]
    qatorlar += ["", "-- Ochiq TCP portlar (qurilmaning o'zida video server bo'lishi mumkin) --"]
    qatorlar += [f"{s.protokol:5} {s.lokal_ip}:{s.lokal_port:<6} {nomi(s.uid)}"
                 + ("   <- RTSP bo'lishi mumkin" if s.lokal_port in RTSP_PORTLAR else "")
                 for s in tinglovchilar] or ["yo'q"]

    lan = [s for s in hammasi if mahalliy(s.uzoq_ip) or (s.protokol.startswith("udp") and mahalliy(s.lokal_ip))]
    qatorlar += ["", "-- Mahalliy tarmoqdagi aloqalar (dron bilan aloqa shular orasida) --"]
    qatorlar += [f"{s.protokol:5} {s.lokal_ip}:{s.lokal_port} -> {s.uzoq_ip}:{s.uzoq_port} {s.holat:11} {nomi(s.uid)}"
                 for s in lan] or ["yo'q"]

    qatorlar += ["", "-- Xulosa --"]
    if not hammasi:
        qatorlar.append("* Soketlar ro'yxatini o'qib bo'lmadi (Android cheklovi), port bo'limlari bo'sh chiqdi.")
    video = [(nom, q) for nom, (q, _) in tezlik if q >= VIDEO_CHEGARA]
    if video:
        nom, q = video[0]
        qatorlar.append(f"* Video {nom} orqali kelyapti ({q:.1f} Mbit/s).")
        if nom.startswith("wlan") and not any(i == nom and v for _, i, v, _ in tarm):
            qatorlar.append("* Wi-Fi dronga ulangan va unda internet yo'q: serverga yuborish uchun internet "
                            "boshqa yo'ldan kerak (SIM, USB-Ethernet). README 4-bo'lim.")
    else:
        qatorlar.append("* Hech bir IP tarmoqda katta oqim ko'rinmadi: video IP tarmoqsiz (qurilmaning ichki "
                        "radio moduli orqali) kelyapti yoki o'lchash paytida video yo'q edi.")
    if not internetli:
        qatorlar.append("* Qurilmada hozir internet yo'q. Serverga yuborishdan oldin uni ulash kerak (README 4-bo'lim).")
    rtsp = [s for s in tinglovchilar if s.lokal_port in RTSP_PORTLAR]
    if rtsp:
        qatorlar.append(f"* Qurilmada RTSP server bor (port {rtsp[0].lokal_port}): toza oqim yo'lini sinab ko'ring "
                        "(README 3-bo'lim).")
    qatorlar.append("* Zaxira yo'l har qanday holatda ishlaydi: ekranni Larix Screencaster bilan uzatish "
                    "(README 4-bo'lim). Pult QR kodda IP bersa, dron_qidiruv.py afzal (README 2-bo'lim).")
    return qatorlar


def adb(buyruq):
    r = subprocess.run(["adb", "shell", buyruq], capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "replace").strip()


def yig(ishga_tushir=adb, kutish=3.0):
    x = {kalit: ishga_tushir(b) for kalit, b in BUYRUQLAR.items()}
    dev1, t1 = ishga_tushir("cat /proc/net/dev"), time.monotonic()
    time.sleep(kutish)
    dev2, t2 = ishga_tushir("cat /proc/net/dev"), time.monotonic()
    x["trafik_soniya"] = max(t2 - t1, 1e-3)
    x["trafik"] = trafik(dev1, dev2, x["trafik_soniya"])
    x["dev"] = dev2
    return x


def main():
    if not shutil.which("adb"):
        sys.exit("adb topilmadi. O'rnating: https://developer.android.com/tools/releases/platform-tools")
    holat = subprocess.run(["adb", "get-state"], capture_output=True, text=True)
    if holat.stdout.strip() != "device":
        sys.exit("Qurilma ulanmagan yoki ruxsat berilmagan: " + (holat.stderr.strip() or holat.stdout.strip())
                 + "\nQurilma ekranida 'USB debugging'ga ruxsat bering va qayta ishga tushiring.")
    print("Ma'lumot yig'ilmoqda (~10 s). Dron ilovasida video ko'rinib tursin...")
    x = yig()
    vaqt = datetime.datetime.now()
    hisobot = [f"=== Android qurilma haqida ma'lumot ({vaqt:%Y-%m-%d %H:%M}) ==="] + tahlil(x)
    print("\n".join(hisobot))
    fayl = f"android_malumot_{vaqt:%Y%m%d_%H%M%S}.txt"
    with open(fayl, "w", encoding="utf-8") as f:
        f.write("\n".join(hisobot) + "\n\n=== Xom ma'lumot ===\n")
        for kalit in list(BUYRUQLAR) + ["dev"]:
            f.write(f"\n--- {kalit} ---\n{x[kalit]}\n")
    print(f"\nTo'liq ma'lumot: {fayl} (shu faylni jamoaga yuboring)")


if __name__ == "__main__":
    main()
