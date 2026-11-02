# CRM (Spring Boot)

Do'kon CRM'i (ombor, mahsulot, sotuv, nasiya, Telegram OTP). Asl repo: `isroil096/CRM`; loyiha kodi shu
yerda, autopilot repo ichida saqlanadi.

## Yetkazib berish (`/api/deliveries`)

Sotuvni avtonom skuter bilan yetkazish. CRM buyurtmani flot dispetcheriga (`sim/world/operator_panel.py`,
`/api/buyurtma`) yuboradi, PIN, skuter, taxminiy vaqt va mijoz Telegram botiga havolani saqlaydi, holatni
har 30 soniyada yangilaydi.

| So'rov | Vazifasi |
|---|---|
| `POST /api/deliveries` `{saleId?, customerName, customerPhone, address, lat, lon, note?}` | Yangi yetkazish |
| `GET /api/deliveries`, `GET /api/deliveries/{id}` | Ro'yxat va holat |
| `POST /api/deliveries/{id}/refresh` | Holatni hozir yangilash (FAILED bo'lsa qayta yuborish) |

Sozlamalar (muhit o'zgaruvchilari): `FLEET_URL` (masalan `https://167-86-72-220.sslip.io`),
`FLEET_API_KEY` (serverdagi `FLOT_API_KALIT` bilan bir xil; `deploy/ornat.sh` oxirida ko'rsatadi),
`TELEGRAM_BOT_TOKEN`, `DB_PASSWORD`.

Sinov: `bash gradlew test --tests 'com.example.CRM.delivery.*'` (Windows'dan tashqarida
`-Dorg.gradle.java.home=<JDK 17 yo'li>` qo'shing, chunki `gradle.properties` Windows yo'lini ko'rsatadi).
