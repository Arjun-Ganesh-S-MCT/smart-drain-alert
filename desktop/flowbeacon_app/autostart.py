"""Start with the computer: a Run key on Windows, an autostart entry on Linux."""
import os
import sys
from pathlib import Path

NAME = "FlowBeacon"


def supported():
    return sys.platform.startswith("win") or sys.platform.startswith("linux")


def _command():
    if getattr(sys, "frozen", False):
        return '"%s" --hidden' % sys.executable
    main = Path(__file__).resolve().parent.parent / "__main__.py"
    return '"%s" "%s" --hidden' % (sys.executable, main)


def _desktop_file():
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart" / "flowbeacon.desktop"


def is_enabled():
    try:
        if sys.platform.startswith("win"):
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, NAME)
                return True
        return _desktop_file().exists()
    except OSError:
        return False


def set_enabled(on):
    try:
        if sys.platform.startswith("win"):
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
                if on:
                    winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, _command())
                else:
                    try:
                        winreg.DeleteValue(k, NAME)
                    except FileNotFoundError:
                        pass
            return True
        f = _desktop_file()
        if on:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("[Desktop Entry]\nType=Application\nName=FlowBeacon\nExec=%s\nX-GNOME-Autostart-enabled=true\n" % _command(), encoding="utf8")
        elif f.exists():
            f.unlink()
        return True
    except OSError:
        return False
