/*
  Flow Beacon - Arduino Uno/Nano (classic 5 V)

  Sensors:
    ZJ-S201 Water Flow Sensor
    AZDM01 Turbidity Sensor
    Rain Sensor
    3-Level Water Sensor using BC547 transistors
*/

#include <Arduino.h>

// Original sensor pins
const uint8_t PIN_FLOW = 2;
const uint8_t PIN_RAIN = 7;
const uint8_t PIN_TURBIDITY = A0;

// Water level transistor pins
const uint8_t PIN_LEVEL_LOW = 3;
const uint8_t PIN_LEVEL_MID = 4;
const uint8_t PIN_LEVEL_HIGH = 5;

// Calibration values
const float FLOW_HZ_PER_LPM = 7.5f;
const float BASELINE_FLOW_LPM = 4.2f;
const int TURBIDITY_CLOUDY_THRESHOLD = 700;

// Rain sensor configuration
const uint8_t RAIN_WET_LEVEL = LOW;

const unsigned long SAMPLE_PERIOD_MS = 1000;
const unsigned long MIN_FLOW_PULSE_US = 500UL;

volatile unsigned long flowPulseCount = 0;
volatile unsigned long lastFlowPulseUs = 0;

unsigned long lastSampleMs = 0;


// Flow sensor interrupt
void countFlowPulse() {
  const unsigned long nowUs = micros();

  if (nowUs - lastFlowPulseUs >= MIN_FLOW_PULSE_US) {
    flowPulseCount++;
    lastFlowPulseUs = nowUs;
  }
}


void setup() {

  Serial.begin(115200);

  // Original sensors
  pinMode(PIN_FLOW, INPUT_PULLUP);
  pinMode(PIN_RAIN, INPUT);
  pinMode(PIN_TURBIDITY, INPUT);

  // Water level sensors
  pinMode(PIN_LEVEL_LOW, INPUT_PULLUP);
  pinMode(PIN_LEVEL_MID, INPUT_PULLUP);
  pinMode(PIN_LEVEL_HIGH, INPUT_PULLUP);

  // Flow sensor interrupt
  attachInterrupt(
    digitalPinToInterrupt(PIN_FLOW),
    countFlowPulse,
    FALLING
  );

  Serial.println(
    F("{\"device\":\"flow-beacon-arduino\",\"state\":\"ready\"}")
  );
}


void loop() {

  const unsigned long nowMs = millis();

  if (nowMs - lastSampleMs < SAMPLE_PERIOD_MS)
    return;

  lastSampleMs = nowMs;


  // Read flow pulses safely
  noInterrupts();

  const unsigned long pulses = flowPulseCount;
  flowPulseCount = 0;

  interrupts();


  // Flow calculation
  const float flowLpm = pulses / FLOW_HZ_PER_LPM;


  // Read turbidity
  const int turbidityRaw = analogRead(PIN_TURBIDITY);


  // Read rain sensor
  const bool rainWet =
    digitalRead(PIN_RAIN) == RAIN_WET_LEVEL;


  // Turbidity detection
  const bool turbidityCloudy =
    turbidityRaw < TURBIDITY_CLOUDY_THRESHOLD;


  // Read water level transistors
  const bool levelLowWet =
    digitalRead(PIN_LEVEL_LOW) == LOW;

  const bool levelMidWet =
    digitalRead(PIN_LEVEL_MID) == LOW;

  const bool levelHighWet =
    digitalRead(PIN_LEVEL_HIGH) == LOW;


  // Calculate water level percentage
  int waterLevelPercent = 0;

  if (levelLowWet)
    waterLevelPercent = 33;

  if (levelMidWet)
    waterLevelPercent = 66;

  if (levelHighWet)
    waterLevelPercent = 100;


  // Flow drop detection
  const bool flowDropped =
    flowLpm <= BASELINE_FLOW_LPM * 0.75f;

  const bool severeFlowDrop =
    flowLpm <= BASELINE_FLOW_LPM * 0.50f;


  // Status information
  const char *status = "normal";
  const char *cause = "none_indicated";
  const char *confidence = "low";


  // Blockage detection
  if (severeFlowDrop) {

    status = "blockage_warning";
    confidence = "medium";

    if (rainWet && turbidityCloudy) {

      cause = "major_flow_drop_rain_and_cloudy_water";

    } else if (rainWet) {

      cause = "major_flow_drop_rain_may_contribute";

    } else if (turbidityCloudy) {

      cause = "major_flow_drop_cloudy_water_possible_silt";

    } else {

      cause = "major_flow_drop_possible_restriction";
    }

  }

  else if (flowDropped) {

    status = "blockage_warning";
    confidence = "low";

    if (rainWet && turbidityCloudy) {

      cause = "flow_drop_rain_and_cloudy_water";

    } else if (rainWet) {

      cause = "flow_drop_rain_may_contribute";

    } else if (turbidityCloudy) {

      cause = "flow_drop_cloudy_water_possible_silt";

    } else {

      cause = "flow_drop_possible_restriction";
    }

  }

  else if (rainWet) {

    status = "rain_detected";
    cause = "rain_plate_wet_monitoring_flow";
  }


  // Send JSON data
  Serial.print(
    F("{\"device\":\"flow-beacon-arduino\",\"flow_l_min\":")
  );

  Serial.print(flowLpm, 2);


  // Water level
  Serial.print(F(",\"water_level_percent\":"));
  Serial.print(waterLevelPercent);

  Serial.print(F(",\"level_low_wet\":"));
  Serial.print(levelLowWet ? F("true") : F("false"));

  Serial.print(F(",\"level_mid_wet\":"));
  Serial.print(levelMidWet ? F("true") : F("false"));

  Serial.print(F(",\"level_high_wet\":"));
  Serial.print(levelHighWet ? F("true") : F("false"));


  // Turbidity
  Serial.print(F(",\"turbidity_raw\":"));
  Serial.print(turbidityRaw);

  Serial.print(F(",\"turbidity_cloudy\":"));
  Serial.print(
    turbidityCloudy ? F("true") : F("false")
  );


  // Rain
  Serial.print(F(",\"rain_wet\":"));
  Serial.print(
    rainWet ? F("true") : F("false")
  );


  // Status
  Serial.print(F(",\"status\":\""));
  Serial.print(status);

  Serial.print(F("\",\"likely_cause\":\""));
  Serial.print(cause);

  Serial.print(F("\",\"confidence\":\""));
  Serial.print(confidence);

  Serial.println(F("\"}"));

}
