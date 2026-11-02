# Investorlar uchun demo sayt

Bitta sahifali sayt (o'zbek / rus / ingliz): loyiha nima, jonli Chirchiq xaritasidagi demo,
simulyatsiya natijalari, operator paneli, skuter tuzilishi, reja va pilot byudjeti.

- `index.html` sahifa (kutubxonasiz, faqat Google Fonts).
- `xarita.json` Chirchiq ko'chalari va ombordan 10 manzilga marshrutlar. Qayta yaratish:
  `python3 demo-sayt/xarita_eksport.py` (xarita `sim/world/xaritalar/chirchiq.osm.gz` dan).
- `img/` operator paneli, flot paneli va yon g'ildirak chizmasi.

Lokal ko'rish: `cd demo-sayt && python3 -m http.server 8000` va http://localhost:8000.
Demodagi jadval raqamlari `sim/world/natijalar_chirchiq.txt` va `natijalar_flot.txt` dan olingan.
