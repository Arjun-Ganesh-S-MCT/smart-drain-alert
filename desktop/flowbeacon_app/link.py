"""Talks to the ESP32-S3: USB serial, Wi-Fi WebSocket (port 81) and a built-in demo generator."""
import json
import random
import time

from PySide6.QtCore import QIODevice, QObject, QTimer, QUrl, Signal

try:
    from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
except ImportError:  # pragma: no cover
    QSerialPort = QSerialPortInfo = None
try:
    from PySide6.QtWebSockets import QWebSocket
except ImportError:  # pragma: no cover
    QWebSocket = None

SCEN = {"normal": (4.2, 12.5, 850, 0), "partial": (2, 11, 1150, 0), "rain": (4.1, 10.8, 860, 1),
        "both": (1.6, 8.5, 1200, 1), "over": (0.9, 1.8, 1300, 1)}


class Link(QObject):
    data = Signal(dict)
    connection = Signal(bool, str)      # connected, label
    raw = Signal(str)
    message = Signal(str)               # for the status line
    board_ip = Signal(str)
    wifi_failed = Signal()

    def __init__(self):
        super().__init__()
        self.connected = False
        self.demo = False
        self.scen = "normal"
        self.cal_pending = False        # engine sets this while it collects a baseline
        self.tick = 0
        self.serial = None
        self.ws = None
        self.ws_auto = False
        self.ws_ip = ""
        self.port_name = ""
        self._buf = ""
        self.demo_timer = QTimer(self)
        self.demo_timer.timeout.connect(self._demo_step)

    # ---- demo ----
    def start_demo(self):
        self.stop_all()
        self.demo, self.tick, self.scen = True, 0, "normal"
        self.demo_timer.start(1000)
        self.connection.emit(False, "Demo data")

    def stop_demo(self):
        if self.demo:
            self.demo = False
            self.demo_timer.stop()
            self.connection.emit(False, "Not connected")

    def _demo_step(self):
        self.tick += 1
        p = SCEN["normal" if self.cal_pending else self.scen]
        n = lambda: random.random() - 0.5  # noqa: E731
        self.data.emit({"flow": p[0] + n() * 0.2, "dist": p[1] + n() * 0.2, "turb": p[2] + n() * 30, "rain": p[3]})

    # ---- common ----
    def stop_all(self):
        self.stop_demo()
        self.ws_auto = False
        if self.ws is not None:
            try:
                self.ws.close()
            except RuntimeError:
                pass
        if self.serial is not None and self.serial.isOpen():
            self.serial.close()
        self.serial = None
        self._set(False, "Not connected")

    def _set(self, ok, label):
        self.connected = ok
        self.connection.emit(ok, label)

    def send(self, obj):
        line = (obj if isinstance(obj, str) else json.dumps(obj)) + "\n"
        if self.serial is not None and self.serial.isOpen():
            self.serial.write(line.encode("utf8"))
            return True
        if self.ws is not None and self.ws_ok:
            self.ws.sendTextMessage(line)
            return True
        return False

    ws_ok = False

    @property
    def usb_open(self):
        return self.serial is not None and self.serial.isOpen()

    # ---- USB serial ----
    @staticmethod
    def ports():
        if QSerialPortInfo is None:
            return []
        return [(p.portName(), p.description() or p.portName()) for p in QSerialPortInfo.availablePorts()]

    def open_serial(self, name):
        if QSerialPort is None:
            self.message.emit("Serial support is not installed (QtSerialPort).")
            return
        self.stop_all()
        sp = QSerialPort(name, self)
        sp.setBaudRate(115200)
        if not sp.open(QIODevice.OpenModeFlag.ReadWrite):
            self.message.emit("Could not open %s: %s. Close other serial programs." % (name, sp.errorString()))
            return
        self.serial, self.port_name, self._buf = sp, name, ""
        sp.readyRead.connect(self._on_serial)
        sp.errorOccurred.connect(self._on_serial_error)
        self._set(True, "Connected (USB)")
        self.message.emit("Reading from the ESP32-S3…")

    def _on_serial(self):
        self._buf += bytes(self.serial.readAll()).decode("utf8", "replace")
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self.handle_line(line.strip())

    def _on_serial_error(self, err):
        name = getattr(err, "name", str(err))
        if name not in ("NoError",) and self.serial is not None and not self.serial.isOpen():
            self._set(False, "Not connected, retrying…")
            QTimer.singleShot(3000, lambda: self.port_name and self.serial is not None and self.open_serial(self.port_name))

    # ---- Wi-Fi ----
    def open_ws(self, ip):
        if QWebSocket is None:
            self.message.emit("WebSocket support is not installed (QtWebSockets).")
            return
        ip = ip.strip()
        if not ip:
            self.message.emit("Enter the board address first.")
            return
        self.stop_all()
        self.ws_ip, self.ws_auto = ip, True
        self._ws_connect()

    def _ws_connect(self):
        w = QWebSocket()
        self.ws = w
        w.connected.connect(lambda: self._ws_up(w))
        w.disconnected.connect(lambda: self._ws_down(w))
        w.textMessageReceived.connect(lambda t: [self.handle_line(x.strip()) for x in t.split("\n")])
        w.errorOccurred.connect(lambda _e: self.message.emit("Cannot reach the board. Check the address and that this PC is on the same Wi-Fi."))
        w.open(QUrl("ws://%s:81" % self.ws_ip))

    def _ws_up(self, w):
        if w is self.ws:
            self.ws_ok = True
            self._set(True, "Connected (Wi-Fi)")
            self.message.emit("Connected over Wi-Fi.")

    def _ws_down(self, w):
        if w is not self.ws:
            return
        self.ws_ok = False
        self._set(False, "Not connected, retrying…")
        if self.ws_auto:
            QTimer.singleShot(3000, lambda: self.ws_auto and w is self.ws and self._ws_connect())

    # ---- incoming lines ----
    def handle_line(self, line):
        if not line:
            return
        self.raw.emit(line)
        if line[0] != "{":
            return
        try:
            d = json.loads(line)
        except ValueError:
            return
        if d.get("ip"):
            self.board_ip.emit(str(d["ip"]))
        elif d.get("wifi") == "failed":
            self.wifi_failed.emit()
        elif "flow" in d:
            self.data.emit(d)
