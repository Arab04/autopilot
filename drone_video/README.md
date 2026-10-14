# Dron videosini serverga uzatish (1-versiya)

**Dron:** XiL 019 (pult ekranidagi versiya: `HF-XL-CN019A 338.026.0413`, `RC: V1.2.5`, `wifi: V7.0.3_128`).
Eski tizimda video faqat pultning o'z ekranida edi (Linux, Wi-Fi yo'q). Yangi pultda Wi-Fi va
**APP Flight** rejimi bor: dron videoni Wi-Fi orqali Android telefondagi ilovaga yuboradi.

**Vazifa:** shu videoni serverga yuborish. Serverda operatorlar uni brauzerda ko'radi, video yozib
boriladi, keyinchalik ko'rish moduli ham shu oqimdan foydalanadi.

```
Dron --Wi-Fi--> Android telefon (APP Flight) --4G, SRT--> Server (MediaMTX) --> brauzer, VLC, yozuv, Python
```

Dron ilovasining video protokoli yopiq. Shuning uchun 1-versiyada **telefon ekrani uzatiladi**: istalgan
dron ilovasi bilan ishlaydi, root va dasturlash kerak emas. Kamchiligi: ilova tugmalari ham videoda
ko'rinadi, sifat esa telefon ekrani bilan cheklangan. Tugmalarsiz toza video 5-bo'limda.

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
| 8890/udp | SRT: telefon videoni shu orqali yuboradi |
| 1935/tcp | RTMP: SRT ishlamasa, zaxira yo'l |
| 8889/tcp, 8189/udp | Brauzerda ko'rish (WebRTC) |
| 8888/tcp | Brauzerda ko'rish (HLS) |
| 8554/tcp | VLC, Python, `oqim.sh tekshir` |

**Dronsiz tekshirish** (ffmpeg o'rnatilgan kompyuterdan):

    ./oqim.sh sinov 203.0.113.10 <PULT_PAROLI>

Brauzerda `http://203.0.113.10:8889/dron` ni oching (login `operator`, parol `parollar.txt` da):
rangli sinov tasviri ko'rinsa, server tayyor.

## 2. Telefondan serverga (asosiy yo'l)

1. Pultda **APP Flight** rejimini yoqing, telefonni dron Wi-Fi'siga ulang va dron ilovasida video
   ko'rinishini tekshiring (bu odatdagi ish tartibi).
2. Telefonga **Larix Screencaster** o'rnating (Google Play, bepul). U ekranni yozib, SRT yoki RTMP
   orqali serverga yuboradi.
3. Larix'da yangi ulanish qo'shing (Settings → Connections → +), qiymatlar `parollar.txt` da:
   - URL: `srt://SERVER:8890`
   - Mode: `Caller`
   - streamid: `publish:dron:pult:<PULT_PAROLI>`
   - streamid maydoni bo'lmasa, URL'ni bitta qatorda kiriting:
     `srt://SERVER:8890?streamid=publish:dron:pult:<PULT_PAROLI>`.
     SRT umuman ishlamasa, RTMP manzilini ishlating.
4. Video sozlamalari: 1280x720, 30 kadr/s, bitreyt 2000–3000 kbit/s (4G sekin bo'lsa 1000–1500),
   kalit kadr oralig'i 1 s, ovoz o'chiq.
5. Larix'da efirni boshlang. Android ekranni uzatishga ruxsat so'raydi. "Bitta ilova" tanlash
   mumkin bo'lsa (Android 14+), dron ilovasini tanlang: shunda bildirishnomalar videoga tushmaydi.
6. Dron ilovasiga qayting. Operator videoni `http://SERVER:8889/dron` da ko'radi.

Uzilmasligi uchun: ekran o'chmasin (Ekran → Uyqu rejimi → hech qachon). Larix'ga batareya cheklovi
qo'yilmasin (Sozlamalar → Ilovalar → Larix → Batareya → Cheklanmagan), aks holda Android fonda
oqimni to'xtatib qo'yadi.

## 3. Internet: eng muhim cheklov

Telefonning Wi-Fi'si dronga ulangan, dron Wi-Fi'sida esa internet yo'q. Shuning uchun video serverga
**mobil internet (SIM)** orqali chiqadi:

- Telefonda mobil internetni yoqing. Wi-Fi "Internet yo'q, ulanib qolasizmi?" deb so'rasa, **Ha** deng.
  Android dron Wi-Fi'sida qoladi, boshqa ilovalar (Larix) esa mobil internetdan foydalanadi.
- Dasturchi sozlamalarida "Mobil internet doim faol" (Mobile data always active) yoqilgan bo'lsin.
- Tekshirish: dron Wi-Fi'siga ulangan holda telefonda brauzerda biror sayt ochilsa, internet bor.
- Trafik: 2,5 Mbit/s soatiga taxminan **1,1 GB** mobil internet sarflaydi.

Telefonda SIM bo'lmasa, SIM'li telefondan foydalaning. Yoki USB-OTG Ethernet adapter orqali 4G
routerga ulang (hamma telefonda ishlamaydi). Qaysi holat ekanini `android_malumot.py` ko'rsatadi.

## 4. Telefon haqida ma'lumot yig'ish (`android_malumot.py`)

Skript dron videosi qaysi IP va port orqali kelayotganini, internet bor-yo'qligini va qurilmada RTSP
server bor-yo'qligini ko'rsatadi. 5-bo'limdagi toza video yo'lini tanlash uchun shu ma'lumot kerak.

1. Telefonda: Sozlamalar → Telefon haqida → "Build number" (Yig'ish raqami) ustiga 7 marta bosing.
   Keyin Dasturchi sozlamalari → "USB debugging" ni yoqing.
2. Kompyuterga `adb` o'rnating ([Android platform-tools](https://developer.android.com/tools/releases/platform-tools)),
   telefonni USB bilan ulang va telefon ekranidagi ruxsatni tasdiqlang.
3. Dronni yoqing va dron ilovasida video ko'rinib tursin, keyin:

       python3 android_malumot.py        # Windows'da: py android_malumot.py

4. Yaratilgan `android_malumot_<sana>.txt` faylini jamoaga yuboring.

Skript telefonda hech narsa o'zgartirmaydi va root talab qilmaydi.

## 5. Toza video, ilova tugmalarisiz (keyingi qadam)

Qaysi yo'l mosligini 4-bo'lim natijasi ko'rsatadi:

- **Video Wi-Fi orqali, dronning o'z protokoli bilan keladi** (APP Flight uchun ehtimoli yuqori).
  Bu holda telefon umuman kerak bo'lmaydi: dron Wi-Fi'siga Raspberry Pi ulanadi, videoni o'zi qabul
  qiladi va 4G modem orqali serverga yuboradi. Buning uchun protokolni aniqlash kerak: dronning IP
  manzili va portidan qaysi protokol oilasi ekanini bilsa bo'ladi, arzon Wi-Fi dronlarning ko'pchiligi
  uchun protokol ochiq manbalarda allaqachon tahlil qilingan. Dron bir vaqtda ikki qurilmaga video
  berishini ham tekshirish kerak.
- **Qurilmada RTSP server bor** (port 554 yoki 8554). Shu tarmoqdagi kompyuter yoki Raspberry Pi
  oqimni serverga uzatadi:

      ./oqim.sh rele rtsp://192.168.0.1:8554/<yol> SERVER <PULT_PAROLI>

- **Pultda HDMI chiqish bo'lsa:** HDMI → USB video karta → mini kompyuter:
  `./oqim.sh rele /dev/video0 SERVER <PULT_PAROLI>`.

## 6. Videoni ko'rish va ishlatish

| Qayerda | Manzil | Kechikish |
|---|---|---|
| Brauzer (WebRTC) | `http://SERVER:8889/dron` | eng kam |
| Brauzer (HLS) | `http://SERVER:8888/dron` | 3–6 s, lekin hamma joyda ishlaydi |
| VLC | `rtsp://operator:<OPERATOR_PAROLI>@SERVER:8554/dron` | |
| Serverdagi Python dastur | `cv2.VideoCapture("rtsp://127.0.0.1:8554/dron")`, parolsiz | |
| Yozuvlar | `server/recordings/dron/`, 10 daqiqalik `.mp4` bo'laklar, 7 kun saqlanadi | |

Dron → telefon → server → brauzer yo'lining umumiy kechikishi taxminan 1–2,5 s (4G va Larix'dagi
SRT latency sozlamasiga bog'liq). Bu kuzatish uchun yetarli. Masofadan boshqarish uchun esa 5-bo'limdagi
to'g'ridan-to'g'ri yo'l kerak bo'ladi.

Serverga video kelayotganini kompyuterdan tekshirish (kodek, o'lcham, kadr/s):

    ./oqim.sh tekshir SERVER <OPERATOR_PAROLI>

## 7. Muammolar

| Belgi | Sabab va yechim |
|---|---|
| Larix "Connection failed" | `streamid` yoki parol xato; serverda 8890/udp yopiq; telefonda mobil internet yo'q (3-bo'lim) |
| VLC'da video bor, brauzerda yo'q | Serverda 8189/udp yopiq |
| Video qotib-qotib keladi | Bitreytni 1500 kbit/s ga tushiring, Larix'da SRT latency'ni 2000 ms qiling |
| Brauzerda faqat qora ekran | Dron ilovasi ekranni yozishni taqiqlagan (kam uchraydi). 5-bo'limdagi yo'l kerak |
| Oqim 5–10 daqiqadan keyin to'xtaydi | Batareya tejash rejimi: 2-bo'lim oxiri |

Xavfsizlik: brauzer va RTSP manzillari hozircha shifrlanmagan (HTTP). Pilot uchun bu yetarli.
Doimiy ish uchun domen va HTTPS qo'shish kerak.

## Fayllar

| Fayl | Nima |
|---|---|
| `server/mediamtx.yml` | Media server sozlamasi (shablon): kim yuboradi, kim ko'radi, portlar, yozuv |
| `server/docker-compose.yml` | Serverni ishga tushirish (MediaMTX 1.9.3) |
| `server/ornatish.sh` | Parollarni yaratadi, `mediamtx.local.yml` va `parollar.txt` yozadi |
| `oqim.sh` | `sinov` (telefon o'rnida sinov tasviri), `tekshir` (serverdagi oqim), `rele` (RTSP/HDMI → server) |
| `android_malumot.py` | Telefon yoki Android pult haqida ma'lumot (adb orqali) |
| `sinovlar.py` | Avtomatik sinovlar: `python3 sinovlar.py` |
