"""Update check: asks GitHub for the latest release and compares it with this version. No Qt here."""
import json
import urllib.request

VERSION = "2.0.3"
REPO = "Arjun-Ganesh-S-MCT/smart-drain-alert"


def cmp(a, b):
    x = [int(p) if p.isdigit() else 0 for p in str(a).split(".")]
    y = [int(p) if p.isdigit() else 0 for p in str(b).split(".")]
    for i in range(3):
        d = (x[i] if i < len(x) else 0) - (y[i] if i < len(y) else 0)
        if d:
            return d
    return 0


def check(timeout=8):
    try:
        req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % REPO,
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "FlowBeacon"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf8"))
        latest = str(j.get("tag_name", "")).lstrip("v")
        url = str(j.get("html_url", ""))
        if not url.startswith("https://github.com/"):
            url = "https://github.com/%s/releases/latest" % REPO
        return {"current": VERSION, "latest": latest, "newer": bool(latest) and cmp(latest, VERSION) > 0, "url": url}
    except Exception as e:  # noqa: BLE001 - any network problem just means "could not check"
        return {"current": VERSION, "error": str(e)[:120]}
