# FlowBeacon native apps

Two real native apps, no browser inside either of them:

| Platform | Folder | Toolkit |
|---|---|---|
| Android 5.0+ | `android/` | Kotlin + Jetpack Compose |
| Windows and Linux | `desktop/` | Python + PySide6 (Qt widgets) |

Windows and Linux share one Qt codebase, so there are two projects, not three.

## Run and build
- Desktop: `cd desktop && pip install -r requirements.txt && python -m flowbeacon_app.main` (from the `desktop` folder: `python __main__.py`). Tests: `python -m unittest discover -s tests`. Linux package: `python build_exe.py`. Windows installer: `python build_msi.py`.
- Android: open `android/` in Android Studio, or `gradle -p android assembleRelease`. The release APK is shrunk (R8) and signed with the debug key for sideloading.
- GitHub Actions: `.github/workflows/native.yml` builds both.

## The look
Both apps reproduce the web app's design: the same soft neumorphic raised and pressed shadows (pre-rendered from the CSS box-shadows into small tiles, so they look identical on both platforms), JetBrains Mono, the 7 accent colours with Light / Dark / Follow-system, the real drain cross-section artwork (animated SVG), 3D calibration dials, switches, sliders, segmented control, status orb, KPI tiles, Drip with accent recolouring, and the same tab order. `tools/make_assets.py` and `tools/make_shared.py` regenerate the tiles, icons, SVG template and palettes (needs Pillow; the generated files are already included).

## What is in version 2.0
Splash intro (slow on Android), Consumer / Maintenance / Developer modes (buttons that do not apply are removed, never greyed out), Overview, Drain model, Incidents (reports, test recording, calibration wizard), Connection, Calibration dials, Ask Drip, Settings (theme colour, mode, sounds, reduce motion), Console, Drip with physics, demo mode with scenarios, Wi-Fi link to the ESP32-S3 (WebSocket port 81), USB serial (desktop), SMS through the board.

The analysis core is a line-for-line port of the old `core.js`. `desktop/tests/fixtures.json` holds 400 readings run through the original JavaScript, and the Python port reproduces every result. The Kotlin port follows the same code. Neither UI has been run on a real device yet: only the Python logic and a stand-in for Qt were exercised here.

## What the native apps have now

Both apps have every tab of the web app: Overview, Drain model, Incidents, Connection, **History**, Calibration, Ask Drip, Settings, Console and **City map**. Added in this version:

- History (minute averages kept 90 days, 24 h / 7 d / 30 d, CSV export).
- City map and dispatch: pins, ward / zone / status filters, assign a team, start work, resolve, incident log, officials PIN. The map is drawn as a schematic grid from latitude and longitude, so it needs no internet or map tiles.
- Other drains (demo mode adds two) with their own baselines, alerts and incidents.
- Learn from recordings, replay of a recorded CSV, calibration profiles.
- Tamil and text size, update check (GitHub releases), quiet hours.
- Sounds: click on every button, dial tick and spin, quiet hours and the per-sound switches.
- Desktop: tray icon, desktop notifications, close to tray, start with the computer.
- Android: background alerts (foreground service plus notifications) and USB serial through an OTG cable.

## Hardware (this version)

- Board: **Arduino Nano** (USB only, no Wi-Fi). Sketch and wiring: `firmware/README.md`.
- Water level: a **5-step sensor** (five probes, each through a transistor) instead of the ultrasonic sensor. The Nano sends `lv` (0 to 5) and the app turns it into a distance (`EMPTY_CM` and `STEP_CM` in `core.py` and `Core.kt`).
- Map: **OpenStreetMap tiles** drawn by the apps themselves (no web view), with drag, zoom and pins. Tiles are cached on the device.

## Windows installer

Windows is delivered as an `.msi` only: `cd desktop && pip install -r requirements-msi.txt && python build_msi.py` (on Windows), or take it from the `FlowBeacon-Windows-msi` artifact of the GitHub workflow.

## Still not done

- Speaking alerts aloud (web "Drip voice") is not in the native apps.
- The map has no street tiles.
- Nothing here has been built or run on a real device. The Python logic and a Qt stand-in are tested; the Kotlin and the MSI were written but not compiled in this environment.
