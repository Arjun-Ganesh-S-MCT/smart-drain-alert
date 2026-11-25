"""Quiet hours: no sound, notification or low-level SMS inside the window (overflow always gets through)."""
from datetime import datetime


def _m(x):
    p = str(x).split(":")
    try:
        return int(p[0]) * 60 + (int(p[1]) if len(p) > 1 else 0)
    except ValueError:
        return 0


def in_quiet(q, now=None):
    if not q or not q.get("on"):
        return False
    n = now or datetime.now()
    c, a, b = n.hour * 60 + n.minute, _m(q.get("from", "22:00")), _m(q.get("to", "06:00"))
    return (a <= c < b) if a <= b else (c >= a or c < b)
