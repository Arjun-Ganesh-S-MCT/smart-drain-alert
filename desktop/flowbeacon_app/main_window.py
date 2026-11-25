"""Main window: header, toolbar, tab bar and pages, with Drip floating on top (same layout as the web app)."""
import threading
import time

from PySide6.QtCore import QObject, QPoint, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QScrollArea, QStackedWidget,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from . import drip_core, i18n, pages2, updater
from .history import History as HistoryDb
from .controls import ConnChip, NeuButton, NeuCard, NeuSlider, NeuSwitch, Sep, sub
from .drip_data import MSG
from .engine import Engine
from .link import Link
from .neu import Canvas
from .pages import AskDrip, Banner, Calibration, Connection, Console, Incidents, Model, Overview, Settings
from .role import ROLES, RoleDialog
from .sound import Sound
from .store import Store, data_dir
from .theme import ASSETS, THEME, font, qss
from .widgets import DripWidget

TABS = [("overview", "Overview", "devices"), ("model", "Drain model", "zone"), ("incidents", "Incidents", "blockage"),
        ("connect", "Connection", "connect"), ("history", "History", "resolved"), ("calib", "Calibration", "calibration"),
        ("drip", "Ask Drip", "team"), ("settings", "Settings", "status"), ("console", "Console", "update"), ("map", "City map", "map")]


class _Upd(QObject):
    done = Signal(dict)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlowBeacon")
        self.resize(1240, 860)
        self.setMinimumSize(900, 620)
        self.store = Store()
        THEME.accent, THEME.mode = self.store["accent"], self.store["mode"]
        i18n.set_lang(self.store["lang"])
        i18n.set_zoom(self.store["zoom"])
        self.sound = Sound(self.store)
        self.link = Link()
        self.history = HistoryDb(data_dir() / "history.db")
        self.history.prune()
        self.engine = Engine(self.store, self.link, self.sound, self.history)
        self._quitting, self._tray_told = False, False
        self._upd = _Upd()
        self._upd.done.connect(self.on_update_result)
        self._upd_label, self._upd_manual = None, False
        self.role, self.was_ok, self.current = "consumer", False, "overview"
        self.flash_state, self.flash_until = None, 0.0
        self.cur_drip, self.cur_rain = None, None

        root = Canvas()
        self.root = root
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(28, 8, 28, 0)
        v.setSpacing(10)
        v.addLayout(self._header())
        v.addWidget(self._toolbar())
        v.addWidget(self._update_bar())
        v.addLayout(self._tabbar())
        self.banner = Banner()
        self.banner.ack.connect(self.engine.acknowledge)
        v.addWidget(self.banner)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        self.pages = {}
        for key, cls in (("overview", Overview), ("model", Model), ("incidents", Incidents), ("connect", Connection),
                         ("history", pages2.History), ("calib", Calibration), ("drip", AskDrip), ("settings", Settings),
                         ("console", Console), ("map", pages2.CityMapPage)):
            page = cls(self)
            sc = QScrollArea()
            sc.setWidgetResizable(True)
            sc.setFrameShape(QFrame.Shape.NoFrame)
            sc.viewport().setAutoFillBackground(False)
            sc.setWidget(page)
            self.stack.addWidget(sc)
            self.pages[key] = (page, sc)
        self.pages["drip"][0].action.connect(self.act)
        pages2.add_learn_cards(self.pages["calib"][0], self)
        pages2.add_settings_extras(self.pages["settings"][0], self)
        for kn in self.pages["calib"][0].knobs.values():       # the dials tick and spin like the web app
            kn.changed.connect(lambda _v, kn=kn: self.sound.knob_tick(kn._frac()))
            kn.grabbed.connect(self.sound.knob_spin)
            kn.released.connect(self.sound.knob_stop)

        self.drip = DripWidget(root)
        self.drip.tapped.connect(self.drip_tap)
        self.drip.calm = self.store["calm"]
        self.drip.raise_()
        self.drip.setVisible(self.store["drip"])

        self.engine.say.connect(self.drip.say)
        self._make_tray()
        self.engine.notify.connect(self.on_notify)
        self.engine.city_changed.connect(lambda: None)
        self.engine.flash.connect(self.do_flash)
        self.engine.banner.connect(self.on_banner)
        self.link.connection.connect(self.on_conn)
        THEME.changed.connect(self.restyle)
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _s: THEME.changed.emit() if THEME.mode == "auto" else None)
        except Exception:
            pass
        t = QTimer(self)
        t.timeout.connect(self.sync_drip)
        t.start(1000)
        a = QTimer(self)
        a.timeout.connect(self.engine.repeat_alarm)
        a.start(3000)
        fl = QTimer(self)
        fl.timeout.connect(lambda: self.banner.isVisible() and self.banner.update())
        fl.start(120)
        fh = QTimer(self)
        fh.timeout.connect(lambda: self.history.flush_all(60000))
        fh.start(60000)
        self.restyle()
        self.on_conn(False, "Not connected")
        self.show_tab("overview")
        i18n.apply(self)
        if self.store["upd"]:
            QTimer.singleShot(6000, self.check_updates)

    # ---------- layout pieces ----------
    def _header(self):
        h = QHBoxLayout()
        h.setSpacing(16)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / "img" / "techminds.png")).scaledToHeight(46, Qt.TransformationMode.SmoothTransformation))
        h.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel("FlowBeacon")
        t.setFont(font(18, True))
        col.addWidget(t)
        col.addWidget(sub("by TechMinds · drain blockage prediction · ESP32-S3 live monitor", False))
        h.addLayout(col)
        h.addStretch(1)
        self.chip = NeuButton("Consumer ▾")
        self.chip.clicked.connect(self.change_role)
        h.addWidget(self.chip)
        h.addStretch(1)
        self.conn = ConnChip()
        h.addWidget(self.conn)
        return h

    def _toolbar(self):
        card = NeuCard(pad=(18, 12, 18, 12))
        row = QHBoxLayout()
        row.setSpacing(12)
        self.b_conn = NeuButton("Connect ESP32-S3", tall=True, main=True, ico="connect")
        self.b_conn.clicked.connect(lambda: self.show_tab("connect"))
        self.b_demo = NeuButton("Demo mode", tall=True, ico="demo")
        self.b_demo.setCheckable(True)
        self.b_demo.clicked.connect(self.toggle_demo)
        self.b_cal = NeuButton("Set baseline", tall=True, ico="baseline")
        self.b_cal.clicked.connect(self.engine.start_baseline)
        self.b_wiz = NeuButton("Calibration", tall=True, ico="calibration")
        self.b_wiz.clicked.connect(lambda: (self.show_tab("incidents"), self.engine.wizard_start()))
        self.ctl = [self.b_conn, self.b_demo, self.b_cal, self.b_wiz]
        for b in self.ctl:
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(sub("Sound", False))
        self.snd = NeuSwitch(not self.store["mute"])
        self.snd.toggled.connect(lambda on: (self.store.__setitem__("mute", not on), self.store.save()))
        row.addWidget(self.snd)
        self.vol = NeuSlider(0, 100, round(self.store["vol"] * 100))
        self.vol.setFixedWidth(120)
        self.vol.valueChanged.connect(lambda x: (self.store.__setitem__("vol", x / 100), self.store.save()))
        row.addWidget(self.vol)
        self.sep = Sep()
        row.addWidget(self.sep)
        row.addWidget(sub("Drip", False))
        self.dsw = NeuSwitch(self.store["drip"])
        self.dsw.toggled.connect(self.set_drip_visible)
        row.addWidget(self.dsw)
        card.box.addLayout(row)
        return card

    def _tabbar(self):
        sc = QScrollArea()
        sc.setFixedHeight(66)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sc.viewport().setAutoFillBackground(False)
        inner = Canvas()
        h = QHBoxLayout(inner)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(8)
        self.tab_btns = {}
        for key, name, ic in TABS:
            b = NeuButton(name, mode="tab", ico=ic)
            b.clicked.connect(lambda _c=False, k=key: self.show_tab(k))
            self.tab_btns[key] = b
            h.addWidget(b)
        h.addStretch(1)
        sc.setWidget(inner)
        self.tab_scroll = sc
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(sc)
        return lay

    # ---------- theme ----------
    def restyle(self):
        QApplication.instance().setStyleSheet(qss())
        self.drip.cache.clear()
        for w in self.findChildren(QWidget):
            w.update()

    # ---------- modes ----------
    def set_role(self, role, remember=True):
        self.role = role
        if remember:
            self.store["role"] = role
            self.store.save()
        name, _d, _i, tabs = ROLES[role]
        self.chip.setText(name + " ▾")
        for k, b in self.tab_btns.items():
            b.setVisible(k in tabs)                       # removed, not disabled
        for b in self.ctl:
            b.setVisible(role != "consumer")
        if self.current not in tabs:
            self.show_tab("overview")

    def change_role(self):
        dlg = RoleDialog(self.store, self, cancel=True, current=self.role)
        if dlg.exec() and dlg.choice:
            self.set_role(dlg.choice)

    def start(self, hidden=False):
        saved = self.store["role"]
        if hidden and saved in ("consumer", "team") and self.tray is not None:
            self.set_role(saved)
            return
        self.show()
        if not saved:
            self.set_role("consumer", False)
            dlg = RoleDialog(self.store, self, cancel=False)
            dlg.exec()
            self.set_role(dlg.choice or "consumer")
        elif saved == "dev":
            self.set_role("consumer", False)
            dlg = RoleDialog(self.store, self, cancel=False, ask_dev=True)
            dlg.exec()
            self.set_role(dlg.choice or "consumer")
        else:
            self.set_role(saved if saved in ROLES else "consumer")

    # ---------- tabs ----------
    def show_tab(self, key):
        if key not in self.pages or key not in ROLES[self.role][3]:
            key = "overview"
        self.current = key
        self.stack.setCurrentWidget(self.pages[key][1])
        for k, b in self.tab_btns.items():
            b.setChecked(k == key)

    # ---------- demo ----------
    def toggle_demo(self):
        if self.link.demo:
            self.link.stop_demo()
            for k in [k for k in self.engine.nodes if k.startswith("demo-")]:
                del self.engine.nodes[k]
            self.engine.nodes_changed.emit()
        else:
            self.engine.hist.clear()
            self.engine.last_lvl = 0
            self.link.start_demo()
        self.on_conn(self.link.connected, "Demo data" if self.link.demo else "Not connected")

    def set_scen(self, k):
        self.link.scen = k
        self.engine.message.emit("Demo scenario: " + {"normal": "Normal", "partial": "Partial valve", "rain": "Rain", "both": "Blockage + rain", "over": "Overflow"}[k])

    def on_conn(self, ok, label):
        self.conn.set_state(label, "#22b573" if ok else ("#e8b422" if self.link.demo else "mu"))
        if ok != self.was_ok:
            self.sound.play("connect" if ok else "disconnect")
            if ok:
                self.do_flash("wave", 2200, "Board connected.")
            self.was_ok = ok
        self.b_demo.setChecked(self.link.demo)
        self.pages["overview"][0].scen_row.setVisible(self.link.demo)

    def on_banner(self, show, text):
        self.banner.setVisible(show)
        self.banner.t.setText(text)

    # ---------- Drip ----------
    def say(self, text, ms=4500):
        self.drip.say(text, ms)

    def set_drip_visible(self, on):
        self.store["drip"] = bool(on)
        self.store.save()
        self.drip.setVisible(on)

    def do_flash(self, state, ms, text):
        self.flash_state, self.flash_until = state, time.time() + ms / 1000
        self.sync_drip()
        if text:
            self.drip.say(text)
        QTimer.singleShot(ms + 50, self.sync_drip)

    def sync_drip(self):
        now = time.time()
        n = self.flash_state if now < self.flash_until else self.engine.drip_state()
        rain = bool(self.engine.prev_rain)
        self.drip.calm = self.store["calm"]
        if n != self.cur_drip or rain != self.cur_rain:
            changed = n != self.cur_drip
            self.cur_drip, self.cur_rain = n, rain
            self.drip.set_state(n, rain)
            if changed and n in MSG and now >= self.flash_until:
                self.drip.say(drip_core.line(n) or MSG[n])
        if self.link.connected and self.engine.last_rx and now - self.engine.last_rx > 5:
            self.engine.message.emit("No data for %d s: check cable and firmware" % round(now - self.engine.last_rx))

    def drip_tap(self):
        self.drip.say(drip_core.reply("status", self.engine.chat_ctx())[0], 7000)
        self.do_flash("happy", 1400, "")

    def act(self, a):
        if a == "baseline": self.engine.start_baseline()
        elif a == "demo": self.toggle_demo()
        elif a == "mute": self.store["mute"] = True; self.store.save(); self.snd.setChecked(False)
        elif a == "unmute": self.store["mute"] = False; self.store.save(); self.snd.setChecked(True)
        elif a == "ack": self.engine.acknowledge()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.root.width(), self.root.height()
        if not self.drip.drag:
            if getattr(self, "_drip_placed", False):
                x = max(0, min(self.drip.x(), w - self.drip.width()))
            else:
                x, self._drip_placed = w - self.drip.width() - 6, True
            self.drip.move(int(x), int(h - self.drip.height() + 18))
            self.drip.falling = True

    # ---------- update bar, language, text size ----------
    def _update_bar(self):
        self.upd_bar = NeuCard(pad=(18, 10, 18, 10))
        row = QHBoxLayout()
        self.upd_text = QLabel("")
        self.upd_url = ""
        go, later = NeuButton("Download", main=True), NeuButton("Later")
        go.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.upd_url)))
        later.clicked.connect(self.upd_bar.hide)
        row.addWidget(self.upd_text, 1)
        row.addWidget(go)
        row.addWidget(later)
        self.upd_bar.box.addLayout(row)
        self.upd_bar.hide()
        return self.upd_bar

    def check_updates(self, label=None, manual=False):
        self._upd_label, self._upd_manual = label, manual
        if label is not None:
            label.setText(i18n.tr("Checking…"))
        threading.Thread(target=lambda: self._upd.done.emit(updater.check()), daemon=True).start()

    def on_update_result(self, r):
        lab = self._upd_label if self._upd_manual else None
        if r.get("error"):
            if lab is not None:
                lab.setText("Could not check: " + r["error"])
        elif r.get("newer"):
            self.upd_url = r["url"]
            self.upd_text.setText("FlowBeacon %s is available (you have %s)." % (r["latest"], r["current"]))
            self.upd_bar.show()
            if lab is not None:
                lab.setText("Version %s is available." % r["latest"])
        elif lab is not None:
            lab.setText("You have the latest version (%s)." % r["current"])

    def apply_language(self):
        i18n.apply(self)
        for w in self.findChildren(QWidget):
            w.update()
        for k in ("history", "map"):
            pg = self.pages[k][0]
            (pg.refresh if k == "history" else pg.render)() if pg.isVisible() else None

    def set_language(self, lang):
        self.store["lang"] = lang
        self.store.save()
        i18n.set_lang(lang)
        self.apply_language()

    def set_zoom(self, z):
        self.store["zoom"] = float(z)
        self.store.save()
        i18n.set_zoom(z)
        self.apply_language()

    # ---------- tray icon and desktop notifications ----------
    def _make_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(ASSETS / "icon.png")), self)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("Open FlowBeacon").triggered.connect(self.bring_up)
        self.tray_menu.addAction("Quit").triggered.connect(self.quit_app)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(lambda r: self.bring_up() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.setToolTip("FlowBeacon")
        self.tray.show()

    def on_notify(self, title, body):
        if self.tray is not None:
            self.tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Warning, 8000)

    def bring_up(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self._quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, e):
        if self.store["tray"] and self.tray is not None and not self._quitting:
            e.ignore()
            self.hide()
            if not self._tray_told:
                self._tray_told = True
                self.tray.showMessage("FlowBeacon", "Still running in the tray. Alerts will keep coming.", QSystemTrayIcon.MessageIcon.Information, 5000)
            return
        try:
            self.history.close()
        except Exception:  # noqa: BLE001
            pass
        e.accept()
