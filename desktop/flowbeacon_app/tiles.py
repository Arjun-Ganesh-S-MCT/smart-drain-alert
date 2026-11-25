"""Map tiles from OpenStreetMap (free, no key, no browser). Pure Python: tile maths and a small threaded downloader with a disk cache.
Please keep the User-Agent and the credit line: it is part of the OpenStreetMap tile usage policy."""
import math
import queue
import threading
import urllib.request
from pathlib import Path

UA = "FlowBeacon/2.0.2 (+https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert)"
URL = "https://tile.openstreetmap.org/%d/%d/%d.png"
CREDIT = "© OpenStreetMap contributors"
MIN_Z, MAX_Z = 2, 18


def world(lat, lng, z):
    """Latitude/longitude to tile units at zoom z (a float zoom is fine)."""
    n = 2.0 ** z
    lat = max(-85.0511, min(85.0511, lat))
    x = (lng + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def unworld(x, y, z):
    n = 2.0 ** z
    lng = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    return lat, lng


def fit_zoom(points, w, h, pad=60, tile=256):
    """Highest zoom (a whole number) at which all points fit in a w x h view."""
    if not points:
        return 12, 13.0827, 80.2707
    la = [p[0] for p in points]
    lo = [p[1] for p in points]
    clat, clng = (min(la) + max(la)) / 2, (min(lo) + max(lo)) / 2
    for z in range(MAX_Z, MIN_Z - 1, -1):
        xs = [world(a, b, z) for a, b in points]
        if (max(x for x, _ in xs) - min(x for x, _ in xs)) * tile <= w - 2 * pad and (max(y for _, y in xs) - min(y for _, y in xs)) * tile <= h - 2 * pad:
            return min(z, 17), clat, clng
    return MIN_Z, clat, clng


class TileCache:
    """get(z, x, y) returns the cached file path or None and starts a background download. `on_ready` runs in a worker thread."""

    def __init__(self, folder, on_ready=None, workers=3):
        self.dir = Path(folder)
        self.on_ready = on_ready
        self.q = queue.Queue()
        self.pending = set()
        self.failed = {}
        self.lock = threading.Lock()
        for _ in range(workers):
            threading.Thread(target=self._work, daemon=True).start()

    def path(self, z, x, y):
        return self.dir / str(z) / str(x) / ("%d.png" % y)

    def get(self, z, x, y):
        n = 2 ** z
        if y < 0 or y >= n:
            return None
        x %= n
        p = self.path(z, x, y)
        if p.exists():
            return p
        key = (z, x, y)
        with self.lock:
            import time
            if key in self.pending or time.time() < self.failed.get(key, 0):
                return None
            self.pending.add(key)
        self.q.put(key)
        return None

    def _work(self):
        import time
        while True:
            z, x, y = self.q.get()
            p = self.path(z, x, y)
            try:
                req = urllib.request.Request(URL % (z, x, y), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = r.read()
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(p)
                if self.on_ready:
                    self.on_ready()
            except Exception:  # noqa: BLE001 - offline or blocked: try again in a while
                self.failed[(z, x, y)] = time.time() + 30
            finally:
                with self.lock:
                    self.pending.discard((z, x, y))
