#include "Bitcraze_PMW3901.h"  // This library must be installed via the Arduino IDE or https://github.com/bitcraze/Bitcraze_PMW3901

// Using digital pin 10 for chip select
Bitcraze_PMW3901 flow(10);

void setup() {
  Serial.begin(115200);

  if (!flow.begin()) {
    Serial.print("Init flow failed :'(\n");
    while (1) {}
  }

  flow.setLed(true);
}

int16_t deltaX,deltaY;

void loop() {
  // Get motion count since last call
  flow.readMotionCount(&deltaX, &deltaY);

  Serial.print("X: ");
  Serial.print(deltaX);
  Serial.print(", Y: ");
  Serial.println(deltaY);

  delay(100);
}
