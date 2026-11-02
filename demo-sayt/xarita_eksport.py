"""Demo sayt uchun Chirchiq xaritasini (asosiy ko'chalar) va ombordan 10 manzilga marshrutlarni
ixcham JSON ga eksport qiladi: demo-sayt/xarita.json. Ishga tushirish: python3 demo-sayt/xarita_eksport.py"""
import json
import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ / "sim" / "world"))
from xarita_sinovlar import CHIRCHIQ_MANZILLAR, CHIRCHIQ_OMBOR, CHIRCHIQ_OSM, _asosiy  # noqa: E402
from autopilot.xarita import Xarita  # noqa: E402

CHET = 600  # m


def main():
    x = Xarita.osm_dan(str(CHIRCHIQ_OSM))
    ombor = CHIRCHIQ_OMBOR[1:]
    ml = [(nomi, x.skuter_marshruti(ombor, (lat, lon), _asosiy)) for nomi, lat, lon in CHIRCHIQ_MANZILLAR]
    # Ko'rinish: marshrutlar atrofi + 600 m chet (butun shahar emas, demo uchun yaqinroq)
    pts = [x.xy(i) for _, m in ml for i in m.tugunlar]
    x0, x1 = min(p[0] for p in pts) - CHET, max(p[0] for p in pts) + CHET
    y0, y1 = min(p[1] for p in pts) - CHET, max(p[1] for p in pts) + CHET
    k = 1000 / max(x1 - x0, y1 - y0)
    W, H = round((x1 - x0) * k), round((y1 - y0) * k)

    def ichida(i):
        a, b = x.xy(i)
        return x0 - 300 < a < x1 + 300 and y0 - 300 < b < y1 + 300

    def xy(i):
        a, b = x.xy(i)
        return [round((a - x0) * k, 1), round((y1 - b) * k, 1)]

    yollar = []
    for y in x.yollar:
        if not any(i in x.asosiy and ichida(i) for i in y.tugunlar):
            continue
        katta = 1 if y.turi in ("primary", "secondary", "trunk") else 0
        yollar.append([katta, [c for i in y.tugunlar for c in xy(i)]])
    svetofor = [xy(t.id) for t in x.tugunlar.values() if t.svetofor and t.id in x._yonma and ichida(t.id)]
    marshrutlar = []
    for nomi, m in ml:
        marshrutlar.append({"nomi": nomi, "uzunlik": round(m.uzunlik_xarita),
                            "chiziq": [c for i in m.tugunlar for c in xy(i)]})
    out = {"W": W, "H": H, "metr_px": round(k, 5), "ombor": xy(x.eng_yaqin_tugun(*ombor)),
           "yollar": yollar, "svetofor": svetofor, "marshrutlar": marshrutlar}
    f = Path(__file__).with_name("xarita.json")
    f.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{f}: {len(yollar)} yo'l, {len(marshrutlar)} marshrut, {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
