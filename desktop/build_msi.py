"""Builds the Windows installer: dist/FlowBeacon-<version>-win64.msi  (run this on Windows, needs: pip install -r requirements-msi.txt)."""
import subprocess
import sys
from pathlib import Path

if not sys.platform.startswith("win"):
    sys.exit("The .msi installer can only be built on Windows (use the 'Build native apps' GitHub workflow).")
subprocess.check_call([sys.executable, "setup.py", "bdist_msi"])
for f in Path("dist").glob("*.msi"):
    print("Built", f)
