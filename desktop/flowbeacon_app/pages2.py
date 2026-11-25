"""Tabs and cards the web app has that the first native version lacked: History, City map and dispatch,
Learn from recordings, Replay, Calibration profiles, and the language / notification / quiet-hours settings."""
import time
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout, QWidget

from . import autostart, citymap, history as hist_mod, i18n, ml, updater
from .controls import H2, Inset, NeuButton, NeuCard, NeuCombo, NeuField, NeuSwitch, sub
from .core import ICONS, LEVELS
from .i18n import tr
from .pages import Page, flabel, hbox
from .theme import THEME, font


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- History
class HistChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.list = []

    def set_list(self, lst):
        self.list = lst
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, v = self.width(), self.height(), self.list
        if len(v) < 2:
            p.setPen(THEME.c("mu"))
            p.setFont(font(12))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("No history yet. Readings are stored every minute while the app runs."))
            p.end()
            return

        def line(key, col, inv):
            a = [g[key] for g in v]
            mn, mx = min(a), max(a)
            if mx - mn < 0.5:
                mx = mn + 0.5
            path = QPainterPath()
            for i, y in enumerate(a):
                px = i / (len(a) - 1) * (w - 20) + 10
                q = (y - mn) / (mx - mn)
                py = (q if inv else 1 - q) * (h - 44) + 12
                path.moveTo(px, py) if i == 0 else path.lineTo(px, py)
            p.setPen(QPen(col, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        line("f", THEME.c("ac"), False)
        line("l", THEME.c("tx"), True)
        for i, g in enumerate(v):
            px = i / (len(v) - 1) * (w - 20) + 10
            p.fillRect(QRectF(px - 3, h - 18, 6, 10), QColor(LEVELS[g["lvl"]][1]))
        p.end()


class History(Page):
    def __init__(self, ctx):
        super().__init__()
        self.ctx, self.rows = ctx, []
        c = NeuCard()
        self.node = NeuCombo([("Drain 1", "drain-1")])
        self.node.setFixedWidth(180)
        self.range = NeuCombo([("24 hours", 1), ("7 days", 7), ("30 days", 30)])
        self.range.setFixedWidth(150)
        go, csv_b = NeuButton("Refresh"), NeuButton("Export CSV")
        go.clicked.connect(self.refresh)
        csv_b.clicked.connect(self.export)
        self.node.currentIndexChanged.connect(self.refresh)
        self.range.currentIndexChanged.connect(self.refresh)
        c.box.addLayout(hbox(H2("History"), None, self.node, self.range, go, csv_b))
        ins = Inset(8)
        self.chart = HistChart()
        ins.box.addWidget(self.chart)
        c.box.addWidget(ins)
        c.box.addWidget(sub("Flow (accent) and water level (dark). The coloured marks at the bottom show the worst condition of each period."))
        self.tab = QTextBrowser()
        self.tab.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.tab.setMinimumHeight(260)
        self.tab.viewport().setAutoFillBackground(False)
        c.box.addWidget(self.tab)
        self.v.addWidget(c)
        self.v.addStretch(1)
        ctx.engine.nodes_changed.connect(self.fill_nodes)

    def showEvent(self, e):
        super().showEvent(e)
        self.fill_nodes()
        self.refresh()

    def fill_nodes(self):
        e = self.ctx.engine
        ids = [("drain-1", self.ctx.store["node"])] + [(n["id"], n["name"]) for n in e.nodes.values()]
        if [self.node.itemData(i) for i in range(self.node.count())] == [i for i, _ in ids]:
            return
        cur = self.node.currentData()
        self.node.blockSignals(True)
        self.node.clear()
        for i, n in ids:
            self.node.addItem(n, i)
        k = self.node.findData(cur)
        self.node.setCurrentIndex(max(0, k))
        self.node.blockSignals(False)

    def refresh(self, *_):
        h = self.ctx.engine.history
        if h is None:
            return
        days, now = self.range.currentData() or 1, time.time() * 1000
        self.rows = h.range(self.node.currentData() or "drain-1", now - days * 86400000, now)
        lst = hist_mod.group(self.rows, days)
        self.chart.set_list(lst)
        hourly = days == 1
        fmt = (lambda t: datetime.fromtimestamp(t / 1000).strftime("%H:%M")) if hourly else (lambda t: datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d"))
        pal = THEME.pal()
        head = "<tr>%s</tr>" % "".join("<th align='left'>%s</th>" % esc(tr(x)) for x in ("Hour" if hourly else "Day", "Minutes", "Avg flow", "Level min/max (cm)", "Worst"))
        body = "".join("<tr><td>%s</td><td>%d</td><td>%.2f</td><td>%.1f / %.1f</td><td style='color:%s'>%s</td></tr>" % (
            fmt(g["t"]), g["n"], g["f"], g["lmin"], g["lmax"], LEVELS[g["lvl"]][1], esc(ICONS[g["lvl"]] + " " + tr(LEVELS[g["lvl"]][0]))) for g in reversed(lst[-14:]))
        self.tab.setHtml("<body style='color:%s'><table cellspacing='8'>%s%s</table></body>" % (pal["tx"], head, body))

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export history", "flowbeacon-history.csv", "CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf8", newline="") as f:
                f.write(hist_mod.csv_text(self.rows))


# ---------------------------------------------------------------- City map
from .tilemap import TileMap as MapCanvas  # noqa: E402  (OpenStreetMap tiles, drag and zoom)


class CityMapPage(Page):
    label = staticmethod(citymap.CityBook.label)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.city, self.sel = ctx.engine.city, None
        # PIN lock
        self.lock = NeuCard("City map is locked")
        self.pin_in = NeuField("", "Officials PIN", password=True)
        self.pin_go, self.pin_msg = NeuButton("Unlock", main=True), sub("")
        self.pin_go.clicked.connect(self.try_unlock)
        self.pin_in.returnPressed.connect(self.try_unlock)
        self.lock.box.addWidget(self.pin_in)
        self.lock.box.addLayout(hbox(self.pin_go, self.pin_msg))
        self.v.addWidget(self.lock)

        self.body = QWidget()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(22)
        # filters + map
        c = NeuCard()
        self.f_ward, self.f_zone = NeuCombo([("All wards", "")]), NeuCombo([("All zones", "")])
        self.f_stat = NeuCombo([("All statuses", "")] + [(citymap.STAT[k], k) for k in citymap.STAT])
        for f in (self.f_ward, self.f_zone, self.f_stat):
            f.setFixedWidth(170)
            f.currentIndexChanged.connect(self.render)
        self.summary = sub("", False)
        c.box.addLayout(hbox(H2("City map"), None, self.f_ward, self.f_zone, self.f_stat))
        ins = Inset(8)
        self.canvas = MapCanvas()
        self.canvas.picked.connect(self.select)
        ins.box.addWidget(self.canvas)
        c.box.addWidget(ins)
        c.box.addWidget(self.summary)
        zb, zo, zf = NeuButton("Zoom in"), NeuButton("Zoom out"), NeuButton("Fit all drains")
        zb.clicked.connect(lambda: self.canvas.zoom_by(1))
        zo.clicked.connect(lambda: self.canvas.zoom_by(-1))
        zf.clicked.connect(self.canvas.fit)
        c.box.addLayout(hbox(zb, zo, zf, None))
        c.box.addWidget(sub("Map from OpenStreetMap (free). Drag to move, scroll to zoom. Tiles you have seen are saved on this computer, so they still show offline."))
        bl.addWidget(c)
        # selected drain
        self.side = NeuCard("Selected drain")
        self.s_info = sub("Select a pin on the map or a row in the list.")
        self.side.box.addWidget(self.s_info)
        self.team = NeuCombo([])
        self.b_assign, self.b_start, self.b_done = NeuButton("Assign", main=True), NeuButton("Start work"), NeuButton("Mark resolved")
        self.b_assign.clicked.connect(self.assign)
        self.b_start.clicked.connect(self.start_work)
        self.b_done.clicked.connect(self.resolve)
        self.side.box.addLayout(hbox((self.team, 1), self.b_assign, self.b_start, self.b_done))
        self.msg = sub("")
        self.side.box.addWidget(self.msg)
        self.side.box.addWidget(flabel("Edit device"))
        self.e_name, self.e_ward, self.e_zone = NeuField("", "Name"), NeuField("", "Ward"), NeuField("", "Zone")
        self.e_lat, self.e_lng = NeuField("", "Latitude"), NeuField("", "Longitude")
        self.side.box.addLayout(hbox((self.e_name, 2), (self.e_ward, 1), (self.e_zone, 1)))
        sv, rm = NeuButton("Save"), NeuButton("Remove from map")
        sv.clicked.connect(self.save_dev)
        rm.clicked.connect(self.remove_dev)
        self.side.box.addLayout(hbox((self.e_lat, 1), (self.e_lng, 1), sv, rm))
        bl.addWidget(self.side)
        # list
        lc = NeuCard("Drains and incidents")
        self.table = QTextBrowser()
        self.table.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.table.setMinimumHeight(260)
        self.table.viewport().setAutoFillBackground(False)
        self.table.setOpenLinks(False)
        self.table.anchorClicked.connect(lambda u: self.select(u.toString().lstrip("#")))
        lc.box.addWidget(self.table)
        bl.addWidget(lc)
        # setup
        sc = NeuCard("Teams, officials and devices")
        self.officer = NeuField(self.city.d["officer"], "Your name (kept in the incident log)")
        self.officer.editingFinished.connect(self.set_officer)
        sc.box.addWidget(flabel("Officer name"))
        sc.box.addWidget(self.officer)
        self.new_team = NeuField("", "New team name")
        at = NeuButton("Add team")
        at.clicked.connect(self.add_team)
        self.teams_lbl = sub("")
        sc.box.addLayout(hbox((self.new_team, 1), at))
        self.team_del = NeuCombo([])
        dt = NeuButton("Remove team")
        dt.clicked.connect(self.del_team)
        sc.box.addLayout(hbox(self.teams_lbl, None, self.team_del, dt))
        self.new_id = NeuField("", "New device id, e.g. ward12-drain3")
        ad = NeuButton("Add device")
        ad.clicked.connect(self.add_dev)
        sc.box.addLayout(hbox((self.new_id, 1), ad))
        self.pin_new = NeuField("", "New PIN (at least 4 characters)", password=True)
        ps, po = NeuButton("Set PIN"), NeuButton("Remove PIN")
        ps.clicked.connect(self.set_pin)
        po.clicked.connect(self.clear_pin)
        sc.box.addLayout(hbox((self.pin_new, 1), ps, po))
        self.setup_msg = sub("")
        sc.box.addWidget(self.setup_msg)
        bl.addWidget(sc)
        self.v.addWidget(self.body)
        self.v.addStretch(1)
        ctx.engine.city_changed.connect(self.render)
        ctx.engine.nodes_changed.connect(self._soft)
        ctx.engine.updated.connect(lambda _u: self._soft())
        t = QTimer(self)
        t.timeout.connect(self._soft)
        t.start(3000)
        self.gate()

    # ---- helpers ----
    def _soft(self):
        if self.isVisible() and not self.body.isHidden():
            self.render()

    def save(self):
        self.ctx.store.save()

    def gate(self):
        locked = self.city.locked
        self.lock.setVisible(locked)
        self.body.setVisible(not locked)
        if not locked:
            self.render()

    def try_unlock(self):
        if self.city.try_unlock(self.pin_in.text()):
            self.pin_in.clear()
            self.pin_msg.setText("")
            self.gate()
        else:
            self.pin_msg.setText(tr("Wrong PIN."))

    def states(self):
        return self.city.states(self.ctx.engine.live_nodes())

    def _fill(self, combo, first, items):
        cur = combo.currentData()
        want = [("", first)] + [(i, i) for i in items]
        if [(combo.itemData(i), combo.itemText(i)) for i in range(combo.count())] == [(d, t) for d, t in want]:
            return
        combo.blockSignals(True)
        combo.clear()
        for d, t in want:
            combo.addItem(t, d)
        combo.setCurrentIndex(max(0, combo.findData(cur)))
        combo.blockSignals(False)

    # ---- drawing ----
    def render(self, *_):
        allst = self.states()
        self._fill(self.f_ward, "All wards", self.city.wards(allst))
        self._fill(self.f_zone, "All zones", self.city.zones(allst))
        st = [s for s in allst if self.city.passes(s, self.f_ward.currentData() or "", self.f_zone.currentData() or "", self.f_stat.currentData() or "")]
        ids = {s["id"] for s in st}
        incs = [i for i in self.city.d["incidents"] if i["dev"] in ids]
        self.canvas.set_states(st, self.sel)
        n_open = sum(1 for i in incs if i["status"] != "resolved")
        self.summary.setText("%d drains · %d online · %d open incidents" % (len(st), sum(1 for s in st if s["online"]), n_open))
        teams = self.city.d["teams"]
        if [self.team.itemText(i) for i in range(self.team.count())] != teams:
            self.team.clear()
            self.team_del.clear()
            for t in teams:
                self.team.addItem(t, t)
                self.team_del.addItem(t, t)
        self.teams_lbl.setText("Teams: " + ", ".join(teams))
        by = {s["id"]: s for s in allst}
        f = lambda t: datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M")  # noqa: E731
        rows = "".join("<tr><td><a href='#%s' style='color:%s'>%s</a></td><td>%s</td><td>%s</td><td style='color:%s'>%s</td></tr>" % (
            esc(s["id"]), THEME.pal()["ac"], esc(self.label(s)), esc(s["dv"].get("ward") or "Unassigned"), esc(s["dv"].get("zone") or "Unassigned"),
            citymap.STAT_COLOR[s["status"]], esc(tr(citymap.STAT[s["status"]]))) for s in st)
        irows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            f(i["start"]), esc(self.label(by[i["dev"]]) if i["dev"] in by else i["dev"]), esc(tr(citymap.LVLN[i["max"]])),
            esc(tr(citymap.INC_ST[i["status"]])), esc(i["team"] or "-")) for i in incs[:40])
        h = lambda *x: "<tr>%s</tr>" % "".join("<th align='left'>%s</th>" % esc(tr(y)) for y in x)  # noqa: E731
        self.table.setHtml("<body style='color:%s'><table cellspacing='8'>%s%s</table><br><table cellspacing='8'>%s%s</table></body>" % (
            THEME.pal()["tx"], h("Drain", "Ward", "Zone", "Status"), rows, h("Started", "Drain", "Worst", "Status", "Team"), irows))
        self.side_update(by)

    def side_update(self, by):
        s = by.get(self.sel)
        for b in (self.b_assign, self.b_start, self.b_done):
            b.setEnabled(bool(s))
        if not s:
            self.s_info.setText(tr("Select a pin on the map or a row in the list."))
            return
        l, inc = s["last"] or {}, self.city.open_inc(s["id"])
        rise = (s["base"]["dist"] - l["dist"]) if s["base"] and l.get("dist") is not None else None
        txt = "%s · %s" % (self.label(s), tr(citymap.STAT[s["status"]]))
        if l:
            txt += " · flow %.2f L/min · level %.1f cm%s" % (l.get("flow", 0), l.get("dist", 0), (" (+%.1f vs baseline)" % rise) if rise is not None else "")
        if inc:
            txt += "\n%s: %s%s" % (tr("Incident"), tr(citymap.INC_ST[inc["status"]]), (" · " + inc["team"]) if inc["team"] else "")
            txt += "\n" + "\n".join("%s  %s" % (datetime.fromtimestamp(x["t"] / 1000).strftime("%m-%d %H:%M"), x["m"]) for x in inc["log"][-4:])
        self.s_info.setText(txt)

    # ---- actions ----
    def select(self, did):
        self.sel = did
        dv = self.city.d["devices"].get(did)
        if dv:
            self.e_name.setText(dv.get("name", ""))
            self.e_ward.setText(dv.get("ward", ""))
            self.e_zone.setText(dv.get("zone", ""))
            self.e_lat.setText(str(dv["lat"]))
            self.e_lng.setText(str(dv["lng"]))
        self.render()

    def assign(self):
        st = next((s for s in self.states() if s["id"] == self.sel), None)
        if st:
            self.msg.setText(tr(self.city.assign(self.sel, self.team.currentData() or "", st["lvl"])))
            self.save()
            self.render()

    def start_work(self):
        self.city.start_work(self.sel)
        self.save()
        self.render()

    def resolve(self):
        from PySide6.QtWidgets import QMessageBox
        if self.city.open_inc(self.sel) and QMessageBox.question(self, "FlowBeacon", "Mark this incident as resolved?") == QMessageBox.StandardButton.Yes:
            self.city.resolve(self.sel)
            self.save()
            self.render()

    def save_dev(self):
        try:
            lat, lng = float(self.e_lat.text()), float(self.e_lng.text())
        except ValueError:
            self.msg.setText(tr("Enter a valid latitude and longitude."))
            return
        if self.sel and self.city.edit_device(self.sel, self.e_name.text(), self.e_ward.text(), self.e_zone.text(), lat, lng):
            self.msg.setText("")
            self.save()
            self.render()
        else:
            self.msg.setText(tr("Enter a valid latitude and longitude."))

    def remove_dev(self):
        from PySide6.QtWidgets import QMessageBox
        if self.sel and QMessageBox.question(self, "FlowBeacon", "Remove this device from the city map? Past incidents are kept.") == QMessageBox.StandardButton.Yes:
            self.city.remove_device(self.sel)
            self.sel = None
            self.save()
            self.render()

    def add_dev(self):
        did = self.city.add_device(self.new_id.text())
        if did:
            self.new_id.clear()
            self.save()
            self.select(did)

    def set_officer(self):
        self.city.d["officer"] = self.officer.text().strip()
        self.save()

    def add_team(self):
        if self.city.add_team(self.new_team.text()):
            self.new_team.clear()
            self.save()
            self.render()

    def del_team(self):
        self.city.remove_team(self.team_del.currentIndex())
        self.save()
        self.render()

    def set_pin(self):
        self.setup_msg.setText(tr(self.city.set_pin(self.pin_new.text())))
        self.pin_new.clear()
        self.save()

    def clear_pin(self):
        self.setup_msg.setText(tr(self.city.clear_pin()))
        self.save()


# ---------------------------------------------------------------- Learn, replay, profiles (added to the Calibration tab)
def add_learn_cards(page, ctx):
    e = ctx.engine
    st = ctx.store
    state = {"train": [], "play": []}

    c = NeuCard("Learn from recordings")
    c.box.addWidget(sub("Load the labelled CSV files saved by Test recording (normal, partial valve, rain and so on). Set the baseline first."))
    pick, train, hdr, js = NeuButton("Choose CSV files"), NeuButton("Train"), NeuButton("Export model.h"), NeuButton("Export JSON")
    msg = sub("")
    use = NeuSwitch(bool(st["useModel"]))
    use.toggled.connect(lambda on: (st.__setitem__("useModel", on), st.save()))
    for b in (train, hdr, js):
        b.setEnabled(False)
    if st["model"]:
        hdr.setEnabled(True)
        js.setEnabled(True)
        msg.setText("Saved model: " + ", ".join(st["model"]["labels"]))

    def load():
        files, _ = QFileDialog.getOpenFileNames(page, "Choose recordings", "", "CSV (*.csv)")
        rows = []
        for f in files:
            try:
                with open(f, encoding="utf8") as fh:
                    rows += ml.parse_csv(fh.read(), f.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0])
            except OSError:
                pass
        state["train"] = rows
        train.setEnabled(bool(rows))
        msg.setText("%d readings loaded." % len(rows))

    def do_train():
        msg.setText(e.train(state["train"]))
        ok = bool(st["model"])
        hdr.setEnabled(ok)
        js.setEnabled(ok)

    def save_text(name, text):
        path, _ = QFileDialog.getSaveFileName(page, "Save", name)
        if path:
            with open(path, "w", encoding="utf8") as fh:
                fh.write(text)

    pick.clicked.connect(load)
    train.clicked.connect(do_train)
    hdr.clicked.connect(lambda: save_text("model.h", ml.header(st["model"], st["model"]["base"])))
    js.clicked.connect(lambda: save_text("flowbeacon-model.json", __import__("json").dumps(st["model"])))
    c.box.addLayout(hbox(pick, train, hdr, js))
    c.box.addLayout(hbox(QLabel("Use the learned model on the Overview"), None, use))
    c.box.addWidget(msg)

    r = NeuCard("Replay a recording")
    rpick = NeuButton("Choose CSV")
    speed = NeuCombo([("1x", 1), ("2x", 2), ("5x", 5), ("10x", 10)])
    speed.setFixedWidth(100)
    go = NeuButton("Play")
    go.setEnabled(False)
    rmsg = sub("")

    def rload():
        f, _ = QFileDialog.getOpenFileName(page, "Choose a recording", "", "CSV (*.csv)")
        if not f:
            return
        with open(f, encoding="utf8") as fh:
            state["play"] = ml.parse_csv(fh.read(), "replay")
        go.setEnabled(bool(state["play"]))
        rmsg.setText("%s: %d readings" % (f.replace("\\", "/").split("/")[-1], len(state["play"])) if state["play"] else "No readings found in that file.")

    def toggle():
        if ctx.link.replaying:
            ctx.link.stop_replay()
            go.setText(tr("Play"))
            return
        e.start_replay(state["play"], speed.currentData() or 1)
        go.setText(tr("Stop"))
        rmsg.setText("Playing %d readings…" % len(state["play"]))

    ctx.link.replay_done.connect(lambda: (rmsg.setText("Replay finished."), go.setText(tr("Play"))))
    rpick.clicked.connect(rload)
    go.clicked.connect(toggle)
    r.box.addLayout(hbox(rpick, speed, go))
    r.box.addWidget(rmsg)
    r.box.addSpacing(8)
    r.box.addWidget(H2("Calibration profiles"))
    psel = NeuCombo([])
    pname = NeuField("", "Profile name")
    psave, papply, pdel = NeuButton("Save"), NeuButton("Apply"), NeuButton("Delete")

    def fill():
        psel.clear()
        for i, p in enumerate(st["profiles"]):
            psel.addItem(p["name"], i)

    psave.clicked.connect(lambda: (e.profile_save(pname.text()), pname.clear(), fill()))
    papply.clicked.connect(lambda: e.profile_apply(psel.currentIndex()))
    pdel.clicked.connect(lambda: (e.profile_delete(psel.currentIndex()), fill()))
    fill()
    r.box.addLayout(hbox((psel, 1), papply, pdel))
    r.box.addLayout(hbox((pname, 1), psave))
    g = QGridLayout()
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(22)
    g.addWidget(c, 0, 0)
    g.addWidget(r, 0, 1)
    page.v.insertLayout(page.v.count() - 1, g)


# ---------------------------------------------------------------- Language, notifications, quiet hours, updates (added to Settings)
def add_settings_extras(page, ctx):
    st = ctx.store
    c = NeuCard("Language, notifications and quiet hours")
    cols = QHBoxLayout()
    cols.setSpacing(34)
    a, b = QVBoxLayout(), QVBoxLayout()
    a.setSpacing(10)
    b.setSpacing(10)
    a.addWidget(flabel("Language"))
    lang = NeuCombo([("English", "en"), ("தமிழ்", "ta")])
    lang.setCurrentIndex(lang.findData(st["lang"]))
    lang.currentIndexChanged.connect(lambda _i: ctx.set_language(lang.currentData()))
    a.addWidget(lang)
    a.addWidget(flabel("Text size"))
    zoom = NeuCombo([("Normal", 1.0), ("Large", 1.15), ("Extra large", 1.3)])
    zoom.setCurrentIndex(max(0, zoom.findData(float(st["zoom"]))))
    zoom.currentIndexChanged.connect(lambda _i: ctx.set_zoom(zoom.currentData()))
    a.addWidget(zoom)

    def sw(text, key, extra=None, obj=None):
        o = obj if obj is not None else st
        s = NeuSwitch(bool(o[key]))
        s.toggled.connect(lambda on: (o.__setitem__(key, on), st.save(), extra(on) if extra else None))
        return hbox(QLabel(text), None, s)

    a.addLayout(sw("Desktop notifications", "notify"))
    a.addLayout(sw("Keep running in the tray when closed", "tray"))
    if autostart.supported():
        s = NeuSwitch(autostart.is_enabled())
        s.toggled.connect(lambda on: autostart.set_enabled(on))
        a.addLayout(hbox(QLabel("Start with the computer"), None, s))
    a.addLayout(sw("Check for updates on start", "upd"))
    umsg = sub("Version " + updater.VERSION)
    chk = NeuButton("Check now")
    chk.clicked.connect(lambda: ctx.check_updates(umsg, manual=True))
    a.addLayout(hbox(chk, (umsg, 1)))
    a.addStretch(1)

    b.addWidget(flabel("Quiet hours"))
    q = st["quiet"]
    b.addLayout(sw("Quiet hours", "on", obj=q))
    tf, tt = NeuField(q["from"], "22:00"), NeuField(q["to"], "06:00")
    tf.setFixedWidth(110)
    tt.setFixedWidth(110)

    def tfix(f, key):
        t = f.text().strip()
        try:
            h, m = t.split(":")
            assert 0 <= int(h) < 24 and 0 <= int(m) < 60
            q[key] = "%02d:%02d" % (int(h), int(m))
        except (ValueError, AssertionError):
            f.setText(q[key])
        st.save()

    tf.editingFinished.connect(lambda: tfix(tf, "from"))
    tt.editingFinished.connect(lambda: tfix(tt, "to"))
    b.addLayout(hbox(tf, QLabel("to"), tt, None))
    b.addWidget(flabel("SMS minimum during quiet hours"))
    qs = NeuCombo([("Blockage warning", 2), ("Overflow risk", 3), ("Overflow only", 4)])
    qs.setCurrentIndex(max(0, qs.findData(int(q["smsMin"]))))
    qs.currentIndexChanged.connect(lambda _i: (q.__setitem__("smsMin", qs.currentData()), st.save()))
    b.addWidget(qs)
    b.addWidget(sub("During quiet hours there are no sounds or notifications below Overflow risk. Overflow always gets through."))
    b.addStretch(1)
    cols.addLayout(a, 1)
    cols.addLayout(b, 1)
    c.box.addLayout(cols)
    page.v.insertWidget(page.v.count() - 1, c)
