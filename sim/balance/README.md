# Skuter simulyatsiyasi (1-versiya)

Ikki g'ildirakli skuterning muvozanat dasturi va yig'iladigan yon g'ildiraklar mantig'ini
skuterga o'rnatishdan oldin kompyuterda sinash uchun.

Ishga tushirish:

    python3 -m pip install numpy matplotlib
    python3 sinovlar.py

Natija: terminalda jadval (`natijalar.txt`) va grafik (`natijalar.png`).

- `skuter_sim.py`: skuter fizikasi (soddalashtirilgan velosiped modeli), muvozanat dasturi, yon g'ildirak qoidalari.
- `sinovlar.py`: 11 ta ssenariy (oddiy yurish, chuqur, tok uzilishi, dastur qotishi, sekin kompyuter va boshqalar).

## Simulyatsiya topgan va tuzatilgan muammolar

1. **Kompyuter kechikishi 200 ms dan oshsa muvozanat buziladi**, yon g'ildiraklar esa qayta-qayta ochilib-yopilardi.
   Tuzatish: kechikish 120 ms dan oshsa dastur "xato" deb hisoblanadi va g'ildiraklar ochiq qoladi.
2. **Yon g'ildirak mantig'i asosiy kompyuterga bog'liq bo'lsa, u qotganda kech ochiladi.**
   Tuzatish: bu mantiq alohida mikrokontrollerda, o'z IMU'si bilan ishlaydi (5 ms).
3. **Xavfli qiyalikdan keyin darhol qayta yig'ilish.** Tuzatish: 10 soniya kutish; 2 marta takrorlansa,
   operator tekshirmaguncha yig'ish o'chiriladi.

## Cheklovlar

Bu birinchi, sodda model: faqat to'g'ri yo'lda qiyalikni hisoblaydi. Burilishlar, yo'l notekisligi,
g'ildirak sirpanishi, kamera va marshrut hali yo'q. Raqamlar (og'irlik markazi 0,6 m, g'ildirak oralig'i
1,05 m va h.k.) taxminiy. Haqiqiy skuterni o'lchab, `Params` ichida yangilash kerak.

Keyingi qadam: Gazebo yoki Isaac Sim'da 3D simulyatsiya (kameralar bilan), keyin stendda haqiqiy
rul motori va IMU bilan sinov, keyin skuterning o'zida.
