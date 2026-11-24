"""Access modes: Consumer (view), Maintenance team (operate), Developer (everything, password)."""
import time

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .controls import H2, NeuButton, NeuCard, NeuField, icon, sub
from .neu import Canvas, NeuItem, tiles
from .store import DEFAULT_PW_HASH, pw_hash
from .theme import THEME, font

ALL = ["overview", "model", "incidents", "connect", "calib", "drip", "settings", "console"]
ROLES = {
    "consumer": ("Consumer", "See drain status, live readings, the drain model and history. No controls.", "devices", ["overview", "model", "drip", "settings"]),
    "team": ("Maintenance team", "Full operational control: incidents, board connection and calibration.", "team", [t for t in ALL if t != "console"]),
    "dev": ("Developer", "Full control of everything, including the firmware console. Can switch to any mode. Password required.", "lock", ALL),
}


class RoleCard(NeuItem, QPushButton):
    neu_margin = 20

    def __init__(self, key, current):
        super().__init__("")
        name, desc, ic, _t = ROLES[key]
        self.key, self.name, self.desc, self.ic, self.cur = key, name, desc, ic, current
        self.setMinimumHeight(190)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pressed.connect(self.neu_update)
        self.released.connect(self.neu_update)

    def neu_paint(self, p, r):
        tiles().draw(p, "card", r)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        if self.cur:
            p.setPen(THEME.c("ac"))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(-2, -2, 2, 2), 20, 20)
        pm = icon(self.ic).pixmap(QSize(44, 44))
        p.drawPixmap(18, 18, pm)
        p.setFont(font(15, True))
        p.setPen(THEME.c("ac"))
        p.drawText(QRectF(18, 72, self.width() - 36, 24), Qt.AlignmentFlag.AlignVCenter, self.name)
        p.setFont(font(12))
        p.setPen(THEME.c("mu"))
        p.drawText(QRectF(18, 100, self.width() - 36, self.height() - 110), Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop, self.desc)
        p.end()


class RoleDialog(QDialog):
    """Choose a mode. With cancel=False the person must choose (first start)."""

    def __init__(self, store, parent=None, cancel=True, ask_dev=False, current="consumer"):
        super().__init__(parent)
        self.store, self.cancel, self.choice = store, cancel, None
        self.fails, self.lock = 0, 0.0
        self.setWindowTitle("FlowBeacon")
        self.setModal(True)
        self.setMinimumWidth(900)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        cv = Canvas()
        outer.addWidget(cv)
        lay = QVBoxLayout(cv)
        lay.setContentsMargins(34, 30, 34, 30)
        card = NeuCard(pad=(30, 28, 30, 28))
        lay.addWidget(card)
        t = QLabel("Welcome to FlowBeacon")
        t.setFont(font(21, True))
        card.box.addWidget(t)
        card.box.addWidget(sub("Choose how you will use the app. You can switch later from the top bar."))
        row = QHBoxLayout()
        row.setSpacing(22)
        for key in ROLES:
            c = RoleCard(key, cancel and key == current)
            c.clicked.connect(lambda _c=False, k=key: self.pick(k))
            row.addWidget(c, 1)
        card.box.addSpacing(8)
        card.box.addLayout(row)
        card.box.addSpacing(8)
        self.pw_box = QWidget()
        pl = QVBoxLayout(self.pw_box)
        pl.setContentsMargins(0, 0, 0, 0)
        lab = QLabel("DEVELOPER PASSWORD")
        lab.setProperty("sub", "true")
        lab.setFont(font(11, True, 0.7))
        pl.addWidget(lab)
        self.pw = NeuField(password=True)
        self.pw.setMaximumWidth(260)
        self.pw.returnPressed.connect(self.try_dev)
        go = NeuButton("Unlock", main=True)
        go.clicked.connect(self.try_dev)
        self.msg = sub("", False)
        r = QHBoxLayout()
        r.setSpacing(12)
        r.addWidget(self.pw)
        r.addWidget(go)
        r.addWidget(self.msg, 1)
        pl.addLayout(r)
        self.pw_box.setVisible(ask_dev)
        card.box.addWidget(self.pw_box)
        if cancel:
            c = NeuButton("Cancel")
            c.clicked.connect(self.reject)
            h = QHBoxLayout()
            h.addStretch(1)
            h.addWidget(c)
            card.box.addLayout(h)
        if ask_dev:
            self.pw.setFocus()

    def pick(self, key):
        if key == "dev":
            self.pw_box.setVisible(True)
            self.pw.setFocus()
        else:
            self.choice = key
            self.accept()

    def try_dev(self):
        if time.time() < self.lock:
            self.msg.setText("Too many attempts. Wait a few seconds.")
            return
        if pw_hash(self.pw.text()) == (self.store["devpw"] or DEFAULT_PW_HASH):
            self.choice = "dev"
            self.accept()
        else:
            self.fails += 1
            self.msg.setText("Wrong password.")
            self.pw.selectAll()
            if self.fails >= 5:
                self.lock, self.fails = time.time() + 30, 0

    def reject(self):
        if self.cancel:
            super().reject()
