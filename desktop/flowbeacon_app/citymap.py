"""City drainage map data and dispatch workflow (port of src/map.js, without the Leaflet drawing). No Qt here."""
import hashlib
import math
import random
import time

STALE_MS = 30000
CENTER = [13.0827, 80.2707]
STAT = {"normal": "Normal", "possible": "Possible blockage", "blockage": "Blockage detected", "overflow": "Overflow warning", "offline": "Offline"}
STAT_COLOR = {"normal": "#22b573", "possible": "#e6b800", "blockage": "#e8761f", "overflow": "#c0143c", "offline": "#8a8a8a"}
LVLN = ["Normal", "Possible blockage", "Blockage warning", "Overflow risk", "Overflow detected"]
INC_ST = {"open": "Open", "assigned": "Assigned", "progress": "In progress", "resolved": "Resolved"}
DEMO = {
    "demo-2": {"lat": 13.0850, "lng": 80.2101, "ward": "Ward 34", "zone": "Zone 5", "name": "Anna Nagar 2nd Ave (demo)"},
    "demo-3": {"lat": 13.0418, "lng": 80.2341, "ward": "Ward 57", "zone": "Zone 8", "name": "T. Nagar Usman Rd (demo)"},
}


def now_ms():
    return int(time.time() * 1000)


def pin_hash(salt, pin):
    return hashlib.sha256((salt + pin).encode("utf8")).hexdigest()


class CityBook:
    """Everything the map remembers. `d` is a plain dict kept inside the settings file, so it saves with the rest."""

    def __init__(self, d):
        self.d = d
        for k, v in (("devices", {}), ("teams", ["Team A", "Team B", "Team C"]), ("incidents", []), ("hide", {}),
                     ("officer", ""), ("pin", None), ("salt", ""), ("center", list(CENTER))):
            self.d.setdefault(k, v)
        self.normal_count = {}
        self.unlocked = False

    # ---- devices ----
    def auto_place(self, did):
        if did in DEMO:
            return dict(DEMO[did], placed=True)
        h = 0
        for ch in did:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        a = math.radians(h % 360)
        r = 0.004 + ((h >> 9) % 100) / 100 * 0.02
        c = self.d["center"]
        return {"lat": round(c[0] + math.sin(a) * r, 5), "lng": round(c[1] + math.cos(a) * r, 5), "ward": "", "zone": "", "name": "", "placed": False}

    def ensure(self, did):
        if self.d["hide"].get(did):
            return None
        if did not in self.d["devices"]:
            self.d["devices"][did] = self.auto_place(did)
        return self.d["devices"][did]

    def states(self, live, now=None):
        """live: list of {"id","name","lvl","rx"(ms),"last","base"} from the node book."""
        now = now_ms() if now is None else now
        by = {n["id"]: n for n in live}
        for did in by:
            self.ensure(did)
        out = []
        for did, dv in self.d["devices"].items():
            if self.d["hide"].get(did):
                continue
            n = by.get(did)
            rx = n["rx"] if n else 0
            online = bool(rx) and now - rx < STALE_MS
            lvl = n["lvl"] if n and online else 0
            status = "offline" if not online else ["normal", "possible", "blockage", "overflow", "overflow"][lvl]
            out.append({"id": did, "dv": dv, "lvl": lvl, "status": status, "online": online, "rx": rx,
                        "last": n["last"] if n else None, "base": n.get("base") if n else None,
                        "name": (n["name"] if n else did)})
        return out

    @staticmethod
    def label(st):
        return st["dv"]["name"] or (st["name"] if st["name"] != st["id"] else st["id"])

    def wards(self, states):
        return sorted({s["dv"].get("ward") or "Unassigned" for s in states})

    def zones(self, states):
        return sorted({s["dv"].get("zone") or "Unassigned" for s in states})

    @staticmethod
    def passes(st, ward="", zone="", status=""):
        return ((not ward or (st["dv"].get("ward") or "Unassigned") == ward) and
                (not zone or (st["dv"].get("zone") or "Unassigned") == zone) and
                (not status or st["status"] == status))

    def add_device(self, did):
        did = did.strip()[:40]
        if not did:
            return None
        self.d["hide"].pop(did, None)
        if did not in self.d["devices"]:
            self.d["devices"][did] = self.auto_place(did)
        return did

    def edit_device(self, did, name, ward, zone, lat, lng):
        dv = self.d["devices"].get(did)
        if not dv or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return False
        dv.update({"name": name.strip(), "ward": ward.strip(), "zone": zone.strip(), "lat": lat, "lng": lng, "placed": True})
        return True

    def remove_device(self, did):
        self.d["hide"][did] = 1

    # ---- incidents ----
    def open_inc(self, did):
        return next((i for i in self.d["incidents"] if i["dev"] == did and i["status"] != "resolved"), None)

    @staticmethod
    def add_log(inc, msg):
        inc["log"].append({"t": now_ms(), "m": msg})

    def new_inc(self, did, lvl):
        i = {"id": "I%x%04x" % (now_ms(), random.randint(0, 0xFFFF)), "dev": did, "level": lvl, "max": lvl, "start": now_ms(),
             "status": "open", "team": "", "log": []}
        self.add_log(i, "Detected: " + LVLN[lvl])
        self.d["incidents"].insert(0, i)
        del self.d["incidents"][500:]
        return i

    def track(self, st):
        """Called for every reading of a drain: opens, escalates and auto-closes incidents. Returns True when something changed."""
        if not st["online"]:
            return False
        did, lvl, inc = st["id"], st["lvl"], self.open_inc(st["id"])
        if lvl >= 2:
            self.normal_count[did] = 0
            if not inc:
                self.new_inc(did, lvl)
                return True
            if lvl != inc["level"]:
                inc["level"] = lvl
                if lvl > inc["max"]:
                    inc["max"] = lvl
                    self.add_log(inc, "Escalated: " + LVLN[lvl])
                return True
        elif lvl == 0 and inc:
            self.normal_count[did] = self.normal_count.get(did, 0) + 1
            if self.normal_count[did] >= 3:
                inc.update({"status": "resolved", "end": now_ms(), "by": "Sensor (back to normal)"})
                self.add_log(inc, "Sensor reads normal: closed automatically")
                return True
        else:
            self.normal_count[did] = 0
        return False

    def officer(self):
        return self.d["officer"] or "Official"

    def assign(self, did, team, lvl):
        if not team:
            return "Choose a maintenance team first."
        inc = self.open_inc(did)
        if not inc:
            if lvl < 1:
                return "Nothing to assign for this drain."
            inc = self.new_inc(did, lvl)
        inc.update({"team": team, "status": "assigned", "assigned": now_ms()})
        self.add_log(inc, "Assigned to %s by %s" % (team, self.officer()))
        return ""

    def start_work(self, did):
        i = self.open_inc(did)
        if i:
            i["status"] = "progress"
            self.add_log(i, "Work started by " + (i["team"] or "team"))

    def resolve(self, did):
        i = self.open_inc(did)
        if i:
            i.update({"status": "resolved", "end": now_ms(), "by": self.officer()})
            self.add_log(i, "Marked resolved by " + self.officer())

    def add_team(self, name):
        name = name.strip()
        if name and name not in self.d["teams"]:
            self.d["teams"].append(name)
            return True
        return False

    def remove_team(self, idx):
        if 0 <= idx < len(self.d["teams"]):
            del self.d["teams"][idx]

    # ---- officials PIN (a convenience lock kept on this computer) ----
    def set_pin(self, pin):
        if len(pin) < 4:
            return "PIN must be at least 4 characters."
        self.d["salt"] = "%x" % random.getrandbits(48)
        self.d["pin"] = pin_hash(self.d["salt"], pin)
        self.unlocked = True
        return "PIN set. It will be asked each time the app starts."

    def clear_pin(self):
        self.d["pin"] = None
        return "PIN removed."

    def try_unlock(self, pin):
        if pin_hash(self.d["salt"], pin) == self.d["pin"]:
            self.unlocked = True
        return self.unlocked

    @property
    def locked(self):
        return bool(self.d["pin"]) and not self.unlocked

    # ---- schematic projection (no map tiles are needed) ----
    @staticmethod
    def project(states, w, h, pad=28):
        pts = [(s["dv"]["lat"], s["dv"]["lng"]) for s in states]
        if not pts:
            return {}
        la = [p[0] for p in pts]
        lo = [p[1] for p in pts]
        mnla, mxla, mnlo, mxlo = min(la), max(la), min(lo), max(lo)
        dla, dlo = max(mxla - mnla, 0.004), max(mxlo - mnlo, 0.004)
        sc = min((w - 2 * pad) / dlo, (h - 2 * pad) / dla)
        cx, cy = (mnlo + mxlo) / 2, (mnla + mxla) / 2
        return {s["id"]: (w / 2 + (s["dv"]["lng"] - cx) * sc, h / 2 - (s["dv"]["lat"] - cy) * sc) for s in states}
