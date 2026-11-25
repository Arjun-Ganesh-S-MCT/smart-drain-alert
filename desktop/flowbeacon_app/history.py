"""Stored sensor history: one averaged row per minute per drain, kept 90 days in a small SQLite file. No Qt here."""
import sqlite3
import time
from datetime import datetime, timezone


class History:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS mins (node TEXT, t INTEGER, n INTEGER, f REAL, l REAL, tb REAL, r REAL, lvl INTEGER, PRIMARY KEY (node, t))")
        self.db.commit()
        self.b = {}

    def add(self, node, d, lvl, now_ms=None):
        now = int(now_ms if now_ms is not None else time.time() * 1000)
        m = now // 60000 * 60000
        b = self.b.get(node)
        if b is None or b["t"] != m:
            self._flush(b)
            b = self.b[node] = {"node": node, "t": m, "n": 0, "f": 0.0, "l": 0.0, "tb": 0.0, "r": 0.0, "lvl": 0}
        b["n"] += 1
        b["f"] += float(d.get("flow") or 0)
        b["l"] += float(d.get("dist") or 0)
        b["tb"] += float(d.get("turb") or 0)
        b["r"] += 1 if d.get("rain") else 0
        b["lvl"] = max(b["lvl"], lvl)

    def _flush(self, b):
        if not b or not b["n"]:
            return
        n = b["n"]
        try:
            self.db.execute("INSERT OR REPLACE INTO mins VALUES (?,?,?,?,?,?,?,?)",
                            (b["node"], b["t"], n, b["f"] / n, b["l"] / n, b["tb"] / n, b["r"] / n, b["lvl"]))
            self.db.commit()
        except sqlite3.Error:
            pass

    def flush_all(self, older_than_ms=None):
        now = time.time() * 1000
        for b in list(self.b.values()):
            if older_than_ms is None or b["t"] < now - older_than_ms:
                self._flush(b)

    def range(self, node, a, b):
        self.flush_all(60000)
        cur = self.db.execute("SELECT node,t,n,f,l,tb,r,lvl FROM mins WHERE node=? AND t>=? AND t<=? ORDER BY t", (node, int(a), int(b)))
        return [dict(zip(("node", "t", "n", "f", "l", "tb", "r", "lvl"), r)) for r in cur.fetchall()]

    def prune(self, days=90):
        try:
            self.db.execute("DELETE FROM mins WHERE t<?", (int((time.time() - days * 86400) * 1000),))
            self.db.commit()
        except sqlite3.Error:
            pass

    def nodes(self):
        return [r[0] for r in self.db.execute("SELECT DISTINCT node FROM mins")]

    def close(self):
        self.flush_all()
        self.db.close()


def group(rows, days):
    """Hourly groups for a 1 day range, daily groups for longer ranges (same as the web History tab)."""
    hourly = days == 1
    grp = {}
    for r in rows:
        if hourly:
            k = r["t"] // 3600000 * 3600000
        else:
            k = int(datetime.fromtimestamp(r["t"] / 1000).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        g = grp.setdefault(k, {"t": k, "n": 0, "f": 0.0, "l": 0.0, "lmin": 1e9, "lmax": -1e9, "lvl": 0})
        g["n"] += r["n"]
        g["f"] += r["f"] * r["n"]
        g["l"] += r["l"] * r["n"]
        g["lmin"] = min(g["lmin"], r["l"])
        g["lmax"] = max(g["lmax"], r["l"])
        g["lvl"] = max(g["lvl"], r["lvl"])
    out = []
    for k in sorted(grp):
        g = grp[k]
        g["f"] /= g["n"]
        g["l"] /= g["n"]
        out.append(g)
    return out


def csv_text(rows):
    head = "node,time,minutes,avg_flow,avg_dist,avg_turb,rain_fraction,worst_level"
    return "\n".join([head] + ["%s,%s,%d,%.3f,%.2f,%.0f,%.2f,%d" % (r["node"], datetime.fromtimestamp(r["t"] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                                     r["n"], r["f"], r["l"], r["tb"], r["r"], r["lvl"]) for r in rows])
