"""Analysis core: a line-for-line port of src/core.js (blockage and overflow evaluation). No Qt here, so it is testable."""
import math

DEF = {"dropWarn": 25, "dropBlock": 50, "rise": 1, "risk": 4, "over": 2, "turb": 30}
LEVELS = [
    ("Normal", "#22b573", "None"),
    ("Possible blockage", "#e6b800", "Low"),
    ("Blockage warning", "#e8761f", "Medium"),
    ("Overflow risk", "#ef4444", "High"),
    ("Overflow detected", "#c0143c", "Critical"),
]
ICONS = ["✓", "?", "▲", "■", "✖"]


def conf(c):
    return {"dw": c["dropWarn"] / 100, "db": c["dropBlock"] / 100, "rise": c["rise"], "risk": c["risk"],
            "over": c["over"], "tb": c["turb"] / 100}


def health(d, hist):
    """hist: list of dicts with t (ms), f (flow), l (dist). Returns (issues, bad)."""
    r = hist[-20:]
    issues = []
    bad = d["dist"] <= 0 or d["dist"] > 600
    if bad:
        issues.append("Ultrasonic reading out of range, check wiring")
    if d["turb"] <= 0 or d["turb"] >= 4095:
        issues.append("Turbidity reading at its limit")
    if len(r) >= 20:
        if all(q["l"] == d["dist"] for q in r):
            issues.append("Ultrasonic value is not changing")
        if d["flow"] > 0 and all(q["f"] == d["flow"] for q in r):
            issues.append("Flow value is frozen")
    return issues, bad


def health_full(d, hist, base):
    issues, bad = health(d, hist)
    if base and d["flow"] == 0:
        issues.append("Flow is 0: blockage or sensor fault")
    return issues, bad


def predict_eta(hist, over):
    p = hist[-20:]
    if len(p) < 10:
        return None
    n, t0 = len(p), p[0]["t"]
    sx = sy = sxy = sxx = 0.0
    for q in p:
        x = (q["t"] - t0) / 1000
        sx += x; sy += q["l"]; sxy += x * q["l"]; sxx += x * x
    den = n * sxx - sx * sx
    if not den:
        return None
    m = (n * sxy - sx * sy) / den
    cur = p[-1]["l"]
    if m > -0.005 or cur <= over:
        return None
    return (cur - over) / -m


def evaluate(d, bad, b, cfg):
    c = conf(cfg)
    lvl = 0
    ev = []
    pts = 0
    fd = rise = td = z = 0.0
    cause = "No fault indicated"
    if b:
        fd = 1 - d["flow"] / b["flow"] if b["flow"] > 0 else 0
        rise = 0 if bad else b["dist"] - d["dist"]
        td = (d["turb"] - b["turb"]) / b["turb"] if b["turb"] > 0 else 0
        z = max(abs(d["flow"] - b["flow"]) / b["sf"], 0 if bad else abs(d["dist"] - b["dist"]) / b["sd"])
        if fd > 0.05:
            ev.append("Flow %d%% vs baseline" % round(-fd * 100))
        if rise > 0.2:
            ev.append("Level +%.1f cm" % rise)
        if abs(td) > 0.1:
            ev.append("Turbidity %s%d%%" % ("+" if td > 0 else "", round(td * 100)))
        if z > 3:
            ev.append("Anomaly %.1f σ" % z)
    if d["rain"]:
        ev.append("Rain plate wet")
    blk, rising, dirty = fd >= c["dw"], rise >= c["rise"], td >= c["tb"]
    if b:
        if blk and (rising or dirty):
            lvl = 1
        if fd >= c["db"] and rising:
            lvl = 2
        if z > 4 and fd > 0.1 and not lvl:
            lvl = 1
    if not bad:
        if d["dist"] <= c["risk"]:
            lvl = max(lvl, 3)
        if d["dist"] <= c["over"]:
            lvl = 4
    if blk and d["rain"]:
        cause = "Blockage and rainfall likely both contributing"
    elif blk:
        cause = "Likely blockage: flow falling" + (" while level rises" if rising else "")
    elif d["rain"] and rising:
        cause = "Rainfall likely contributing to rising level"
    elif lvl >= 3:
        cause = "Water level high; cause unclear"
    elif lvl:
        cause = "Unusual pattern against baseline"
    if blk:
        pts += 40 if fd >= c["db"] else 25
    if rising:
        pts += 25
    if dirty:
        pts += 15
    if d["rain"] and rising:
        pts += 10
    if lvl >= 3:
        pts += 15
    if z > 3:
        pts += 10
    return {"lvl": lvl, "ev": ev, "cause": cause, "conf": min(95, pts) if lvl else 0, "fd": fd, "rise": rise}


def base_from(rows):
    n = len(rows)
    def m(k): return sum(x[k] for x in rows) / n
    def sd(k, fl):
        mu = m(k)
        return max(math.sqrt(sum((x[k] - mu) ** 2 for x in rows) / n), fl)
    return {"flow": m("flow"), "dist": m("dist"), "turb": m("turb"),
            "sf": sd("flow", max(0.05, 0.05 * m("flow"))), "sd": sd("dist", 0.2), "st": sd("turb", 10)}


def norm_num(v):
    import re
    d = re.sub(r"[\s\-()]", "", str(v))
    if re.fullmatch(r"\d{10}", d):
        d = "+91" + d
    elif re.fullmatch(r"0\d{10}", d):
        d = "+91" + d[1:]
    elif re.fullmatch(r"91\d{10}", d):
        d = "+" + d
    return d if re.fullmatch(r"\+\d{10,15}", d) else None
