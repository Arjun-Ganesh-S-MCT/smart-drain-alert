"""Runs the engine (conditions, incidents, baseline, wizard, Drip state) without a display."""
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["APPDATA"] = tempfile.mkdtemp()

try:
    import PySide6.QtCore  # noqa: F401
except ImportError:                      # minimal stand-in so the logic can be tested anywhere
    class _Sig:
        def __init__(self): self.f = []
        def connect(self, fn): self.f.append(fn)
        def emit(self, *a): [fn(*a) for fn in list(self.f)]
    class _Bound:
        def __init__(self, n): self.n = n
        def __get__(self, o, t):
            if o is None: return self
            return o.__dict__.setdefault("_s_" + self.n, _Sig())
    def Signal(*a): return _Bound("x")
    class QObject:
        def __init_subclass__(cls, **k):
            for n, v in list(cls.__dict__.items()):
                if isinstance(v, _Bound): setattr(cls, n, _Bound(n))
        def __init__(self, *a): pass
    m = types.ModuleType("PySide6"); c = types.ModuleType("PySide6.QtCore")
    c.QObject, c.Signal = QObject, Signal
    sys.modules.update({"PySide6": m, "PySide6.QtCore": c})

from flowbeacon_app.engine import Engine  # noqa: E402
from flowbeacon_app.store import Store  # noqa: E402


class FakeLink:
    def __init__(self):
        self.connected, self.demo, self.cal_pending, self.sent = True, False, False, []
        self.data = type("S", (), {"connect": lambda s, f: setattr(self, "cb", f)})()
    def send(self, o): self.sent.append(o); return True


class FakeSound:
    def __init__(self): self.played = []
    def play(self, n, idle=False): self.played.append(n)


def feed(link, n, flow, dist, turb=850, rain=0):
    for _ in range(n):
        link.cb({"flow": flow, "dist": dist, "turb": turb, "rain": rain})


class EngineFlow(unittest.TestCase):
    def setUp(self):
        self.link, self.snd = FakeLink(), FakeSound()
        self.e = Engine(Store(), self.link, self.snd)

    def baseline(self):
        self.e.start_baseline()
        feed(self.link, 10, 4.2, 12.5)
        self.assertIsNotNone(self.e.base)
        self.assertFalse(self.link.cal_pending)

    def test_baseline_then_normal(self):
        self.baseline()
        feed(self.link, 3, 4.2, 12.5)
        self.assertEqual(self.e.last["name"], "Normal")
        self.assertEqual(self.e.drip_state(), "idle")

    def test_blockage_creates_incident_and_alarm_sound(self):
        self.baseline()
        feed(self.link, 2, 1.0, 11.0)
        self.assertGreaterEqual(self.e.last_lvl, 2)
        self.assertTrue(self.e.store_inc() if hasattr(self.e, "store_inc") else self.e.s["inc"])
        self.assertIn("warning", self.snd.played)
        feed(self.link, 2, 0.9, 1.5)
        self.assertEqual(self.e.last["name"], "Overflow detected")
        self.assertEqual(self.e.drip_state(), "panic")

    def test_hiding_not_disabled_logic_acknowledge(self):
        self.baseline()
        feed(self.link, 1, 0.9, 1.5)
        self.e.acknowledge()
        self.assertTrue(self.e.acked)

    def test_wizard_suggests_thresholds(self):
        self.e.wizard_start()
        for flow, dist in ((4.2, 12.5), (2.0, 11.0), (0.8, 10.0), (4.2, 12.5)):
            self.e.wizard_record()
            feed(self.link, 10, flow, dist)
        self.assertIsNotNone(self.e.wz["sug"])
        self.e.wizard_apply()
        self.assertEqual(self.e.cfg["dropWarn"], self.e.wz["sug"]["dropWarn"])

    def test_sms_goes_through_board(self):
        self.e.s["sms"] = {"on": True, "nums": "9876543210", "min": 2, "cool": 5}
        self.baseline()
        feed(self.link, 2, 1.0, 11.0)
        self.assertTrue(any(m.get("cmd") == "sms" and m["to"] == "+919876543210" for m in self.link.sent))


if __name__ == "__main__":
    unittest.main()
