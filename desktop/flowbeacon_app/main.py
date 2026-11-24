"""FlowBeacon native desktop app (PySide6). Run:  python -m flowbeacon_app.main"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import theme
from .main_window import MainWindow
from .store import Store
from .theme import ASSETS, THEME
from .widgets import Splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FlowBeacon")
    app.setOrganizationName("TechMinds")
    app.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
    theme.load_fonts()
    st = Store()
    THEME.accent, THEME.mode = st["accent"], st["mode"]
    app.setFont(theme.font(13))
    app.setStyleSheet(theme.qss())
    splash = Splash()
    win = MainWindow()
    splash.show()

    def done():
        splash.close()
        win.start()

    splash.finished.connect(done)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
