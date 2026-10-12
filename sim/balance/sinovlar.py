"""Sinov ssenariylari. Ishga tushirish: python3 sinovlar.py

Har bir ssenariy uchun natija chiqariladi va grafiklar natijalar.png ga yoziladi.
Biror sinov o'tmasa, dastur 1 kod bilan tugaydi.
"""

import math
import sys
from pathlib import Path

from skuter_sim import Scenario, Params, run, KMH


def profile(points):
    """[(t, km/soat), ...] bo'yicha chiziqli tezlik profili."""
    def f(t):
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            if t0 <= t <= t1:
                return (v0 + (v1 - v0) * (t - t0) / (t1 - t0)) * KMH
        return points[-1][1] * KMH
    return f


def pulse(t_start, length, accel):
    return lambda t: accel if t_start <= t < t_start + length else 0.0


normal = profile([(0, 0), (6, 20), (16, 20), (22, 0), (25, 0)])
cruise = profile([(0, 0), (6, 20), (30, 20)])

SCENARIOS = [
    # (ssenariy, kutilgan natija: yiqilmasligi kerakmi, qo'shimcha tekshiruv)
    (Scenario("1. Oddiy yurish: 0 → 20 km/soat → to'xtash", 25, normal, phi0=0.02),
     True, lambda r: any("yig'iq" == e for _, e in r["events"])
                     and r["events"][-1][1] == "ochiq"),
    (Scenario("2. Tezlikda chuqurga tushish (yonga turtki)", 20, cruise,
              disturbance=pulse(12, 0.15, 3.0)),
     True, None),
    (Scenario("3. Tezlikda tok uzilishi", 20, cruise, phi0=0.0,
              power_ok=lambda t: t < 12, disturbance=pulse(12, 0.1, 1.0)),
     True, lambda r: any("tok" in e for _, e in r["events"])),
    (Scenario("4. Tezlikda dastur qotib qolishi", 20, cruise,
              healthy=lambda t: t < 12, disturbance=pulse(12, 0.1, 1.0)),
     True, lambda r: any("dastur" in e for _, e in r["events"])),
    (Scenario("5. Kuchli yon zarba (katta qiyalik)", 20, cruise,
              disturbance=pulse(12, 0.3, 8.0)),
     True, lambda r: any("qiyalik" in e for _, e in r["events"])),
    (Scenario("6. Trotuarda 6 km/soat, yon g'ildiraklar bilan", 20,
              profile([(0, 0), (3, 6), (20, 6)]), phi0=0.03,
              disturbance=pulse(10, 0.2, 2.0)),
     True, lambda r: not any("yig'iq" == e for _, e in r["events"])),
    (Scenario("7. Taqqoslash: 6 km/soat, yon g'ildiraksiz", 20,
              profile([(0, 0), (3, 6), (20, 6)]), phi0=0.03, side_wheels=False),
     False, None),
    (Scenario("8. Sekin kompyuter (100 ms kechikish) + chuqur", 20, cruise,
              disturbance=pulse(12, 0.15, 3.0), params=Params(sensor_delay=0.10)),
     True, None),
    (Scenario("10. Juda sekin kompyuter (300 ms) + chuqur: yon g'ildiraklar ushlashi kerak",
              30, cruise, disturbance=pulse(12, 0.15, 3.0), params=Params(sensor_delay=0.30)),
     True, lambda r: not any("yig'iq" == e for _, e in r["events"])),
    (Scenario("11. Muvozanat yomon sozlangan: 2 marta qiyalik → yig'ish o'chadi", 40, cruise,
              disturbance=lambda t: 7.0 if (t % 12) < 0.3 and t > 8 else 0.0),
     True, lambda r: any("o'chirildi" in e for _, e in r["events"])),
    (Scenario("9. Tezlik 9–13 km/soat orasida tebranadi (tez-tez ochilib-yopilmasin)",
              30, lambda t: (11 + 2 * math.sin(t)) * KMH),
     True, lambda r: len(r["events"]) <= 4),
]

SCENARIOS.sort(key=lambda s: int(s[0].name.split(".")[0]))


def main():
    results, failed = [], []
    print(f"{'Ssenariy':62} {'Yiqildimi':10} {'Maks. qiyalik':14} {'Natija'}")
    for sc, should_survive, extra in SCENARIOS:
        r = run(sc)
        ok = (not r["fell"]) == should_survive and (extra is None or extra(r))
        results.append((sc, r, ok))
        if not ok:
            failed.append(sc.name)
        fell = f"ha ({r['fell_at']:.1f} s)" if r["fell"] else "yo'q"
        print(f"{sc.name[:62]:62} {fell:10} {r['max_lean_deg']:6.1f}°{'':7} "
              f"{'O`TDI' if ok else 'O`TMADI'}")
        for t, e in r["events"]:
            print(f"      {t:6.2f} s  yon g'ildirak: {e}")
    plot(results)
    print("\nO'tmagan sinovlar:", ", ".join(failed) if failed else "yo'q")
    return 1 if failed else 0


def plot(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    n = len(results)
    fig, axes = plt.subplots(n, 1, figsize=(11, 2.3 * n), sharex=False)
    for ax, (sc, r, ok) in zip(axes, results):
        lg = r["log"]
        ax.plot(lg["t"], [math.degrees(x) for x in lg["phi"]], color="#1f77b4", label="qiyalik (°)")
        ax.plot(lg["t"], [math.degrees(x) for x in lg["delta"]], color="#9467bd", lw=0.8, label="rul (°)")
        ax.plot(lg["t"], [v * 3.6 / 2 for v in lg["v"]], color="#7f7f7f", lw=0.8, ls="--", label="tezlik (km/soat ÷ 2)")
        ax.fill_between(lg["t"], -25, 25, where=[w >= 0.9 for w in lg["wheel_pos"]],
                        color="#2ca02c", alpha=0.08, label="yon g'ildiraklar ochiq")
        ax.axhline(3.5, color="#2ca02c", lw=0.5, ls=":")
        ax.axhline(-3.5, color="#2ca02c", lw=0.5, ls=":")
        ax.set_ylim(-25, 25)
        ax.set_xlim(0, sc.duration)
        status = "O'TDI" if ok else "O'TMADI"
        ax.set_title(f"{sc.name}   [{status}]", fontsize=10, loc="left",
                     color="#2ca02c" if ok else "#d62728")
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, loc="upper right", ncol=4)
    axes[-1].set_xlabel("vaqt (s)")
    fig.tight_layout()
    out = Path(__file__).with_name("natijalar.png")
    fig.savefig(out, dpi=90)
    print(f"\nGrafik: {out}")


if __name__ == "__main__":
    sys.exit(main())
