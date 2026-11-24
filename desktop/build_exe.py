"""Builds a stand-alone FlowBeacon folder with PyInstaller (run on the OS you are building for)."""
import os
import subprocess
import sys

sep = os.pathsep
cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "FlowBeacon",
       "--add-data", "flowbeacon_app/assets%sflowbeacon_app/assets" % sep]
if sys.platform.startswith("win"):
    cmd += ["--icon", "flowbeacon_app/assets/icon.ico"]
subprocess.check_call(cmd + ["__main__.py"])
print("Built dist/FlowBeacon")
