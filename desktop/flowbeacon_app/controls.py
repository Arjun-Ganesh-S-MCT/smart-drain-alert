"""Neumorphic controls: cards, buttons, fields, selects, switches, sliders, segmented control, dials, orb, swatches."""
import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractButton, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
                               QVBoxLayout, QWidget)

from .neu import NeuItem, tiles
from .theme import ASSETS, THEME, font


def icon(name):
    return QIcon(str(ASSETS / "icons" / THEME.mode_dir / (name + ".png")))


def sub(text="", wrap=True):
    l = QLabel(text)
    l.setProperty("sub", "true")
    l.setFont(font(12))
    l.setWordWrap(wrap)
    return l


def rr(p, r, rad, color):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(r, rad, rad)


# ---------------------------------------------------------------- headings, separators
class H2(QWidget):
    """Section heading: accent tick + small bold uppercase label (the web app's h2)."""

    def __init__(self, text):
        super().__init__()
        self.text = text.upper()
        self.setFixedHeight(18)
        THEME.changed.connect(self.update)

    def sizeHint(self):
        from PySide6.QtGui import QFontMetrics
        return QSize(QFontMetrics(font(12, True, 1.7)).horizontalAdvance(self.text) + 16, 18)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rr(p, QRectF(0, 2, 4, 14), 2, THEME.c("ac"))
        p.setFont(font(12, True, 1.7))
        p.setPen(THEME.c("mu"))
        p.drawText(QRectF(14, 0, self.width() - 14, 18), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text)


class Sep(QWidget):
    def __init__(self, h=28):
        super().__init__()
        self.setFixedSize(4, h)
        THEME.changed.connect(self.update)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(QRectF(0, 0, 2, self.height()), THEME.c("sd"))
        p.fillRect(QRectF(2, 0, 2, self.height()), THEME.c("sl"))


# ---------------------------------------------------------------- panels
class NeuCard(NeuItem, QFrame):
    """Raised card (.raised.card): 18px radius, 22x24 padding, optional heading."""
    neu_margin = 20

    def __init__(self, title="", pad=(24, 22, 24, 22)):
        super().__init__()
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(*pad)
        self.box.setSpacing(10)
        if title:
            self.box.addWidget(H2(title))
            self.box.addSpacing(4)

    def neu_paint(self, p, r):
        tiles().draw(p, "card", r)


class Inset(NeuItem, QFrame):
    neu_margin = 0

    def __init__(self, pad=8):
        super().__init__()
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(pad, pad, pad, pad)

    def neu_paint(self, p, r):
        tiles().draw(p, "inset", r)


# ---------------------------------------------------------------- buttons
class NeuButton(NeuItem, QPushButton):
    """mode: raised (default) | tab | seg.  tall=True gives the 40px toolbar size."""
    neu_margin = 14

    def __init__(self, text="", mode="raised", tall=False, main=False, ico=None):
        super().__init__(text)
        self.mode, self.tall, self.main = mode, tall, main
        self.setProperty("main", "true" if main else "false")
        self.setFixedHeight(40 if tall else (34 if mode in ("tab", "seg") else 36))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(font(13, True))
        if mode == "tab":
            self.setProperty("tab", "true")
            self.setCheckable(True)
        if mode == "seg":
            self.setCheckable(True)
            self.toggled.connect(self._seg_on)
        if ico:
            self.set_icon(ico)
        self.toggled.connect(lambda _c: self.neu_update())
        self.pressed.connect(self.neu_update)
        self.released.connect(self.neu_update)
        THEME.changed.connect(self._theme)
        self._ico = ico

    def set_icon(self, name):
        self._ico = name
        self.setIcon(icon(name))
        self.setIconSize(QSize(20 if self.tall else 18, 20 if self.tall else 18))

    def _theme(self):
        if self._ico:
            self.setIcon(icon(self._ico))

    def _seg_on(self, on):
        self.setProperty("segon", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def sizeHint(self):
        s = super().sizeHint()
        return QSize(s.width() + 8, self.height())

    def neu_paint(self, p, r):
        t = tiles()
        on = self.isDown() or self.isChecked()
        if self.mode == "seg":
            if self.isChecked():
                t.draw(p, "segon34", r)
                rr(p, r, r.height() / 2, THEME.c("ac"))
            return
        if self.mode == "tab":
            t.draw(p, "tab34on" if self.isChecked() else "pill36", r)
            return
        if self.main:
            t.draw(p, "pill40" if self.tall else "pill36", r)
            rr(p, r, r.height() / 2, THEME.c("ac"))
            return
        sfx = "40" if self.tall else "36"
        t.draw(p, ("pillin" if on else "pill") + sfx, r)


class Seg(NeuItem, QWidget):
    """Segmented control (raised pill containing seg buttons). Emits picked(key)."""
    neu_margin = 20
    picked = Signal(str)

    def __init__(self, options, current=None):
        super().__init__()
        self.setFixedHeight(42)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.btns = {}
        for k, name in options:
            b = NeuButton(name, mode="seg")
            b.clicked.connect(lambda _c=False, k=k: self.select(k, True))
            lay.addWidget(b)
            self.btns[k] = b
        self.select(current or options[0][0], False)

    def select(self, k, emit):
        for key, b in self.btns.items():
            b.setChecked(key == k)
        if emit:
            self.picked.emit(k)

    def neu_paint(self, p, r):
        tiles().draw(p, "seg42", r)


# ---------------------------------------------------------------- inputs
class NeuField(NeuItem, QLineEdit):
    neu_margin = 0

    def __init__(self, text="", placeholder="", password=False):
        super().__init__(text)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(40)
        self.setFont(font(13))
        if password:
            self.setEchoMode(QLineEdit.EchoMode.Password)

    def neu_paint(self, p, r):
        tiles().draw(p, "field40", r)


class NeuCombo(NeuItem, QComboBox):
    neu_margin = 0

    def __init__(self, items=()):
        super().__init__()
        for text, data in items:
            self.addItem(text, data)
        self.setFixedHeight(40)
        self.setFont(font(13))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def neu_paint(self, p, r):
        tiles().draw(p, "pillin40", r)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(THEME.c("mu"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        x, y = self.width() - 26, self.height() / 2 - 2
        path = QPainterPath(QPointF(x, y))
        path.lineTo(x + 5, y + 5)
        path.lineTo(x + 10, y)
        p.drawPath(path)
        p.end()


class NeuSwitch(NeuItem, QAbstractButton):
    neu_margin = 12

    def __init__(self, checked=False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(54, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pos_ = 1.0 if checked else 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.valueChanged.connect(self._tick)
        self.toggled.connect(self._go)

    def _go(self, on):
        self.anim.stop()
        self.anim.setStartValue(self.pos_)
        self.anim.setEndValue(1.0 if on else 0.0)
        self.anim.start()

    def _tick(self, v):
        self.pos_ = float(v)
        self.neu_update()

    def paintEvent(self, _e):
        pass

    def neu_paint(self, p, r):
        t = tiles()
        t.draw(p, "swtrack", r)
        if self.pos_ > 0.01:
            c = THEME.c("ac")
            c.setAlphaF(max(0.0, min(1.0, self.pos_)))
            rr(p, r, 14, c)
        x = r.x() + 4 + 24 * self.pos_
        t.draw(p, "thumb", QRectF(x, r.y() + 3, 22, 22))


class NeuSlider(NeuItem, QSlider):
    neu_margin = 12

    def __init__(self, lo=0, hi=100, value=50):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(lo, hi)
        self.setValue(value)
        self.setFixedHeight(22)
        self.setMinimumWidth(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.valueChanged.connect(lambda _v: self.neu_update())

    def paintEvent(self, _e):
        pass

    def _from_x(self, x):
        span = max(1, self.width() - 22)
        f = max(0.0, min(1.0, (x - 11) / span))
        self.setValue(round(self.minimum() + f * (self.maximum() - self.minimum())))

    def mousePressEvent(self, e):
        self._from_x(e.position().x())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._from_x(e.position().x())

    def neu_paint(self, p, r):
        t = tiles()
        f = (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())
        track = QRectF(r.x(), r.y() + 5, r.width(), 12)
        t.draw(p, "slider12", track)
        tx = r.x() + f * (r.width() - 22)
        fill = QRectF(track.x(), track.y(), max(12.0, tx + 11 - track.x()), 12)
        rr(p, fill, 6, THEME.c("ac"))
        t.draw(p, "thumb", QRectF(tx, r.y(), 22, 22))


class Swatch(NeuItem, QAbstractButton):
    neu_margin = 20

    def __init__(self, key, color):
        super().__init__()
        self.key, self.color = key, QColor(color)
        self.setCheckable(True)
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(lambda _c: self.neu_update())

    def neu_paint(self, p, r):
        tiles().draw(p, "swatchon" if self.isChecked() else "swatch", r)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.color)
        p.drawEllipse(QRectF(9, 9, 16, 16))


class ConnChip(NeuItem, QLabel):
    """The connection status pill: inset, with a coloured dot."""
    neu_margin = 0

    def __init__(self):
        super().__init__("")
        self.dot = "mu"
        self.setFixedHeight(30)
        self.setFont(font(12, True))
        self.setContentsMargins(34, 0, 16, 0)

    def set_state(self, text, dot):
        self.setText(text)
        self.dot = dot
        self.adjustSize()
        self.setFixedWidth(self.fontMetrics().horizontalAdvance(text) + 56)
        self.update()

    def neu_paint(self, p, r):
        tiles().draw(p, "conn30", r)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.dot if isinstance(self.dot, QColor) else THEME.c(self.dot)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(14, 9, 12, 12))


# ---------------------------------------------------------------- orb + dial
class Orb(NeuItem, QWidget):
    """Status orb: an inset well with a raised coloured dot."""
    neu_margin = 12

    def __init__(self):
        super().__init__()
        self.setFixedSize(92, 92)
        self.color = THEME.c("mu")

    def set_color(self, c):
        self.color = QColor(c)
        self.update()

    def neu_paint(self, p, r):
        t = tiles()
        t.draw(p, "orb", r)
        t.draw(p, "orbdot", QRectF(r.x() + 22, r.y() + 22, 48, 48))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.color)
        p.drawEllipse(QRectF(22, 22, 48, 48))


class Knob(NeuItem, QWidget):
    """Calibration dial: 28 ticks, 270 degree arc, raised knob with an accent dot. Drag, wheel or arrow keys."""
    neu_margin = 26
    changed = Signal(float)

    def __init__(self, lo, hi, step, value):
        super().__init__()
        self.lo, self.hi, self.step, self.v = lo, hi, step, value
        self.setFixedSize(130, 130)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_value(self, v, emit=False):
        v = round(round(min(self.hi, max(self.lo, v)) / self.step) * self.step, 2)
        if v != self.v:
            self.v = v
            self.update()
            if emit:
                self.changed.emit(v)

    def _frac(self):
        return max(0.0, min(1.0, (self.v - self.lo) / (self.hi - self.lo)))

    def _from_pos(self, pt):
        a = math.degrees(math.atan2(pt.x() - 65, -(pt.y() - 65)))
        a = max(-135.0, min(135.0, a)) if abs(a) > 135 else a
        self.set_value(self.lo + (a + 135) / 270 * (self.hi - self.lo), True)

    def mousePressEvent(self, e):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._from_pos(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._from_pos(e.position())

    def mouseReleaseEvent(self, _e):
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, e):
        self.set_value(self.v + (1 if e.angleDelta().y() > 0 else -1) * self.step, True)
        e.accept()

    def keyPressEvent(self, e):
        d = {Qt.Key.Key_Up: 1, Qt.Key.Key_Right: 1, Qt.Key.Key_Down: -1, Qt.Key.Key_Left: -1}.get(e.key())
        if d:
            self.set_value(self.v + d * self.step, True)
        else:
            super().keyPressEvent(e)

    def neu_paint(self, p, r):
        t = tiles()
        t.draw(p, "dial", r)
        t.draw(p, "dialin", QRectF(r.x() + 26, r.y() + 26, 78, 78))
        t.draw(p, "knob", QRectF(r.x() + 34, r.y() + 34, 62, 62))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = self._frac()
        ac, mu, sd = THEME.c("ac"), THEME.c("mu"), THEME.c("sd")

        def pt(rad, a):
            return QPointF(65 + rad * math.sin(math.radians(a)), 65 - rad * math.cos(math.radians(a)))

        for i in range(28):
            g = -135 + 270 * i / 27
            p.setPen(QPen(ac if i / 27 <= f + 1e-6 else mu, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(pt(55, g), pt(61, g))
        arc = QRectF(65 - 47, 65 - 47, 94, 94)
        pen = QPen(sd, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(arc, 225 * 16, -270 * 16)
        if f > 0:
            pen.setColor(ac)
            p.setPen(pen)
            p.drawArc(arc, int(225 * 16), int(-270 * f * 16))
        a = -135 + 270 * f
        c = pt(20, a)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ac)
        p.drawEllipse(c, 4, 4)
