"""Live theme: 7 accent colours x light / dark / follow-system, the JetBrains Mono font, and the application style sheet."""
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication

from .palettes import ACCENTS, PALETTES

ASSETS = Path(__file__).parent / "assets"
FAMILY = "JetBrains Mono"
_fam = [FAMILY]


def load_fonts():
    for f in ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf"):
        i = QFontDatabase.addApplicationFont(str(ASSETS / "fonts" / f))
        if i >= 0:
            fams = QFontDatabase.applicationFontFamilies(i)
            if fams:
                _fam[0] = fams[0]


def font(px=13, bold=False, spacing=0.0):
    f = QFont(_fam[0])
    f.setPixelSize(int(px))
    f.setBold(bold)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


class Theme(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.accent, self.mode = "coral", "light"

    def is_dark(self):
        if self.mode == "auto":
            try:
                return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
            except Exception:
                return False
        return self.mode == "dark"

    @property
    def key(self):
        return "%s_%s" % (self.accent, "dark" if self.is_dark() else "light")

    @property
    def mode_dir(self):
        return "dark" if self.is_dark() else "light"

    def pal(self):
        return PALETTES[self.key]

    def c(self, name):
        return QColor(self.pal()[name])

    def set(self, accent=None, mode=None):
        if accent in dict((a[0], 1) for a in ACCENTS):
            self.accent = accent
        if mode in ("light", "dark", "auto"):
            self.mode = mode
        self.changed.emit()


THEME = Theme()


def qss():
    p = THEME.pal()
    return f"""
* {{ color: {p['tx']}; }}
QMainWindow, QDialog {{ background: {p['bg']}; }}
QLabel {{ background: transparent; }}
QLabel[sub="true"] {{ color: {p['mu']}; }}
QPushButton {{ background: transparent; border: none; padding: 0 18px; }}
QPushButton:hover {{ color: {p['ac']}; }}
QPushButton:disabled {{ color: {p['mu']}; }}
QPushButton[main="true"], QPushButton[main="true"]:hover {{ color: {p['on']}; }}
QPushButton[segon="true"], QPushButton[segon="true"]:hover {{ color: {p['on']}; }}
QPushButton[tab="true"]:checked {{ color: {p['ac']}; }}
QLineEdit {{ background: transparent; border: none; padding: 0 14px; selection-background-color: {p['ac']}; selection-color: {p['on']}; }}
QLineEdit::placeholder {{ color: {p['mu']}; }}
QComboBox {{ background: transparent; border: none; padding: 0 36px 0 14px; }}
QComboBox::drop-down {{ border: none; width: 0; }}
QComboBox QAbstractItemView {{ background: {p['bg']}; color: {p['tx']}; border: 1px solid {p['sd']}; outline: 0;
  selection-background-color: {p['ac']}; selection-color: {p['on']}; padding: 4px; }}
QPlainTextEdit, QTextBrowser {{ background: transparent; border: none; selection-background-color: {p['ac']}; selection-color: {p['on']}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 9px; background: transparent; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['mu']}; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ height: 9px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {p['mu']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; height: 0; width: 0; }}
QTableWidget {{ background: transparent; border: none; gridline-color: {p['sd']}; selection-background-color: {p['ac']}; }}
QHeaderView::section {{ background: {p['bg']}; border: none; padding: 8px 10px; font-weight: bold; color: {p['mu']}; }}
QToolTip {{ background: {p['bg']}; color: {p['tx']}; border: 1px solid {p['sd']}; padding: 4px 8px; }}
QMessageBox {{ background: {p['bg']}; }}
"""
