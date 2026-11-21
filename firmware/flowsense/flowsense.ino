#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

#if __has_include("model.h")
#include "model.h"
#else
#define HAS_MODEL 0
#endif

const char* NODE_ID = "drain-1";

const int PIN_FLOW = 4;
const int PIN_TRIG = 5;
const int PIN_ECHO = 6;
const int PIN_TURB = 1;
const int PIN_RAIN = 7;
const int GSM_RX = 17;
const int GSM_TX = 18;

const float PULSES_PER_LITRE = 450.0;
const bool TURB_INVERT = true;
const bool RAIN_ACTIVE_LOW = true;

WebSocketsServer ws(81);
volatile uint32_t pulses = 0;
bool wsOn = false;
bool wifiPending = false;
uint32_t wifiStart = 0;
uint32_t intervalMs = 1000;
uint32_t lastMs = 0;
String lineBuf;

void IRAM_ATTR onPulse() { pulses++; }

float readDistanceCm() {
  float v[3];
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_TRIG, LOW);
    delayMicroseconds(4);
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(12);
    digitalWrite(PIN_TRIG, LOW);
    uint32_t us = pulseIn(PIN_ECHO, HIGH, 40000);
    v[i] = us ? us * 0.0343f / 2.0f : 0;
    delay(30);
  }
  if (v[0] > v[1]) { float t = v[0]; v[0] = v[1]; v[1] = t; }
  if (v[1] > v[2]) { float t = v[1]; v[1] = v[2]; v[2] = t; }
  if (v[0] > v[1]) { float t = v[0]; v[0] = v[1]; v[1] = t; }
  return v[1];
}

int readTurbidity() {
  long sum = 0;
  for (int i = 0; i < 16; i++) sum += analogRead(PIN_TURB);
  int raw = sum / 16;
  return TURB_INVERT ? 4095 - raw : raw;
}

int readRain() {
  int v = digitalRead(PIN_RAIN);
  return (RAIN_ACTIVE_LOW ? v == LOW : v == HIGH) ? 1 : 0;
}

#if HAS_MODEL
const char* classify(float flow, float dist, float turb, int rain) {
  float x[4] = {
    BASE_FLOW > 0 ? 1 - flow / BASE_FLOW : 0,
    BASE_DIST - dist,
    BASE_TURB > 0 ? (turb - BASE_TURB) / BASE_TURB : 0,
    (float)rain
  };
  int best = 0;
  float bestScore = -1e30;
  for (int i = 0; i < ML_N; i++) {
    float s = log(ML_PRIOR[i]);
    for (int j = 0; j < 4; j++) {
      float z = (x[j] - ML_MEAN[i][j]) / ML_STD[i][j];
      s += -0.5f * z * z - log(ML_STD[i][j]);
    }
    if (s > bestScore) { bestScore = s; best = i; }
  }
  return ML_LABELS[best];
}
#endif

void sendSms(const String& to, const String& msg) {
  Serial1.println("AT+CMGF=1");
  delay(300);
  Serial1.println("AT+CMGS=\"" + to + "\"");
  delay(300);
  Serial1.print(msg);
  Serial1.write(26);
  delay(3000);
}

void handleLine(String line) {
  line.trim();
  if (!line.length()) return;
  if (line == "restart") ESP.restart();
  if (line == "ping") { Serial.println("{\"pong\":1}"); return; }
  JsonDocument d;
  if (deserializeJson(d, line)) return;
  String cmd = d["cmd"] | "";
  if (cmd == "sms") sendSms(d["to"].as<String>(), d["msg"].as<String>());
  else if (cmd == "interval") intervalMs = constrain((uint32_t)d["ms"].as<uint32_t>(), 250, 60000);
  else if (cmd == "restart") ESP.restart();
  else if (cmd == "wifi") {
    WiFi.disconnect();
    WiFi.begin(d["ssid"].as<const char*>(), d["pass"].as<const char*>());
    wifiPending = true;
    wifiStart = millis();
  }
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, GSM_RX, GSM_TX);
  pinMode(PIN_FLOW, INPUT_PULLUP);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_RAIN, INPUT);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);
  WiFi.mode(WIFI_STA);
  WiFi.begin();
  wifiPending = true;
  wifiStart = millis();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { handleLine(lineBuf); lineBuf = ""; }
    else if (lineBuf.length() < 400) lineBuf += c;
  }

  if (wifiPending) {
    if (WiFi.status() == WL_CONNECTED) {
      wifiPending = false;
      if (!wsOn) { ws.begin(); wsOn = true; }
      Serial.printf("{\"ip\":\"%s\"}\n", WiFi.localIP().toString().c_str());
    } else if (millis() - wifiStart > 20000) {
      wifiPending = false;
      Serial.println("{\"wifi\":\"failed\"}");
    }
  }
  if (wsOn) ws.loop();

  uint32_t now = millis();
  if (now - lastMs < intervalMs) return;
  uint32_t window = now - lastMs;
  lastMs = now;

  noInterrupts();
  uint32_t p = pulses;
  pulses = 0;
  interrupts();
  float flow = (p / PULSES_PER_LITRE) * (60000.0f / window);
  float dist = readDistanceCm();
  int turb = readTurbidity();
  int rain = readRain();

  char out[200];
#if HAS_MODEL
  snprintf(out, sizeof(out), "{\"node\":\"%s\",\"flow\":%.2f,\"dist\":%.1f,\"turb\":%d,\"rain\":%d,\"ml\":\"%s\"}", NODE_ID, flow, dist, turb, rain, classify(flow, dist, turb, rain));
#else
  snprintf(out, sizeof(out), "{\"node\":\"%s\",\"flow\":%.2f,\"dist\":%.1f,\"turb\":%d,\"rain\":%d}", NODE_ID, flow, dist, turb, rain);
#endif
  Serial.println(out);
  if (wsOn) ws.broadcastTXT(out);
}
