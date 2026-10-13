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
| Manzilga o'zi yetdi | 175/200 |
| Qotib qolib operator chaqirdi | 25/200 (12,5%) |
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

## Chirchiq xaritasida sinov

    python3 xarita_sinovlar.py --chirchiq 10   # ombordan 10 manzilga, har biri 10 marta (100 ta yetkazish)

Xarita: `xaritalar/chirchiq.osm.gz` (OpenStreetMap, 2026-10-12 da overpass-api.de dan yuklangan,
41.43-41.53 sh.k., 69.52-69.64 sh.u.; (c) OpenStreetMap hissadorlari, ODbL). Unda 2627 ta yo'l, lekin atigi
18 ta svetofor belgilangan: haqiqatda ko'proq bo'lishi mumkin, joyida tekshirish kerak.

Ombor va 1-5 manzilni Isroil bergan: ombor Navoiy (Markaziy) bozoriga yetmasdan; manzillar Jismoniy tarbiya
instituti (Troitsk), O'rmon parki, Chirchiq bozori, 8-kichik nohiya, Oktyabr. 6-10 manzilni Claude tanlagan
(pedagogika universiteti, shoshilinch yordam markazi, 4-kichik nohiya, Do'stlik mahallasi, Kimyogar sport majmuasi).
Koordinatalar OSM dagi shu nomli joylardan olingan.

Natija (100 ta yetkazish, 1,3-7,9 km): **to'qnashuv 0**, 45 tasida skuter manzilga o'zi yetdi, 55 tasida
operator chaqirildi. Operator chaqiruvining 44 tasi chorrahada: ombordan g'arbga boradigan deyarli har marshrut
svetoforsiz Alisher Navoiy shoh ko'chasini (4 polosa) kesadi va zich oqimda 2 daqiqa ichida xavfsiz oraliq
topilmaydi. Oktyabrga 10 tadan 0 tasi o'zi yetdi. O'rtacha tezlik 13,5 km/soat. To'liq jadval
`natijalar_chirchiq.txt`, xarita `natijalar_chirchiq.svg`.

### Haqiqiy xaritada topilgan xatolar (tuzatildi)

Sun'iy shaharda ko'rinmagan, birinchi Chirchiq yugurishida 50 ta yetkazishdan 11 tasida to'qnashuv bo'lgan
(1-6), haqiqiy ombor bilan yana 100 tadan 1 tasida (7-8):

1. **Ikki tugunli chorraha.** OSM'da ajratilgan yo'l (o'rtasida ajratuvchi bor) ikki yaqin chorraha bo'lib chizilgan
   (orasi 1-2 m). Skuter birinchisini o'tib, ikkinchisi oldida to'xtay olmay, uning **o'rtasida** to'xtab qolardi.
   Endi orasi 10 m dan kam o'tishlar bitta keng o'tish deb kesib o'tiladi.
2. **To'siq chorrahadan keyin.** Chorrahadan 5-10 m keyin mashina yoki avtobus turgan bo'lsa, skuter chorraha
   ichida to'xtab qolardi (to'xtash masofasi xato hisoblangan). Endi to'siqni aylanishni chorrahadan oldin boshlaydi
   (velosipedchilar kabi chaproqda kesib o'tadi), yoki orqa bo'sh bo'lmasa chorrahaga kirmay kutadi.
3. **Yondagi piyoda.** Skuter to'siq orqasida turganda, uning yonidan yo'lga tushgan odamni "orqada" deb hisoblab,
   joyidan qo'zg'alardi. Endi yonidagi odam ham hisobga olinadi.
4. **Ko'cha tartibi o'zgarganda** (masalan chorrahadan keyin parkovka boshlansa) skuter orqaga qaramay chapga
   surilardi. Endi orqadan mashina kelayotgan bo'lsa, u o'tib ketguncha joyida qoladi.
5. **Marshrut katta ko'chalarni svetoforsiz kesishdan qochadi**: chorrahada kesib o'tiladigan yo'l turiga qarab
   qo'shimcha narx (primary 200 m, secondary 120 m, svetofor bo'lsa 4 marta kam).
6. Faqat skuter yura oladigan asosiy tarmoqqa (tranzit yo'llar ajratib qo'ygan kichik bo'laklarga emas) manzil
   bog'lanadi; aks holda ba'zi manzillarga yo'l topilmasdi.
7. **Sekin velosipedchini cheksiz quvish.** Skuter oldidagi sekin velosipedchini aylanib o'tishni har safar
   cho'zib, 100 m dan ko'p polosada yurdi va chapga burilish chorrahasiga yon tomonda kirib, ikkinchi o'tish
   ichida to'xtab qoldi. Endi aylanish faqat turgan (yoki allaqachon yonidagi) narsa uchun cho'ziladi; chapga
   ikki bosqichli burilishdan oldin yon tomonda turib chorrahaga kirilmaydi; keyingi o'tish yaqin bo'lsa
   hozirgisini uning chizig'ida to'xtay oladigan tezlikda o'tadi.
8. Aylanishdan **o'ngga qaytishda** ham orqaga qaraydi (o'ng tomondan kelayotgan velosipedchi).

Simulyatorning o'zida ham tuzatildi: chorrahadagi ko'ndalang oqim ko'cha turiga qarab (hovli ko'chasida kam, katta
ko'chada ko'p), 900 s dan uzun marshrutlarda ham mashinalar bor; velosipedchi va mashinalar avtobus orqasida
abadiy tiqilib qolmaydi (chapdan aylanib o'tadi). 3-bosqich sinovi shu o'zgarishlardan keyin ham o'tadi
(150 ko'cha: to'qnashuv 0, operator 17/150; avval 16/150).

### Keyingi qadamlar

- Alisher Navoiy ko'chasini kesish: ombor yonidagi eng yaqin svetoforli o'tishni joyida aniqlab xaritaga
  qo'shish (OSM da yo'q), yoki u yerda doim operator tasdig'i bilan o'tish, yoki omborni ko'chaning g'arbiy
  tomoniga qo'yish.
- Chirchiqdagi svetoforlarni joyida (yoki videodan) xaritaga qo'shish.

# 5-bosqich: joylashuvni aniqlash (`joylashuv_sinovlar.py`)

Oldingi bosqichlarda simulyator skuterga uning aniq joyini berardi. Endi skuter joyini o'zi baholaydi:
`autopilot/joylashuv.py` (skuterga o'rnatiladi) faqat datchik o'lchovlarini oladi.

    cd sim/world
    python3 joylashuv_sinovlar.py 200              # 10 ta nosozlik ssenariysi + 200 ta tasodifiy ko'cha
    python3 xarita_sinovlar.py --chirchiq 2 --joylashuv   # Chirchiq marshrutlari, skuter joyini o'zi baholaydi

| Fayl | Nima |
|---|---|
| `autopilot/joylashuv.py` | **Skuter dasturi**: Kalman filtri (EKF), o'lchovlarni rad etish, ehtiyot qoidalari |
| `sim/world/joylashuv_dunyo.py` | **Datchiklar simulyatori**: GPS, odometr, giroskop, kamera (yo'l cheti, belgilar) |
| `sim/world/joylashuv_sinovlar.py` | Ssenariylar; har bir tasodifiy ko'cha aniq joy bilan va filtr bilan solishtiriladi |

## Datchiklar

| Datchik | Nima beradi | Simulyatordagi xatolar |
|---|---|---|
| GPS (5 Hz) | xaritadagi joy (x, y) va qabul qilgich aytgan aniqlik | tasodifiy 0,5-1 m + sekin o'zgaruvchi 1-2 m; binolar orasida 3-6 m (qabul qilgich buni 0,6-1 barobar kamaytirib aytadi); signal yo'qolishi; 35 m gacha "sakrash" (qabul qilgich sezmaydi) |
| G'ildirak odometri | tezlik | masshtab xatosi (yeyilgan g'ildirak): odatda 2% gacha, sinovda 6% |
| Giroskop | burilish tezligi | o'z xatosi 0,3-1 grad/s, sekin o'zgaradi |
| Kamera: yo'l cheti | bordyur yoki parkovka chizig'igacha yon masofa | 2-7 sm; 5-15% kadrda ko'rinmaydi; ba'zan 5-25 m umuman ko'rinmaydi (qor, loy); 2% noto'g'ri |
| Kamera: belgilar | chorrahaga kirish/chiqish cheti, o'ngga burilishda bordyur egilishi boshigacha masofa | 10-50 sm; 20-40% kadrda ko'rinmaydi; 2% noto'g'ri |

## Filtr va qoidalar

1. **Holat**: marshrut bo'ylab joy `s`, yon joy `d`, yo'nalish, giroskop xatosi, odometr masshtabi, GPS xatosi.
   Odometr va giroskop bilan oldinga hisoblanadi (20 Hz), GPS va kamera bilan tuzatiladi.
2. **Rad etish**: o'lchov filtr kutganidan juda uzoq bo'lsa (chi-kvadrat, 99,9%), ishlatilmaydi. Kamera bir xil
   narsani 5 kadr ketma-ket ko'rsatib, filtr uni rad etaversa, filtr adashgan: o'sha holatni qayta tiklaydi.
3. **O'lchov faqat o'z holatini tuzatadi**: yo'l cheti faqat yon holatni, belgilar faqat marshrut bo'ylab holatni.
4. **Binolar orasi**: GPS aniqligi yomonlashsa, joy GPS bo'yicha emas, odometr va belgilar bo'yicha baholanadi.
5. **Ehtiyot**: rejalovchi skuterni taxminiy joyidan 2 sigma oldinroq (chorraha va burilish yaqinroq) va 2 sigma
   bordyurga yaqinroq (bordyurdan uzoqroq yuradi) deb hisoblaydi. Kamera ko'rgan obyektlar skuterga nisbatan
   o'lchangani uchun joy tuzatilsa, kuzatuvdagi obyektlar ham shuncha suriladi.
6. **Noaniqlik katta bo'lsa**: oddiy yo'lda yon sigma 20 sm dan oshsa 10 km/soat, 50 sm dan oshsa to'xtab
   operatorni chaqiradi. Chorrahaga kirgan bo'lsa to'xtamaydi, oxirigacha o'tadi.

## Simulyatsiya topgan xatolar (tuzatildi)

1. **Aylanib o'tishda joy o'nlab metrga sakradi.** Filtr yon xatoni odometr xatosi deb tushunib, bordyur
   o'lchovidan marshrut bo'ylab joyni ham "tuzatardi" (bir o'lchovda 0,5 m gacha). Endi yon o'lchov faqat yon
   holatni tuzatadi.
2. **O'ngga burilishda bordyurga tegish.** Burilish boshini 1-2 m xato bilgan skuter erta burilardi, filtr esa bu
   xato yo'nalish xatosiga aylanishini bilmasdan, to'g'ri bordyur o'lchovlarini rad etardi. Endi filtr buni
   hisobga oladi va kamera burilish boshidagi bordyur egilishini ko'radi.
3. **Ikki bosqichli chap burilishda chetlarni adashtirish.** Chorraha chetlari 7 m oraliqda turadi; endi ular
   "kirish" va "chiqish" turiga ajratiladi, ikkita bir xil chet filtr darvozasiga tushsa, o'lchov ishlatilmaydi.
4. **Chorraha ichida to'xtab qolish.** Yon noaniqlik chap burilish burchagida (bordyur yo'q) oshib, skuter
   chorraha ichida "joyimni bilmayman" deb to'xtardi va ko'ndalang mashinalar urib ketardi (40 marshrutdan 15 tasida).
   Endi bu qoida faqat oddiy yo'lda ishlaydi.
5. **Binolar orasida filtr o'ziga ortiqcha ishondi** (9 m xato, sigma 1 m). Endi qabul qilgich aytgan aniqlikni
   hisobga oladi.
6. **3-bosqich rejalovchisidagi xato** (filtr bilan vaqt o'zgargani uchun chiqdi): bekatdagi avtobusni chorrahadan
   oldin aylanib o'tishni boshlagan skuter, chap polosadagi mashinalar yo'l bermagani uchun chorraha chiqishida
   qoldi. Endi aylanib o'tish rejimida chorrahaga faqat yon joyiga chiqib bo'lgach kiradi.

## Natija

200 ta tasodifiy ko'cha (3-bosqichdagi ko'chalar, har biriga tasodifiy datchik sharoiti: 40% da GPS 40-200 m
yo'qoladi, 25% da sakraydi, 25% da binolar orasi, 30% da bordyur 5-25 m ko'rinmaydi). Har bir ko'cha ikki marta
yuriladi: simulyator aniq joyni bergan holda va skuter joyini o'zi baholagan holda.

| Ko'rsatkich | Aniq joy | Joylashuv filtri |
|---|---|---|
| Manzilga o'zi yetdi | 175/200 | 174/200 |
| Qotib qolib operator chaqirdi | 25 | 26 (shundan 1 tasi joyini bilmagani uchun) |
| To'qnashuv yoki bordyurga tegish | 1 (kocha-192, 3-bosqichdagi odam holati) | 1 (o'sha kocha-192) |
| Chorraha ichida to'xtab qolish | 0 | 0 |
| O'rtacha tezlik | 12,2 km/soat | 12,2 km/soat |

Joy xatosi (filtr bilan): marshrut bo'ylab o'rtacha marshrutda eng ko'pi 1,5 m, eng yomonida 4,6 m; chorrahaga
15 m qolganda eng ko'pi 0,53 m (kamera chorraha chetini ko'radi). Yon tomonga oddiy yo'lda 5-15 sm; bordyur
ko'rinmaydigan joyda (chorraha, chap burilish burchagi) 1 m gacha, lekin filtr buni biladi va bordyurga tegish yo'q.
Haqiqiy xato filtr aytgan 3 sigma ichida: eng yomon marshrutda 80% vaqt, qolganlarida 99-100%.

Chirchiq xaritasida (`--chirchiq 2 --joylashuv`, 20 ta yetkazish): to'qnashuv 0, chorraha ichida to'xtash 0,
8 tasi o'zi yetdi (aniq joy bilan 9), operator chaqiruvlarining hammasi svetoforsiz katta ko'chani kesishda.
Joy xatosi: marshrut bo'ylab 1,4 m, chorrahaga 15 m qolganda 0,3 m.

CI 100 ta ko'cha bilan ishlaydi (kocha-192 kirmaydi).

## Cheklovlar va keyingi qadamlar

- **Xarita aniq deb olingan**: simulyatorda dunyo va skuter xaritasi bir xil. Haqiqiy OpenStreetMap ko'chalari
  1-3 m xato chizilgan, chorraha chetlari va burilish boshlari xaritada yo'q. Ularni Chirchiq videolaridan yoki
  joyida o'lchab, xaritaga qo'shish kerak.
- Skuter marshruti xaritadan bo'laklar (to'g'ri chiziq va yoy) sifatida tuziladi, GPS esa kenglik va uzunlik beradi.
  Haqiqiy skuterda marshrut chizig'i xaritadagi haqiqiy nuqtalardan tuzilishi kerak (`MarshrutChizigi`).
- Kamera o'lchovlari (bordyur, chorraha cheti) hali "shovqinli aniqlash" modeli. Ularni haqiqiy tasvirdan
  aniqlash ko'rish modulining vazifasi (Chirchiq videolari, 3D simulyatsiya).
- Tunda (yo'l cheti ko'rinmasa) skuter to'xtab operatorni chaqiradi: tungi ish uchun chiroq yoki IQ kamera kerak.
- Bitta tasodifiy ko'chada (avvalgi sinovda) skuter to'xtagan mashinani aylanib o'tishni uning orqa burchagidan
  0,72 m da boshlagan (eshik zonasi chegarasi 0,8 m). Joy xatosi 3 sm edi: bu rejalovchining chegaraviy harakati.
