#include "Bitcraze_PMW3901.h"  // This library must be installed via the Arduino IDE or https://github.com/bitcraze/Bitcraze_PMW3901

// Using digital pin 10 for chip select
Bitcraze_PMW3901 flow(10);

void setup() {
  Serial.begin(115200);

  if (!flow.begin()) {
    Serial.println("ERROR_FLOW_INIT");
    while (1) {}
  }

  flow.setLed(true);
}

int16_t deltaX,deltaY;

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');

    if (command.equals("FLOW")) {
      // Get motion count since last call
      flow.readMotionCount(&deltaX, &deltaY);

      Serial.print(deltaX);
      Serial.print(",");
      Serial.println(deltaY);
    }
  }

  delay(10);
}
