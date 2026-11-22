import os, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sep = os.pathsep
cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--name", "FlowBeacon", "--icon", str(root / "build" / "icon.png"),
       "--add-data", f"{root / 'src'}{sep}src", "--add-data", f"{root / 'build'}{sep}build", "--add-data", f"{root / 'package.json'}{sep}.",
       "--add-data", f"{root / 'pyside' / 'shim.js'}{sep}pyside", str(root / "pyside" / "main.py")]
raise SystemExit(subprocess.call(cmd, cwd=root))
