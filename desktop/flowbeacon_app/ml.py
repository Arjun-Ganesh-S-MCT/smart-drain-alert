"""Learn from recordings: a small naive Bayes classifier, ported from src/core.js. No Qt here, so it is testable."""
import math

FLOORS = (0.05, 0.3, 0.05, 0.15)


def features(d, b):
    return [1 - d["flow"] / b["flow"] if b["flow"] > 0 else 0.0,
            b["dist"] - d["dist"],
            (d["turb"] - b["turb"]) / b["turb"] if b["turb"] > 0 else 0.0,
            1.0 if d.get("rain") else 0.0]


def train_nb(rows):
    """rows: [{"label": str, "x": [4 floats]}]"""
    labels = []
    for r in rows:
        if r["label"] not in labels:
            labels.append(r["label"])
    mean, std, prior = [], [], []
    for lab in labels:
        xs = [r["x"] for r in rows if r["label"] == lab]
        prior.append(len(xs) / len(rows))
        m, s = [], []
        for j in range(4):
            mu = sum(x[j] for x in xs) / len(xs)
            v = sum((x[j] - mu) ** 2 for x in xs) / len(xs)
            m.append(mu)
            s.append(max(math.sqrt(v), FLOORS[j]))
        mean.append(m)
        std.append(s)
    return {"labels": labels, "prior": prior, "mean": mean, "std": std, "n": len(rows)}


def predict_nb(m, x):
    lp = []
    for i in range(len(m["labels"])):
        s = math.log(m["prior"][i])
        for j in range(len(x)):
            sd = m["std"][i][j]
            z = (x[j] - m["mean"][i][j]) / sd
            s += -0.5 * z * z - math.log(sd)
        lp.append(s)
    mx = max(lp)
    ex = [math.exp(v - mx) for v in lp]
    tot = sum(ex)
    probs = [v / tot for v in ex]
    k = probs.index(max(probs))
    return {"label": m["labels"][k], "p": probs[k], "probs": probs}


def accuracy(m, rows):
    return sum(1 for r in rows if predict_nb(m, r["x"])["label"] == r["label"]) / len(rows) if rows else 0.0


def _num(v):
    t = ("%.5f" % v).rstrip("0").rstrip(".")
    return "0" if t in ("", "-0") else t


def header(m, b):
    f = lambda a: ",".join(_num(v) for v in a)  # noqa: E731
    return "\n".join([
        "#define HAS_MODEL 1",
        "const int ML_N=%d;" % len(m["labels"]),
        "const char* ML_LABELS[]={" + ",".join('"%s"' % "".join(c for c in l if c.isalnum() or c in " _-") for l in m["labels"]) + "};",
        "const float ML_PRIOR[]={" + f(m["prior"]) + "};",
        "const float ML_MEAN[][4]={" + ",".join("{" + f(r) + "}" for r in m["mean"]) + "};",
        "const float ML_STD[][4]={" + ",".join("{" + f(r) + "}" for r in m["std"]) + "};",
        "const float BASE_FLOW=%.3f,BASE_DIST=%.3f,BASE_TURB=%.1f;" % (b["flow"], b["dist"], b["turb"]),
        ""])


def parse_csv(text, default_label=""):
    lines = [l for l in text.replace("\r", "").split("\n") if l]
    if len(lines) < 2:
        return []
    h = [x.strip().lower().replace('"', "") for x in lines[0].split(",")]
    ix = lambda n: h.index(n) if n in h else -1  # noqa: E731
    if ix("flow") < 0 or ix("dist") < 0 or ix("turb") < 0:
        return []
    out = []
    for l in lines[1:]:
        c = [x.replace('"', "") for x in l.split(",")]
        try:
            lab = c[ix("label")] if ix("label") >= 0 and ix("label") < len(c) else ""
            rain = 0
            if ix("rain") >= 0 and ix("rain") < len(c):
                try:
                    rain = 1 if float(c[ix("rain")]) else 0
                except ValueError:
                    rain = 0
            out.append({"label": lab or default_label, "flow": float(c[ix("flow")]), "dist": float(c[ix("dist")]),
                        "turb": float(c[ix("turb")]), "rain": rain})
        except (ValueError, IndexError):
            continue
    return out
