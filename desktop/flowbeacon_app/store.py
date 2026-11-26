"""Settings and incident history, saved as JSON in the user's app-data folder."""
import hashlib
import json
import os
from pathlib import Path

from .core import DEF

SALT = "fb-dev:"


def data_dir():
    base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    p = Path(base) / "FlowBeacon"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pw_hash(p):
    return hashlib.sha256((SALT + p).encode("utf8")).hexdigest()


DEFAULT_PW_HASH = pw_hash("1234")


class Store:
    FILE = "settings.json"

    def __init__(self):
        self.path = data_dir() / self.FILE
        self.d = {"cfg": dict(DEF), "base": None, "inc": [], "vol": 0.6, "mute": False, "drip": True,
                  "role": "", "ip": "", "ssid": "", "devpw": "", "sms": {"on": False, "nums": "", "min": 3, "cool": 5},
                  "accent": "coral", "mode": "light", "calm": False, "node": "Drain 1",
                  "snd": {"ui": True, "possible": True, "warning": True, "risk": True, "overflow": True, "rain": True, "predict": True},
                  "lang": "en", "zoom": 1.0, "notify": True, "tray": False, "upd": True,
                  "quiet": {"on": False, "from": "22:00", "to": "06:00", "smsMin": 3},
                  "profiles": [], "model": None, "useModel": False, "nodes": {}, "map": {}}
        try:
            self.d.update(json.loads(self.path.read_text(encoding="utf8")))
        except (OSError, ValueError):
            pass
        self.d["cfg"] = {**DEF, **self.d.get("cfg", {})}
        if self.d["cfg"].get("risk") == 4 and self.d["cfg"].get("over") == 2:      # old defaults were for the ultrasonic sensor
            self.d["cfg"]["risk"], self.d["cfg"]["over"] = DEF["risk"], DEF["over"]
        self.d["quiet"] = {"on": False, "from": "22:00", "to": "06:00", "smsMin": 3, **(self.d.get("quiet") or {})}
        self.d["snd"] = {"ui": True, "possible": True, "warning": True, "risk": True, "overflow": True, "rain": True, "predict": True, **self.d.get("snd", {})}

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        self.d[k] = v

    def save(self):
        try:
            tmp = self.path.with_suffix(".tmp")
            d = dict(self.d)
            m = dict(d.get("map") or {})            # demo drains are never saved
            m["devices"] = {k: v for k, v in (m.get("devices") or {}).items() if not k.startswith("demo-")}
            m["incidents"] = [i for i in (m.get("incidents") or []) if not str(i.get("dev", "")).startswith("demo-")]
            d["map"] = m
            tmp.write_text(json.dumps(d), encoding="utf8")
            tmp.replace(self.path)
        except OSError:
            pass
