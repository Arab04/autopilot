# Dron videosini serverga uzatish (1-versiya)

**Dron:** XiL 019 (pult ekranidagi versiya: `HF-XL-CN019A 338.026.0413`, `RC: V1.2.5`, `wifi: V7.0.3_128`).
Eski tizimda video faqat pultning o'z ekranida edi (Linux, Wi-Fi yo'q). Yangi pultda Wi-Fi va
**APP Flight** rejimi bor.

**Vazifa:** pultga kelayotgan videoni serverga yuborish. Serverda operatorlar uni brauzerda ko'radi, video
yozib boriladi, keyinchalik ko'rish moduli ham shu oqimdan foydalanadi.

APP Flight rejimida pult QR kod ko'rsatadi: `IP:192.168.0.184;TP:MEDIA;`. Demak pult Wi-Fi tarmoqqa
oddiy qurilma bo'lib ulangan va videoni shu IP manzilda beradi. Shu Wi-Fi'dagi kompyuter videoni
pultdan **to'g'ridan-to'g'ri** olib, serverga uzata oladi. Telefon va dron ilovasi kerak emas.

```
Dron --> Pult (Wi-Fi'da, 192.168.0.184) --Wi-Fi--> Kompyuter / Raspberry Pi --internet, SRT--> Server (MediaMTX)
                                                                                       --> brauzer, VLC, yozuv, Python
```

| Yo'l | Qachon | Bo'lim |
|---|---|---|
| **Asosiy:** pultdan to'g'ridan-to'g'ri | Pult QR kodda IP beradi (hozirgi holat) | 2, 3 |
| **Zaxira:** telefon ekranini uzatish | Faqat dron ilovasi telefonda ishlasa | 4, 5 |

## 1. Server (bir marta)

Kerak: tashqi IP manzilli Linux server (VPS) va Docker.

    git clone https://github.com/arab04/autopilot.git
    cd autopilot/drone_video/server
    ./ornatish.sh 203.0.113.10      # o'rniga serveringizning IP manzili yoki domeni
    docker compose up -d

`ornatish.sh` parollarni yaratadi va kerakli manzillarni `parollar.txt` ga yozadi (bu fayl GitHub'ga
tushmaydi). Serverda portlarni oching:

| Port | Nima uchun |
|---|---|
| 8890/udp | SRT: video shu orqali serverga keladi |
| 1935/tcp | RTMP: SRT ishlamasa, zaxira yo'l |
| 8889/tcp, 8189/udp | Brauzerda ko'rish (WebRTC) |
| 8888/tcp | Brauzerda ko'rish (HLS) |
| 8554/tcp | VLC, Python, `oqim.sh tekshir` |

**Dronsiz tekshirish** (ffmpeg o'rnatilgan kompyuterdan):

    ./oqim.sh sinov 203.0.113.10 <PULT_PAROLI>

Brauzerda `http://203.0.113.10:8889/dron` ni oching (login `operator`, parol `parollar.txt` da):
rangli sinov tasviri ko'rinsa, server tayyor.

## 2. Pultning video manzilini topish (`dron_qidiruv.py`)

QR kod faqat IP manzilni beradi. Video qaysi port va qaysi protokol (RTSP, MJPEG, xom H.264 va h.k.)
orqali berilishini skript aniqlaydi.

1. Pultda APP Flight rejimini yoqing, QR kod chiqsin. Kompyuterni pult bilan **bir Wi-Fi**'ga ulang.
2. Tez qo'lda tekshirish: brauzerda `http://192.168.0.184` ni oching; VLC'da
   (Media → Open Network Stream) `rtsp://192.168.0.184:554/` va `rtsp://192.168.0.184:8554/` ni sinang.
3. Skript (Windows, Linux yoki Mac, faqat Python kerak; ffmpeg bo'lsa natijani ham tekshiradi):

       python3 dron_qidiruv.py "IP:192.168.0.184;TP:MEDIA;"     # Windows'da: py dron_qidiruv.py ...

   Hamma 65 535 TCP port tekshiriladi (bir necha daqiqa), ochiq portlarda video qidiriladi.
   Pultga faqat so'rov yuboriladi, sozlamalari o'zgartirilmaydi.
4. Natija ekranga va `dron_qidiruv_<sana>.txt` fayliga yoziladi:

| Natija | Nima qilish |
|---|---|
| `VIDEO: rtsp://...`, `http://...` yoki `tcp://...` | Skript aytgan buyruq bilan serverga uzating (3-bo'lim) |
| Portlar ochiq, lekin video topilmadi | Natija faylini jamoaga yuboring: protokolni javoblar bo'yicha aniqlaymiz |
| Pult tarmoqda bor, lekin TCP portlari yopiq | Video UDP orqali va faqat ilova so'raganda keladi: quyidagi "TCP portlari yopiq bo'lsa" qismi |
| Pult topilmadi | Kompyuter pult bilan bir Wi-Fi'dami? Routerda mijozlarni ajratish (AP/client isolation) o'chiqmi? |

Pult qayta yoqilganda router unga boshqa IP berishi mumkin. Routerda shu pult uchun doimiy IP
(DHCP reservation) qiling yoki har safar QR koddagi IP'ni ishlating.

### TCP portlari yopiq bo'lsa (XiL 019 da shunday chiqdi)

2026-yil 14-oktabrdagi tekshiruv: pult `192.168.0.184` da javob beradi (MAC `88:49:2d:de:8c:f0`), lekin
birorta ham TCP port ochiq emas, SSDP/ONVIF javobi yo'q. Demak video **UDP** orqali keladi va pult uni
faqat ilova maxsus so'rov yuborgandan keyin boshlaydi. Bu so'rovni bilish uchun ilova bir marta kerak:

1. **Ilovani o'rnating.** Pult proshivkasi `HF-...` deb nomlangan. Bu "HF" oilasidagi dronlarga mos
   ilova **HFDrone** (Google Play: `com.rxdrone.gpshf`; iPhone: "HF Drone"). Bu ilova pult QR kodini
   skanerlay oladi. Play Market'da topilmasa, APK'ni APKPure yoki APKCombo'dan shu nom bilan oling.
   Bu taxmin: pult qutisi yoki qo'llanmasida boshqa ilova nomi yozilgan bo'lsa, o'shani oling.
   **Muhim:** ilovaning Xitoy versiyasi ishlashdan oldin Xitoy fuqaro aviatsiyasi (CAAC) UOM tizimida
   dronni ro'yxatdan o'tkazishni talab qiladi (`实名登记`: UOM ilovasidagi QR kod skrinshoti va dron
   seriya raqami). Bu ro'yxat odatda Xitoy hujjatlari va telefon raqami bilan qilinadi. Bu cheklovni
   aylanib o'tmang: sotuvchi yoki ishlab chiqaruvchidan ilovaning **xalqaro (global) versiyasini** so'rang.
2. **Ilova ishlasa, video darhol serverga uzatiladi:** 4-bo'limdagi zaxira yo'l (Larix Screencaster).
3. **Toza video uchun trafikni yozib oling.** Telefonga **PCAPdroid** (Google Play, bepul, root kerak
   emas) o'rnating. Unda "Target app" sifatida dron ilovasini tanlang, yozishni boshlang, dron ilovasida
   QR'ni skanerlab, videoni 30 soniya ko'ring, so'ng to'xtating va `.pcap` faylini saqlang
   (PCAPdroid'da "Dump mode: PCAP file"). Shu faylni jamoaga yuboring.
4. Fayldan pult bilan ilova o'rtasidagi so'rov va video formatini aniqlaymiz. Keyin kompyuter yoki
   Raspberry Pi ilovasiz, o'zi so'rov yuborib videoni qabul qiladigan dastur yoziladi (3-bo'lim).

## 3. Pultdan serverga uzatish

Pult bilan bir Wi-Fi'dagi kompyuterda (Linux, Mac yoki Raspberry Pi, ffmpeg kerak) `dron_qidiruv.py`
aytgan buyruqni ishga tushiring, masalan:

    ./oqim.sh rele rtsp://192.168.0.184:554/live SERVER <PULT_PAROLI>
    KIRISH_FORMAT=h264 ./oqim.sh rele tcp://192.168.0.184:8080 SERVER <PULT_PAROLI>   # xom H.264

- Kompyuter internetga shu Wi-Fi orqali chiqadi: SIM kerak emas.
- Video toza (ilova tugmalarisiz) va kameraning o'z sifatida.
- Aloqa uzilsa, `rele` 3 soniyadan keyin o'zi qayta ulanadi.
- Doimiy ish uchun pult yonida Raspberry Pi qo'yish qulay: arzon va kam quvvat oladi.
- Pult bir vaqtda faqat bitta qurilmaga video berishi mumkin. Rele ishlayotganda boshqa qurilmani
  pultga ulamang.
- Pultda HDMI chiqish bo'lsa, boshqa yo'l: HDMI → USB video karta → `./oqim.sh rele /dev/video0 ...`.

Windows'da `oqim.sh` WSL yoki Git Bash ichida ishlaydi (ffmpeg ham kerak).

## 4. Zaxira yo'l: telefon ekranini uzatish

Faqat dron ilovasi telefonda ishlasa kerak bo'ladi. Ilova tugmalari ham videoga tushadi, sifat telefon
ekrani bilan cheklangan.

1. Telefonga **Larix Screencaster** o'rnating (Google Play, bepul).
2. Larix'da yangi ulanish qo'shing (Settings → Connections → +), qiymatlar `parollar.txt` da:
   - URL: `srt://SERVER:8890`, Mode: `Caller`, streamid: `publish:dron:pult:<PULT_PAROLI>`
   - streamid maydoni bo'lmasa: `srt://SERVER:8890?streamid=publish:dron:pult:<PULT_PAROLI>`.
     SRT ishlamasa, RTMP manzilini ishlating.
3. Video: 1280x720, 30 kadr/s, 2000–3000 kbit/s, kalit kadr oralig'i 1 s, ovoz o'chiq.
4. Efirni boshlang, Android ruxsat so'raydi ("Bitta ilova" bo'lsa, dron ilovasini tanlang).
   Keyin dron ilovasiga qayting.
5. Ekran o'chmasin va Larix'ga batareya cheklovi qo'yilmasin, aks holda Android oqimni to'xtatadi.

**Internet:** telefon router Wi-Fi'siga ulangan bo'lsa (QR usuli), internet shu orqali bo'ladi.
Telefon dronning o'z Wi-Fi'siga ulansa, u yerda internet yo'q: mobil internetni (SIM) yoqing va
Wi-Fi "Internet yo'q, ulanib qolasizmi?" desa **Ha** deng. 2,5 Mbit/s soatiga ~1,1 GB sarflaydi.

## 5. Telefon haqida ma'lumot (`android_malumot.py`)

Zaxira yo'l uchun: video telefonga qaysi IP/port orqali kelayotganini va internet bor-yo'qligini
ko'rsatadi. Telefonda "USB debugging" ni yoqing (Telefon haqida → "Build number" ustiga 7 marta bosish),
kompyuterga [adb](https://developer.android.com/tools/releases/platform-tools) o'rnating, dron ilovasida
video ko'rinib turganda:

    python3 android_malumot.py

## 6. Videoni ko'rish va ishlatish

| Qayerda | Manzil | Izoh |
|---|---|---|
| Brauzer (WebRTC) | `http://SERVER:8889/dron` | eng kam kechikish |
| Brauzer (HLS) | `http://SERVER:8888/dron` | 3–6 s, lekin hamma joyda ishlaydi |
| VLC | `rtsp://operator:<OPERATOR_PAROLI>@SERVER:8554/dron` | |
| Serverdagi Python dastur | `cv2.VideoCapture("rtsp://127.0.0.1:8554/dron")` | parolsiz |
| Yozuvlar | `server/recordings/dron/` | 10 daqiqalik `.mp4` bo'laklar, 7 kun saqlanadi |

Pultdan to'g'ridan-to'g'ri yo'lda kechikish taxminan 0,5–1,5 s, telefon ekrani orqali 1–2,5 s.

Serverga video kelayotganini tekshirish (kodek, o'lcham, kadr/s):

    ./oqim.sh tekshir SERVER <OPERATOR_PAROLI>

## 7. Muammolar

| Belgi | Sabab va yechim |
|---|---|
| `dron_qidiruv.py` pultni topmadi | Bir Wi-Fi emas, pult o'chgan yoki IP o'zgargan (QR'ni qayta skanerlang), routerda client isolation yoqilgan |
| `rele` ulana olmaydi | Pult boshqa qurilmaga video beryapti; IP o'zgargan; `dron_qidiruv.py` ni qayta ishga tushiring |
| Larix "Connection failed" | `streamid` yoki parol xato; serverda 8890/udp yopiq; telefonda internet yo'q |
| VLC'da video bor, brauzerda yo'q | Serverda 8189/udp yopiq |
| Video qotib-qotib keladi | `BITREYT=1500k ./oqim.sh rele ...`; Larix'da bitreyt 1500, SRT latency 2000 ms |
| Brauzerda faqat qora ekran (Larix) | Dron ilovasi ekranni yozishni taqiqlagan. Asosiy yo'ldan foydalaning |

Xavfsizlik: brauzer va RTSP manzillari hozircha shifrlanmagan (HTTP). Pilot uchun bu yetarli.
Doimiy ish uchun domen va HTTPS qo'shish kerak.

## Fayllar

| Fayl | Nima |
|---|---|
| `server/mediamtx.yml` | Media server sozlamasi (shablon): kim yuboradi, kim ko'radi, portlar, yozuv |
| `server/docker-compose.yml` | Serverni ishga tushirish (MediaMTX 1.9.3) |
| `server/ornatish.sh` | Parollarni yaratadi, `mediamtx.local.yml` va `parollar.txt` yozadi |
| `dron_qidiruv.py` | Pultning Wi-Fi'dagi video manzilini topadi (QR koddagi IP bo'yicha) |
| `oqim.sh` | `rele` (pult/RTSP/MJPEG/xom H.264/HDMI → server), `sinov` (sinov tasviri), `tekshir` (serverdagi oqim) |
| `android_malumot.py` | Zaxira yo'l: telefon haqida ma'lumot (adb orqali) |
| `sinovlar.py` | Avtomatik sinovlar: `python3 sinovlar.py` |
