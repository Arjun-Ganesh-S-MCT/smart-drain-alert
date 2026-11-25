/*
  FlowBeacon for the Arduino Nano (ATmega328P).
  Sensors: YF-S201 flow sensor, 5-step water level sensor (five probes, each through an NPN transistor),
           turbidity module (analog), rain plate module (digital), optional SIM800L for SMS.
  It sends one JSON line per second over USB serial (115200 baud), for example:
    {"node":"drain-1","flow":3.42,"lv":2,"dist":12.0,"turb":1180,"rain":0}
  "lv" is how many level probes are wet (0 to 5). "dist" is the same level as a distance, so older apps still work.
  Commands the app can send (one JSON line each): {"cmd":"interval","ms":1000}  {"cmd":"sms","to":"+91...","msg":"..."}  ping  restart
*/
#include <SoftwareSerial.h>

#define USE_GSM 1                       // set to 0 if there is no SIM800L

const char NODE_ID[] = "drain-1";

// ---- pins ----
const uint8_t PIN_FLOW = 2;             // flow sensor signal (interrupt 0)
const uint8_t PIN_RAIN = 3;             // rain module DO
const uint8_t LEVEL_PINS[5] = {4, 5, 6, 7, 8};   // probe 1 (lowest) ... probe 5 (highest)
const uint8_t PIN_TURB = A0;
const uint8_t PIN_BUZZER = 9;           // optional buzzer, beeps at overflow risk
const uint8_t GSM_RX = 10;              // Arduino receives from SIM800L TX
const uint8_t GSM_TX = 11;              // Arduino sends to SIM800L RX (use a voltage divider)

// ---- settings (keep EMPTY_CM and STEP_CM the same as in the app, see core.py / Core.kt) ----
const float EMPTY_CM = 18.0;            // distance from the sensor top to the water when no probe is wet
const float STEP_CM = 3.0;              // height between two probes
const bool LEVEL_ACTIVE_HIGH = true;    // true: a wet probe makes its transistor output HIGH
const bool RAIN_ACTIVE_LOW = true;
const bool TURB_INVERT = true;
const float PULSES_PER_LITRE = 450.0;

#if USE_GSM
SoftwareSerial gsm(GSM_RX, GSM_TX);
#endif

volatile uint16_t pulses = 0;
uint16_t intervalMs = 1000;
uint32_t lastMs = 0;
char lineBuf[160];
uint8_t lineLen = 0;

void onPulse() { pulses++; }

// Reads the five probes a few times and returns how many are wet (0 to 5). Sets `fault` if an upper probe is wet while a lower one is dry.
uint8_t readLevel(bool &fault) {
  uint8_t votes[5] = {0, 0, 0, 0, 0};
  for (uint8_t s = 0; s < 5; s++) {
    for (uint8_t i = 0; i < 5; i++) {
      bool wet = (digitalRead(LEVEL_PINS[i]) == HIGH) == LEVEL_ACTIVE_HIGH;
      if (wet) votes[i]++;
    }
    delay(4);
  }
  uint8_t lv = 0;
  fault = false;
  bool dryBelow = false;
  for (uint8_t i = 0; i < 5; i++) {
    bool wet = votes[i] >= 3;
    if (wet) { lv = i + 1; if (dryBelow) fault = true; }
    else dryBelow = true;
  }
  return lv;
}

int readTurbidity() {                   // scaled to 0..4095 like the original board, so the app thresholds match
  uint32_t sum = 0;
  for (uint8_t i = 0; i < 16; i++) sum += analogRead(PIN_TURB);
  int raw = (int)(sum / 16) * 4;
  if (raw > 4095) raw = 4095;
  return TURB_INVERT ? 4095 - raw : raw;
}

uint8_t readRain() {
  bool v = digitalRead(PIN_RAIN) == HIGH;
  return (RAIN_ACTIVE_LOW ? !v : v) ? 1 : 0;
}

// Finds "key":"value" in a JSON line and copies the value (no escapes) into out.
bool getStr(const char *line, const char *key, char *out, uint8_t n) {
  char pat[16];
  snprintf(pat, sizeof(pat), "\"%s\":\"", key);
  const char *p = strstr(line, pat);
  if (!p) return false;
  p += strlen(pat);
  uint8_t i = 0;
  while (*p && *p != '"' && i < n - 1) out[i++] = *p++;
  out[i] = 0;
  return true;
}

long getNum(const char *line, const char *key, long def) {
  char pat[16];
  snprintf(pat, sizeof(pat), "\"%s\":", key);
  const char *p = strstr(line, pat);
  return p ? atol(p + strlen(pat)) : def;
}

#if USE_GSM
void sendSms(const char *to, const char *msg) {
  gsm.println(F("AT+CMGF=1"));
  delay(300);
  gsm.print(F("AT+CMGS=\""));
  gsm.print(to);
  gsm.println('"');
  delay(300);
  gsm.print(msg);
  gsm.write(26);
  delay(3000);
}
#endif

void handleLine(char *line) {
  if (!line[0]) return;
  if (!strcmp(line, "ping")) { Serial.println(F("{\"pong\":1}")); return; }
  if (!strcmp(line, "restart")) { asm volatile("jmp 0"); }
  if (strstr(line, "\"cmd\":\"interval\"")) {
    long ms = getNum(line, "ms", 1000);
    intervalMs = (uint16_t)constrain(ms, 250, 60000);
  } else if (strstr(line, "\"cmd\":\"restart\"")) {
    asm volatile("jmp 0");
  }
#if USE_GSM
  else if (strstr(line, "\"cmd\":\"sms\"")) {
    char to[20], msg[100];
    if (getStr(line, "to", to, sizeof(to)) && getStr(line, "msg", msg, sizeof(msg))) sendSms(to, msg);
  }
#endif
}

void setup() {
  Serial.begin(115200);
#if USE_GSM
  gsm.begin(9600);
#endif
  pinMode(PIN_FLOW, INPUT_PULLUP);
  pinMode(PIN_RAIN, INPUT);
  for (uint8_t i = 0; i < 5; i++) pinMode(LEVEL_PINS[i], INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { lineBuf[lineLen] = 0; handleLine(lineBuf); lineLen = 0; }
    else if (c != '\r' && lineLen < sizeof(lineBuf) - 1) lineBuf[lineLen++] = c;
  }

  uint32_t now = millis();
  if (now - lastMs < intervalMs) return;
  uint32_t window = now - lastMs;
  lastMs = now;

  noInterrupts();
  uint16_t p = pulses;
  pulses = 0;
  interrupts();
  float flow = (p / PULSES_PER_LITRE) * (60000.0f / window);

  bool fault;
  uint8_t lv = readLevel(fault);
  float dist = EMPTY_CM - lv * STEP_CM;
  int turb = readTurbidity();
  uint8_t rain = readRain();

  digitalWrite(PIN_BUZZER, lv >= 4 ? HIGH : LOW);

  char f[12], d[10];
  dtostrf(flow, 1, 2, f);
  dtostrf(dist, 1, 1, d);
  char out[120];
  snprintf(out, sizeof(out), "{\"node\":\"%s\",\"flow\":%s,\"lv\":%u,\"dist\":%s,\"turb\":%d,\"rain\":%u%s}",
           NODE_ID, f, lv, d, turb, rain, fault ? ",\"fault\":1" : "");
  Serial.println(out);
}
