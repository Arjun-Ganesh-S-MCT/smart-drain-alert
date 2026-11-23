# FlowBeacon

**Smart Drainage Monitoring & Blockage Prediction System**

Developed by **TechMinds**

![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=linux&logoColor=white)
![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3-orange?style=for-the-badge&logo=espressif&logoColor=white)
![Framework](https://img.shields.io/badge/Framework-Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Prototype-yellow?style=for-the-badge)

FlowBeacon is an Electron-based desktop application that monitors drainage conditions using an ESP32-S3 prototype. It analyses sensor readings, detects abnormal conditions and alerts operators about potential blockages and overflow risks.

## Features

- **Live Monitoring** – Real-time flow, water level, turbidity and rainfall readings.
- **Blockage Detection** – Identifies abnormal patterns and potential drainage issues.
- **Overflow Prediction** – Offline prediction and anomaly detection.
- **Smart Alerts** – Sound notifications, desktop alerts and GSM-based SMS support.
- **City Drainage Map** – Live device locations, ward status and maintenance tracking.
- **Data & Reports** – Incident history, CSV recordings and PDF reports.
- **Calibration** – Sensor calibration controls and guided setup.
- **Drip Assistant** – Interactive mascot with offline assistance.
- **Customisation** – Multiple themes, English and Tamil language support.

## Supported Platforms

| Platform | Formats |
|---|---|
| Windows 11 | Installer (.exe), Portable (.exe) |
| Linux | AppImage, DEB |

## Installation

Download the latest version from [GitHub Releases](https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert/releases).

## Run from Source

**Requirements:** Node.js, npm and Git.

```bash
git clone https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert.git
cd smart-drain-alert
npm install
npm start
```

## Build

**Windows**
```bash
npm run dist:win
```

**Linux**
```bash
npm run dist:linux
```

## Hardware

Built around the **ESP32-S3** with support for:

- Flow sensor
- Water level sensor
- Turbidity sensor
- Rain detection plate
- GSM module for SMS alerts

Communication is supported through USB Serial and Wi-Fi.

## Technology Stack

- Electron
- JavaScript
- ESP32-S3
- Leaflet & OpenStreetMap
- GitHub Actions

## Project

**Developed by:** TechMinds

**Repository:** [GitHub – FlowBeacon](https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert)

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <strong>FlowBeacon — Detect Early. Alert Smart. Prevent Overflow.</strong><br>
  <sub>Developed with ❤️ by TechMinds</sub>
</p>
