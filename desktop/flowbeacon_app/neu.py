"""The neumorphic look: shadow tiles (pre-rendered from the web app's box-shadows) painted by a Canvas behind plain widgets.
Items (buttons, cards, fields...) only draw their own text; their raised / inset background is painted by the nearest Canvas
ancestor, so shadows can spill outside the widget's own rectangle exactly like CSS box-shadow."""
import json

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .theme import ASSETS, THEME

S = 2  # tiles are stored at 2x


class Tiles:
    def __init__(self):
        self.meta = json.loads((ASSETS / "neu" / "meta.json").read_text(encoding="utf8"))
        self.cache = {}

    def pix(self, kind):
        k = (THEME.key, kind)
        if k not in self.cache:
            self.cache[k] = QPixmap(str(ASSETS / "neu" / THEME.key / (kind + ".png")))
        return self.cache[k]

    def margin(self, kind):
        return self.meta[kind]["m"]

    def draw(self, p, kind, body: QRectF):
        """Paint tile `kind` so that its body fills `body` (logical px); shadows spill outside it."""
        m = self.meta[kind]
        mm = m["m"]
        t = QRectF(body.x() - mm, body.y() - mm, body.width() + 2 * mm, body.height() + 2 * mm)
        pm = self.pix(kind)
        pw, ph = pm.width(), pm.height()
        sh = m["shape"]
        if sh in ("c", "f"):
            p.drawPixmap(QRectF(t.x(), t.y(), m["w"], m["h"]), pm, QRectF(0, 0, pw, ph))
            return
        cap = min(m["cap"], t.width() / 2)
        cs = m["cap"] * S                      # source cap in pixels
        capx = cap
        x0, x1, x2 = t.x(), t.x() + capx, t.right() - capx
        sxs = [(0, cs), (cs, pw - cs), (pw - cs, pw)]
        dxs = [(x0, x1), (x1, x2), (x2, t.right())]
        if sh == "h":
            sys_ = [(0, ph)]
            dys = [(t.y(), t.bottom())]
        else:
            capy = min(m["cap"], t.height() / 2)
            sys_ = [(0, cs), (cs, ph - cs), (ph - cs, ph)]
            dys = [(t.y(), t.y() + capy), (t.y() + capy, t.bottom() - capy), (t.bottom() - capy, t.bottom())]
        for i, (sx0, sx1) in enumerate(sxs):
            for j, (sy0, sy1) in enumerate(sys_):
                dx0, dx1 = dxs[i]
                dy0, dy1 = dys[j]
                if dx1 - dx0 <= 0 or dy1 - dy0 <= 0:
                    continue
                if i == 1:      # centre strip: sample only its middle 2 css px, so no seam or gradient is stretched
                    mid = (sx0 + sx1) / 2
                    sx0, sx1 = mid - S, mid + S
                if sh == "n" and j == 1:
                    mid = (sy0 + sy1) / 2
                    sy0, sy1 = mid - S, mid + S
                p.drawPixmap(QRectF(dx0, dy0, dx1 - dx0, dy1 - dy0), pm, QRectF(sx0, sy0, sx1 - sx0, sy1 - sy0))


TILES = None


def tiles():
    global TILES
    if TILES is None:
        TILES = Tiles()
    return TILES


class Canvas(QWidget):
    """Paints the background and the shadow tiles of every NeuItem below it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        THEME.changed.connect(self.update)

    def add(self, w):
        if w not in self.items:
            self.items.append(w)

    def _depth(self, w):
        d, x = 0, w
        while x is not None and x is not self:
            x = x.parentWidget()
            d += 1
        return d

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), THEME.c("bg"))
        p.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)
        live = []
        for w in self.items:
            try:
                if w.isVisibleTo(self):
                    live.append((self._depth(w), w))
            except RuntimeError:
                pass
        live.sort(key=lambda t: t[0])
        for _d, w in live:
            o = w.mapTo(self, QPoint(0, 0))
            r = QRectF(o.x(), o.y(), w.width(), w.height())
            try:
                w.neu_paint(p, r)
            except RuntimeError:
                pass
        p.end()


class NeuItem:
    """Mixin: a widget whose neumorphic background is painted by its Canvas. Implement neu_paint(p, body_rect)."""
    neu_margin = 20

    def neu_register(self):
        x = self.parentWidget()
        while x is not None and not isinstance(x, Canvas):
            x = x.parentWidget()
        self._cv = x
        if x is not None:
            x.add(self)

    def showEvent(self, e):
        super().showEvent(e)
        self.neu_register()

    def neu_update(self):
        cv = getattr(self, "_cv", None)
        if cv is not None:
            m = self.neu_margin + 4
            o = self.mapTo(cv, QPoint(0, 0))
            r = QRectF(o.x(), o.y(), self.width(), self.height()).adjusted(-m, -m, m, m)
            cv.update(r.toAlignedRect())

    def neu_paint(self, p, r):
        pass
