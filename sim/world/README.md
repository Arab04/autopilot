# Virtual trotuar simulyatsiyasi (2D, 1-versiya)

Skuterning o'z dasturini (`autopilot/haydash.py`) virtual trotuarda sinaydi: piyodalar, ustunlar,
daraxtlar, to'satdan chiqqan odam, kamera nosozligi.

    python3 -m pip install matplotlib   # faqat grafik uchun
    cd sim/world
    python3 sinovlar.py 200             # 8 ta aniq ssenariy + 200 ta tasodifiy trotuar

## Nima sinaladi

| Fayl | Nima |
|---|---|
| `autopilot/haydash.py` | **Skuter dasturi** (keyin skuterga o'rnatiladi): obyektlarni kuzatish, yo'l tanlash, tezlik, xavfsizlik qatlami, operatorni chaqirish |
| `sim/world/dunyo.py` | **Simulyator**: trotuar, piyodalar, kamera va ultratovush modeli, skuter harakati |
| `sim/world/sinovlar.py` | Ssenariylar va o'tish shartlari |

Dastur qismlari:
1. **Kuzatuvchi**: kameraning shovqinli aniqlashlarini silliqlaydi, tezlikni baholaydi, odam va ustunni alohida kuzatadi.
2. **Rejalovchi**: 17 ta yon yo'lakni (va kerak bo'lsa ilon izi yo'lni) sinab, odamlardan 40 sm, ustunlardan 15 sm
   uzoqlikda o'tadigan eng qulay yo'lni tanlaydi. Oldidagi odamga 1,5 m masofada ergashadi.
   Yonidan odam o'tayotganda joyida kutadi.
3. **Xavfsizlik qatlami** (mikrokontrollerda): ultratovush yo'lda yaqin narsani ko'rsa favqulodda tormoz;
   kameradan 0,3 s ma'lumot kelmasa to'xtaydi.
4. **Yordam nazoratchisi**: 30 s ichida 1 m ham siljimasa, operatorni chaqiradi.

## Natijalar

Oxirgi natija: `natijalar.txt` va `natijalar.png`.

## Simulyatsiya topgan xatolar (tuzatildi)

1. Ultratovush yon tomondagi narsani ham "oldinda" deb hisoblab, skuterni ustun yonida abadiy to'xtatib qo'yardi.
2. Rejalovchi faqat 3 s oldinga qarardi va ustunni juda kech ko'rardi; endi turg'un narsalarga 10 m oldindan qaraydi.
3. Kamera shovqini tufayli skuter ustunni goh chapdan, goh o'ngdan aylanmoqchi bo'lib tebranardi;
   endi kuzatuvchi ustun joyini o'rtachalaydi va rejalovchi tanlagan tomonida qoladi.
4. Kuzatuvchi ustunni yonidan o'tgan odam bilan "adashtirib", ustunni odam deb hisoblardi.
5. Sekin yuruvchi odamning orqasidan to'liq tezlikda yaqinlashib, favqulodda tormoz berardi; endi 1,5 m masofada ergashadi.
6. Yonidan odam o'tib turganda burilib ketsa, skuterning orqasi odamga tegib ketardi; endi odam o'tguncha kutadi.

## Cheklovlar (keyingi versiyalarda)

- Trotuar to'g'ri chiziq: burilishlar, chorrahalar, yo'lni kesib o'tish hali yo'q.
- Kamera haqiqiy tasvir emas, "shovqinli aniqlash" modeli. Haqiqiy kamera Gazebo/Isaac Sim va Chirchiq videolarida sinaladi.
- Piyodalar modeli sodda: ba'zan turgan skuterga o'zlari kelib tegadi (natijada alohida sanaladi, skuter xatosi emas).
- Skuter burilganda orqa qismining yon tomonga surilishi rejalovchida hisobga olinmagan; buning o'rniga
  odam yonida bo'lsa skuter kutadi.
- Juda tor ilon izi joylarda (ikki to'siq orasi 1,5 m dan kam) skuter operatorni chaqiradi.
- Skuter to'siqni aylanib o'tgandan keyin o'ng tomonga qaytmaydi (o'ng tomonda yurish qoidasi hali yo'q).
