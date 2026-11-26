"""Builds the drain cross-section SVG (same artwork as the web app) from a template and the live values. No Qt here."""
import math
from pathlib import Path

from . import core

TPL = (Path(__file__).parent / "assets" / "drain.svg.tpl").read_text(encoding="utf8")


def mix(a, b, t):
    return "rgb(%d,%d,%d)" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class DrainState:
    """Holds the animated values (water height, wave, pipe flow) and renders SVG text."""

    def __init__(self):
        self.p = 0.5            # water level 0..1
        self.y = 167 - 0.5 * 134
        self.amp = 1.2
        self.phase = 0.0
        self.t = 0.0
        self.flow_speed = 0.0   # seconds per dash cycle, 0 = stopped
        self.debris = 0.0       # eased 0..1
        self.debris_target = 0.0
        self.turb = 0.0
        self.rain = False
        self.drops = [[28 + (i * 37 % 104), (i * 11) % 30, 40 + (i * 13) % 60] for i in range(9)]
        self.pipe_phase = 0.0
        self.calm = False

    def set_values(self, p, flow_ratio, debris, turb, rain, calm=False):
        y = 167 - max(0.0, min(1.0, p)) * 134
        if not calm and abs(y - self.y) > 0.4:
            self.amp = min(7.0, self.amp + abs(y - self.y) * 1.2)
        self.y, self.p = y, p
        self.debris_target = 1.0 if debris else 0.0
        self.turb, self.rain, self.calm = max(0.0, min(1.0, turb)), rain, calm
        self.flow_speed = 0.0 if flow_ratio <= 0 else max(0.4, min(6.0, 1.2 / max(flow_ratio, 0.1)))

    def step(self, dt):
        self.t += dt
        self.phase += dt * 3.2
        self.amp = max(1.2 if self.flow_speed else 0.7, self.amp - dt * 2.2)
        self.debris += (self.debris_target - self.debris) * min(1.0, dt * 6)
        if self.flow_speed and not self.calm:
            self.pipe_phase = (self.pipe_phase + dt / self.flow_speed) % 1.0
        if self.rain and not self.calm:
            for d in self.drops:
                d[1] += d[2] * dt
                if d[1] > 30:
                    d[1] = 0

    def svg(self):
        y, amp, ph = self.y, self.amp, self.phase
        pts = [(23 + i * 114 / 12, y + amp * math.sin(ph + i * 0.9)) for i in range(13)]
        surf = "M" + " L".join("%.1f %.2f" % p for p in pts)
        water = "M23 168 L23 %.1f" % y + "".join(" L%.1f %.2f" % p for p in pts) + " L137 168 Z"
        sp = 6 + max(0.0, y - 48) * 0.16
        beam = "70,48 90,48 %.1f,%.1f %.1f,%.1f" % (90 + sp, y, 70 - sp, y)
        t = 0.0 if self.calm else self.t
        led = "%.2f" % (1.0 - 0.75 * (0.5 - 0.5 * math.cos(t * 2 * math.pi / 1.6)))
        wet = lambda i: "1.0" if self.p > core.PROBE_P[i] else "0.22"  # noqa: E731 - a probe lights up when the water is above it
        rep = {"P1": wet(0), "P2": wet(1), "P3": wet(2), "WATER": water, "SURF": surf, "BEAM": beam, "WG1": mix((86, 170, 220), (168, 128, 74), self.turb),
               "WG2": mix((40, 110, 170), (104, 74, 40), self.turb), "DEBRIS": "%.2f" % self.debris, "LED": led,
               "PIPE": "%.1f" % (-36 * self.pipe_phase), "PIPE2": "%.1f" % (-36 * ((self.pipe_phase + 0.1) % 1.0)),
               "WET": ("%.2f" % (1.0 - 0.75 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))) if self.rain else "0")}
        for i, name in enumerate(("S1", "S2", "S3")):       # sonar arcs
            k = (t / 1.8 - i * 0.14) % 1.0
            o = 0.0 if self.calm else (k / 0.3 * 0.9 if k < 0.3 else 0.9 * (1 - (k - 0.3) / 0.7))
            dy = -4 + 12 * k
            base = (56, 63, 70)[i]
            rep[name + "O"] = "%.2f" % max(0.0, o)
            rep[name + "Y"] = "%.1f" % (base + dy)
            rep[name + "Q"] = "%.1f" % ((62, 72, 82)[i] + dy)
        for i, name in enumerate(("B1", "B2", "B3")):       # bubbles rising
            k = ((t / 4.0) + i * 0.33) % 1.0
            rep[name + "Y"] = "%.1f" % ((160, 164, 158)[i] - 70 * k)
            rep[name + "O"] = "0" if self.calm else "%.2f" % (0.5 * min(1, k / 0.15) * (1 - k) / 0.85 if k > 0.15 else 0.5 * k / 0.15)
        rep["DROPS"] = "".join('<circle cx="%d" cy="%.1f" r="3.2"/>' % (d[0], d[1] + 2) for d in self.drops) if self.rain else ""
        out = TPL
        for k, v in rep.items():
            out = out.replace("{{%s}}" % k, v)
        return out
