"""App logic: turns readings into conditions, incidents, sounds and Drip reactions (port of the old index.html logic)."""
import time
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from . import core
from .core import ICONS, LEVELS

WZ_STEPS = ["Normal flow, valve fully open", "Partial valve, about half closed", "Valve mostly closed", "Wet the rain plate"]


class Engine(QObject):
    updated = Signal(dict)
    incidents_changed = Signal()
    message = Signal(str)
    say = Signal(str, int)
    flash = Signal(str, int, str)
    config_changed = Signal()
    wizard_changed = Signal()
    banner = Signal(bool, str)

    def __init__(self, store, link, sound):
        super().__init__()
        self.s, self.link, self.snd = store, link, sound
        self.hist, self.last_lvl, self.acked = [], 0, False
        self.cal_buf = None
        self.wz = {"on": False, "step": 0, "res": [], "buf": None, "sug": None}
        self.last_rx, self.prev_rain, self.pred_warn, self.drip_fault = 0.0, 0, False, False
        self.sms_last, self.sms_last_lvl = 0.0, 0
        self.last = None
        self.rec = None            # list of rows while Test recording is running
        link.data.connect(self.on_data)

    # ---- helpers ----
    @property
    def cfg(self):
        return self.s["cfg"]

    @property
    def base(self):
        return self.s["base"]

    def set_cfg(self, k, v):
        self.cfg[k] = v
        self.s.save()

    def reset_cfg(self):
        self.s["cfg"] = dict(core.DEF)
        self.s.save()
        self.config_changed.emit()

    def _mean(self, rows, k):
        return sum(x[k] for x in rows) / len(rows)

    # ---- calibration ----
    def start_baseline(self):
        if not self.link.connected and not self.link.demo:
            self.message.emit("Connect the board or start demo mode first.")
            return
        self.cal_buf = []
        self.link.cal_pending = True
        self.message.emit("Setting baseline… keep normal flow.")

    def _finish_baseline(self, rows):
        self.s["base"] = core.base_from(rows)
        self.s.save()
        self.snd.play("baseline")
        self.flash.emit("cheer", 2500, "Baseline saved!")

    def wizard_start(self):
        self.wz = {"on": True, "step": 0, "res": [], "buf": None, "sug": None}
        self.link.cal_pending = self.cal_buf is not None
        self.wizard_changed.emit()

    def wizard_record(self):
        if not self.link.connected and not self.link.demo:
            self.message.emit("Connect the board or start demo mode first.")
            return
        self.wz["buf"] = []
        self.link.cal_pending = True
        self.wizard_changed.emit()

    def wizard_apply(self):
        if self.wz["sug"]:
            self.cfg.update(self.wz["sug"])
            self.s.save()
            self.config_changed.emit()
            self.message.emit("Suggested thresholds applied.")

    def _wz_data(self, d):
        wz = self.wz
        wz["buf"].append(d)
        if len(wz["buf"]) < 10:
            return
        b = wz["buf"]
        wz["res"].append({"flow": self._mean(b, "flow"), "dist": self._mean(b, "dist"), "turb": self._mean(b, "turb"), "rain": self._mean(b, "rain")})
        if wz["step"] == 0:
            self._finish_baseline(b)
        wz["buf"] = None
        wz["step"] += 1
        self.link.cal_pending = self.cal_buf is not None
        if wz["step"] >= len(WZ_STEPS):
            n, p, hv = wz["res"][:3]
            wz["sug"] = {"dropWarn": max(10, round((1 - p["flow"] / n["flow"]) * 50)),
                         "dropBlock": max(30, round((1 - hv["flow"] / n["flow"]) * 70)),
                         "rise": max(0.5, round((n["dist"] - p["dist"]) * 5) / 10)}
        self.snd.play("baseline")
        self.flash.emit("cheer", 2500, "Step saved!")
        self.wizard_changed.emit()

    # ---- incoming data ----
    def on_data(self, raw):
        d = {"flow": float(raw.get("flow") or 0), "dist": float(raw.get("dist") or 0),
             "turb": float(raw.get("turb") or 0), "rain": 1 if raw.get("rain") else 0}
        self.last_rx = time.time()
        if self.cal_buf is not None:
            self.cal_buf.append(d)
            self.message.emit("Setting baseline… %d/10" % len(self.cal_buf))
            if len(self.cal_buf) >= 10:
                self._finish_baseline(self.cal_buf)
                self.cal_buf = None
                self.link.cal_pending = self.wz["buf"] is not None
                self.message.emit("Baseline saved. Keep the valve fully open.")
        if self.wz["buf"] is not None:
            self._wz_data(d)
        issues, bad = core.health_full(d, self.hist, self.base)
        r = core.evaluate(d, bad, self.base, self.cfg)
        name, color, sev = LEVELS[r["lvl"]]
        if d["rain"] and not self.prev_rain:
            self.snd.play("rain")
            self.say.emit("Rain detected.", 4500)
        self.prev_rain = d["rain"]
        eta = core.predict_eta(self.hist, self.cfg["over"])
        pred = ""
        if eta and eta < 1800:
            pred = "Prediction: overflow in about " + ("%d s" % round(eta) if eta < 90 else "%.1f min" % (eta / 60)) + " at the current rate"
            if eta < 180 and not self.pred_warn:
                self.pred_warn = True
                self.snd.play("predict")
                self.say.emit("Overflow predicted in about %d min." % max(1, round(eta / 60)), 4500)
        else:
            self.pred_warn = False
        if r["lvl"] > self.last_lvl:
            self.s["inc"].insert(0, {"time": datetime.now().isoformat(timespec="seconds"), "cond": name, "cause": r["cause"],
                                     "ev": "; ".join(r["ev"]), "sev": sev, "conf": r["conf"], "lvl": r["lvl"], "c": color})
            del self.s["inc"][200:]
            self.s.save()
            self.incidents_changed.emit()
            self.acked = False
            self.snd.play(["", "possible", "warning", "risk", "overflow"][r["lvl"]])
            self._maybe_sms(r, name)
        elif r["lvl"] == 0 and self.last_lvl > 0:
            self.snd.play("normal")
            self.sms_last_lvl = 0
            self.flash.emit("cheer", 2500, "Back to normal!")
        self.last_lvl = r["lvl"]
        if self.rec is not None:
            self.rec.append([datetime.now().isoformat(timespec="seconds"), d["flow"], d["dist"], d["turb"], d["rain"], name])
        self.hist.append({"t": time.time() * 1000, "f": d["flow"], "l": d["dist"]})
        del self.hist[:-900]
        self.drip_fault = bad or any(k in x for x in issues for k in ("not changing", "frozen", "limit"))
        show = r["lvl"] >= 3 and not self.acked
        self.banner.emit(show, "%s: %s" % (name, r["cause"]) if show else "")
        self.last = {"d": d, "r": r, "name": name, "color": color, "sev": sev, "issues": issues, "pred": pred, "bad": bad,
                     "icon": ICONS[r["lvl"]]}
        self.updated.emit(self.last)

    def acknowledge(self):
        self.acked = True
        self.banner.emit(False, "")

    def repeat_alarm(self):
        if self.last_lvl >= 3 and not self.acked:
            self.snd.play("overflow" if self.last_lvl == 4 else "risk", True)

    # ---- Drip ----
    def drip_state(self):
        if not self.link.demo and (not self.link.connected or time.time() - self.last_rx > 5):
            return "sleep"
        if self.drip_fault:
            return "dizzy"
        if self.last_lvl >= 4: return "panic"
        if self.last_lvl == 3: return "alarmed"
        if self.last_lvl == 2: return "worried"
        if self.last_lvl == 1: return "curious"
        if self.cal_buf is not None or self.wz["buf"] is not None:
            return "think"
        return "idle"

    def chat_ctx(self):
        l = self.last
        nodes = [("Drain", "%s %s" % (l["icon"], l["name"]))] if l and time.time() - self.last_rx < 30 else []
        return {"worst": self.last_lvl, "nodes": nodes, "cause": l["r"]["cause"] if l else "",
                "evid": "; ".join(l["r"]["ev"]) if l else "", "pred": l["pred"] if l else ""}

    # ---- SMS through the board ----
    def sms_numbers(self):
        return [n for n in (core.norm_num(x.strip()) for x in self.s["sms"]["nums"].split(",")) if n]

    def sms_send(self, text):
        nums = self.sms_numbers()
        if not nums:
            return "No valid mobile number"
        if not self.link.send({"cmd": "sms", "to": nums[0], "msg": text}):
            return "Not sent: board not connected"
        for n in nums[1:]:
            self.link.send({"cmd": "sms", "to": n, "msg": text})
        return "Sent to " + ", ".join(nums) + " via the board"

    def _maybe_sms(self, r, name):
        sm = self.s["sms"]
        if not sm["on"] or r["lvl"] < sm["min"]:
            return
        if time.time() - self.sms_last < sm["cool"] * 60 and r["lvl"] <= self.sms_last_lvl:
            return
        m = ("FlowBeacon: %s. %s. %s. %s" % (name, r["cause"], ", ".join(r["ev"]), datetime.now().strftime("%d/%m/%Y %H:%M")))
        m = "".join(ch for ch in m if 32 <= ord(ch) < 127)[:160]
        if self.sms_send(m).startswith("Sent"):
            self.sms_last, self.sms_last_lvl = time.time(), r["lvl"]
