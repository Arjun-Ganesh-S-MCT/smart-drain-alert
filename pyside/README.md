# FlowBeacon (PySide6)

Same FlowBeacon, same UI (the files in `../src`), running in Python/PySide6 instead of Electron.
Python handles the serial port (QSerialPort), tray, setup checks, downloads, notifications and PDF export.

    pip install -r requirements.txt
    python main.py            # add --hidden to start in the tray

Windows .exe / Linux binary:

    pip install pyinstaller
    python build_exe.py

Note: fonts come from `npm install` (JetBrains Mono). Without it the UI falls back to a system monospace font.
The map loads Leaflet from the internet if `src/vendor/leaflet` is absent.
