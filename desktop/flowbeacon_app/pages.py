"""The app's tabs, laid out like the web app: same cards, same order, same wording."""
import csv
import time
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QTextBrowser,
                               QVBoxLayout, QWidget)

from . import __version__, core, drip_core
from .controls import (ConnChip, H2, Inset, Knob, NeuButton, NeuCard, NeuCombo, NeuField, NeuSlider, NeuSwitch, Orb, Seg,
                       Swatch, sub)
from .engine import WZ_STEPS
from .i18n import tr, tr_ev
from .link import Link
from .neu import Canvas, NeuItem, tiles
from .palettes import ACCENTS
from .store import pw_hash
from .theme import THEME, font
from .widgets import ChartWidget, DrainView

DL = {"dropWarn": (5, 90, 1, "%", "Flow drop: possible (%)"), "dropBlock": (10, 95, 1, "%", "Flow drop: blockage (%)"),
      "rise": (0.2, 5, 0.1, "cm", "Level rise warning (cm)"), "risk": (1, 20, 0.5, "cm", "Overflow risk distance (cm)"),
      "over": (0.5, 10, 0.5, "cm", "Overflow distance (cm)"), "turb": (5, 100, 1, "%", "Turbidity change (%)")}


def hbox(*items, gap=12, align=Qt.AlignmentFlag.AlignVCenter):
    l = QHBoxLayout()
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(gap)
    for it in items:
        if it is None:
            l.addStretch(1)
        elif isinstance(it, tuple):          # (widget, stretch)
            l.addWidget(it[0], it[1])
        else:
            l.addWidget(it, 0, align)
    return l


def flabel(text):
    """Small uppercase field label (the web app's `label`)."""
    l = QLabel(text.upper())
    l.setProperty("sub", "true")
    l.setFont(font(11, True, 0.7))
    return l


def tiny(text):
    return sub(text)


class Page(Canvas):
    def __init__(self):
        super().__init__()
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(26, 10, 26, 44)
        self.v.setSpacing(22)

    def two(self, a, b, ratio=(1, 1)):
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(22)
        g.addWidget(a, 0, 0)
        g.addWidget(b, 0, 1)
        g.setColumnStretch(0, ratio[0])
        g.setColumnStretch(1, ratio[1])
        self.v.addLayout(g)


# ---------------------------------------------------------------- small custom pieces
class Pill(NeuItem, QLabel):
    neu_margin = 0

    def __init__(self, text, color):
        super().__init__(text)
        self.setFont(font(12, True))
        self.setStyleSheet("color:%s;padding:0 12px" % color)
        self.setFixedHeight(26)

    def neu_paint(self, p, r):
        tiles().draw(p, "conn30", r)


class Tile(NeuItem, QWidget):
    """A drain tile in the Drains card."""
    neu_margin = 20

    def __init__(self, name):
        super().__init__()
        self.setFixedSize(190, 64)
        self.name, self.status, self.color = name, "No data", "#948a82"

    def set_state(self, name, status, color):
        self.name, self.status, self.color = name, status, color
        self.update()

    def neu_paint(self, p, r):
        tiles().draw(p, "card", r)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(16, 15, 11, 11)
        p.setPen(THEME.c("tx"))
        p.setFont(font(14, True))
        p.drawText(QRectF(34, 8, 150, 22), Qt.AlignmentFlag.AlignVCenter, self.name)
        p.setPen(THEME.c("mu"))
        p.setFont(font(12))
        p.drawText(QRectF(16, 34, 170, 20), Qt.AlignmentFlag.AlignVCenter, self.status)


class Kpi(NeuCard):
    """Stat tile: dot + small caps label, big number with unit, baseline line, accent underline."""

    def __init__(self, title, unit=""):
        super().__init__(pad=(24, 18, 24, 20))
        self.title = title.upper()
        self.top = QLabel("")
        self.top.setFixedHeight(16)
        self.box.addWidget(self.top)
        self.val = QLabel("–")
        self.val.setFont(font(34, True))
        self.unit = QLabel(unit)
        self.unit.setProperty("sub", "true")
        row = hbox(self.val, self.unit, None, gap=8, align=Qt.AlignmentFlag.AlignBottom)
        self.box.addLayout(row)
        self.base = sub("Baseline not set")
        self.box.addWidget(self.base)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = THEME.c("ac")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(24, 18, 8, 8)
        p.setFont(font(11, True, 1.3))
        p.setPen(THEME.c("mu"))
        p.drawText(QRectF(40, 14, self.width() - 50, 16), Qt.AlignmentFlag.AlignVCenter, self.title)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 18, 18)
        p.setClipPath(path)
        g = QLinearGradient(0, 0, self.width(), 0)
        c.setAlphaF(0.7)
        g.setColorAt(0, c)
        c2 = QColor(c)
        c2.setAlphaF(0.0)
        g.setColorAt(0.7, c2)
        p.fillRect(QRectF(0, self.height() - 3, self.width(), 3), g)
        p.end()


class Banner(QFrame):
    """Flashing alarm bar."""
    ack = Signal()

    def __init__(self):
        super().__init__()
        self.t = QLabel("")
        self.t.setStyleSheet("color:white;font-weight:bold")
        self.t.setWordWrap(True)
        b = NeuButton("Acknowledge")
        b.setStyleSheet("QPushButton{color:#a8212e;background:white;border-radius:18px;padding:0 18px}")
        b.neu_paint = lambda p, r: None
        b.clicked.connect(self.ack.emit)
        l = QHBoxLayout(self)
        l.setContentsMargins(22, 12, 22, 12)
        l.addWidget(self.t, 1)
        l.addWidget(b)
        self.phase = 0.0
        self.hide()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        a, b = QColor("#a8212e"), QColor("#d6483f")
        k = (1 - abs(((time.time() * 1.0) % 2) - 1))
        c = QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k), int(a.blue() + (b.blue() - a.blue()) * k))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(self.rect(), 18, 18)
        p.end()


# ---------------------------------------------------------------- Overview
class Overview(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        e = ctx.engine
        st = NeuCard()
        self.orb = Orb()
        self.cond = QLabel("Waiting for data")
        self.cond.setFont(font(26, True))
        self.cause, self.evid, self.pred, self.hl = sub("Connect the board or start demo mode."), sub(), sub(), sub()
        self.mlt = sub()
        self.pred.setStyleSheet("color:%s" % THEME.pal()["ac"])
        col = QVBoxLayout()
        col.setSpacing(2)
        for w in (self.cond, self.cause, self.evid, self.pred, self.hl, self.mlt):
            col.addWidget(w)
        self.pills = hbox(gap=8)
        col.addLayout(self.pills)
        st.box.addLayout(hbox(self.orb, (self._wrap(col), 1), gap=22, align=Qt.AlignmentFlag.AlignTop))
        self.msg = sub("")
        st.box.addWidget(self.msg)
        self.scen_row = QWidget()
        sl = QHBoxLayout(self.scen_row)
        sl.setContentsMargins(0, 4, 0, 0)
        sl.setSpacing(12)
        sl.addWidget(sub("Demo scenario:", False))
        self.scen = Seg([("normal", "Normal"), ("partial", "Partial valve"), ("rain", "Rain"), ("both", "Blockage + rain"), ("over", "Overflow")])
        self.scen.picked.connect(ctx.set_scen)
        sl.addWidget(self.scen)
        sl.addStretch(1)
        self.scen_row.hide()
        st.box.addWidget(self.scen_row)
        dr = NeuCard("Drains")
        self.tile = Tile(ctx.store["node"])
        dr.box.addLayout(hbox(self.tile, None))
        self.more = sub("")
        dr.box.addWidget(self.more)
        e.nodes_changed.connect(self.show_more)
        self.rn = NeuField(ctx.store["node"])
        rb = NeuButton("Rename")
        rb.clicked.connect(self.rename)
        dr.box.addLayout(hbox((self.rn, 1), rb))
        self.two(st, dr, (115, 100))
        g = QGridLayout()
        g.setHorizontalSpacing(22)
        g.setContentsMargins(0, 0, 0, 0)
        self.k_flow, self.k_dist, self.k_turb = Kpi("Water flow", "L/min"), Kpi("Distance to water surface", "cm"), Kpi("Turbidity", "units")
        self.k_rain = Kpi("Rain sensor plate")
        self.k_rain.base.setText("Wet or dry only")
        for i, k in enumerate((self.k_flow, self.k_dist, self.k_turb, self.k_rain)):
            g.addWidget(k, 0, i)
            g.setColumnStretch(i, 1)
        self.v.addLayout(g)
        self.v.addStretch(1)
        e.updated.connect(self.on_update)
        e.message.connect(self.msg.setText)
        ctx.link.message.connect(self.msg.setText)

    @staticmethod
    def _wrap(layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def show_more(self):
        icons = ["✓", "?", "▲", "■", "✖"]
        self.more.setText("\n".join("%s · %s %s" % (n["name"], icons[n["lvl"]], tr(core.LEVELS[n["lvl"]][0])) for n in self.ctx.engine.nodes.values()))

    def rename(self):
        n = self.rn.text().strip() or "Drain 1"
        self.ctx.store["node"] = n
        self.ctx.store.save()
        self.tile.set_state(n, self.tile.status, self.tile.color)

    def on_update(self, u):
        d, r, b = u["d"], u["r"], self.ctx.engine.base
        self.cond.setText("%s %s" % (u["icon"], u["name"]))
        self.cond.setStyleSheet("color:%s" % u["color"])
        self.orb.set_color(u["color"])
        self.cause.setText(tr(r["cause"]))
        self.evid.setText(tr_ev(" · ".join(r["ev"])) or tr("Readings match baseline" if b else "Set a baseline while flow is normal"))
        self.pred.setText(tr(u["pred"]))
        self.mlt.setText(u.get("ml", ""))
        self.hl.setText((tr("Sensor check") + ": " + "; ".join(u["issues"])) if u["issues"] else tr("Sensors look healthy"))
        self.hl.setStyleSheet("color:#e8761f" if u["issues"] else "")
        while self.pills.count():
            it = self.pills.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if r["lvl"]:
            self.pills.addWidget(Pill("Severity: %s" % u["sev"], u["color"]))
            self.pills.addWidget(Pill("Confidence: %d%% (estimate)" % r["conf"], "#fc8068"))
            self.pills.addStretch(1)
        self.tile.set_state(self.ctx.store["node"], "%s %s" % (u["icon"], u["name"]), u["color"])
        self.k_flow.val.setText("%.2f" % d["flow"])
        self.k_dist.val.setText("%.1f" % d["dist"])
        self.k_turb.val.setText("%d" % round(d["turb"]))
        self.k_rain.val.setText("Wet" if d["rain"] else "Dry")
        if b:
            self.k_flow.base.setText("Baseline %.2f" % b["flow"])
            self.k_dist.base.setText("Baseline %.1f cm" % b["dist"])
            self.k_turb.base.setText("Baseline %d" % round(b["turb"]))


# ---------------------------------------------------------------- Drain model
class Model(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        c1 = NeuCard("Drain model")
        fr = Inset(8)
        self.drain = DrainView()
        fr.box.setContentsMargins(0, 0, 0, 0)
        fr.box.addWidget(self.drain)
        c1.box.addWidget(fr)
        c2 = NeuCard()
        self.win = NeuCombo([("Last 90", 90), ("Last 300", 300), ("Last 900", 900)])
        self.win.setFixedWidth(150)
        self.win.currentIndexChanged.connect(lambda _i: self.chart.set_history(ctx.engine.hist, self.win.currentData()))
        c2.box.addLayout(hbox(H2("Trend"), None, self.win))
        ch = Inset(8)
        self.chart = ChartWidget()
        ch.box.addWidget(self.chart)
        c2.box.addWidget(ch)
        leg = QLabel('<span style="color:%s">Flow</span> and <span>water level</span>' % THEME.pal()["ac"])
        leg.setFont(font(12))
        c2.box.addWidget(leg)
        self.two(c1, c2)
        self.v.addStretch(1)
        ctx.engine.updated.connect(self.on_update)

    def on_update(self, u):
        d, b, c = u["d"], self.ctx.engine.base, self.ctx.engine.cfg
        ref, over = (b["dist"] if b else 15) + 3, c["over"]
        p = max(0.0, min(1.0, 1 - (d["dist"] - over) / max(ref - over, 1)))
        fl = d["flow"] / b["flow"] if b and b["flow"] > 0 else (1 if d["flow"] > 0 else 0)
        tb = (d["turb"] / b["turb"] - 1) / 1.2 if b and b["turb"] > 0 else (d["turb"] - 800) / 800
        self.drain.set_values(p, fl if d["flow"] > 0.05 else 0, u["r"]["fd"] >= c["dropWarn"] / 100, tb, bool(d["rain"]), self.ctx.store["calm"])
        self.chart.set_history(self.ctx.engine.hist, self.win.currentData())


# ---------------------------------------------------------------- Incidents
class Incidents(Page):
    HEAD = ["Time", "Drain", "Condition", "Likely cause", "Sensor evidence", "Severity", "Confidence %"]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        c1 = NeuCard()
        self.flt = NeuCombo([("All", 0), ("Warning+", 2), ("Risk+", 3)])
        self.flt.setFixedWidth(130)
        self.flt.currentIndexChanged.connect(self.refresh)
        b_pdf, b_csv, b_clr = NeuButton("PDF report"), NeuButton("CSV"), NeuButton("Clear")
        b_pdf.clicked.connect(self.export_pdf)
        b_csv.clicked.connect(self.export_csv)
        b_clr.clicked.connect(self.clear)
        c1.box.addLayout(hbox(H2("Incident reports"), None, self.flt, b_pdf, b_csv, b_clr))
        self.log = Inset(8)
        self.log.box.setSpacing(12)
        self.log.setMinimumHeight(280)
        c1.box.addWidget(self.log)
        self.log.box.addStretch(1)
        c2 = NeuCard("Test recording")
        c2.box.addWidget(flabel("Label for this session"))
        self.lab = NeuCombo([(n, n) for n in ("normal", "partial valve", "heavy valve", "rain", "overflow")])
        c2.box.addWidget(self.lab)
        self.rb, self.rs = NeuButton("Start recording"), NeuButton("Save CSV")
        self.rn = sub("", False)
        self.rb.clicked.connect(self.toggle_rec)
        self.rs.clicked.connect(self.save_rec)
        c2.box.addLayout(hbox(self.rb, self.rs, self.rn))
        c2.box.addWidget(sub("Saved files are labelled data you can use later to train a TinyML model."))
        c2.box.addSpacing(6)
        c2.box.addWidget(H2("Calibration wizard"))
        self.wt = sub("Press Calibration to start.")
        c2.box.addWidget(self.wt)
        self.wb, self.wa = NeuButton("Record step"), NeuButton("Apply thresholds")
        self.wb.clicked.connect(ctx.engine.wizard_record)
        self.wa.clicked.connect(ctx.engine.wizard_apply)
        c2.box.addLayout(hbox(self.wb, self.wa))
        self.wb.hide()
        self.wa.hide()
        self.two(c1, c2)
        self.v.addStretch(1)
        ctx.engine.incidents_changed.connect(self.refresh)
        ctx.engine.wizard_changed.connect(self.wiz_ui)
        ctx.engine.updated.connect(lambda _u: self.rn.setText("%d rows" % len(ctx.engine.rec)) if ctx.engine.rec is not None else None)
        self.refresh()

    def rows(self):
        m = self.flt.currentData() or 0
        return [i for i in self.ctx.store["inc"] if i["lvl"] >= m]

    def refresh(self, *_):
        lay = self.log.box
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        rows = self.rows()
        if not rows:
            lay.addWidget(sub("No incidents recorded."))
        for i in rows[:60]:
            row = QFrame()
            c = i["c"]
            row.setStyleSheet("QFrame{border-left:6px solid %s;border-radius:6px}" % c)
            html = ('<b style="color:%s">%s · %s</b> · %s severity, %s%% confidence<br>%s<br><span style="color:%s">%s<br>%s</span>'
                    % (c, self.ctx.store["node"], i["cond"], i["sev"], i["conf"], i["cause"], THEME.pal()["mu"], i["ev"], i["time"].replace("T", " ")))
            lab = QLabel(html)
            lab.setWordWrap(True)
            lab.setFont(font(12))
            lab.setStyleSheet("border:none;padding-left:8px")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(8, 8, 8, 8)
            rl.addWidget(lab)
            lay.addWidget(row)
        lay.addStretch(1)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export incidents", "drainage-incidents.csv", "CSV (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf8") as f:
                w = csv.writer(f)
                w.writerow(self.HEAD)
                for i in self.ctx.store["inc"]:
                    w.writerow([i["time"], self.ctx.store["node"], i["cond"], i["cause"], i["ev"], i["sev"], i["conf"]])

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Incident report", "flowbeacon-report.pdf", "PDF (*.pdf)")
        if not path:
            return
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
        rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % esc(v) for v in (i["time"].replace("T", " "), self.ctx.store["node"], i["cond"], i["cause"], i["ev"], i["sev"], i["conf"])) for i in self.ctx.store["inc"])
        doc = QTextDocument()
        doc.setHtml("<h1>FlowBeacon: incident report</h1><p>Generated %s. Prototype estimates, not confirmed measurements.</p><table border='1' cellspacing='0' cellpadding='4'><tr>%s</tr>%s</table>"
                    % (datetime.now().strftime("%Y-%m-%d %H:%M"), "".join("<th>%s</th>" % h for h in self.HEAD), rows))
        doc.print_(QPdfWriter(path))

    def clear(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "FlowBeacon", "Clear all saved incidents?") == QMessageBox.StandardButton.Yes:
            self.ctx.store["inc"] = []
            self.ctx.store.save()
            self.refresh()

    def toggle_rec(self):
        e = self.ctx.engine
        if e.rec is None:
            e.rec = []
            self.rb.setText("Stop recording")
        else:
            self.rb.setText("Start recording")
            self.rn.setText("%d rows" % len(e.rec))

    def save_rec(self):
        e = self.ctx.engine
        if not e.rec:
            self.rn.setText("Nothing recorded yet")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save recording", "flowbeacon-%s.csv" % self.lab.currentData().replace(" ", "-"), "CSV (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf8") as f:
                w = csv.writer(f)
                w.writerow(["time", "label", "flow", "dist", "turb", "rain", "condition"])
                for r in e.rec:
                    w.writerow([r[0], self.lab.currentData()] + r[1:])
            e.rec = None
            self.rb.setText("Start recording")
            self.rn.setText("Saved")

    def wiz_ui(self):
        wz = self.ctx.engine.wz
        done = wz["step"] >= len(WZ_STEPS)
        if not wz.get("on"):
            self.wt.setText("Press Calibration to start.")
        elif done:
            s = wz["sug"]
            self.wt.setText("Done. Suggested: flow drop %d%% / %d%%, level rise %s cm." % (s["dropWarn"], s["dropBlock"], s["rise"]))
        elif wz["buf"] is not None:
            self.wt.setText("Recording step %d… keep conditions steady for 10 readings." % (wz["step"] + 1))
        else:
            self.wt.setText("Step %d of 4: %s. Set it up, then record." % (wz["step"] + 1, WZ_STEPS[wz["step"]]))
        self.wb.setVisible(bool(wz.get("on")) and not done)
        self.wa.setVisible(bool(wz.get("on")) and done)


# ---------------------------------------------------------------- Connection
class Connection(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        link, st = ctx.link, ctx.store
        c1 = NeuCard("Connection")
        self.tabs = Seg([("usb", "USB")])
        self.tabs.picked.connect(self.pick)
        c1.box.addLayout(hbox(self.tabs, None))
        self.usb = QWidget()
        ul = QVBoxLayout(self.usb)
        ul.setContentsMargins(0, 6, 0, 0)
        ul.addWidget(sub("Plug in the Arduino Nano and pick its port, then press Connect. It reconnects by itself if the cable is pulled."))
        self.port = NeuCombo()
        rf, self.bu = NeuButton("Refresh"), NeuButton("Connect")
        rf.clicked.connect(self.refresh_ports)
        self.bu.clicked.connect(self.toggle_usb)
        ul.addLayout(hbox((self.port, 1), rf, self.bu))
        ul.addWidget(sub("On Linux, if the port cannot be opened, add your user to the dialout group and log in again."))
        c1.box.addWidget(self.usb)
        self.wifi = QWidget()
        wl = QVBoxLayout(self.wifi)
        wl.setContentsMargins(0, 6, 0, 0)
        wl.setSpacing(8)
        wl.addWidget(flabel("Wi-Fi name"))
        self.ssid = NeuField(st["ssid"])
        wl.addWidget(self.ssid)
        wl.addWidget(flabel("Wi-Fi password"))
        self.pw = NeuField(password=True)
        show = NeuButton("Show")
        show.clicked.connect(lambda: self.pw.setEchoMode(self.pw.EchoMode.Normal if self.pw.echoMode() == self.pw.EchoMode.Password else self.pw.EchoMode.Password))
        wl.addLayout(hbox((self.pw, 1), show))
        sb = NeuButton("Send to board over USB")
        sb.clicked.connect(self.send_wifi)
        wl.addLayout(hbox(sb, None))
        wl.addWidget(flabel("Board address (IP)"))
        self.ip = NeuField(st["ip"], "192.168.1.45")
        self.bw = NeuButton("Connect")
        self.bw.clicked.connect(self.toggle_ws)
        wl.addLayout(hbox((self.ip, 1), self.bw))
        self.wmsg = sub()
        wl.addWidget(self.wmsg)
        self.wifi.hide()
        c1.box.addWidget(self.wifi)
        c2 = NeuCard("SMS alerts")
        self.sms_on = NeuSwitch(st["sms"]["on"])
        c2.box.addLayout(hbox(QLabel("Send SMS alerts"), None, self.sms_on))
        c2.box.addWidget(flabel("Mobile numbers (separate with commas)"))
        self.sms_num = NeuField(st["sms"]["nums"], "+91 98765 43210")
        c2.box.addWidget(self.sms_num)
        self.sms_min = NeuCombo([("Blockage warning or worse", 2), ("Overflow risk or worse", 3), ("Overflow detected only", 4)])
        self.sms_min.setCurrentIndex(max(0, self.sms_min.findData(st["sms"]["min"])))
        self.sms_cool = NeuCombo([("1 minute", 1), ("5 minutes", 5), ("10 minutes", 10), ("30 minutes", 30)])
        self.sms_cool.setCurrentIndex(max(0, self.sms_cool.findData(st["sms"]["cool"])))
        a, b = QVBoxLayout(), QVBoxLayout()
        a.addWidget(flabel("Send when")); a.addWidget(self.sms_min)
        b.addWidget(flabel("Wait between SMS")); b.addWidget(self.sms_cool)
        g = QHBoxLayout(); g.setSpacing(14); g.addLayout(a, 1); g.addLayout(b, 1)
        c2.box.addLayout(g)
        bt = NeuButton("Send test SMS")
        bt.clicked.connect(self.test_sms)
        c2.box.addLayout(hbox(bt, None))
        self.sms_log = Inset(10)
        self.sms_log.setMinimumHeight(90)
        self.sms_txt = sub("")
        self.sms_log.box.addWidget(self.sms_txt)
        c2.box.addWidget(self.sms_log)
        self.sms_on.toggled.connect(self.save_sms)
        self.sms_num.textChanged.connect(self.save_sms)
        self.sms_min.currentIndexChanged.connect(self.save_sms)
        self.sms_cool.currentIndexChanged.connect(self.save_sms)
        self.two(c1, c2)
        self.v.addStretch(1)
        link.connection.connect(self.on_conn)
        link.board_ip.connect(self.on_ip)
        link.wifi_failed.connect(lambda: self.wmsg.setText("The board could not join that Wi-Fi. Check the name and password."))
        self.refresh_ports()

    def pick(self, k):
        self.usb.setVisible(k == "usb")
        self.wifi.setVisible(k == "wifi")

    def refresh_ports(self):
        self.port.clear()
        for name, desc in Link.ports():
            self.port.addItem("%s  (%s)" % (name, desc), name)

    def toggle_usb(self):
        if self.ctx.link.usb_open:
            self.ctx.link.stop_all()
        elif self.port.currentData():
            self.ctx.link.open_serial(self.port.currentData())
        else:
            self.ctx.link.message.emit("No serial port found. Plug in the board and press Refresh.")

    def toggle_ws(self):
        l = self.ctx.link
        if l.ws_auto:
            l.stop_all()
        else:
            self.ctx.store["ip"] = self.ip.text().strip()
            self.ctx.store.save()
            l.open_ws(self.ip.text())

    def on_conn(self, ok, label):
        self.bu.setText("Disconnect" if self.ctx.link.usb_open else "Connect")
        self.bw.setText("Disconnect" if self.ctx.link.ws_auto else "Connect")

    def on_ip(self, ip):
        self.ip.setText(ip)
        self.ctx.store["ip"] = ip
        self.ctx.store.save()
        self.wmsg.setText("Board joined Wi-Fi. Address: %s. Press Connect." % ip)

    def send_wifi(self):
        n = self.ssid.text().strip()
        if not n:
            self.wmsg.setText("Enter the Wi-Fi name.")
        elif not self.ctx.link.usb_open:
            self.wmsg.setText("Connect the board over USB first, then send the Wi-Fi details.")
        else:
            self.ctx.store["ssid"] = n
            self.ctx.store.save()
            self.ctx.link.send({"cmd": "wifi", "ssid": n, "pass": self.pw.text()})
            self.wmsg.setText("Sent. Waiting for the board to join Wi-Fi…")

    def save_sms(self, *_):
        self.ctx.store["sms"] = {"on": self.sms_on.isChecked(), "nums": self.sms_num.text(), "min": self.sms_min.currentData(), "cool": self.sms_cool.currentData()}
        self.ctx.store.save()

    def test_sms(self):
        self.sms_txt.setText(time.strftime("%H:%M:%S  ") + self.ctx.engine.sms_send("FlowBeacon: test message from the app."))


# ---------------------------------------------------------------- Calibration
class Calibration(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.knobs, self.vals = ctx, {}, {}
        c = NeuCard("Calibration dials")
        g = QGridLayout()
        g.setHorizontalSpacing(34)
        g.setVerticalSpacing(26)
        for i, (k, (mn, mx, step, unit, label)) in enumerate(DL.items()):
            kn = Knob(mn, mx, step, ctx.engine.cfg[k])
            kn.changed.connect(lambda v, k=k: self.on_knob(k, v))
            val = QLabel()
            val.setFont(font(15, True))
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb = flabel(label)
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setWordWrap(True)
            lb.setFixedWidth(150)
            col = QVBoxLayout()
            col.setSpacing(10)
            col.addWidget(kn, 0, Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(val)
            col.addWidget(lb, 0, Qt.AlignmentFlag.AlignHCenter)
            g.addLayout(col, i // 6, i % 6)
            self.knobs[k], self.vals[k] = kn, val
        c.box.addLayout(g)
        rd = NeuButton("Reset thresholds")
        rd.clicked.connect(ctx.engine.reset_cfg)
        c.box.addLayout(hbox(rd, None))
        c.box.addWidget(sub("Turn a dial by dragging it, using the mouse wheel, or the arrow keys. Tune them with normal-flow readings and partial-valve tests. Everything is saved automatically."))
        self.v.addWidget(c)
        self.v.addStretch(1)
        ctx.engine.config_changed.connect(self.load)
        self.load()

    def load(self):
        for k, kn in self.knobs.items():
            kn.set_value(self.ctx.engine.cfg[k])
            self.vals[k].setText("%g %s" % (self.ctx.engine.cfg[k], DL[k][3]))

    def on_knob(self, k, v):
        self.ctx.engine.set_cfg(k, v)
        self.vals[k].setText("%g %s" % (v, DL[k][3]))


# ---------------------------------------------------------------- Ask Drip
class AskDrip(Page):
    action = Signal(str)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        c = NeuCard("Ask Drip")
        c.box.addWidget(sub("Drip answers offline. Try: status, why, when will it overflow, tip, help."))
        fr = Inset(10)
        self.log = QTextBrowser()
        self.log.setMinimumHeight(340)
        self.log.setFont(font(13))
        self.log.setHtml("<p><b>Drip:</b> %s</p>" % drip_core.HELP)
        fr.box.addWidget(self.log)
        c.box.addWidget(fr)
        self.inp = NeuField("", "Ask Drip…")
        self.inp.returnPressed.connect(self.ask)
        b = NeuButton("Ask", main=True)
        b.clicked.connect(self.ask)
        c.box.addLayout(hbox((self.inp, 1), b))
        self.v.addWidget(c)
        self.v.addStretch(1)

    def ask(self):
        t = self.inp.text().strip()
        if not t:
            return
        self.inp.clear()
        text, act = drip_core.reply(t, self.ctx.engine.chat_ctx())
        esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
        self.log.append("<p style='color:%s'><b>You:</b> %s</p><p><b>Drip:</b> %s</p>" % (THEME.pal()["mu"], esc(t), esc(text)))
        self.ctx.say(text, 7000)
        if act:
            self.action.emit(act)


# ---------------------------------------------------------------- Settings
class Settings(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, st = ctx, ctx.store
        c = NeuCard("Appearance and behaviour")
        cols = QHBoxLayout()
        cols.setSpacing(34)
        a = QVBoxLayout(); a.setSpacing(10)
        a.addWidget(flabel("Theme colour"))
        self.sw = []
        row = QHBoxLayout(); row.setSpacing(12)
        for key, name, color in ACCENTS:
            s = Swatch(key, color)
            s.setToolTip(name)
            s.setChecked(key == st["accent"])
            s.clicked.connect(lambda _c=False, k=key: self.accent(k))
            self.sw.append(s)
            row.addWidget(s)
        row.addStretch(1)
        a.addLayout(row)
        a.addSpacing(6)
        a.addWidget(flabel("Mode"))
        self.mode = NeuCombo([("Light", "light"), ("Dark", "dark"), ("Follow system", "auto")])
        self.mode.setCurrentIndex(self.mode.findData(st["mode"]))
        self.mode.currentIndexChanged.connect(lambda _i: self.set_mode(self.mode.currentData()))
        a.addWidget(self.mode)
        self.calm = NeuSwitch(st["calm"])
        self.calm.toggled.connect(lambda on: (st.__setitem__("calm", on), st.save()))
        a.addLayout(hbox(QLabel("Reduce motion"), None, self.calm))
        a.addStretch(1)
        b = QVBoxLayout(); b.setSpacing(12)
        b.addWidget(flabel("Alerts"))
        self.rows = {}
        for key, label in (("ui", "Interface sounds"), ("possible", "Possible blockage"), ("warning", "Blockage warning"), ("risk", "Overflow risk"),
                           ("overflow", "Overflow"), ("rain", "Rain"), ("predict", "Prediction")):
            sw = NeuSwitch(st["snd"].get(key, True))
            sw.toggled.connect(lambda on, k=key: (st["snd"].__setitem__(k, on), st.save()))
            b.addLayout(hbox(QLabel(label), None, sw))
        b.addStretch(1)
        d = QVBoxLayout(); d.setSpacing(10)
        d.addWidget(flabel("About"))
        d.addWidget(QLabel("FlowBeacon %s" % __version__))
        d.addWidget(sub("by TechMinds. Smart drainage monitoring and blockage prediction for the Arduino Nano prototype."))
        d.addWidget(sub("Switch between Consumer, Maintenance and Developer modes with the button in the top bar."))
        d.addStretch(1)
        for l in (a, b, d):
            cols.addLayout(l, 1)
        c.box.addLayout(cols)
        self.v.addWidget(c)
        self.v.addStretch(1)

    def accent(self, key):
        for s in self.sw:
            s.setChecked(s.key == key)
        self.ctx.store["accent"] = key
        self.ctx.store.save()
        THEME.set(accent=key)

    def set_mode(self, m):
        self.ctx.store["mode"] = m
        self.ctx.store.save()
        THEME.set(mode=m)


# ---------------------------------------------------------------- Console
class Console(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        c = NeuCard("Firmware console")
        fr = Inset(10)
        self.raw = QPlainTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setMaximumBlockCount(300)
        self.raw.setMinimumHeight(180)
        self.raw.setFont(font(12))
        fr.box.addWidget(self.raw)
        c.box.addWidget(fr)
        self.cmd = NeuField("", "Command to send, e.g. restart")
        self.cmd.returnPressed.connect(self.send)
        b = NeuButton("Send")
        b.clicked.connect(self.send)
        c.box.addLayout(hbox((self.cmd, 1), b))
        c.box.addWidget(sub('Send one JSON line per second at 115200 baud: {"flow":4.2,"dist":12.5,"turb":850,"rain":0}  flow = L/min, dist = cm to water, turb = higher means dirtier, rain = 1 wet / 0 dry.'))
        pw = NeuCard("Developer access")
        self.new = NeuField("", "At least 4 characters", password=True)
        sv, rs = NeuButton("Save"), NeuButton("Reset to 1234")
        self.pm = sub()
        sv.clicked.connect(self.save_pw)
        rs.clicked.connect(self.reset_pw)
        pw.box.addLayout(hbox((self.new, 1), sv, rs))
        pw.box.addWidget(self.pm)
        self.v.addWidget(c)
        self.v.addWidget(pw)
        self.v.addStretch(1)
        ctx.link.raw.connect(lambda l: self.raw.appendPlainText(l))

    def send(self):
        t = self.cmd.text().strip()
        if t:
            if self.ctx.link.send(t):
                self.raw.appendPlainText("> " + t)
                self.cmd.clear()
            else:
                self.ctx.engine.message.emit("Connect the board first.")

    def save_pw(self):
        v = self.new.text()
        if len(v) < 4:
            self.pm.setText("At least 4 characters.")
            return
        self.ctx.store["devpw"] = pw_hash(v)
        self.ctx.store.save()
        self.new.clear()
        self.pm.setText("Password changed.")

    def reset_pw(self):
        self.ctx.store["devpw"] = ""
        self.ctx.store.save()
        self.pm.setText("Password reset to 1234.")
