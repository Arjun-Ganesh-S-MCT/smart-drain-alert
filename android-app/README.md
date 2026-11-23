# FlowBeacon for Android

The APK is built automatically by `.github/workflows/android.yml` (GitHub -> Actions -> "Android APK" -> Run workflow, or push a `v*` tag).
Download `FlowBeacon.apk` from the run's Artifacts (or the release), copy it to the phone and install it (allow "install unknown apps").

Local build (needs Node 20, JDK 17, Android SDK): in the repo root `npm install`, then in this folder `npm install && npm run prepare-web && npx cap add android && npx capacitor-assets generate --android --assetPath assets && npx cap sync android && cd android && ./gradlew assembleDebug`.

On a phone: use Demo mode, the city map and everything else normally; connect the ESP32 over **Wi-Fi** (Connection tab, board IP, WebSocket port 81). USB serial is not available on Android.
