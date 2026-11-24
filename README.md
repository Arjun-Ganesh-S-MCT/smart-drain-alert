# FlowBeacon native apps

Two real native apps, no browser inside either of them:

| Platform | Folder | Toolkit |
|---|---|---|
| Android 5.0+ | `android/` | Kotlin + Jetpack Compose |
| Windows and Linux | `desktop/` | Python + PySide6 (Qt widgets) |

Windows and Linux share one Qt codebase, so there are two projects, not three.

## Run and build
- Desktop: `cd desktop && pip install -r requirements.txt && python -m flowbeacon_app.main` (from the `desktop` folder: `python __main__.py`). Tests: `python -m unittest discover -s tests`. Package: `python build_exe.py`.
- Android: open `android/` in Android Studio, or `gradle -p android assembleRelease`. The release APK is shrunk (R8) and signed with the debug key for sideloading.
- GitHub Actions: `.github/workflows/native.yml` builds both.

## The look
Both apps reproduce the web app's design: the same soft neumorphic raised and pressed shadows (pre-rendered from the CSS box-shadows into small tiles, so they look identical on both platforms), JetBrains Mono, the 7 accent colours with Light / Dark / Follow-system, the real drain cross-section artwork (animated SVG), 3D calibration dials, switches, sliders, segmented control, status orb, KPI tiles, Drip with accent recolouring, and the same tab order. `tools/make_assets.py` and `tools/make_shared.py` regenerate the tiles, icons, SVG template and palettes (needs Pillow; the generated files are already included).

## What is in version 2.0
Splash intro (slow on Android), Consumer / Maintenance / Developer modes (buttons that do not apply are removed, never greyed out), Overview, Drain model, Incidents (reports, test recording, calibration wizard), Connection, Calibration dials, Ask Drip, Settings (theme colour, mode, sounds, reduce motion), Console, Drip with physics, demo mode with scenarios, Wi-Fi link to the ESP32-S3 (WebSocket port 81), USB serial (desktop), SMS through the board.

The analysis core is a line-for-line port of the old `core.js`. `desktop/tests/fixtures.json` holds 400 readings run through the original JavaScript, and the Python port reproduces every result. The Kotlin port follows the same code. Neither UI has been run on a real device yet: only the Python logic and a stand-in for Qt were exercised here.

## Not ported yet
History tab (stored sensor charts), City map and team dispatch, Tamil and text size, learn-from-recordings and replay, tray icon, start-with-PC, update checker, quiet hours, Android background alerts, Android USB serial.

## Licences
JetBrains Mono is bundled under the SIL Open Font License (see `JetBrainsMono-OFL.txt` in each assets/fonts folder).
