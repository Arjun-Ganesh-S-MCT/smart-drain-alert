"""Custom-painted widgets: Drip (with physics and a raised speech bubble), the drain picture (real SVG), live chart, splash."""
import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from .drain import DrainState
from .drip_data import BODY, EX, POS, SIZE
from .neu import tiles
from .theme import ASSETS, THEME, font

TINT = {"coral": 0, "blue": 205, "green": 125, "purple": 255, "red": -15, "yellow": 40, "black": None}


def tint_pixmap(pm, accent):
    """Recolours Drip's coral body for the other accents (the web app does this with a CSS hue-rotate filter)."""
    deg = TINT.get(accent, 0)
    if deg == 0:
        return pm
    img = pm.toImage().convertToFormat(pm.toImage().Format.Format_ARGB32)
    from PySide6.QtGui import qAlpha, qBlue, qGreen, qRed, qRgba
    w, h = img.width(), img.height()
    ca, sa = math.cos(math.radians(deg or 0)), math.sin(math.radians(deg or 0))
    for y in range(h):
        for x in range(w):
            c = img.pixel(x, y)
            a = qAlpha(c)
            if a == 0:
                continue
            r, g, b = qRed(c), qGreen(c), qBlue(c)
            if deg is None:                              # black: grayscale, darker
                v = int((0.3 * r + 0.59 * g + 0.11 * b) * 0.5)
                img.setPixel(x, y, qRgba(v, v, v, a))
                continue
            nr = (0.213 + ca * 0.787 - sa * 0.213) * r + (0.715 - ca * 0.715 - sa * 0.715) * g + (0.072 - ca * 0.072 + sa * 0.928) * b
            ng = (0.213 - ca * 0.213 + sa * 0.143) * r + (0.715 + ca * 0.285 + sa * 0.140) * g + (0.072 - ca * 0.072 - sa * 0.283) * b
            nb = (0.213 - ca * 0.213 - sa * 0.787) * r + (0.715 - ca * 0.715 + sa * 0.715) * g + (0.072 + ca * 0.928 + sa * 0.072) * b
            img.setPixel(x, y, qRgba(max(0, min(255, int(nr))), max(0, min(255, int(ng))), max(0, min(255, int(nb))), a))
    return QPixmap.fromImage(img)


class DripWidget(QWidget):
    """The mascot from the original layered PNGs. Drag or throw it; it falls with gravity and bounces off the window edges."""
    tapped = Signal()
    thrown = Signal()
    BUBBLE_H = 84
    TINTED = ("body", "arm_left", "arm_right", "arm_up", "arm_wave", "umbrella", "sweat_drop")

    def __init__(self, parent, width=150):
        super().__init__(parent)
        self.bw = width
        self.bh = width * BODY[1] / BODY[0]
        self.setFixedSize(int(width + 110), int(self.bh + self.BUBBLE_H + 22))
        self.setMouseTracking(True)
        self.cache = {}
        self.state, self.rain = "idle", False
        self.blink_until, self.next_blink = 0.0, time.time() + 3
        self.say_text, self.say_until = "", 0.0
        self.t0 = time.time()
        self.look = (0.0, 0.0)
        self.drag = None
        self.vx = self.vy = 0.0
        self.falling = False
        self.last_move = None
        self.calm = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        THEME.changed.connect(self.cache.clear)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)

    # ---- sprite
    def pm(self, name):
        if name not in self.cache:
            pm = QPixmap(str(ASSETS / "drip" / (name + ".png")))
            if name in self.TINTED and THEME.accent != "coral":
                pm = tint_pixmap(pm, THEME.accent)
            self.cache[name] = pm
        return self.cache[name]

    def set_state(self, s, rain=False):
        self.state, self.rain = s, rain
        self.update()

    def say(self, text, ms=4500):
        self.say_text, self.say_until = text, time.time() + ms / 1000
        self.update()

    def floor(self):
        par = self.parentWidget()
        return (par.height() if par else 600) - self.height() + 18

    def tick(self):
        if not self.isVisible():
            return
        now = time.time()
        if now > self.next_blink:
            self.blink_until, self.next_blink = now + 0.14, now + 3 + random.random() * 2.5
        if self.say_text and now > self.say_until:
            self.say_text = ""
        if self.falling and not self.drag and not self.calm:
            dt = 0.03
            self.vy += 1900 * dt
            x, y = self.x() + self.vx * dt, self.y() + self.vy * dt
            par = self.parentWidget()
            fl, wr = self.floor(), (par.width() if par else 800) - self.width()
            if y >= fl:
                y = fl
                if self.vy > 140:
                    self.vy = -self.vy * 0.52
                    self.vx *= 0.88
                else:
                    self.vy = 0
                self.vx *= 0.6
            if y < 0:
                y, self.vy = 0, -self.vy * 0.5
            if x < 0:
                x, self.vx = 0, -self.vx * 0.6
            if x > wr:
                x, self.vx = wr, -self.vx * 0.6
            self.move(int(x), int(y))
            if abs(self.vx) < 6 and abs(self.vy) < 6 and y >= fl - 1:
                self.falling = False
        self.update()

    # ---- painting
    def _layers(self):
        eyes, brows, mouth, la, ra, extra, _a = EX.get(self.state, EX["idle"])
        closed = eyes == "c" or time.time() < self.blink_until
        names = ["eyes_closed" if closed else "eyes_open"]
        if brows:
            names.append(brows)
        names.append(mouth)
        names += list(extra)
        if not closed:
            names += ["pupil_l", "pupil_r"]
        arms = [la, ra]
        if self.rain:
            names.append("umbrella")
            arms[0] = "arm_up2"
        return arms, names

    def _draw(self, p, name, extra=(0, 0)):
        cx, cy, wp = POS[name]
        src = "arm_up" if name == "arm_up2" else name
        sw, sh = SIZE[src]
        w = wp / 100 * self.bw
        h = w * sh / sw
        x = cx / 100 * self.bw - w / 2 + extra[0]
        y = cy / 100 * self.bh - h / 2 + extra[1]
        pm = self.pm(src)
        if name == "arm_up2":
            p.save()
            p.translate(x + w, y)
            p.scale(-1, 1)
            p.drawPixmap(QRectF(0, 0, w, h), pm, QRectF(pm.rect()))
            p.restore()
        else:
            p.drawPixmap(QRectF(x, y, w, h), pm, QRectF(pm.rect()))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        t = time.time() - self.t0
        anim = EX.get(self.state, EX["idle"])[6]
        dx = dy = rot = 0.0
        sx = sy = 1.0
        if self.calm:
            anim = ""
        if anim == "float": dy = -3.5 * (0.5 - 0.5 * math.cos(t * 2.1)) * 2; sy = 1 + 0.015 * math.sin(t * 2.1)
        elif anim == "bounce": dy = -26 * abs(math.sin(t * 5.2)) * 0.5; sx, sy = 1.06 - 0.12 * abs(math.sin(t * 5.2)), 0.94 + 0.12 * abs(math.sin(t * 5.2))
        elif anim == "tilt": rot = math.sin(t * 3.5) * 6
        elif anim == "shiver": dx = math.sin(t * 45) * 2
        elif anim == "hop": dy = -22 * abs(math.sin(t * 3.5))
        elif anim == "shake": dx, rot = math.sin(t * 52) * 5, math.sin(t * 52) * 3
        elif anim == "sleep": dy = math.sin(t * 1.6) * 3
        left = (self.width() - self.bw) / 2
        base_y = self.BUBBLE_H
        p.setPen(Qt.PenStyle.NoPen)                          # ground shadow
        c = THEME.c("sd")
        c.setAlphaF(0.5)
        p.setBrush(c)
        p.drawEllipse(QRectF(left + self.bw * 0.2, base_y + self.bh + 6, self.bw * 0.6, 10))
        p.translate(left + self.bw / 2 + dx, base_y + self.bh + dy)
        p.rotate(rot)
        p.scale(sx, sy)
        p.translate(-self.bw / 2, -self.bh)
        arms, names = self._layers()
        for a in arms:
            self._draw(p, a)
        p.drawPixmap(QRectF(0, 0, self.bw, self.bh), self.pm("body"), QRectF(self.pm("body").rect()))
        for n in names:
            off = (self.look[0] * 0.04 * self.bw, self.look[1] * 0.035 * self.bw) if n.startswith("pupil") else (0, 0)
            self._draw(p, n, off)
        p.resetTransform()
        if self.say_text:
            self._bubble(p)
        p.end()

    def _bubble(self, p):
        p.setFont(font(12, True))
        maxw = 230
        flags = Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        need = p.boundingRect(QRectF(0, 0, maxw - 32, 200), flags, self.say_text)
        w, h = min(maxw, need.width() + 32), need.height() + 20
        box = QRectF(self.width() - w - 18, self.BUBBLE_H - h - 12, w, h)
        tiles().draw(p, "pill36", box)
        p.setPen(THEME.c("tx"))
        p.drawText(box.adjusted(16, 10, -16, -10), flags, self.say_text)

    # ---- interaction
    def mousePressEvent(self, e):
        self.drag = (e.globalPosition().toPoint(), self.pos(), False)
        self.falling = False
        self.vx = self.vy = 0
        self.last_move = (time.time(), e.globalPosition().toPoint())
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self.drag:
            g0, p0, moved = self.drag
            d = e.globalPosition().toPoint() - g0
            if moved or abs(d.x()) + abs(d.y()) > 5:
                self.drag = (g0, p0, True)
                par = self.parentWidget()
                nx = max(0, min(p0.x() + d.x(), (par.width() if par else 9999) - self.width()))
                ny = max(0, min(p0.y() + d.y(), self.floor()))
                self.move(nx, ny)
                now, gp = time.time(), e.globalPosition().toPoint()
                lt, lp = self.last_move
                dt = max(0.016, now - lt)
                self.vx, self.vy = (gp.x() - lp.x()) / dt * 0.6, (gp.y() - lp.y()) / dt * 0.6
                self.last_move = (now, gp)
        else:
            c = self.rect().center()
            dx, dy = e.position().x() - c.x(), e.position().y() - c.y()
            d = math.hypot(dx, dy) or 1
            k = min(1.0, d / 220)
            self.look = (dx / d * k, dy / d * k)

    def mouseReleaseEvent(self, _e):
        if not self.drag:
            return
        moved = self.drag[2]
        self.drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if moved:
            if time.time() - self.last_move[0] > 0.1:
                self.vx = self.vy = 0
            self.falling = True
            self.thrown.emit()
        else:
            self.tapped.emit()

    def settle(self, x, y):
        """Place Drip at the bottom right (used on resize); keeps it inside the window."""
        if self.drag:
            return
        par = self.parentWidget()
        nx = max(0, min(self.x() if self.x() > 0 else x, par.width() - self.width()))
        self.move(int(max(0, par.width() - self.width() - 6)) if x < 0 else int(nx), int(self.floor()))
        self.falling = True


# ---------------------------------------------------------------- drain picture
class DrainView(QWidget):
    """Cross-section of the drain: the web app's SVG artwork, with live water, sonar, pipe flow and blockage."""

    def __init__(self):
        super().__init__()
        self.st = DrainState()
        self.r = QSvgRenderer(self)
        self.setMinimumHeight(180)
        self.t = QTimer(self)
        self.t.timeout.connect(self._tick)
        self.t.start(50)
        self._build()

    def _build(self):
        self.r.load(self.st.svg().encode("utf8"))

    def set_values(self, *a, **k):
        self.st.set_values(*a, **k)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return int(w * 220 / 560)

    def _tick(self):
        if not self.isVisible():
            return
        self.st.step(0.05)
        self._build()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = w * 220 / 560
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 14, 14)
        p.setClipPath(path)
        self.r.render(p, QRectF(0, 0, w, h))
        p.end()


# ---------------------------------------------------------------- chart
class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.hist, self.n = [], 90

    def set_history(self, hist, n=None):
        self.hist = hist
        if n:
            self.n = n
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        v = self.hist[-self.n:]
        w, h = self.width(), self.height()
        if len(v) < 2:
            p.setPen(THEME.c("mu"))
            p.setFont(font(12))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for readings…")
            p.end()
            return

        def line(key, col, inv):
            a = [q[key] for q in v]
            mn, mx = min(a), max(a)
            if mx - mn < 0.5:
                mx = mn + 0.5
            path = QPainterPath()
            for i, y in enumerate(a):
                px = i / (len(a) - 1) * (w - 24) + 12
                q = (y - mn) / (mx - mn)
                py = (q if inv else 1 - q) * (h - 40) + 20
                path.moveTo(px, py) if i == 0 else path.lineTo(px, py)
            p.setPen(QPen(col, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        line("f", THEME.c("ac"), False)
        line("l", THEME.c("tx"), True)
        p.end()


# ---------------------------------------------------------------- splash
class Splash(QWidget):
    """Same intro as the web splash: TechMinds, then Drip and FlowBeacon, with a progress bar."""
    finished = Signal()
    TOTAL = 4.3

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFixedSize(720, 460)
        self.logo = QPixmap(str(ASSETS / "img" / "techminds.png"))
        self.drip = QPixmap(str(ASSETS / "img" / "drip-full.png"))
        self.t0 = time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def showEvent(self, e):
        super().showEvent(e)
        scr = self.screen().availableGeometry() if self.screen() else None
        if scr:
            self.move(scr.center() - self.rect().center())

    def _tick(self):
        if time.time() - self.t0 >= self.TOTAL:
            self.timer.stop()
            self.finished.emit()
            return
        self.update()

    @staticmethod
    def e(x):
        return max(0.0, min(1.0, x))

    def paintEvent(self, _e):
        t = time.time() - self.t0
        e = self.e
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), THEME.c("bg"))
        W, H = self.width(), self.height() - 70
        a = e((t - 0.2) / 0.8) * (1 - e((t - 2.6) / 0.5))
        if a > 0:
            s = (0.85 + 0.15 * e((t - 0.2) / 0.8)) * (1 - 0.04 * e((t - 2.6) / 0.5))
            ph = 200 * s
            pw = self.logo.width() * ph / self.logo.height()
            p.setOpacity(a)
            p.drawPixmap(QRectF(W / 2 - pw / 2, H / 2 - ph / 2 - 20, pw, ph), self.logo, QRectF(self.logo.rect()))
            p.setOpacity(a * e((t - 1.3) / 0.7))
            p.setFont(font(15, False, 9.0))
            p.setPen(THEME.c("tx"))
            p.drawText(QRectF(0, H / 2 + 92, W, 24), Qt.AlignmentFlag.AlignCenter, "PRESENTS")
        b = e((t - 3.1) / 0.7)
        if b > 0:
            k = e((t - 3.1) / 0.9)
            hop = (1 - k) * 40 - 14 * math.sin(min(1.0, k * 1.6) * math.pi) * (1 - k) if k < 1 else 0
            ph = 150
            pw = self.drip.width() * ph / self.drip.height()
            p.setOpacity(b)
            p.drawPixmap(QRectF(W / 2 - pw / 2, H / 2 - 120 + hop, pw, ph), self.drip, QRectF(self.drip.rect()))
            p.setFont(font(34, True, 2.0))
            fm = p.fontMetrics()
            w1, w2 = fm.horizontalAdvance("Flow"), fm.horizontalAdvance("Beacon")
            x = W / 2 - (w1 + w2) / 2
            p.setPen(THEME.c("tx"))
            p.drawText(QPointF(x, H / 2 + 74), "Flow")
            p.setPen(THEME.c("ac"))
            p.drawText(QPointF(x + w1, H / 2 + 74), "Beacon")
            p.setFont(font(13, False, 1.0))
            p.setPen(THEME.c("mu"))
            p.drawText(QRectF(0, H / 2 + 88, W, 20), Qt.AlignmentFlag.AlignCenter, "drain blockage prediction")
        p.setOpacity(1)
        bar = QRectF(120, self.height() - 48, W - 240, 14)
        tiles().draw(p, "slider12", bar)
        f = e((t - 0.1) / 4.2)
        f = f * f * (3 - 2 * f)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(THEME.c("ac"))
        p.drawRoundedRect(QRectF(bar.x(), bar.y(), max(14.0, bar.width() * f), 14), 7, 7)
        p.end()
