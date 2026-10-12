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

# 3-bosqich: yo'lda yurish (`yol_sinovlar.py`)

Trotuarlar skuter uchun moslanmagani sababli skuter **yo'lning o'ng chetida** yuradi (trotuar dasturi faqat
eshik oldidagi oxirgi 20-50 m uchun qoladi).

    cd sim/world
    python3 yol_sinovlar.py 200   # 14 ta aniq ssenariy + 200 ta tasodifiy ko'cha

| Fayl | Nima |
|---|---|
| `autopilot/yol.py` | **Skuter dasturi (yo'l)**: kuzatuvchi, rejalovchi, chorraha, xavfsizlik qatlami |
| `sim/world/yol_dunyo.py` | **Ko'cha simulyatori**: polosalar, parkovka, velosiped yo'lagi, mashinalar (IDM), avtobus, velosipedchi, odamlar, svetofor, ko'ndalang oqim |
| `sim/world/yol_sinovlar.py` | Ssenariylar va o'tish shartlari |

Yo'lda `d` = o'ng bordyurdan chapga masofa (m). Ko'cha o'ngdan chapga: `[parkovka][velosiped yo'lagi][polosalar]`.

## Skuter qoidalari

1. **Joyi**: velosiped yo'lagi bo'lsa uning o'rtasida; bo'lmasa bordyurdan 0,8 m; parkovka bo'lsa ochilgan eshikdan
   (1 m) tashqarida.
2. **Tezlik**: eng ko'pi 20 km/soat; to'xtagan mashinalar qatori yonida 12 km/soat (orasidan odam chiqishi mumkin).
3. **Aylanib o'tish** (chetda to'xtagan mashina, avtobus, to'siq, sekin velosipedchi): faqat orqadan kelayotgan
   mashina bemalol sekinlasha olsa (oraliq ≥ v·1,5 s + farq²/(2·2 m/s²) + 8 m). Yonimizda yoki orqamizda
   mashina o'tayotgan bo'lsa, chapga surilmay joyida kutadi. Chorrahaga 5-15 m qolganda aylanishni boshlamaydi.
4. **Ergashish**: oldingi transportdan 1,5 s + 3 m.
5. **Odamlar**: yo'li bizning yo'lakni kesadigan odam oldida to'xtaydi.
6. **O'ngga buriluvchi mashina** (chorraha oldida, signal bergan): unga yo'l beradi.
7. **Chorraha**: yashilda va mashina bo'lmasa to'xtamasdan o'tadi; chap burilish ikki bosqichda (chorrahani ikki marta
   kesib o'tish). Chorrahadan keyin joy bo'lmasa (to'xtagan avtobus, tirbandlik), chorrahaga kirmaydi.
   Chiroq o'zgarganda qulay to'xtay olmasa o'tib ketadi ("sariq dilemma"), lekin mashina xavfi bo'lsa doim to'xtaydi.
   Kamera bir-ikki kadrda mashinani ko'rmay qolsa ham uni 0,6 s eslab qoladi.
8. **Burilishning ichki tomoni**: s bo'yicha tezlik haqiqiy tezlikdan katta bo'lgani uchun tormoz masofasi to'g'rilanadi.

## Simulyator

- Mashinalar IDM modeli bilan yuradi, skuterni polosa ichida yoki qo'shni polosaga o'tib quvib o'tadi
  (bir polosali yo'lda qarama-qarshi polosaga chiqib). 2% haydovchi e'tiborsiz (skuterni juda kech ko'radi),
  25% o'ngga buriladi, ko'ndalang oqimda 3% qizilda o'tib ketadi.
- To'xtagan mashinalar orasidan chiqadigan odamlar (25% e'tiborsiz), avtobus bekatlari, to'siqlar, velosipedchilar.
- Kamera: oldinga 50 m, orqaga 60 m, shovqin, 3% ko'rmay qolish; har 5-marshrutda kamera 0,5-3 s o'chadi.

## Natija (200 ta tasodifiy ko'cha)

| Ko'rsatkich | Natija |
|---|---|
| Manzilga o'zi yetdi | 176/200 |
| Qotib qolib operator chaqirdi | 24/200 (12%) |
| Mashina / velosipedchi / to'siq / ko'ndalang mashina bilan to'qnashuv | 0 / 0 / 0 / 0 |
| Odam bilan to'qnashuv | 1 (kocha-192, pastda) |
| Bordyurga tegish, eshik zonasidan o'tish | 0, 0 |
| O'rtacha tezlik | 12,3 km/soat |

CI 150 ta marshrut bilan ishlaydi (kocha-192 kirmaydi), aniq ssenariylarning hammasi o'tadi.

## Ochiq qolgan xavflar

- **kocha-192**: e'tiborsiz odam to'xtagan mashinalar orasidan skuterning naq yonidan (0,7 m oldida) chiqib, skuterga
  kirib ketadi. Bunda hech qanday tezlikda to'xtab bo'lmaydi; yagona yechim parkovka yonida sekinroq yurish yoki
  ulardan uzoqroq yurish. Haqiqiy sinovda bu holat kuzatiladi.
- Simulyatordagi ba'zi mashinalar skuterni 0,3 m yaqindan quvib o'tadi. Haqiqiy yo'lda orqa kamera va
  ko'rinadigan chiroqlar/bayroqcha kerak.
- Qotib qolishlarning ko'pi: bekatda turgan avtobus orqasida, tirband polosa yonida yoki chorrahadan keyin joy
  bo'lmaganda. Skuter orqaga yura olmaydi; bu holatda operator boshqaradi.
- Xarita (Yandex) va joylashuv hali ulanmagan: marshrut bo'laklari oldindan ma'lum deb olingan.

# 4-bosqich: xaritadan marshrut (`xarita_sinovlar.py`)

`autopilot/xarita.py` ikki nuqta (kenglik, uzunlik) orasida skuter yo'lini topadi va uni dastur tushunadigan
bo'laklarga (yo'l, burilish, chorraha) aylantiradi.

**Nega hozir OpenStreetMap:** Yandex xaritalarining bepul API shartlari pullik loyihada ishlatishni, ma'lumotni
saqlashni (oflayn nusxa) va transportni kuzatish tizimini taqiqlaydi, marshrut esa faqat Yandex MapKit ilovasida
beriladi ([shartlar](https://yandex.ru/legal/maps_api/), 4.1.1, 5.1.3, 5.1.5, 6.2.1). OSM bepul, tijoratda
ishlatish va oflayn saqlash mumkin (ODbL, mualliflik ko'rsatiladi). Modul manbaga bog'lanmagan: Yandex tijorat
litsenziyasi olinsa, faqat o'quvchi funksiya qo'shiladi.

Qoidalar:
- motorway/trunk ishlatilmaydi, primary qimmatroq (kichik ko'chalar afzal), bir tomonlama ko'chaga teskari kirilmaydi;
- 3 va undan ko'p tarmoqli tugun chorraha: to'g'ri kesib o'tish (`otish`), o'ngga r = 6 m burilish,
  chapga ikki bosqich (ko'ndalang ko'cha, burchakda burilish, o'z ko'chamiz);
- svetofor (tugunda yoki 25 m ichida), polosalar soni, velosiped yo'lagi va parkovka OSM teglaridan olinadi.

Sinov (`python3 xarita_sinovlar.py`): sun'iy shaharda (Chirchiq emas) 10 ta tasodifiy manzil: yo'l qoidalari va
marshrut uzunligi tekshiriladi, keyin har marshrut tasodifiy transport bilan simulyatorda bosib o'tiladi.
Natija: 10 tadan 10 tasi xavfsiz, 8 tasi o'zi yetdi, 2 tasida operator.

Chirchiq uchun: openstreetmap.org da shahar hududini eksport qilib (`.osm`), `python3 xarita_sinovlar.py --osm chirchiq.osm`.
Chirchiq OSM'da qanchalik to'liq chizilgani hali tekshirilmagan.
