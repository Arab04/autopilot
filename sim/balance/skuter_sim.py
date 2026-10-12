"""Ikki g'ildirakli avtonom skuterning muvozanat va yon g'ildirak simulyatsiyasi.

Model: soddalashtirilgan velosiped yonlama dinamikasi (Astrom, "Bicycle dynamics
and control", 2005). Skuter teskari mayatnik kabi yiqiladi, rulni qiyalik
tomonga burish markazdan qochma kuch hosil qilib, uni tik holatga qaytaradi.

    phi'' = (g/h)*phi - (v^2/(h*L))*delta - (a*v/(h*L))*delta' + yon_g'ildirak + tashqi

phi   - qiyalik burchagi (rad), musbat = o'ngga
delta - rul burchagi (rad), musbat = o'ngga

Bu model faqat qiyalikni ko'rib chiqadi (to'g'ri chiziqda yurish). Marshrut,
kamera va boshqa qismlar keyingi bosqichda qo'shiladi.
"""

from dataclasses import dataclass, field
import math
import random

G = 9.81
KMH = 1 / 3.6  # km/soat -> m/s


@dataclass
class Params:
    h: float = 0.60          # og'irlik markazi balandligi (m), yuk qutisi bilan
    L: float = 1.05          # g'ildiraklar oralig'i (m)
    a: float = 0.35          # og'irlik markazining orqa o'qdan masofasi (m)
    steer_max: float = 0.35  # rulning maksimal burilishi (rad, ~20 daraja)
    steer_rate_max: float = 3.0  # rul aktuatorining maksimal tezligi (rad/s)
    steer_tau: float = 0.04  # rul aktuatorining kechikishi (s)
    sensor_delay: float = 0.02   # IMU + dastur kechikishi (s)
    sensor_noise: float = 0.002  # IMU shovqini (rad)
    mcu_delay: float = 0.005     # mikrokontrollerning o'z IMU'sidan o'qish kechikishi (s)
    # Yon g'ildiraklar
    contact_angle: float = math.radians(3.5)  # ochiq g'ildirak shu qiyalikda yerga tegadi
    wheel_k: float = 400.0   # g'ildirak "prujinasi" (1/s^2)
    wheel_c: float = 40.0    # g'ildirak dempfiri (1/s)
    deploy_time: float = 0.25   # prujina bilan ochilish (s)
    retract_time: float = 1.5   # motor bilan yig'ilish (s)
    fall_angle: float = math.radians(25)  # shundan ortiq = yiqildi


@dataclass
class Rules:
    """Yon g'ildirak qoidalari (yon-gildirak-mexanizm.md, 5-bo'lim)."""
    retract_speed: float = 12 * KMH
    retract_hold: float = 2.0
    retract_max_lean: float = math.radians(3)
    deploy_speed: float = 9 * KMH
    deploy_lean: float = math.radians(8)
    balance_min_speed: float = 7 * KMH  # bundan sekinda muvozanat dasturi rulni burmaydi
    cooldown: float = 10.0  # xavfli holatda ochilgandan keyin shuncha vaqt yig'ilmaydi (s)
    max_lean_events: int = 2  # shuncha marta qiyalik sabab ochilsa, yig'ish butunlay o'chadi
    max_loop_delay: float = 0.12  # kompyuter kechikishi bundan oshsa = "dastur xatosi" (s)


class BalanceController:
    """Rulni qiyalik tomonga burib muvozanat saqlaydi (PD, tezlikka bog'liq koeffitsient)."""

    def __init__(self, p: Params, wn: float = 4.0, zeta: float = 0.8):
        self.p, self.wn, self.zeta = p, wn, zeta

    def command(self, phi, phi_dot, v):
        if v < 0.5:
            return 0.0
        p = self.p
        # Yopiq tizim phi'' + 2*zeta*wn*phi' + wn^2*phi = 0 bo'lishi uchun
        kp = (G / p.h + self.wn ** 2) * p.h * p.L / v ** 2
        kd = 2 * self.zeta * self.wn * p.h * p.L / v ** 2
        return max(-p.steer_max, min(p.steer_max, kp * phi + kd * phi_dot))


class SideWheels:
    """Yon g'ildiraklar holati: 'ochiq', 'yig'ilmoqda', 'yig'iq', 'ochilmoqda'."""

    def __init__(self, p: Params, r: Rules):
        self.p, self.r = p, r
        self.state = "ochiq"
        self.pos = 1.0          # 1 = to'liq ochiq, 0 = to'liq yig'iq
        self.fast_since = None
        self.blocked_until = 0.0
        self.lean_events = 0
        self.locked = False  # True = operator tekshirmaguncha yig'ilmaydi
        self.events = []

    def effective(self):
        return self.pos >= 0.9  # faqat deyarli to'liq ochilganda yuk ko'taradi

    def update(self, t, dt, v, phi, healthy, power_ok, route_ok):
        r, p = self.r, self.p
        must_deploy = (not power_ok or not healthy or v < r.deploy_speed
                       or abs(phi) > r.deploy_lean or not route_ok)
        if must_deploy and self.state in ("yig'iq", "yig'ilmoqda"):
            why = ("tok yo'q" if not power_ok else "dastur xatosi" if not healthy
                   else "qiyalik katta" if abs(phi) > r.deploy_lean
                   else "marshrut" if not route_ok else "sekinlashdi")
            self.state = "ochilmoqda"
            self.events.append((t, f"ochilmoqda ({why})"))
            if why != "sekinlashdi":
                self.blocked_until = t + r.cooldown
            if why == "qiyalik katta":
                self.lean_events += 1
                if self.lean_events >= r.max_lean_events:
                    self.locked = True
                    self.events.append((t, "yig'ish o'chirildi, operator tekshirishi kerak"))
        if v > r.retract_speed and not must_deploy:
            if self.fast_since is None:
                self.fast_since = t
        else:
            self.fast_since = None
        can_retract = (self.state == "ochiq" and self.fast_since is not None
                       and t - self.fast_since >= r.retract_hold
                       and abs(phi) < r.retract_max_lean and power_ok and healthy
                       and t >= self.blocked_until and not self.locked)
        if can_retract:
            self.state = "yig'ilmoqda"
            self.events.append((t, "yig'ilmoqda"))
        if self.state == "ochilmoqda":
            self.pos = min(1.0, self.pos + dt / p.deploy_time)
            if self.pos >= 1.0:
                self.state = "ochiq"
                self.events.append((t, "ochiq"))
        elif self.state == "yig'ilmoqda" and power_ok:
            self.pos = max(0.0, self.pos - dt / p.retract_time)
            if self.pos <= 0.0:
                self.state = "yig'iq"
                self.events.append((t, "yig'iq"))

    def torque(self, phi, phi_dot):
        """Yerga tegsa qaytaruvchi tezlanish (rad/s^2)."""
        if not self.effective():
            return 0.0
        p = self.p
        over = abs(phi) - p.contact_angle
        if over <= 0:
            return 0.0
        s = 1 if phi > 0 else -1
        return -s * p.wheel_k * over - p.wheel_c * phi_dot


@dataclass
class Scenario:
    name: str
    duration: float
    speed: callable                      # t -> m/s
    disturbance: callable = lambda t: 0.0  # t -> rad/s^2 (shamol, chuqur)
    power_ok: callable = lambda t: True
    healthy: callable = lambda t: True
    route_ok: callable = lambda t: True
    side_wheels: bool = True             # False = yon g'ildiraksiz oddiy skuter
    phi0: float = 0.0
    params: Params = field(default_factory=Params)


def run(sc: Scenario, dt=0.001, seed=1):
    rnd = random.Random(seed)
    p, r = sc.params, Rules()
    ctrl = BalanceController(p)
    wheels = SideWheels(p, r)
    if not sc.side_wheels:
        wheels.state, wheels.pos = "yig'iq", 0.0
    phi, phi_dot, delta, delta_dot = sc.phi0, 0.0, 0.0, 0.0
    delay_buf = [(phi, phi_dot)] * max(1, int(p.sensor_delay / dt))
    # Yon g'ildirak mantig'i alohida mikrokontrollerda, o'z IMU'si bilan ishlaydi:
    # asosiy kompyuter sekinlashsa yoki qotsa ham, u tez javob beradi.
    mcu_buf = [phi] * max(1, int(p.mcu_delay / dt))
    log = {k: [] for k in ("t", "v", "phi", "delta", "wheel_pos")}
    fell_at, max_lean, contact_time = None, 0.0, 0.0
    n = int(sc.duration / dt)
    for i in range(n):
        t = i * dt
        v = sc.speed(t)
        # Kechikish nazoratchisi (watchdog): kompyuter juda sekin bo'lsa = xato
        power = sc.power_ok(t)
        healthy = sc.healthy(t) and p.sensor_delay <= r.max_loop_delay
        # Datchik: kechikish + shovqin
        delay_buf.append((phi, phi_dot))
        m_phi, m_phid = delay_buf.pop(0)
        m_phi += rnd.gauss(0, p.sensor_noise)
        mcu_buf.append(phi)
        mcu_phi = mcu_buf.pop(0) + rnd.gauss(0, p.sensor_noise)
        # Boshqaruv
        if power and healthy and v >= r.balance_min_speed:
            target = ctrl.command(m_phi, m_phid, v)
        elif power and healthy:
            target = 0.0
        else:
            target = delta  # tok yoki dastur o'chsa rul qotib qoladi
        if sc.side_wheels:
            wheels.update(t, dt, v, mcu_phi, healthy, power, sc.route_ok(t))
        # Rul aktuatori (birinchi tartibli, tezligi cheklangan)
        rate = (target - delta) / p.steer_tau
        rate = max(-p.steer_rate_max, min(p.steer_rate_max, rate))
        if not (power and healthy):
            rate = 0.0
        delta_dot = rate
        delta = max(-p.steer_max, min(p.steer_max, delta + rate * dt))
        # Dinamika
        wt = wheels.torque(phi, phi_dot) if sc.side_wheels else 0.0
        if wt:
            contact_time += dt
        phi_dd = (G / p.h * phi - v ** 2 / (p.h * p.L) * delta
                  - p.a * v / (p.h * p.L) * delta_dot + wt + sc.disturbance(t))
        phi_dot += phi_dd * dt
        phi += phi_dot * dt
        max_lean = max(max_lean, abs(phi))
        if i % 10 == 0:
            for k, val in zip(log, (t, v, phi, delta, wheels.pos)):
                log[k].append(val)
        if abs(phi) > p.fall_angle:
            fell_at = t
            break
    return {
        "name": sc.name,
        "fell": fell_at is not None,
        "fell_at": fell_at,
        "max_lean_deg": math.degrees(max_lean),
        "contact_s": contact_time,
        "events": wheels.events,
        "log": log,
    }
