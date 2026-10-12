# Autopilot: avtonom yetkazib beruvchi skuter dasturi

Ikki g'ildirakli, yig'iladigan yon g'ildirakli, faqat kamera bilan ishlaydigan yetkazib beruvchi skuter uchun dastur.
Pilot: Chirchiq. Tamoyil: avval butun dastur simulyatsiyada yoziladi va sinaladi, keyin skuterga o'rnatiladi.

Reja: [docs/dastur-reja.md](docs/dastur-reja.md)

## Tuzilma

| Papka | Modul | Holati |
|---|---|---|
| `sim/balance/` | Muvozanat va yon g'ildirak simulyatsiyasi | 1-versiya, 11 ta sinov |
| `autopilot/` | **Skuter dasturi**: kuzatish, yo'l tanlash, burilish, yo'lni kesib o'tish, xavfsizlik qatlami | 2-versiya |
| `sim/world/` | Virtual shahar (2D): trotuar, burilish, yo'l o'tish joyi, piyodalar, mashinalar, svetofor | 2-versiya, 16 + 200 + 100 ta sinov |
| `sim/3d/` | 3D simulyatsiya (Gazebo + ROS 2) | rejada |
| `perception/` | Kamera orqali ko'rish | rejada |
| `localization/` | Joylashuvni aniqlash | rejada |
| `safety/` | Mikrokontroller xavfsizlik dasturi | rejada |
| `teleop/` | Teleoperatsiya | rejada |
| `fleet/` | Flot, dispetcherlik, CRM, Telegram bot | rejada |

## Sinovlarni ishga tushirish

    python3 -m pip install numpy matplotlib
    cd sim/balance && python3 sinovlar.py
    cd sim/world && python3 sinovlar.py 200
