"""Imports every UI module and builds the whole window against the Qt stand-in. Skipped when real PySide6 is installed."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["APPDATA"] = tempfile.mkdtemp()

try:
    import PySide6.QtWidgets  # noqa: F401
    REAL = True
except ImportError:
    REAL = False


@unittest.skipIf(REAL, "real PySide6 present")
class Smoke(unittest.TestCase):
    def test_build_window(self):
        sys.path.insert(0, os.path.dirname(__file__))
        import stub_qt
        stub_qt.install()
        from flowbeacon_app import main_window, pages, controls, widgets, role, neu, theme  # noqa: F401
        w = main_window.MainWindow()
        w.set_role("dev")
        w.show_tab("calib")
        w.toggle_demo()
        w.link.data.emit({"flow": 4.2, "dist": 12.5, "turb": 850, "rain": 0}) if hasattr(w.link.data, "emit") else None
        w.engine.on_data({"flow": 4.0, "dist": 12.0, "turb": 800, "rain": 0})
        w.engine.on_data({"flow": 1.0, "dist": 1.5, "turb": 1200, "rain": 1})
        self.assertIsNotNone(w.engine.last)


if __name__ == "__main__":
    unittest.main()
