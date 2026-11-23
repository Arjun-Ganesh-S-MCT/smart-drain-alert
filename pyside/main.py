"""FlowBeacon (PySide6). Hosts the unchanged FlowBeacon UI (../src) in Qt WebEngine; Python handles the
serial port, tray, setup checks, downloads, notifications and PDF export that Electron handled before."""
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import threading
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QFile, QIODevice, QObject, QProcess, QStandardPaths, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineSettings)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QFileDialog, QInputDialog, QMainWindow, QMenu, QMessageBox,
                               QSystemTrayIcon)

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
SRC, BUILD = ROOT / "src", ROOT / "build"
PKG = json.loads((ROOT / "package.json").read_text(encoding="utf8"))
VERSION = PKG["version"]
REPO_URL = "https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert"
RELEASE_API = "https://api.github.com/repos/Arjun-Ganesh-S-MCT/smart-drain-alert/releases/latest"
BG = "#e0d9d3"
SPLASH_MS = 4300
DRIVER_LINKS = {
    "cp210x": "https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers",
    "ch340": "https://www.wch-ic.com/downloads/CH341SER_EXE.html",
}
DATA = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation) or Path.home() / ".flowbeacon")
HIDDEN = "--hidden" in sys.argv


def data_dir():
    DATA.mkdir(parents=True, exist_ok=True)
    return DATA


def write_log(text):
    try:
        f = data_dir() / "flowbeacon.log"
        if f.exists() and f.stat().st_size > 1048576:
            f.replace(f.with_suffix(".log.old"))
        with f.open("a", encoding="utf8") as fh:
            fh.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + str(text)[:2000] + "\n")
    except OSError:
        pass


class Settings:
    def __init__(self):
        self.d = {"closeToTray": False, "startWithPc": False}
        try:
            self.d.update(json.loads((data_dir() / "settings.json").read_text(encoding="utf8")))
        except (OSError, ValueError):
            pass

    def save(self):
        (data_dir() / "settings.json").write_text(json.dumps(self.d), encoding="utf8")
        if sys.platform == "win32":
            from PySide6.QtCore import QSettings
            reg = QSettings(r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run", QSettings.Format.NativeFormat)
            if self.d.get("startWithPc"):
                exe = f'"{sys.executable}"' if getattr(sys, "frozen", False) else f'"{sys.executable}" "{Path(__file__).resolve()}"'
                reg.setValue("FlowBeacon", exe + " --hidden")
            else:
                reg.remove("FlowBeacon")


class Page(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main):
        if url.scheme() in ("file", "qrc", "about", "blob", "data", "devtools"):
            return True
        if is_main:
            if url.scheme() in ("http", "https", "sms", "tel", "mailto"):
                QDesktopServices.openUrl(url)
            return False
        return True

    def createWindow(self, _type):  # target=_blank links open in the system browser
        helper = QWebEnginePage(self.profile(), self)
        helper.urlChanged.connect(lambda u: QDesktopServices.openUrl(u) if u.scheme() in ("http", "https") else None)
        return helper

    def javaScriptConsoleMessage(self, level, message, line, source):
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            write_log(f"js error: {message} @{source}:{line}")


class Bridge(QObject):
    setupStep = Signal(str)
    setupResult = Signal(str)
    serialData = Signal(str)
    serialClosed = Signal()
    notifyClicked = Signal()

    def __init__(self, app_ctx):
        super().__init__()
        self.ctx = app_ctx
        self.sp = None
        self.last_port = ""

    # ---- app ----
    @Slot(result=str)
    def getSettings(self):
        s = self.ctx.settings.d
        return json.dumps({"closeToTray": s["closeToTray"], "startWithPc": s["startWithPc"], "platform": sys.platform, "version": VERSION})

    @Slot(str)
    def setSettings(self, js):
        o = json.loads(js or "{}")
        for k in ("closeToTray", "startWithPc"):
            if isinstance(o.get(k), bool):
                self.ctx.settings.d[k] = o[k]
        self.ctx.settings.save()

    @Slot(int, str)
    def setLevel(self, lvl, text):
        self.ctx.set_level(max(0, min(4, lvl)), text[:120] or "FlowBeacon")

    @Slot()
    def focus(self):
        self.ctx.show_main()

    @Slot(str)
    def log(self, text):
        write_log(text)

    @Slot()
    def openLog(self):
        if not (data_dir() / "flowbeacon.log").exists():
            write_log("log started")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    @Slot(str)
    def openUrl(self, url):
        if url.startswith("https://github.com/"):
            QDesktopServices.openUrl(QUrl(url))

    @Slot(str, str)
    def notify(self, title, body):
        self.ctx.tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Warning, 8000)

    @Slot()
    def printReport(self):
        path, _ = QFileDialog.getSaveFileName(self.ctx.win, "Save report", "flowbeacon-report.pdf", "PDF (*.pdf)")
        if path:
            self.ctx.win.page.printToPdf(path)

    # ---- self-update (checks GitHub releases; source installs pull the new code, packaged installs download the installer) ----
    updateState = Signal(str)

    @Slot(result=str)
    def checkUpdate(self):
        if not getattr(self, "_upd_busy", False):
            self._upd_busy = True
            threading.Thread(target=self._update_job, daemon=True).start()
        return json.dumps({"current": VERSION, "latest": VERSION, "newer": False, "auto": True})

    def _emit(self, **kw):
        self.updateState.emit(json.dumps(kw))

    def _update_job(self):
        try:
            if getattr(self, "pending", None):
                return
            req = urllib.request.Request(RELEASE_API, headers={"User-Agent": f"FlowBeacon/{VERSION}", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                rel = json.load(r)
            latest = str(rel.get("tag_name", "")).lstrip("v")
            if not latest or vtuple(latest) <= vtuple(VERSION):
                return
            self._emit(state="available", version=latest)
            if getattr(sys, "frozen", False):
                a = pick_asset(rel.get("assets", []))
                if not a:
                    return write_log("update: no installer asset for this platform in the release")
                dest = data_dir() / "updates"
                dest.mkdir(exist_ok=True)
                path = dest / a["name"]
                with urllib.request.urlopen(urllib.request.Request(a["browser_download_url"], headers={"User-Agent": "FlowBeacon"}), timeout=30) as r, open(path, "wb") as f:
                    total, got, last = int(r.headers.get("Content-Length") or 0), 0, -1
                    while True:
                        b = r.read(65536)
                        if not b:
                            break
                        f.write(b)
                        got += len(b)
                        pct = int(got * 100 / total) if total else 0
                        if pct != last:
                            last = pct
                            self._emit(state="downloading", percent=pct)
                self.pending = ("installer", str(path))
            elif (ROOT / ".git").exists() and shutil.which("git"):
                self._emit(state="downloading", percent=30)
                r = subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"], capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    return write_log("update: git pull failed: " + (r.stderr or r.stdout)[:300])
                self._emit(state="downloading", percent=100)
                self.pending = ("restart", "")
            else:
                return write_log("update: not a git checkout or packaged build, cannot self-update")
            self._emit(state="ready", version=latest)
        except Exception as e:  # network down etc.: stay quiet in the UI
            write_log(f"update: {e}")
        finally:
            self._upd_busy = False

    @Slot()
    def installUpdate(self):
        kind, path = getattr(self, "pending", None) or (None, "")
        if kind == "installer":
            if sys.platform.startswith("linux"):
                os.chmod(path, 0o755)
            QProcess.startDetached(path, [])
        elif kind == "restart":
            QProcess.startDetached(sys.executable, sys.argv)
        else:
            return
        self.ctx.quit()

    # ---- serial ----
    def _ports(self):
        ports = QSerialPortInfo.availablePorts()
        usb = [p for p in ports if p.hasVendorIdentifier() or re.match(r"tty(ACM|USB)", p.portName())]
        return usb or ports

    @Slot(result=str)
    def pickPort(self):
        ports = self._ports()
        if not ports:
            return ""
        if len(ports) == 1:
            self.last_port = ports[0].systemLocation()
            return self.last_port
        names = [f"{p.description() or 'Serial device'} ({p.portName()})" for p in ports[:8]]
        item, ok = QInputDialog.getItem(self.ctx.win, "Select board", "Choose the ESP32-S3 port", names, 0, False)
        if not ok:
            return ""
        self.last_port = ports[names.index(item)].systemLocation()
        return self.last_port

    @Slot(result=str)
    def lastPort(self):
        return self.last_port if any(p.systemLocation() == self.last_port for p in self._ports()) else ""

    @Slot(str, int, result=str)
    def serialOpen(self, name, baud):
        self.serialClose()
        sp = QSerialPort(name)
        sp.setBaudRate(baud)
        if not sp.open(QIODevice.OpenModeFlag.ReadWrite):
            return sp.errorString() or "Could not open the port"
        sp.readyRead.connect(lambda: self.serialData.emit(base64.b64encode(bytes(sp.readAll())).decode()))
        sp.errorOccurred.connect(self._serial_error)
        self.sp, self.last_port = sp, name
        return ""

    def _serial_error(self, err):
        if err in (QSerialPort.SerialPortError.ResourceError, QSerialPort.SerialPortError.DeviceNotFoundError):
            self.serialClose()
            self.serialClosed.emit()

    @Slot(str)
    def serialWrite(self, b64):
        if self.sp and self.sp.isOpen():
            self.sp.write(base64.b64decode(b64))

    @Slot()
    def serialClose(self):
        sp, self.sp = self.sp, None
        if sp:
            try:
                sp.errorOccurred.disconnect()
                sp.close()
            except (RuntimeError, TypeError):
                pass

    # ---- first-time setup ----
    @Slot()
    def openSetup(self):
        self.ctx.open_setup()

    @Slot()
    def runSetup(self):
        threading.Thread(target=self._checks, daemon=True).start()

    def _checks(self):
        res = {"platform": sys.platform, "needsGroup": False, "group": "", "driverIssues": []}

        def step(i, label, fn):
            self.setupStep.emit(json.dumps({"id": i, "state": "run", "text": label}))
            time.sleep(0.45)
            state, text = fn()
            self.setupStep.emit(json.dumps({"id": i, "state": state, "text": text}))

        step("sys", "Checking this computer", lambda: ("ok", f"{platform.system()} {platform.release()} ({platform.machine()})"))
        step("app", "Checking app files", lambda: ("ok", "Sounds, fonts and the mascot are built in. Nothing to download."))
        if sys.platform.startswith("linux"):
            group = linux_group()
            res["group"] = group

            def ports():
                devs = sorted(n for n in os.listdir("/dev") if re.match(r"tty(ACM|USB)\d+$", n))
                return "ok", ("Found: " + ", ".join(devs)) if devs else "No board plugged in yet. That is fine."

            def perm():
                out = run_cmd(["id", "-nG"])
                ok = os.getuid() == 0 or group in out.split()
                res["needsGroup"] = not ok
                return ("ok", f"Allowed (group {group})") if ok else ("warn", f"Your account is not in the {group} group, so Linux blocks USB serial ports.")

            step("ports", "Looking for serial devices", ports)
            step("perm", "Checking serial port access", perm)
        elif sys.platform == "win32":
            ps = lambda c: [x.strip() for x in run_cmd(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", c]).splitlines() if x.strip()]
            step("ports", "Looking for serial devices",
                 lambda: ("ok", ("Found: " + ", ".join(n)) if (n := ps("Get-CimInstance Win32_SerialPort | Select-Object -ExpandProperty Name")) else "No board plugged in yet. That is fine."))

            def drv():
                bad = ps("Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Error' -and $_.InstanceId -like 'USB*' } | Select-Object -ExpandProperty FriendlyName")
                res["driverIssues"] = bad
                return ("warn", "A USB device has no driver: " + ", ".join(bad)) if bad else ("ok", "No missing USB serial drivers")

            step("drv", "Checking USB serial drivers", drv)
        step("final", "Finishing", lambda: ("ok", "Setup check finished"))
        self.setupResult.emit(json.dumps(res))

    @Slot(result=str)
    def grantSerial(self):
        if not sys.platform.startswith("linux"):
            return json.dumps({"ok": False, "error": "Only needed on Linux"})
        group = linux_group()
        try:
            r = subprocess.run(["pkexec", "usermod", "-aG", group, os.environ.get("USER", "")], timeout=120, capture_output=True)
            return json.dumps({"ok": r.returncode == 0, "group": group, "error": "" if r.returncode == 0 else r.stderr.decode()[:200]})
        except (OSError, subprocess.SubprocessError) as e:
            return json.dumps({"ok": False, "group": group, "error": str(e)})

    @Slot(str)
    def openLink(self, key):
        if key in DRIVER_LINKS:
            QDesktopServices.openUrl(QUrl(DRIVER_LINKS[key]))

    @Slot()
    def finish(self):
        (data_dir() / "setup-done.json").write_text(json.dumps({"done": time.strftime("%Y-%m-%dT%H:%M:%S"), "version": VERSION}), encoding="utf8")
        self.ctx.close_setup()


def vtuple(v):
    n = [int(x) for x in re.findall(r"\d+", str(v))[:3]]
    return tuple(n + [0] * (3 - len(n)))


def pick_asset(assets):
    want = (".exe",) if sys.platform == "win32" else (".appimage",) if sys.platform.startswith("linux") else (".dmg", ".zip")
    for a in assets:
        n = a.get("name", "").lower()
        if n.endswith(want) and "blockmap" not in n:
            return a
    return None


def run_cmd(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=20, text=True).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def linux_group():
    try:
        names = [l.split(":")[0] for l in Path("/etc/group").read_text().splitlines()]
        for g in ("dialout", "uucp"):
            if g in names:
                return g
    except OSError:
        pass
    return "dialout"


class Ctx(QObject):
    """Owns the profile, windows and tray."""

    def __init__(self, app):
        super().__init__()
        self.app, self.settings = app, Settings()
        self.quitting = False
        self.setup_win = None
        self.icon = QIcon(str(BUILD / "icon.png"))
        app.setWindowIcon(self.icon)
        app.setApplicationName("FlowBeacon")
        self.profile = QWebEngineProfile("FlowBeacon", self)
        # OpenStreetMap blocks browser-looking requests that carry no Referer (403 "Access blocked").
        # Qt cancels hand-set Referer headers, so identify the app through the User-Agent instead, as OSM's tile policy allows.
        self.profile.setHttpUserAgent(f"FlowBeacon/{VERSION} (+{REPO_URL})")
        self.profile.downloadRequested.connect(self.on_download)
        self.bridge = Bridge(self)
        f = QFile(":/qtwebchannel/qwebchannel.js")
        f.open(QIODevice.OpenModeFlag.ReadOnly)
        qwc = bytes(f.readAll()).decode("utf8")
        shim = (Path(__file__).parent / "shim.js") if not getattr(sys, "frozen", False) else (ROOT / "pyside" / "shim.js")
        self.script_src = qwc + "\n" + shim.read_text(encoding="utf8").replace("__PLATFORM__", sys.platform)
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("FlowBeacon")
        menu = QMenu()
        menu.addAction("Show FlowBeacon", self.show_main)
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_main() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.messageClicked.connect(lambda: (self.show_main(), self.bridge.notifyClicked.emit()))
        self.tray.show()
        self.win = MainWindow(self)

    def make_view(self, html, size, title):
        view = QWebEngineView()
        page = Page(self.profile, view)
        page.setBackgroundColor(QColor(BG))
        st = page.settings()
        st.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        st.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        st.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        s = QWebEngineScript()
        s.setName("flowbeacon-shim")
        s.setSourceCode(self.script_src)
        s.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        s.setWorldId(0)  # main world
        s.setRunsOnSubFrames(False)
        page.scripts().insert(s)
        ch = QWebChannel(page)
        ch.registerObject("bridge", self.bridge)
        page.setWebChannel(ch, 0)
        view.setPage(page)
        view.setWindowTitle(title)
        view.resize(*size)
        view.page_ref = page
        view.load(QUrl.fromLocalFile(str(SRC / html)))
        return view

    def on_download(self, d):
        path, _ = QFileDialog.getSaveFileName(self.win, "Save file", str(Path.home() / d.downloadFileName()))
        if not path:
            d.cancel()
            return
        d.setDownloadDirectory(str(Path(path).parent))
        d.setDownloadFileName(Path(path).name)
        d.accept()

    def set_level(self, lvl, text):
        p = BUILD / f"tray-{lvl}.png"
        if p.exists():
            self.tray.setIcon(QIcon(str(p)))
        self.tray.setToolTip(text)

    def show_main(self):
        self.win.showNormal() if self.win.isMinimized() else self.win.show()
        self.win.raise_()
        self.win.activateWindow()

    def open_setup(self):
        if self.setup_win:
            self.setup_win.raise_()
            return
        self.setup_win = self.make_view("setup.html", (640, 640), "FlowBeacon setup")
        self.setup_win.setWindowFlag(Qt.WindowType.Dialog, True)
        self.setup_win.show()

    def close_setup(self):
        if self.setup_win:
            self.setup_win.close()
            self.setup_win = None

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        self.bridge.serialClose()
        self.app.quit()

    def cleanup(self):
        # pages must be deleted before their profile, otherwise Qt prints "Release of profile requested..."
        views = [self.win.view, self.setup_win]
        for v in views:
            if v:
                v.page().deleteLater()
                v.hide()
        self.app.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
        self.app.processEvents()


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("FlowBeacon")
        self.resize(1320, 900)
        self.setMinimumSize(960, 640)
        self.view = ctx.make_view("index.html", (1320, 900), "FlowBeacon")
        self.page = self.view.page()
        self.page.pdfPrintingFinished.connect(
            lambda p, ok: QDesktopServices.openUrl(QUrl.fromLocalFile(p)) if ok else write_log("pdf export failed"))
        self.setCentralWidget(self.view)

    def closeEvent(self, e):
        if not self.ctx.quitting and self.ctx.settings.d["closeToTray"] and self.ctx.tray.isVisible():
            e.ignore()
            self.hide()
        else:
            self.ctx.quit()
            e.accept()


def main():
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--autoplay-policy=no-user-gesture-required --disable-features=Vulkan --log-level=3")
    # Qt Wayland text-input bug spams "Trying to disable ... but 0x0 is focused"; Vulkan probing prints a harmless error
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false;qt.webenginecontext.debug=false")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # single instance
    name = "flowbeacon-pyside"
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(name)
    server = QLocalServer()
    server.listen(name)

    ctx = Ctx(app)
    app.aboutToQuit.connect(ctx.cleanup)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), ctx.show_main()))

    splash = ctx.make_view("splash.html", (640, 420), "FlowBeacon")
    splash.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    splash.move(app.primaryScreen().geometry().center() - splash.rect().center())
    splash.show()

    def reveal():
        splash.close()
        if HIDDEN:
            return
        ctx.win.show()
        if not (data_dir() / "setup-done.json").exists():
            ctx.open_setup()

    QTimer.singleShot(SPLASH_MS, reveal)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
