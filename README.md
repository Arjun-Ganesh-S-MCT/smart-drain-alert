# Smart Drainage Alert

Desktop monitor for the Smart Drainage Alert and Blockage Prediction System, an ESP32-S3 prototype that watches flow, water level, turbidity and a rain plate and warns of a developing blockage. Runs on Windows 11 and Linux. Licensed under MIT.

## Features
- Live readings, condition (normal, possible blockage, blockage warning, overflow risk, overflow detected), likely cause, severity and confidence
- Offline overflow prediction and anomaly detection, with sound alerts and the Drip mascot
- USB serial or Wi-Fi connection to the ESP32-S3, SMS alerts through a GSM module on the board
- Calibration dials and wizard, incident log, PDF report, CSV test recording

## Run from source
```
npm install
npm start
```

## Build locally
```
npm run dist:win     # Windows installer and portable .exe (run on Windows)
npm run dist:linux   # AppImage and .deb (run on Linux)
```
Output goes to `dist/`.

## Release with GitHub Actions
1. Create a **public** GitHub repository, push this folder, and keep the `LICENSE` file.
2. Edit `homepage` and `author` in `package.json`.
3. Tag a version: `git tag v1.0.0 && git push origin v1.0.0`.
4. The workflow in `.github/workflows/build.yml` builds Linux and Windows and attaches the files to a GitHub Release.

## Signing the Windows .exe
The MIT licence does not sign anything. It is what makes the project eligible for free signing from the SignPath Foundation. Signing needs a code-signing certificate, and the workflow supports two ways:

**A. Your own certificate (.pfx)**: add repository secrets `WIN_CSC_LINK` (the .pfx file as base64) and `WIN_CSC_PASSWORD`. electron-builder then signs the app and both installers.

**B. SignPath Foundation (free for open source)**:
1. Apply at https://signpath.org for your public MIT repository and wait for approval.
2. In SignPath create a project with two artifact configurations named `app` and `installer`. `app` signs `*.exe` and `*.dll` inside a zip. `installer` signs the `.exe` files.
3. In GitHub add the secret `SIGNPATH_API_TOKEN` and the variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG` and `SIGNPATH_POLICY_SLUG`.
4. Link GitHub Actions as a trusted build system in SignPath, then tag a release.

With neither set up, the workflow still builds, but the .exe is unsigned and Windows will warn about it.

A signed file removes the "unknown publisher" warning. Microsoft SmartScreen may still show a warning to new publishers until the signature builds reputation.

## Linux notes
- Serial access: `sudo usermod -aG dialout $USER`, then log out and back in.
- On Ubuntu 23.10 and later the AppImage may fail to start because of the Chromium sandbox. Install the `.deb` instead, or run the AppImage with `--no-sandbox`.

## ESP32-S3 side
The serial format, Wi-Fi provisioning and SMS firmware sketch are in the app under Firmware console, Serial format and wiring help.

## Credits
Font: JetBrains Mono (SIL Open Font License). Drip mascot artwork made by the project team.
