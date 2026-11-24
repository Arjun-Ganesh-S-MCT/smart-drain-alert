"""Generates the neumorphic shadow tiles (same look as the web CSS box-shadows) for every theme.
Run once:  python tools/make_assets.py   (needs Pillow). Output goes to both apps' asset folders.
Tiles are drawn at 2x so they stay sharp on high-density screens."""
import json
import math
import os
import shutil
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 2  # render scale

def T(bg, sd, sl, tx, mu, ac, on): return dict(bg=bg, sd=sd, sl=sl, tx=tx, mu=mu, ac=ac, on=on)
THEMES = {
    "coral": ("Coral", "#fc8068", T("#e0d9d3", "#bdb3ac", "#f4f0ea", "#6b625b", "#948a82", "#fc8068", "#ffffff"), T("#2f2a27", "#1f1b19", "#3f3935", "#e6ded8", "#a1958c", "#ff8f78", "#2a1f1c")),
    "blue": ("Blue", "#4f86c6", T("#d9dfe7", "#b3bccb", "#f2f5f9", "#4d5a6b", "#8793a3", "#4f86c6", "#ffffff"), T("#262b33", "#181c21", "#343b46", "#dde3ec", "#8f9bad", "#6aa3f0", "#13202f")),
    "green": ("Green", "#3f9a63", T("#d9e2da", "#b2c0b4", "#f1f6f2", "#4b5f50", "#84998a", "#3f9a63", "#ffffff"), T("#232b25", "#161c18", "#313b34", "#dbe6dd", "#8ea294", "#62c283", "#102014")),
    "purple": ("Purple", "#8a6bc9", T("#e0dbe7", "#bab3c8", "#f5f2f9", "#5b5270", "#928aa6", "#8a6bc9", "#ffffff"), T("#2a2631", "#1b1820", "#39343f", "#e4dff0", "#9d94b2", "#a78bfa", "#1c1230")),
    "red": ("Red", "#d9444f", T("#e6dada", "#c4b0b0", "#f7f0f0", "#6b4f4f", "#9b8484", "#d9444f", "#ffffff"), T("#2e2626", "#1e1818", "#3d3333", "#ecdddd", "#a99090", "#f06a73", "#2e1012")),
    "yellow": ("Yellow", "#e8b422", T("#e5e0d0", "#c4bda5", "#f7f4ea", "#655f48", "#968f74", "#e8b422", "#3b2f05"), T("#2d2a22", "#1e1c16", "#3b372d", "#ece6d2", "#a79f84", "#f5c542", "#2b2205")),
    "black": ("Black", "#2b2b2b", T("#dcdcdc", "#b8b8b8", "#f3f3f3", "#3a3a3a", "#7d7d7d", "#2b2b2b", "#ffffff"), T("#1c1c1c", "#0e0e0e", "#2a2a2a", "#e6e6e6", "#8a8a8a", "#f2f2f2", "#111111")),
}

# name: (shape, kind, radius, offset, blur, fixed body height / size)
#  n = 9-slice (any size) | h = 3-slice horizontally (fixed height) | c = fixed circle | f = fixed w x h
KINDS = {
    "card":    ("n", "raised", 18, 6, 14, None),   # .raised cards
    "inset":   ("n", "inset", 12, 5, 10, None),    # .inset panels, log, chart frames
    "pill36":  ("h", "raised", 18, 4, 9, 36),      # buttons
    "pill40":  ("h", "raised", 20, 4, 9, 40),      # toolbar buttons
    "pillin36": ("h", "inset", 18, 4, 8, 36),      # pressed / on buttons
    "pillin40": ("h", "inset", 20, 4, 8, 40),      # selects, pressed toolbar buttons
    "field40": ("h", "inset", 12, 4, 8, 40),       # text inputs
    "seg42":   ("h", "raised", 21, 6, 14, 42),     # segmented control
    "segon34": ("h", "raised", 17, 3, 6, 34),      # active segment
    "conn30":  ("h", "inset", 15, 3, 6, 30),       # connection chip
    "tab34on": ("h", "inset", 17, 3, 7, 34),       # active tab
    "slider12": ("h", "inset", 6, 3, 6, 12),       # slider track
    "swtrack": ("f", "inset", 14, 3, 6, (54, 28)),  # switch track
    "thumb":   ("c", "raised", 11, 3, 6, None),    # switch + slider thumb (22px)
    "swatch":  ("c", "raised", 17, 6, 14, None),
    "swatchon": ("c", "inset", 17, 4, 8, None),
    "dial":    ("c", "raised", 65, 8, 16, None),   # dial body (130px)
    "dialin":  ("c", "inset", 39, 4, 8, None),     # dial inner well
    "knob":    ("c", "raised", 31, 5, 10, None),   # rotating knob
    "orb":     ("c", "inset", 46, 5, 10, None),    # status orb well (92px)
    "orbdot":  ("c", "raised", 24, 4, 8, None),
}

def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def shape_mask(size, box, r, circle):
    ss = 4
    im = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    d = ImageDraw.Draw(im)
    b = [v * ss for v in box]
    if circle: d.ellipse(b, fill=255)
    else: d.rounded_rectangle(b, radius=r * ss, fill=255)
    return im.resize(size, Image.LANCZOS)

def layer(color, mask):
    im = Image.new("RGBA", mask.size, color + (255,))
    im.putalpha(mask)
    return im

def make(pal, shape, kind, r, off, blur, fixed):
    sigma = blur / 2 * S
    m = (off + blur) if kind == "raised" else 0
    cap = r + blur + 2
    if shape == "c": bw = bh = 2 * r
    elif shape == "n": bw = bh = 2 * cap + 2
    elif shape == "h": bw, bh = 2 * cap + 2, fixed
    else: bw, bh = fixed
    tw, th = bw + 2 * m, bh + 2 * m
    pad = int(math.ceil(3 * sigma)) + off * S + 4
    P = (tw * S + 2 * pad, th * S + 2 * pad)
    box = (pad + m * S, pad + m * S, pad + (m + bw) * S, pad + (m + bh) * S)
    body = shape_mask(P, box, r * S, shape == "c")
    bg, sd, sl = hexrgb(pal["bg"]), hexrgb(pal["sd"]), hexrgb(pal["sl"])
    def shifted(mask, d): return ImageChops.offset(mask, d * S, d * S)
    if kind == "raised":
        dark = shifted(body, off).filter(ImageFilter.GaussianBlur(sigma))
        light = shifted(body, -off).filter(ImageFilter.GaussianBlur(sigma))
        out = Image.new("RGBA", P, (0, 0, 0, 0))
        out = Image.alpha_composite(out, layer(sl, light))
        out = Image.alpha_composite(out, layer(sd, dark))
        out = Image.alpha_composite(out, layer(bg, body))
    else:
        out = layer(bg, body)
        for col, d in ((sl, -off), (sd, off)):
            inv = ImageChops.invert(shifted(body, d)).filter(ImageFilter.GaussianBlur(sigma))
            out = Image.alpha_composite(out, layer(col, ImageChops.multiply(inv, body)))
    out = out.crop((pad, pad, pad + tw * S, pad + th * S))
    return out, {"w": tw, "h": th, "m": m, "shape": shape, "cap": cap + m}

def build(outdirs):
    meta = {}
    for acc, (name, swatch, light, dark) in THEMES.items():
        for mode, pal in (("light", light), ("dark", dark)):
            key = f"{acc}_{mode}"
            for kname, (shape, kind, r, off, blur, fixed) in KINDS.items():
                im, info = make(pal, shape, kind, r, off, blur, fixed)
                for od in outdirs:
                    d = os.path.join(od, key); os.makedirs(d, exist_ok=True)
                    im.save(os.path.join(d, kname + ".png"), optimize=True)
                meta[kname] = info
    return meta

# ---------- preview helpers: the same slicing the apps use ----------
def nine(tile, info, w, h):
    """Stretch a tile to w x h css px (the same slicing the Qt and Compose code does)."""
    sh = info["shape"]
    W, H = w * S, h * S
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tw, th = tile.size
    if sh in ("c", "f"):
        out.alpha_composite(tile, (0, 0)); return out
    cx = info["cap"] * S
    cy = cx if sh == "n" else th // 2
    def put(src, dst):
        if dst[2] <= dst[0] or dst[3] <= dst[1]: return
        out.alpha_composite(tile.crop(src).resize((dst[2] - dst[0], dst[3] - dst[1])), (dst[0], dst[1]))
    xs = [(0, cx, 0, cx), (cx, tw - cx, cx, W - cx), (tw - cx, tw, W - cx, W)]
    if sh == "h": ys = [(0, th, 0, H)]
    else: ys = [(0, cy, 0, cy), (cy, th - cy, cy, H - cy), (th - cy, th, H - cy, H)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if sx1 - sx0 > 4 and dx1 - dx0 > 0 and sx0 == cx and sx1 == tw - cx:   # centre strip: use its middle 2px
                mid = (sx0 + sx1) // 2
                put((mid - S, sy0, mid + S, sy1), (dx0, dy0, dx1, dy1))
            else:
                put((sx0, sy0, sx1, sy1), (dx0, dy0, dx1, dy1))
    return out

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    outs = [os.path.join(root, "desktop/flowbeacon_app/assets/neu"), os.path.join(root, "android/app/src/main/assets/neu")]
    for o in outs: shutil.rmtree(o, ignore_errors=True)
    meta = build(outs)
    for o in outs: json.dump(meta, open(os.path.join(o, "meta.json"), "w"))
    print("tiles:", sum(len(f) for _, _, f in os.walk(outs[0])), "meta kinds:", len(meta))
