# Virtual shahar simulyatsiyasi (2D, 2-versiya)

Skuterning o'z dasturini (`autopilot/`) virtual shaharda sinaydi: piyodalar, ustunlar, daraxtlar,
to'satdan chiqqan odam, kamera nosozligi, burilishlar, mashinalar yuradigan yo'lni kesib o'tish, svetoforlar.

    python3 -m pip install matplotlib   # faqat grafik uchun
    cd sim/world
    python3 sinovlar.py 200             # 16 ta aniq ssenariy + 200 ta tasodifiy trotuar + 100 ta shahar marshruti

## Nima sinaladi

| Fayl | Nima |
|---|---|
| `autopilot/haydash.py` | **Skuter dasturi** (keyin skuterga o'rnatiladi): obyektlarni kuzatish, yo'l tanlash, tezlik, xavfsizlik qatlami, operatorni chaqirish |
| `autopilot/marshrut.py` | Marshrut xaritasi: trotuar, burilish, yo'l o'tish joyi; burilishdan oldin sekinlashish |
| `autopilot/otish.py` | Yo'lni kesib o'tish: to'xtash chizig'i, svetofor, mashinalar oralig'i, operator tasdig'i |
| `autopilot/avtopilot.py` | Hammasini birlashtiruvchi `Avtopilot` klassi (yarim va to'liq avtonom rejim) |
| `sim/world/dunyo.py` | **Simulyator**: marshrut, piyodalar, mashinalar, svetofor, operator, kamera va ultratovush modeli, skuter harakati |
| `sim/world/sinovlar.py` | Ssenariylar va o'tish shartlari |

Dastur qismlari:
1. **Kuzatuvchi**: kameraning shovqinli aniqlashlarini silliqlaydi, tezlikni baholaydi, odam va ustunni alohida kuzatadi.
2. **Rejalovchi**: 17 ta yon yo'lakni (va kerak bo'lsa ilon izi yo'lni) sinab, odamlardan 40 sm, ustunlardan 15 sm
   uzoqlikda o'tadigan eng qulay yo'lni tanlaydi. Oldidagi odamga 1,5 m masofada ergashadi.
   Yonidan odam o'tayotganda joyida kutadi.
3. **Xavfsizlik qatlami** (mikrokontrollerda): ultratovush yo'lda yaqin narsani ko'rsa favqulodda tormoz;
   kameradan 0,3 s ma'lumot kelmasa to'xtaydi.
4. **Yordam nazoratchisi**: 30 s ichida 1 m ham siljimasa, operatorni chaqiradi (yo'l o'tish joyida 120 s).
5. **O'ng tomon qoidasi**: yo'l bo'sh bo'lsa trotuar markazidan 40 sm o'ngroqda yuradi.
6. **Burilish**: yon tezlanish 0,8 m/s² dan oshmasligi uchun burilishdan oldin sekinlashadi (r = 3 m da ~5,6 km/soat).
7. **Yo'lni kesib o'tish**:
   - o'tish joyidan oldin chiziqda to'xtaydi;
   - svetofor bo'lsa, piyodaga yashil va o'tib ulgurishga yetarli vaqt (+3 s) qolgan bo'lsa o'tadi;
   - svetofor bo'lsa ham mashinalarni tekshiradi (qizilda o'tib ketadigan haydovchilar);
   - svetofor bo'lmasa, har bir polosada mashina yetib kelguncha chiqib ulgurish + 2,5 s zaxira bo'lishi kerak;
   - yarim avtonom rejimda svetoforsiz joyda operator tasdiqlaydi; to'liq avtonom rejimda o'zi qaror qiladi;
   - oldida sekin odam bo'lsa, shu tezlikda o'tishini hisobga oladi; yo'lga chiqqach to'xtamaydi, 8 km/soat bilan o'tadi.

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

7. (2-versiya) Svetofor yashil yonganda skuter "otish" holatiga o'tsa ham, qizilda kutgan vaqti "qotib qoldi" deb
   hisoblanib operator chaqirilardi; endi yo'lga chiqish boshlanganda kutish hisobi qaytadan boshlanadi.
8. (2-versiya) To'liq avtonom rejimda skuter yo'lga sekin yuruvchi odam orqasidan chiqib, mashinalar oralig'ini 8 km/soat
   uchun hisoblagan, aslida 2-3 km/soatda o'tgan: mashina bilan to'qnashuv. Endi oldidagi odam tezligini hisobga oladi.
9. (2-versiya) To'xtash chizig'ida turgan mashinani kamera shovqini tufayli "o'tish joyiga kiryapti" deb ko'rib,
   skuter svetofor yashil bo'lsa ham o'tmasdi.
10. (2-versiya) Ikki to'siq ketma-ket turganda (biri chapda, biri o'ngda, 4-7 m oraliqda) ilon izi yo'lni topa olmay,
    to'g'ri borib to'siq oldida qotib qolardi. Endi uzoqroq ilon izi variantlari bor va yo'l topilmasa ham
    eng bo'sh tomonga oldindan buriladi.

## Cheklovlar (keyingi versiyalarda)

- Xarita oldindan ma'lum (marshrut bo'laklari) deb olingan; haqiqiy xarita va joylashuv keyingi bosqichda.
- Mashina va svetofor holati kameradan "shovqinli aniqlash" sifatida keladi; haqiqiy aniqlash 3D/video sinovida.
- Skuter orqaga yura olmaydi: to'siqqa juda yaqin kelib qolsa, operatorni chaqiradi.
- Kamera haqiqiy tasvir emas, "shovqinli aniqlash" modeli. Haqiqiy kamera Gazebo/Isaac Sim va Chirchiq videolarida sinaladi.
- Piyodalar modeli sodda: ba'zan turgan skuterga o'zlari kelib tegadi (natijada alohida sanaladi, skuter xatosi emas).
- Skuter burilganda orqa qismining yon tomonga surilishi rejalovchida hisobga olinmagan; buning o'rniga
  odam yonida bo'lsa skuter kutadi.
- Juda tor ilon izi joylarda (ikki to'siq orasi 1,5 m dan kam) skuter operatorni chaqiradi.
