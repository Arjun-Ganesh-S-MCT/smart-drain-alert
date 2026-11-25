# FlowBeacon firmware: Arduino Nano

Sketch: `flowbeacon-nano/flowbeacon-nano.ino` (Arduino IDE, board "Arduino Nano", processor ATmega328P, old bootloader if upload fails). No extra libraries.

## Wiring

| Part | Nano pin |
|---|---|
| Flow sensor YF-S201 signal | D2 (5 V and GND) |
| Rain module DO | D3 |
| Level probe 1 (lowest) | D4 |
| Level probe 2 | D5 |
| Level probe 3 | D6 |
| Level probe 4 | D7 |
| Level probe 5 (highest) | D8 |
| Turbidity module analog out | A0 |
| Buzzer (optional) | D9 |
| SIM800L TX / RX (optional) | D10 / D11 (use a voltage divider on D11 to the SIM800L RX) |

## The 5-level sensor

Mount five probes in the drain at 3 cm steps. Each probe feeds the base of an NPN transistor (through a resistor, about 100 k) so the Nano pin goes HIGH when the probe is wet. If your circuit is the other way round, set `LEVEL_ACTIVE_HIGH` to `false`.

The Nano sends `lv` (how many probes are wet, 0 to 5) and the matching `dist`. If you change the probe spacing or the empty distance, change `STEP_CM` and `EMPTY_CM` in the sketch and the same two numbers in `desktop/flowbeacon_app/core.py` and `android/.../Core.kt`.

## Connecting

The Nano talks over USB only (115200 baud): a USB cable to the PC, or a USB OTG cable to the phone. There is no Wi-Fi. If a probe reads wet while a lower one is dry, the Nano adds `"fault":1` to the line.
