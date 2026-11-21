# FlowSense firmware (ESP32-S3)

Arduino sketch in `flowsense/flowsense.ino`. Install the libraries **ArduinoJson** (version 7) and **WebSockets** by Markus Sattler from the Library Manager, select an ESP32-S3 board, then upload.

## Before you upload
- Open `flowsense.ino` and set the pin numbers at the top to match your wiring. The values there are placeholders.
- Set `NODE_ID` to a different name for each drain, for example `drain-2`. The app shows each node as its own drain.
- The ultrasonic echo, turbidity output and flow signal can exceed 3.3 V. Put them through the 4-channel voltage divider before connecting.
- If your turbidity module reads lower when the water is dirtier, keep `TURB_INVERT` true. If the rain plate reads high when wet, set `RAIN_ACTIVE_LOW` to false.
- The flow constant `PULSES_PER_LITRE` is 450 for a YF-S201 type sensor (7.5 Hz per L/min). Check your ZJ-S201 datasheet and calibrate it against a measured litre.

## What it does
- Prints one JSON line every second over USB and, once Wi-Fi is up, on WebSocket port 81.
- Accepts JSON commands from the app: `wifi` (name and password), `sms` (needs a GSM module on Serial1), `interval` and `restart`. Plain `restart` and `ping` also work.
- Remembers the Wi-Fi details in flash and reconnects after a restart.

## Learned model (optional)
In the app, record labelled tests, train under Learn from recordings, press Export model.h, and replace `flowsense/model.h` with it. The board then adds an `"ml"` field with its own classification, computed on the ESP32-S3 with no PC.
