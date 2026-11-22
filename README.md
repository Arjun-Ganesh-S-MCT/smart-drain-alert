# 🌊 FlowSense
### Smart Drainage Monitoring & Blockage Prediction System

<p align="center">
  <strong>Developed by TechMinds</strong><br>
  An intelligent desktop monitoring system powered by ESP32-S3.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=linux&logoColor=white" />
  <img src="https://img.shields.io/badge/Hardware-ESP32--S3-orange?style=for-the-badge&logo=espressif&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Prototype-yellow?style=for-the-badge" />
</p>

---

## 💧 Overview

**FlowSense** is a desktop monitoring application designed for the **Smart Drainage Alert and Blockage Prediction System**.

Powered by an ESP32-S3 prototype, FlowSense continuously monitors drainage conditions using multiple sensors to identify abnormal flow patterns, detect potential blockages, and predict overflow risks before they become serious problems.

With real-time visualization, intelligent anomaly detection, offline predictions, and instant alerts, FlowSense makes drainage monitoring smarter and more accessible.

---

## ✨ Key Features

| Feature | Description |
|:---|:---|
| 📊 Live Monitoring | Real-time sensor readings and drainage conditions |
| 🧠 Smart Prediction | Offline overflow prediction and anomaly detection |
| 🚨 Intelligent Alerts | Sound notifications for critical drainage events |
| 📡 Dual Connectivity | USB Serial and Wi-Fi communication |
| 📱 SMS Notifications | GSM-based SMS alerts through the hardware |
| 🎛️ Sensor Calibration | Calibration dials and guided calibration wizard |
| 📋 Incident History | Records and tracks drainage incidents |
| 📄 PDF Reports | Generate downloadable incident reports |
| 📈 CSV Recording | Record sensor readings for testing and analysis |
| 💧 Drip Mascot | Interactive mascot for system notifications |

---

## 🔬 Monitoring Parameters

FlowSense monitors four important drainage parameters:

- 🌊 **Water Flow** — Detects changes in drainage flow.
- 📏 **Water Level** — Tracks rising water levels.
- 🧪 **Turbidity** — Monitors water quality and suspended particles.
- 🌧️ **Rain Plate** — Detects rainfall conditions.

### 🚦 Detection Conditions

| Condition | Meaning |
|:---|:---|
| 🟢 Normal | Drainage operating normally |
| 🟡 Possible Blockage | Abnormal flow pattern detected |
| 🟠 Blockage Warning | Potential blockage developing |
| 🔴 Overflow Risk | High possibility of overflow |
| 🚨 Overflow Detected | Overflow condition identified |

---

## 🖥️ Supported Platforms

<p align="center">
  <img src="https://img.shields.io/badge/Windows-11-0078D6?style=flat-square&logo=windows11&logoColor=white" />
  <img src="https://img.shields.io/badge/Linux-Supported-FCC624?style=flat-square&logo=linux&logoColor=black" />
</p>

| Platform | Distribution |
|:---|:---|
| 🪟 Windows | Installer and Portable EXE |
| 🐧 Linux | AppImage and DEB |

---

## ⚙️ Installation & Setup

### 📦 Run from Source

**Prerequisites:** Node.js and npm.

```bash
# Clone the repository
git clone YOUR_REPOSITORY_URL

# Enter the project directory
cd FlowSense

# Install dependencies
npm install

# Start FlowSense
npm start
```

### 🏗️ Build Locally

Build the application on the respective operating system.

**Windows:**
```bash
npm run dist:win
```

**Linux:**
```bash
npm run dist:linux
```

📁 All generated installers and executables will be available inside:

```text
dist/
```

---

## 🚀 Automated Builds with GitHub Actions

FlowSense supports automated cross-platform release builds using GitHub Actions.

### Release Process

1. Create a public GitHub repository.
2. Push the project source code.
3. Keep the `LICENSE` file in the repository.
4. Update `homepage` and `author` in `package.json`.
5. Create and push a version tag.

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions automatically builds:

- 🪟 Windows Installer
- 📦 Windows Portable EXE
- 🐧 Linux AppImage
- 📦 Linux DEB Package

The generated files are attached to the GitHub Release.

---

## 🔐 Windows Code Signing

The MIT license does not automatically sign application binaries.

FlowSense supports two code-signing approaches.

### Option A — Personal Certificate

Add these GitHub repository secrets:

```text
WIN_CSC_LINK
WIN_CSC_PASSWORD
```

### Option B — SignPath Foundation

Free code signing may be available for eligible open-source projects.

🌐 Application: https://signpath.org

Required GitHub configuration:

**Repository Secret**
```text
SIGNPATH_API_TOKEN
```

**Repository Variables**
```text
SIGNPATH_ORGANIZATION_ID
SIGNPATH_PROJECT_SLUG
SIGNPATH_POLICY_SLUG
```

The SignPath project requires two artifact configurations:

- `app` — Application executables and DLLs.
- `installer` — Installer executables.

**Note:** Without code-signing configuration, builds still work but Windows may display an unknown publisher warning. SmartScreen reputation warnings may also remain.

---

## 🐧 Linux Configuration

### Serial Port Permissions

Run:

```bash
sudo usermod -aG dialout $USER
```

Log out and log back in to apply the changes.

Some Linux distributions use the `uucp` group instead.

### Ubuntu AppImage Issue

On Ubuntu 23.10 and later, Chromium sandbox restrictions may prevent the AppImage from launching.

**Recommended:** Use the `.deb` package.

Alternative:

```bash
./FlowSense.AppImage --no-sandbox
```

---

## 🔌 ESP32-S3 Integration

FlowSense communicates with the ESP32-S3 prototype through:

- 🔗 USB Serial Communication
- 📡 Wi-Fi Connectivity
- 📲 GSM-based SMS Notifications

Additional technical information is available inside the application:

- Firmware Console
- Serial Data Format
- Wiring Help

---

## 🛠️ First-Run Setup

On the first launch, FlowSense displays a setup assistant.

It checks external system requirements, including:

**Linux**
- Serial port permissions.
- Required `dialout` or `uucp` group membership.

**Windows**
- Missing USB-to-serial drivers.
- CP210x and CH340 driver availability.

The setup assistant provides guidance and driver links. It can also be opened again from:

`Help → Setup`

The application bundles its fonts, sounds, and mascot artwork, so these assets do not need separate downloads.

---

## 📦 Application Size

FlowSense uses several optimizations to reduce its distribution size:

- Only the English Chromium locale is included.
- Maximum compression is enabled.
- Only three font files are shipped.
- The rain sound effect is optimized to 6 seconds.

Actual package sizes can be checked in the GitHub Actions build output.

**Future Possibility:** A smaller application footprint (approximately 10–15 MB) may be achievable through a Tauri rewrite with native serial support.

---

## 👥 Credits

**Project:** FlowSense  
**Developed by:** TechMinds  
**Hardware:** ESP32-S3  
**Desktop Framework:** Electron  

**Assets & Attribution**
- JetBrains Mono — SIL Open Font License.
- Drip Mascot Artwork — TechMinds.
- TechMinds Logo — TechMinds.

---

## 📜 License

This project is licensed under the **MIT License**.

See the `LICENSE` file for details.
## Code Signing Policy

Free code signing provided by SignPath.io,
certificate by SignPath Foundation.

### Privacy Policy

[Provide your actual privacy policy or the
required SignPath privacy statement.]
---

<p align="center">
  <strong>🌊 FlowSense — Detect Early. Alert Smart. Prevent Overflow.</strong>
  <br><br>
  <sub>Built with innovation by TechMinds 💙</sub>
</p>
