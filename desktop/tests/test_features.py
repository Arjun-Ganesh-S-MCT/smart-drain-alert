import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flowbeacon_app import citymap, history, ml, quiet, tamil, tiles, updater  # noqa: E402

BASE = {"flow": 4.2, "dist": 12.5, "turb": 850, "sf": 0.2, "sd": 0.2, "st": 30}


def row(label, flow, dist, turb, rain=0):
    return {"label": label, "flow": flow, "dist": dist, "turb": turb, "rain": rain}


class MlTest(unittest.TestCase):
    def test_train_predict(self):
        rows = [row("normal", 4.2 + i * 0.01, 12.5, 850) for i in range(20)] + [row("blocked", 1.5 + i * 0.01, 9.5, 1100) for i in range(20)]
        m = ml.train_nb([{"label": r["label"], "x": ml.features(r, BASE)} for r in rows])
        self.assertEqual(m["labels"], ["normal", "blocked"])
        self.assertEqual(ml.predict_nb(m, ml.features(row("", 4.2, 12.5, 850), BASE))["label"], "normal")
        self.assertEqual(ml.predict_nb(m, ml.features(row("", 1.6, 9.4, 1090), BASE))["label"], "blocked")
        self.assertGreater(ml.accuracy(m, [{"label": r["label"], "x": ml.features(r, BASE)} for r in rows]), 0.95)
        h = ml.header(m, BASE)
        self.assertIn("ML_N=2", h)
        self.assertIn('"normal","blocked"', h)

    def test_csv(self):
        txt = "time,label,flow,dist,turb,rain,condition\n2026-01-01T00:00:00,normal,4.2,12.5,850,0,Normal\n2026-01-01T00:00:01,normal,x,12.5,850,0,Normal\n"
        r = ml.parse_csv(txt, "file")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["label"], "normal")
        self.assertEqual(ml.parse_csv("a,b\n1,2", "x"), [])


class HistoryTest(unittest.TestCase):
    def test_buckets_and_group(self):
        with tempfile.TemporaryDirectory() as t:
            h = history.History(os.path.join(t, "h.db"))
            t0 = 1_700_000_000_000
            for i in range(120):
                h.add("drain-1", {"flow": 4, "dist": 12, "turb": 800, "rain": 0}, 2 if i == 70 else 0, now_ms=t0 + i * 1000)
            h.flush_all()
            rows = h.range("drain-1", t0 - 120000, t0 + 10 * 60000)
            self.assertEqual(sum(r["n"] for r in rows), 120)
            self.assertEqual(max(r["lvl"] for r in rows), 2)
            g = history.group(rows, 1)
            self.assertEqual(sum(x["n"] for x in g), 120)
            self.assertIn("node,time", history.csv_text(rows))
            h.close()


class CityTest(unittest.TestCase):
    def live(self, lvl, rx):
        return [{"id": "drain-1", "name": "Drain 1", "lvl": lvl, "rx": rx, "last": {"dist": 5}, "base": BASE}]

    def test_incident_flow(self):
        b = citymap.CityBook({})
        now = citymap.now_ms()
        st = b.states(self.live(2, now), now)[0]
        self.assertEqual(st["status"], "blockage")
        self.assertTrue(b.track(st))
        self.assertEqual(len(b.d["incidents"]), 1)
        self.assertEqual(b.assign("drain-1", "", 2), "Choose a maintenance team first.")
        self.assertEqual(b.assign("drain-1", "Team A", 2), "")
        self.assertEqual(b.open_inc("drain-1")["status"], "assigned")
        b.start_work("drain-1")
        self.assertEqual(b.open_inc("drain-1")["status"], "progress")
        b.resolve("drain-1")
        self.assertIsNone(b.open_inc("drain-1"))

    def test_auto_close_and_offline(self):
        b = citymap.CityBook({})
        now = citymap.now_ms()
        b.track(b.states(self.live(3, now), now)[0])
        for _ in range(3):
            b.track(b.states(self.live(0, now), now)[0])
        self.assertIsNone(b.open_inc("drain-1"))
        self.assertEqual(b.states(self.live(0, now - 60000), now)[0]["status"], "offline")

    def test_pin_and_devices(self):
        b = citymap.CityBook({})
        self.assertIn("at least", b.set_pin("12"))
        b.set_pin("abcd")
        b.unlocked = False
        self.assertTrue(b.locked)
        self.assertFalse(b.try_unlock("zzzz"))
        self.assertTrue(b.try_unlock("abcd"))
        did = b.add_device("North 1")
        self.assertTrue(b.edit_device(did, "North", "Ward 1", "Zone 1", 13.1, 80.3))
        self.assertFalse(b.edit_device(did, "North", "", "", 99, 80))
        pos = citymap.CityBook.project(b.states([]), 300, 200)
        self.assertIn(did, pos)


class MiscTest(unittest.TestCase):
    def test_quiet(self):
        q = {"on": True, "from": "22:00", "to": "06:00"}
        self.assertTrue(quiet.in_quiet(q, datetime(2026, 1, 1, 23, 0)))
        self.assertTrue(quiet.in_quiet(q, datetime(2026, 1, 1, 5, 59)))
        self.assertFalse(quiet.in_quiet(q, datetime(2026, 1, 1, 12, 0)))
        self.assertFalse(quiet.in_quiet({"on": False}, datetime(2026, 1, 1, 23, 0)))

    def test_tamil_and_version(self):
        self.assertEqual(tamil.trans("Sound", "en"), "Sound")
        self.assertNotEqual(tamil.trans("Sound", "ta"), "Sound")
        self.assertGreater(updater.cmp("2.1.0", "2.0.9"), 0)
        self.assertEqual(updater.cmp("2.0.5", "2.0.5"), 0)


class TilesTest(unittest.TestCase):
    def test_round_trip_and_fit(self):
        x, y = tiles.world(13.0827, 80.2707, 12)
        lat, lng = tiles.unworld(x, y, 12)
        self.assertAlmostEqual(lat, 13.0827, 4)
        self.assertAlmostEqual(lng, 80.2707, 4)
        self.assertEqual(tiles.world(0, 0, 1), (1.0, 1.0))
        z, la, lo = tiles.fit_zoom([(13.04, 80.21), (13.09, 80.27)], 800, 400)
        self.assertTrue(10 <= z <= 14)
        self.assertEqual(tiles.fit_zoom([], 800, 400)[0], 12)

    def test_level_sensor_and_nano_json(self):
        from flowbeacon_app import core
        self.assertEqual(core.level_of(15), 0)
        self.assertEqual(core.level_of(3), 3)
        self.assertEqual(core.dist_from_lv(2), 7.0)
        # the Nano sketch's own line
        d = core.normalize({"device": "flow-beacon-arduino", "flow_l_min": 3.5, "water_level_percent": 66, "level_low_wet": True,
                            "level_mid_wet": True, "level_high_wet": False, "turbidity_raw": 800, "rain_wet": True})
        self.assertEqual(d["flow"], 3.5)
        self.assertEqual(d["lv"], 2)
        self.assertEqual(d["dist"], 7.0)
        self.assertEqual(d["rain"], 1)
        self.assertEqual(d["turb"], (1023 - 800) * 4.0)
        d2 = core.normalize({"flow_l_min": 0, "water_level_percent": 100, "turbidity_raw": 1000, "rain_wet": False})
        self.assertEqual(d2["lv"], 3)
        self.assertEqual(d2["rain"], 0)
        # risk and overflow defaults match the mid and high probe
        r = core.evaluate({"flow": 4.2, "dist": 7.0, "turb": 892, "rain": 0}, False, {"flow": 4.2, "dist": 11.0, "turb": 892, "sf": .2, "sd": .2, "st": 30}, core.DEF)
        self.assertEqual(r["lvl"], 3)
        r = core.evaluate({"flow": 4.2, "dist": 3.0, "turb": 892, "rain": 0}, False, {"flow": 4.2, "dist": 11.0, "turb": 892, "sf": .2, "sd": .2, "st": 30}, core.DEF)
        self.assertEqual(r["lvl"], 4)

if __name__ == "__main__":
    unittest.main()
