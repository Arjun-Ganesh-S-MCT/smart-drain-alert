import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flowbeacon_app import core, drip_core  # noqa: E402


class CoreMatchesJavaScript(unittest.TestCase):
    """fixtures.json was produced by running the original src/core.js on 400 random readings."""

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__), "fixtures.json"), encoding="utf8") as f:
            self.rows = json.load(f)

    def test_health_and_evaluate(self):
        for row in self.rows:
            issues, bad = core.health_full(row["d"], [], row["base"])
            self.assertEqual(bad, row["bad"])
            self.assertEqual(issues, [i.replace("Ultrasonic reading out of range", "Water level sensor reading out of range").replace("Ultrasonic value is not changing", "Water level has not changed for a long time") for i in row["issues"]])
            r = core.evaluate(row["d"], bad, row["base"], row["cfg"])
            e = row["r"]
            self.assertEqual(r["lvl"], e["lvl"], row)
            self.assertEqual(r["cause"], e["cause"])
            self.assertEqual(r["conf"], e["conf"])
            self.assertEqual(r["ev"], e["ev"], row)

    def test_eta(self):
        for row in self.rows:
            got = core.predict_eta(row["hist"], row["cfg"]["over"])
            if row["eta"] is None:
                self.assertIsNone(got)
            else:
                self.assertTrue(math.isclose(got, row["eta"], rel_tol=1e-9))


class DripChat(unittest.TestCase):
    def test_actions(self):
        self.assertEqual(drip_core.reply("set baseline", {})[1], "baseline")
        self.assertEqual(drip_core.reply("start demo", {})[1], "demo")
        self.assertIn("No readings", drip_core.reply("status", {"nodes": []})[0])
        self.assertEqual(drip_core.reply("hello", {})[0], "Hello. Ask me for the status any time.")


if __name__ == "__main__":
    unittest.main()
