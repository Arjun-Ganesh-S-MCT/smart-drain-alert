"""A small slippy map widget: OpenStreetMap tiles with drag to move, wheel to zoom and pins on top. No web view."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from . import citymap, tiles
from .store import data_dir
from .theme import THEME, font

TILE = 256


class TileMap(QWidget):
    picked = Signal(str)
    tile_ready = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(360)
        self.setMouseTracking(True)
        self.states, self.sel = [], None
        self.zoom, self.clat, self.clng = 12.0, citymap.CENTER[0], citymap.CENTER[1]
        self.fitted = False
        self.pix = {}
        self.pos = {}
        self.press = None
        self.tile_ready.connect(self.update)
        self.cache = tiles.TileCache(data_dir() / "tiles", on_ready=lambda: self.tile_ready.emit())

    # ---- data ----
    def set_states(self, states, sel):
        self.states, self.sel = states, sel
        if not self.fitted and states and self.width() > 50:
            self.fit()
        self.update()

    def fit(self):
        z, la, lo = tiles.fit_zoom([(s["dv"]["lat"], s["dv"]["lng"]) for s in self.states], self.width(), self.height())
        self.zoom, self.clat, self.clng = float(z), la, lo
        self.fitted = True
        self.update()

    def zoom_by(self, d):
        self.zoom = max(tiles.MIN_Z, min(tiles.MAX_Z, self.zoom + d))
        self.update()

    # ---- projection ----
    def _tz(self):
        return int(math.floor(self.zoom))

    def _px(self):
        """Pixels per tile unit at the current zoom."""
        return TILE * 2.0 ** (self.zoom - self._tz())

    def to_screen(self, lat, lng):
        z = self._tz()
        cx, cy = tiles.world(self.clat, self.clng, z)
        x, y = tiles.world(lat, lng, z)
        k = self._px()
        return QPointF(self.width() / 2 + (x - cx) * k, self.height() / 2 + (y - cy) * k)

    def _pixmap(self, p):
        key = str(p)
        if key not in self.pix:
            if len(self.pix) > 250:
                self.pix.clear()
            self.pix[key] = QPixmap(key)
        return self.pix[key]

    # ---- painting ----
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h, z, k = self.width(), self.height(), self._tz(), self._px()
        p.fillRect(self.rect(), THEME.c("sd"))
        cx, cy = tiles.world(self.clat, self.clng, z)
        x0, x1 = int(math.floor(cx - w / 2 / k)), int(math.floor(cx + w / 2 / k))
        y0, y1 = int(math.floor(cy - h / 2 / k)), int(math.floor(cy + h / 2 / k))
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                r = QRectF(w / 2 + (tx - cx) * k, h / 2 + (ty - cy) * k, k + 1, k + 1)
                f = self.cache.get(z, tx, ty)
                if f is not None:
                    pm = self._pixmap(f)
                    if not pm.isNull():
                        p.drawPixmap(r, pm, QRectF(pm.rect()))
                        continue
                p.setPen(QPen(THEME.c("sl"), 1))
                p.drawRect(r)
        self.pos = {}
        for s in self.states:
            pt = self.to_screen(s["dv"]["lat"], s["dv"]["lng"])
            self.pos[s["id"]] = pt
            col = QColor(citymap.STAT_COLOR[s["status"]])
            if s["id"] == self.sel:
                p.setPen(QPen(QColor("#ffffff"), 5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(pt, 17, 17)
                p.setPen(QPen(THEME.c("ac"), 3))
                p.drawEllipse(pt, 17, 17)
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(col)
            p.drawEllipse(pt, 11, 11)
            label = citymap.CityBook.label(s)
            p.setFont(font(11, True))
            tw = p.fontMetrics().horizontalAdvance(label) + 12
            box = QRectF(pt.x() - tw / 2, pt.y() + 15, tw, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 215))
            p.drawRoundedRect(box, 6, 6)
            p.setPen(QColor("#222222"))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, label)
        p.setFont(font(10))
        txt = tiles.CREDIT
        tw = p.fontMetrics().horizontalAdvance(txt) + 10
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRect(QRectF(w - tw, h - 18, tw, 18))
        p.setPen(QColor("#333333"))
        p.drawText(QRectF(w - tw, h - 18, tw, 18), Qt.AlignmentFlag.AlignCenter, txt)
        p.end()

    # ---- mouse ----
    def mousePressEvent(self, e):
        self.press = (e.position(), e.position(), False)

    def mouseMoveEvent(self, e):
        if not self.press:
            return
        start, last, moved = self.press
        pt = e.position()
        if moved or abs(pt.x() - start.x()) + abs(pt.y() - start.y()) > 5:
            z, k = self._tz(), self._px()
            cx, cy = tiles.world(self.clat, self.clng, z)
            cx -= (pt.x() - last.x()) / k
            cy -= (pt.y() - last.y()) / k
            self.clat, self.clng = tiles.unworld(cx, cy, z)
            self.press = (start, pt, True)
            self.fitted = True
            self.update()

    def mouseReleaseEvent(self, e):
        if self.press and not self.press[2]:
            pt, best = e.position(), None
            for sid, q in self.pos.items():
                d = (q.x() - pt.x()) ** 2 + (q.y() - pt.y()) ** 2
                if d < 24 ** 2 and (best is None or d < best[0]):
                    best = (d, sid)
            if best:
                self.picked.emit(best[1])
        self.press = None

    def wheelEvent(self, e):
        self.fitted = True
        self.zoom_by(1 if e.angleDelta().y() > 0 else -1)

    def mouseDoubleClickEvent(self, e):
        self.fitted = True
        self.zoom_by(1)
