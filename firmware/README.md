# FlowBeacon firmware: Arduino Uno / Nano

Sketch: `flowbeacon-nano/flowbeacon-nano.ino` (Arduino IDE, board "Arduino Nano", processor ATmega328P). No extra libraries. It sends one JSON line per second over USB serial at 115200 baud, and does not read anything from the apps.

## Wiring (as in the sketch)

| Part | Pin |
|---|---|
| ZJ-S201 flow sensor | D2 |
| 3-level sensor, low probe (BC547) | D3 (INPUT_PULLUP, LOW = wet) |
| 3-level sensor, mid probe | D4 |
| 3-level sensor, high probe | D5 |
| Rain sensor | D7 (LOW = wet) |
| AZDM01 turbidity sensor | A0 |

## What the apps read from each line

| Sketch field | App meaning |
|---|---|
| `flow_l_min` | flow in L/min (7.5 Hz per L/min) |
| `level_low_wet`, `level_mid_wet`, `level_high_wet` (or `water_level_percent`) | water level 0 to 3 probes wet |
| `turbidity_raw` | AZDM01, 10 bit. A lower value is cloudier water, so the app uses (1023 - raw) x 4 |
| `rain_wet` | rain plate wet |

The other fields (`status`, `likely_cause`, `confidence`, `turbidity_cloudy`) are ignored: the app works out its own warnings from the baseline you set.

## Level in the app

The apps turn the probes into a distance from the sensor top: 15 cm (dry), 11 (low probe), 7 (mid probe), 3 cm (high probe). `Overflow risk` defaults to 7 cm (mid probe) and `Overflow` to 3 cm (high probe). If your probes are spaced differently, change `EMPTY_CM` and `STEP_CM` in `desktop/flowbeacon_app/core.py` and `android/.../Core.kt`.

## Not in this sketch

No Wi-Fi, no commands from the app, and no GSM module, so the app's "SMS through the board" does nothing. On Android the phone can still show notifications.
