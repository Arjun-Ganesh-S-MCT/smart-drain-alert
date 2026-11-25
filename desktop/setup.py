"""Builds the Windows installer (.msi) with cx_Freeze. Run on Windows:  python setup.py bdist_msi   (or python build_msi.py)
The installer puts FlowBeacon in Program Files, adds a Start menu shortcut and a desktop shortcut, and supports upgrades."""
import sys

from cx_Freeze import Executable, setup

from flowbeacon_app import __version__

UPGRADE_CODE = "{6F2D1B9A-3C47-4E58-9A61-5B7C0D8E2F14}"   # never change: it lets a newer MSI replace an older install

build_exe = {
    "packages": ["flowbeacon_app", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvg", "PySide6.QtMultimedia",
                 "PySide6.QtSerialPort", "PySide6.QtWebSockets", "sqlite3"],
    "includes": ["winreg"] if sys.platform == "win32" else [],
    "excludes": ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick"],
    "include_files": [("flowbeacon_app/assets", "lib/flowbeacon_app/assets")],
    "zip_include_packages": ["encodings", "importlib"],
    "zip_exclude_packages": ["flowbeacon_app", "PySide6"],      # the app reads its images, fonts and sounds from real files
    "include_msvcr": True,
}

bdist_msi = {
    "upgrade_code": UPGRADE_CODE,
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFiles64Folder]\FlowBeacon",
    "summary_data": {"author": "TechMinds", "comments": "FlowBeacon drain monitor"},
    "install_icon": "flowbeacon_app/assets/icon.ico",
}

exe = Executable(
    "__main__.py",
    base="gui" if sys.platform == "win32" else None,
    target_name="FlowBeacon.exe" if sys.platform == "win32" else "FlowBeacon",
    icon="flowbeacon_app/assets/icon.ico",
    shortcut_name="FlowBeacon",
    shortcut_dir="ProgramMenuFolder",
)

setup(
    name="FlowBeacon",
    version=__version__,
    description="FlowBeacon drain blockage monitor",
    author="TechMinds",
    options={"build_exe": build_exe, "bdist_msi": bdist_msi},
    executables=[exe],
)
