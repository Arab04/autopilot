# Dastur (software) rejasi: avval dastur, keyin skuter

*Qoralama, 2026-yil 12-oktabr. Muddatlar taxminiy, 3–4 kishilik jamoa uchun.*

**Tamoyil:** har bir modul skutersiz, kompyuterda sinaladi. Skuter faqat dastur quyidagi 7-bo'limdagi "tayyor" mezonlaridan o'tgandan keyin jihozlanadi.

## 1. Dastur tarkibi

| # | Modul | Vazifasi | Skutersiz qanday sinaladi |
|---|---|---|---|
| 1 | **Muvozanat va yon g'ildirak** | Rul bilan muvozanat, g'ildiraklarni ochish/yig'ish | ✓ 1-versiya bor (`simulyatsiya/`), 11 ta sinov o'tadi. Keyin 3D simulyatsiyaga ko'chiriladi |
| 2 | **3D simulyatsiya muhiti** | Chirchiq ko'chasi, piyodalar, mashinalar, skuter modeli kameralar bilan | Gazebo + ROS 2. Boshqa barcha modullar shu yerda sinaladi |
| 3 | **Ko'rish (faqat kamera)** | Odam, mashina, bordyur, chuqurni aniqlash; masofani baholash; tepadan ko'rinish xaritasi | Simulyatsiya + **Chirchiqda telefon bilan yozilgan videolar** (skuter kerak emas) |
| 4 | **Joylashuvni aniqlash** | GPS + IMU + kamera bo'yicha skuter qayerdaligi | Simulyatsiya + telefon videolari va GPS yozuvlari |
| 5 | **Marshrut va harakat** | Trotuar bo'ylab yurish, to'siqni aylanib o'tish, chorrahada to'xtash | Simulyatsiyada minglab marshrut |
| 6 | **Xavfsizlik qatlami** | Mikrokontroller dasturi: favqulodda to'xtash, ultratovush, watchdog, yon g'ildirak | Simulyatsiya, keyin stendda (faqat plata) |
| 7 | **Teleoperatsiya** | Operator video ko'radi va boshqaradi; avtonom/yarim avtonom rejimlar | Simulyatsiyadagi skuterni internet orqali boshqarish |
| 8 | **Flot va dispetcherlik** | Buyurtmani skuterga berish, kuzatish, CRM bilan bog'lash | Simulyatsiyadagi 5–10 ta virtual skuter bilan |
| 9 | **Mijoz Telegram boti** | Buyurtma kuzatuvi, qutini PIN bilan ochish | Virtual skuterlar bilan |

**Rejimlar** (bir xil dastur, sozlama bilan almashtiriladi):
- **Yarim avtonom:** skuter o'zi yuradi, chorrahalar va qiyin joylarda operator boshqaradi.
- **To'liq avtonom:** operator faqat kuzatadi, skuter yordam so'raganda aralashadi.

## 2. Ish tartibi va muddatlar

| Bosqich | Modullar | Natija | Taxminiy vaqt |
|---|---|---|---|
| A | 2 (3D simulyatsiya), 1 ni ko'chirish | Virtual skuter Chirchiq ko'chasida yuradi | 4–6 hafta |
| B | 7 (teleoperatsiya) | Operator virtual skuterni brauzerdan boshqaradi | 3–4 hafta |
| C | 3, 4 (ko'rish, joylashuv) | Virtual va haqiqiy videolarda to'siqlarni aniqlaydi | 8–10 hafta |
| D | 5, 6 (marshrut, xavfsizlik) | Virtual skuter A nuqtadan B ga o'zi boradi | 6–8 hafta |
| E | 8, 9 (flot, CRM, bot) | Virtual buyurtma → virtual skuter → yetkazildi | 4–6 hafta (B bilan parallel bo'lishi mumkin) |
| F | Hammasi birga | Uzoq sinov: virtual flot kunlab ishlaydi | 4 hafta |

Jami taxminan **6–8 oy**, ba'zi bosqichlar parallel bo'lsa tezroq.

## 3. Skutersiz tekshirib bo'lmaydigan narsalar

Buni oldindan bilish kerak, chunki simulyatsiya hech qachon haqiqatni 100% takrorlamaydi:
- Haqiqiy skuterning og'irligi, rul motori va g'ildiraklarining xususiyatlari (muvozanat sozlamalari qayta moslanadi).
- Kameralarni kalibrlash (har bir skuterda bir marta).
- Haqiqiy 4G signali va kechikishi Chirchiq marshrutida.

Shuning uchun skuter yig'ilgandan keyin ham **2–4 hafta moslash va sinov** kerak bo'ladi. Bu dastur tayyor emas degani emas, bu oddiy jarayon.

**Bitta tavsiya:** C bosqichida faqat **Jetson kompyuter va 1–2 ta kamera** sotib olish (skuter emas, ~1 000–2 500 $). Dastur haqiqiy uskunada yetarlicha tez ishlashini tekshirish kerak, chunki simulyatsiya kechikish 120 ms dan oshmasligi kerakligini ko'rsatdi.

## 4. Texnologiyalar

| Qism | Tanlov |
|---|---|
| Asos | ROS 2 Jazzy, Ubuntu 24.04, Python + C++ |
| Simulyatsiya | Gazebo Harmonic (bepul). Kerak bo'lsa keyinroq NVIDIA Isaac Sim (realistikroq kamera tasviri) |
| Ko'rish | PyTorch → TensorRT (Jetson uchun) |
| Marshrut | Nav2 |
| Teleoperatsiya | WebRTC, brauzerdagi operator paneli |
| Flot / dispetcherlik | Backend + ma'lumotlar bazasi, CRM bilan API orqali |
| Kod saqlash | GitHub, har bir o'zgarishda simulyatsiya sinovlari avtomatik ishlaydi |

## 5. Jamoa

- 1 robototexnika dasturchisi (ROS 2, Gazebo, Nav2, muvozanat)
- 1 kompyuter ko'rish mutaxassisi (modellar, ma'lumotlar)
- 1 backend dasturchi (teleoperatsiya, flot, CRM, bot)
- Ixtiyoriy: 1 kishi Chirchiqda video yozish va ma'lumotlarni belgilash uchun (yarim stavka)

## 6. Birinchi 2 hafta

1. GitHub'da kod ombori (repozitoriy) ochish va tuzilmani yaratish.
2. Mavjud muvozanat simulyatsiyasini omborga ko'chirish, sinovlar avtomatik ishlasin.
3. Gazebo + ROS 2 muhitini o'rnatish, oddiy skuter modelini yaratish.
4. Chirchiqda birinchi marshrutni telefon bilan video + GPS yozib chiqish (ko'rish moduli uchun ma'lumot).

## 7. "Skuterga tayyor" mezonlari

Dastur skuterga o'rnatiladi, faqat quyidagilarning hammasi bajarilganda:

1. Simulyatsiyada **1 000 km** yurish, birorta ham to'qnashuv yoki yiqilishsiz.
2. Barcha nosozlik ssenariylari o'tadi: tok, kompyuter qotishi, 4G uzilishi, kamera ishlamay qolishi, datchik shovqini.
3. Chirchiq videolarida odam va mashinalarni aniqlash: **99%+** (yo'qotib qo'yish xavfliroq, shuning uchun bu asosiy ko'rsatkich).
4. Jetson'da butun dastur kechikishi **< 100 ms**.
5. Operator virtual skuterni Chirchiq marshrutida masofadan muammosiz boshqara oladi.
6. Virtual buyurtma CRM'dan skuterga va mijozga to'liq yo'lni bosib o'tadi.
