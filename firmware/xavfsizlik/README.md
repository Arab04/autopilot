# Xavfsizlik platasi dasturi (6-modul, D bosqich)

Mikrokontroller (ESP32 yoki STM32) dasturining mantig'i: skuterning oxirgi himoya qatlami. Jetson (asosiy
kompyuter) nima buyursa ham, plata quyidagilarni o'zi tekshiradi va kerak bo'lsa motorni cheklaydi yoki to'xtatadi.
Kod apparatga bog'liq emas (C99, standart kutubxona), shuning uchun kompyuterda sinaladi va ko'cha
simulyatoriga ulanadi.

| Qoida | Nima qiladi |
|---|---|
| Ultratovush (oldingi 3 datchik) | To'xtash yo'li `v*0,15 + v²/(2*4) + 0,3 m` dan yaqin narsa: favqulodda tormoz; bo'shagach 0,3 s kutadi |
| Datchik xatosi | Oldingi datchik 0,3 s javob bermasa: tezlik 1,5 m/s gacha |
| Jetson jim qolsa | 120 ms: yumshoq to'xtash va yon g'ildiraklar ochiladi; 1 s: favqulodda |
| Operator / radio pult | Favqulodda to'xtatish bloklanadi; faqat skuter to'xtagach operator ochadi |
| Tezlik chegarasi | 20 km/soatdan tez yurmaydi, Jetson nima desa ham |
| Motor nosozligi | Tezlik kutilganidan 1,5 m/s ortiq va 0,5 s davom etsa: motor toki uziladi (qayta yoqilguncha) |
| Qiyalik | 25° dan oshsa (yiqildi): motor uziladi |
| Batareya | 44 V dan past: 8 km/soat; 41 V dan past: to'xtaydi |
| Yon g'ildirak | `yon-gildirak-mexanizm.md` 5-bo'lim: 12 km/soatdan 2 s keyin yig'iladi, 9 km/soatda yoki xavfda ochiladi, xavfli ochilishdan keyin 10 s kutadi, 2 ta qiyalik hodisasidan keyin operator tekshirmaguncha yig'ilmaydi; tok yo'qolsa qulf o'zi bo'shaydi |

Fayllar:
- `xavfsizlik.h/.c` - qoidalar; har 10 ms da `xv_qadam(holat, kirish, chiqish)`.
- `protokol.h/.c` - Jetson ↔ plata UART kadrlari (CRC16, takroriy/eski kadr rad etiladi, shovqindan keyin tiklanadi).
- `test_xavfsizlik.c` - sinovlar (`make test`, AddressSanitizer bilan).
- `plata.py` - Pythondan chaqirish (ctypes) va Jetson tomoni uchun kadr yozish (sof Python ham bor).
- `sim_sinov.py` - 3-bosqich ko'cha simulyatorini Python xavfsizlik qatlami o'rniga shu C dasturi bilan yurgizadi.

    make test                  # 1048 tekshiruv
    python3 sim_sinov.py 150   # 14 ssenariy + 150 tasodifiy ko'cha

## Natija (2026-10-21)

C dasturi bilan 150 ta tasodifiy ko'cha: to'qnashuv 0, o'zi yetdi 137/150. Bu Python qatlami bilan bir xil natija.

Simulyatsiya topgan xato (tuzatildi): datchik hech narsa ko'rmasa eng uzoq masofasini (4,5 m) qaytaradi.
Birinchi versiya buni "4,5 m da to'siq" deb o'qidi. 20 km/soatda to'xtash yo'li 4,6 m, shuning uchun skuter bo'sh
yo'lda har 1,3 s da favqulodda tormoz berdi va zich oqimda orqadan urilishlar bo'ldi (150 tadan 3 ta).
Endi eng uzoq masofa "oldinda bo'sh" degani.

Bundan xulosa: 20 km/soatda ultratovush to'siqqa urilishdan saqlay olmaydi, faqat zarbani yumshatadi.
Asosiy himoya kamera (Jetson). Ultratovush 15 km/soatgacha to'liq to'xtatadi (to'xtash yo'li 3 m).

## Keyingi qadam: apparat

- Plata: ESP32-S3 (2 yadro: biri datchiklar, biri qoidalar va UART) yoki STM32F4; o'z IMU si (MPU-6050/BMI088).
- Apparat watchdog: sikl 10 ms, 50 ms dan oshsa plata qayta yuklanadi; yuklanganda yon g'ildirak ochiq, motor o'chiq.
- Motor kontrolleri (VESC) ga tezlik chegarasi UART orqali, mexanik tormoz va motor toki alohida rele bilan
  (dastur osilib qolsa ham tok uzilsin).
- Radio pult: 433 MHz, plataga to'g'ridan-to'g'ri (Jetson va 4G orqali emas).
- Stendda sinov: plata + datchiklar + motor, g'ildiraklar havoda.
