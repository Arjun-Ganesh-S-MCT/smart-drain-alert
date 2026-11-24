"""Copies fonts and icons, builds the drain SVG template and the theme tables for both apps."""
import os
import re
import shutil
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_assets import THEMES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/home/claude/fb/flowbeacon/src"
FONTS = "/mnt/skills/examples/canvas-design/canvas-fonts"
DESK = os.path.join(ROOT, "desktop/flowbeacon_app/assets")
ANDR = os.path.join(ROOT, "android/app/src/main/assets")

for dest in (DESK, ANDR):
    os.makedirs(dest + "/fonts", exist_ok=True)
    for f in ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf", "JetBrainsMono-OFL.txt"):
        shutil.copy(os.path.join(FONTS, f), dest + "/fonts/" + f)
    for mode in ("light", "dark"):
        os.makedirs(f"{dest}/icons/{mode}", exist_ok=True)
        for n in ("devices", "zone", "blockage", "connect", "resolved", "calibration", "team", "status", "update", "map", "lock", "demo", "baseline"):
            im = Image.open(f"{SRC}/icons/{mode}/{n}.png").convert("RGBA")
            im.thumbnail((64, 64), Image.LANCZOS)
            im.save(f"{dest}/icons/{mode}/{n}.png", optimize=True)

# ---------- drain SVG template ----------
html = open(SRC + "/index.html", encoding="utf-8").read()
svg = re.search(r'<svg viewBox="0 0 560 220".*?</svg>', html, re.S).group(0)
svg = svg.replace(' width="100%"', "").replace(' class="drain"', "")
svg = re.sub(r'<pattern.*?</pattern>', "", svg, flags=re.S)
svg = re.sub(r'<clipPath.*?</clipPath>', "", svg, flags=re.S)
svg = svg.replace(' clip-path="url(#dWaterClip)"', "")
svg = svg.replace('<rect x="0" y="44" width="560" height="176" fill="url(#dDots)"/>', "")
svg = re.sub(r'<!--.*?-->', "", svg)
svg = svg.replace('<path id="water" d="" fill="url(#wg)" opacity=".92"/>', '<path d="{{WATER}}" fill="url(#wg)" opacity=".92"/>')
svg = svg.replace('<path id="surf" d="" fill="none"', '<path d="{{SURF}}" fill="none"')
svg = svg.replace('<polygon id="beam" points=""', '<polygon points="{{BEAM}}"')
svg = svg.replace('<stop id="wg1" offset="0" stop-color="rgb(86,170,220)"/>', '<stop offset="0" stop-color="{{WG1}}"/>')
svg = svg.replace('<stop id="wg2" offset="1" stop-color="rgb(40,110,170)"/>', '<stop offset="1" stop-color="{{WG2}}"/>')
svg = re.sub(r'<g id="drops".*?</g>', '<g fill="#8cc8f0">{{DROPS}}</g>', svg, flags=re.S)
svg = svg.replace('<g id="debris" style="opacity:0;transition:opacity .4s">', '<g opacity="{{DEBRIS}}">')
svg = svg.replace('<circle id="blk" cx="446" cy="143" r="0" fill="url(#dDebris)" opacity=".92"/>', "")
svg = svg.replace('<g class="bub" fill="#ffffff" opacity=".35"><circle cx="48" cy="160" r="2"/><circle cx="96" cy="164" r="1.6"/><circle cx="118" cy="158" r="2.2"/></g>',
                  '<g fill="#ffffff"><circle cx="48" cy="{{B1Y}}" r="2" opacity="{{B1O}}"/><circle cx="96" cy="{{B2Y}}" r="1.6" opacity="{{B2O}}"/><circle cx="118" cy="{{B3Y}}" r="2.2" opacity="{{B3O}}"/></g>')
svg = svg.replace('<g class="sonar" fill="none" stroke="#9fe0ff" stroke-width="1.4"><path d="M70 56 Q80 62 90 56"/><path d="M66 63 Q80 72 94 63"/><path d="M62 70 Q80 82 98 70"/></g>',
                  '<g fill="none" stroke="#9fe0ff" stroke-width="1.4"><path d="M70 {{S1Y}} Q80 {{S1Q}} 90 {{S1Y}}" opacity="{{S1O}}"/><path d="M66 {{S2Y}} Q80 {{S2Q}} 94 {{S2Y}}" opacity="{{S2O}}"/><path d="M62 {{S3Y}} Q80 {{S3Q}} 98 {{S3Y}}" opacity="{{S3O}}"/></g>')
svg = svg.replace(' class="led"', ' opacity="{{LED}}"')
svg = svg.replace('<path class="pipe" id="pipe" d="M150 142 H556" fill="none" stroke="#bfe6fb" stroke-width="2.4" stroke-linecap="round" opacity=".8"/>',
                  '<path d="M150 142 H556" fill="none" stroke="#bfe6fb" stroke-width="2.4" stroke-linecap="round" opacity=".8" stroke-dasharray="10 8" stroke-dashoffset="{{PIPE}}"/>')
svg = svg.replace('<path class="pipe" d="M150 148 H556" fill="none" stroke="#bfe6fb" stroke-width="1.6" stroke-linecap="round" opacity=".55" style="animation-delay:-.4s"/>',
                  '<path d="M150 148 H556" fill="none" stroke="#bfe6fb" stroke-width="1.6" stroke-linecap="round" opacity=".55" stroke-dasharray="10 8" stroke-dashoffset="{{PIPE2}}"/>')
svg = svg.replace('<path class="wetline" d="M200 26 H232" stroke="#8cc8f0" stroke-width="2" stroke-linecap="round" opacity="0"/>', '<path d="M200 26 H232" stroke="#8cc8f0" stroke-width="2" stroke-linecap="round" opacity="{{WET}}"/>')
svg = svg.replace('<g id="rainp">', "<g>").replace('<g id="valve">', "<g>")
# labels: uppercase, white with a dark outline (drawn as two copies because paint-order is not portable)
def label(m):
    x, y, t = m.group(1), m.group(2), m.group(3).upper()
    common = f'x="{x}" y="{y}" font-family="JetBrains Mono, monospace" font-size="9.5" font-weight="600" letter-spacing="0.4"'
    return f'<text {common} fill="none" stroke="#000000" stroke-opacity="0.65" stroke-width="3" stroke-linejoin="round">{t}</text><text {common} fill="#ffffff">{t}</text>'
svg = re.sub(r'<text x="([\d.]+)" y="([\d.]+)">([^<]*)</text>', label, svg)
svg = svg.replace('<svg viewBox="0 0 560 220" role="img" aria-label="Cross-section of a street drain: catch basin with water, sensors and outlet pipe">', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 220" width="560" height="220">')
assert "{{WATER}}" in svg and "class=" not in svg, "template conversion failed"
for dest in (DESK, ANDR):
    open(dest + "/drain.svg.tpl", "w", encoding="utf-8").write(svg)
print("svg template", len(svg), "bytes; placeholders:", sorted(set(re.findall(r"\{\{(\w+)\}\}", svg))))

# ---------- theme tables ----------
py = '"""Theme palettes (from the web app): 7 accent colours x light/dark. Generated by tools/make_shared.py."""\n'
py += "ACCENTS = %r\n" % [(k, v[0], v[1]) for k, v in THEMES.items()]
py += "PALETTES = {\n" + "".join('    "%s_%s": %r,\n' % (k, m, v[2 if m == "light" else 3]) for k, v in THEMES.items() for m in ("light", "dark")) + "}\n"
open(os.path.join(ROOT, "desktop/flowbeacon_app/palettes.py"), "w").write(py)
def kc(h): return "0xFF" + h.lstrip("#").upper()
kt = "package com.techminds.flowbeacon\n\n// Theme palettes (from the web app): 7 accent colours x light/dark. Generated by tools/make_shared.py.\n"
kt += "class Pal(val bg: Long, val sd: Long, val sl: Long, val tx: Long, val mu: Long, val ac: Long, val on: Long)\n\nobject Palettes {\n"
kt += "    val ACCENTS = listOf(" + ", ".join('Triple("%s", "%s", %s)' % (k, v[0], kc(v[1])) for k, v in THEMES.items()) + ")\n"
kt += "    val ALL: Map<String, Pal> = mapOf(\n" + ",\n".join('        "%s_%s" to Pal(%s)' % (k, m, ", ".join(kc(v[2 if m == "light" else 3][f]) for f in ("bg", "sd", "sl", "tx", "mu", "ac", "on"))) for k, v in THEMES.items() for m in ("light", "dark")) + "\n    )\n}\n"
open(os.path.join(ROOT, "android/app/src/main/java/com/techminds/flowbeacon/Palettes.kt"), "w").write(kt)
print("themes ok")
