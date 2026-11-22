FlowBeacon
Smart Drainage Monitoring & Blockage Prediction System
Developed by TechMinds
An Electron desktop application for monitoring a Smart Drainage Alert and Blockage Prediction System built around an ESP32-S3 prototype.
<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Windows and Linux" />
  <img src="https://img.shields.io/badge/Hardware-ESP32--S3-orange?style=for-the-badge&logo=espressif&logoColor=white" alt="ESP32-S3" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Status-Prototype-yellow?style=for-the-badge" alt="Prototype" />
</p>Overview
FlowBeacon is a desktop monitoring application for the Smart Drainage Alert and Blockage Prediction System. It works with an ESP32-S3 hardware prototype to display drainage sensor readings, identify abnormal conditions, and provide alerts about possible blockages and overflow risks.

The application is intended for prototype monitoring, testing, and analysis. Its assessments depend on the connected sensors, calibration, firmware, and deployment conditions; predictions should not be treated as a substitute for physical inspection or safety procedures.
Features
Feature	Description
Live monitoring	Displays sensor readings and the current drainage condition.
Anomaly detection	Identifies abnormal sensor patterns and possible drainage problems.
Offline prediction	Provides local overflow-risk prediction and anomaly analysis.
Alerts	Provides sound notifications for critical conditions.
USB serial and Wi-Fi	Supports communication with the ESP32-S3 prototype.
GSM SMS notifications	Supports SMS alerts through the connected hardware.
Sensor calibration	Includes calibration controls and a guided calibration wizard.
Incident history	Records and displays drainage incidents.
PDF reports	Generates incident reports.
CSV recording	Records sensor readings for testing and analysis.
Drip mascot	Provides application notifications through the FlowBeacon mascot.


Monitoring Parameters
FlowBeacon is designed to monitor four drainage parameters:
- Water flow — detects changes in drainage flow.
- Water level — tracks changes in water level.
- Turbidity — monitors turbidity readings.
- Rain plate — detects rainfall conditions using the connected sensor.
Detection Conditions
Condition	Meaning
Normal	Readings indicate normal operation.
Possible Blockage	An abnormal flow pattern has been identified.
Blockage Warning	Readings indicate a potential developing blockage.
Overflow Risk	Readings indicate an increased possibility of overflow.
Overflow Detected	The system has identified an overflow condition.


These are application conditions derived from the prototype's sensor data and detection logic. They are not a guarantee that a physical blockage or overflow is present.
Supported Platforms and Packages
Platform	Package formats
Windows 11	NSIS installer (.exe) and portable executable (.exe)
Linux	AppImage and DEB


The Windows package targets x64. Linux package availability can depend on the distribution and system libraries.
Download
Published builds are listed on the GitHub Releases page.

Read the release notes and select the package that matches your operating system. Do not install a build if its source, version, or publisher information cannot be verified.
Run from Source
Requirements
- Node.js
- npm
- Git
Setup
git clone https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert.git
cd smart-drain-alert
npm install
npm start
Build Locally
Run the build command for the operating system on which you are building.

Windows:
npm run dist:win
Linux:
npm run dist:linux
The configured build output directory is dist/.
Automated Builds with GitHub Actions
The repository contains a GitHub Actions workflow named Build and sign (.github/workflows/build.yml). The workflow has produced Windows and Linux build artifacts and publishes release assets for tagged versions.

To prepare a release:
1. Update the application version in package.json.
2. Review the source code and build workflow changes.
3. Commit and push the release changes.
4. Create and push a version tag that matches the release version.
Example tag commands (replace the version with the version being released):
git tag vX.Y.Z
git push origin vX.Y.Z
After the workflow finishes, review the run and confirm that the expected Windows and Linux assets are attached to the GitHub Release. A workflow artifact is not a substitute for checking the public release page.
ESP32-S3 Integration
FlowBeacon supports communication with the ESP32-S3 prototype through:
- USB serial communication
- Wi-Fi communication
- GSM-based SMS notifications through the connected hardware
The application also provides the following help and diagnostic areas:
- Firmware Console
- Serial Data Format
- Wiring Help
Sensor readings and system conditions depend on the connected hardware, firmware, sensor calibration, and communication configuration.
First-Run Setup
The first-run setup assistant checks selected system requirements and provides guidance.

Windows guidance includes:
- USB-to-serial driver availability
- CP210x and CH340 driver information
Linux guidance includes:
- Serial-port permissions
- Common serial-access groups such as dialout or uucp, depending on the distribution
The setup assistant can also be opened from Help → Setup. Driver installation and permission changes should be performed only when needed and with the operating system's normal security prompts.
Privacy and Data Handling
FlowBeacon supports USB serial and Wi-Fi communication with an ESP32-S3 prototype and GSM-based SMS notifications through connected hardware. It also includes incident-history, CSV-recording, and PDF-report features.

The exact data stored, storage locations, Wi-Fi destinations, SMS recipients, retention periods, and available opt-out controls must be documented for the actual application and hardware configuration. This README does not claim that all deployments are offline-only or that no information is transmitted.

Before distributing the application, the project maintainers should publish a complete privacy notice describing the implemented data flows and any optional transmissions. If the application sends user data to services or recipients not specifically selected by the user or operator, the privacy notice and installation controls must address that behavior.
Code Signing Policy
Free code signing provided by SignPath.io, certificate by SignPath Foundation.

SignPath Foundation code signing is intended for eligible open-source projects and is subject to Foundation approval and its current terms. This statement does not mean that the current release is already signed by SignPath. A release should be described as SignPath-signed only after the corresponding signing request has completed successfully and the resulting binary has been verified.
Project Roles
The following role assignments must be completed with the real GitHub accounts responsible for each task before the project relies on SignPath Foundation signing:
- Authors: @Arjun-Ganesh-S-MCT — repository maintainer / author, if this account is authorized to make changes without review.
- Reviewers: Add the GitHub username(s) of the people who review changes submitted by contributors who are not project committers.
- Approvers: Add the GitHub username(s) of the people authorized by the project team to approve each release-signing request.
Do not leave the reviewer or approver entries as instructions or placeholders in the final published policy. List only people who have actually accepted these responsibilities. A person should be listed in more than one role only if that accurately reflects the project's agreed process.
SignPath Release Process
If the project is accepted by SignPath Foundation and the repository is configured for verified builds:
1. The Windows build is generated from the public source repository through the configured GitHub Actions workflow.
2. The workflow submits the eligible artifact to the configured SignPath project and signing policy.
3. The required project approver(s) review and approve the signing request.
4. The completed signed artifact is retrieved, verified, and published as the release asset.
Only binaries built from this project's source code should be submitted for signing. Third-party components must not be represented as binaries authored by FlowBeacon. Product name and version metadata on signed files must match the FlowBeacon product and the release version.
Technology
- Desktop framework: Electron
- Packaging: electron-builder
- Hardware platform: ESP32-S3
- Build automation: GitHub Actions
Credits and Attributions
- Project: FlowBeacon
- Developer / project label: TechMinds
- Hardware: ESP32-S3
- Desktop framework: Electron
- JetBrains Mono: SIL Open Font License
- Drip mascot artwork: TechMinds
- TechMinds logo: TechMinds
License
FlowBeacon is released under the MIT License. See the LICENSE file for the complete license text.
<p align="center">
  <strong>FlowBeacon — Detect Early. Alert Smart. Prevent Overflow.</strong><br />
  <sub>Developed by TechMinds</sub>
</p>
