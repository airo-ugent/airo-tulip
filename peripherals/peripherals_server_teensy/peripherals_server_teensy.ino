#include "WS2812Serial.h"
#include "Bitcraze_PMW3901.h"
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <math.h>
#include <SPI.h>

#define NUM_LED 62
#define PIN_LED 1

byte drawing_memory[NUM_LED*3];         //  3 bytes per LED
DMAMEM byte display_memory[NUM_LED*12]; // 12 bytes per LED

WS2812Serial leds(NUM_LED, display_memory, drawing_memory, PIN_LED, WS2812_GRB);

#define LED_STATE_IDLE 0
#define LED_STATE_ACTIVE 1
#define LED_STATE_ERROR 2
char led_state = LED_STATE_IDLE;
float led_active_angle;
float led_active_velocity;

// Using digital pin 10 and pin 9 for chip select
#define PIN_CS_FLOW1 10
#define PIN_CS_FLOW2 9
Bitcraze_PMW3901 flow1(PIN_CS_FLOW1);
Bitcraze_PMW3901 flow2(PIN_CS_FLOW2);

// Variables for BNO055
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);

int time_last_receive = millis();

void setup() {
  Serial.begin(115200);

  // Setup SPI port
  SPI.begin();
  pinMode(PIN_CS_FLOW1, OUTPUT);
  pinMode(PIN_CS_FLOW2, OUTPUT);
  digitalWrite(PIN_CS_FLOW1, HIGH);
  digitalWrite(PIN_CS_FLOW2, HIGH);

  if (!flow1.begin() || !flow2.begin()) {
    Serial.println("ERROR_FLOW_INIT");
    while (1) {}
  }
  flow1.setLed(true);
  flow2.setLed(true);

  // Setup BNO055
  if (!bno.begin()) {
    Serial.println("ERROR_BNO_INIT");
    while (1) {}
  }
  bno.setExtCrystalUse(true);

  leds.begin();
}

void loop() {
  check_serial();
  update_underglow();

  delay(1);
}

int16_t deltaX1,deltaY1,deltaX2,deltaY2;

void check_serial() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    time_last_receive = millis();

    if (command.equals("PING")) {
      Serial.println("PONG");

    } else if (command.equals("FLOW")) {
      // Get motion count since last call
      flow1.readMotionCount(&deltaX1, &deltaY1);
      flow2.readMotionCount(&deltaX2, &deltaY2);

      Serial.print(deltaX1);
      Serial.print(",");
      Serial.print(deltaY1);
      Serial.print(",");
      Serial.print(deltaX2);
      Serial.print(",");
      Serial.println(deltaY2);

    } else if (command.equals("BNO")) {
      // Get orientation
      sensors_event_t event;
      bno.getEvent(&event);

      Serial.print(event.orientation.x);
      Serial.print(",");
      Serial.print(event.orientation.y);
      Serial.print(",");
      Serial.println(event.orientation.z);

    } else if (command.startsWith("LED ")) {
      command = command.substring(4);

      if (command.equals("IDLE")) {
        led_state = LED_STATE_IDLE;
      } else if (command.startsWith("ACTIVE ")) {
        led_state = LED_STATE_ACTIVE;
        command = command.substring(7);
        led_active_angle = command.substring(0, command.indexOf(" ")).toFloat();
        led_active_velocity = command.substring(command.indexOf(" ")+1).toFloat();
      } else if (command.equals("ERROR")) {
        led_state = LED_STATE_ERROR;
      }

      Serial.println("OK");
    }
  }
}

void update_underglow() {
  if (led_state == LED_STATE_ACTIVE && millis() > time_last_receive + 1000) {
    led_state = LED_STATE_ERROR;
  }

  int color;
  int led;
  int num_led_bar;
  switch (led_state) {
    case LED_STATE_IDLE:
      set_all_leds(0x222222);
      break;
    case LED_STATE_ACTIVE:
      led = angle_to_led(led_active_angle);
      num_led_bar = led_active_velocity * 30;
      color = (millis()%1000 < 500) ? 0x400040 : 0x000000;
      for (int i=0; i<NUM_LED; i++) {
        leds.setPixel(i, color);
      }
      color = 0xffffff;
      for (int i=0; i<num_led_bar/2; i++) {
        leds.setPixel((led-i)%NUM_LED, color);
        leds.setPixel((led+i)%NUM_LED, color);
      }
      leds.show();
      break;
    case LED_STATE_ERROR:
      color = (millis()%500 < 200) ? 0xff0000 : 0x000000;
      set_all_leds(color);
      break;
  }
}

void set_all_leds(int color) {
  for (int i=0; i<NUM_LED; i++) {
    leds.setPixel(i, color);
  }
  leds.show();
}

int angle_to_led(float angle) {
  angle = fmod(angle, 2*3.1415f);
  int led;
  if (angle < 0.111f) led = 6;
  else if (angle < 0.219f) led = 7;
  else if (angle < 0.322f) led = 8;
  else if (angle < 0.418f) led = 9;
  else if (angle < 0.507f) led = 10;
  else if (angle < 0.588f) led = 11;
  else if (angle < 0.644f) led = 12;
  else if (angle < 0.709f) led = 14;
  else if (angle < 0.785f) led = 15;
  else if (angle < 0.876f) led = 16;
  else if (angle < 0.983f) led = 17;
  else if (angle < 1.107f) led = 18;
  else if (angle < 1.249f) led = 19;
  else if (angle < 1.406f) led = 20;
  else if (angle < 1.571f) led = 21;
  else if (angle < 3.142f-1.406f) led = 22;
  else if (angle < 3.142f-1.249f) led = 23;
  else if (angle < 3.142f-1.107f) led = 24;
  else if (angle < 3.142f-0.983f) led = 25;
  else if (angle < 3.142f-0.876f) led = 26;
  else if (angle < 3.142f-0.785f) led = 27;
  else if (angle < 3.142f-0.709f) led = 28;
  else if (angle < 3.142f-0.644f) led = 29;
  else if (angle < 3.142f-0.588f) led = 30;
  else if (angle < 3.142f-0.507f) led = 31;
  else if (angle < 3.142f-0.418f) led = 32;
  else if (angle < 3.142f-0.322f) led = 33;
  else if (angle < 3.142f-0.219f) led = 34;
  else if (angle < 3.142f-0.111f) led = 35;
  else if (angle < 3.142f) led = 36;
  else if (angle < 3.142f+0.111f) led = 37;
  else if (angle < 3.142f+0.219f) led = 38;
  else if (angle < 3.142f+0.322f) led = 39;
  else if (angle < 3.142f+0.418f) led = 40;
  else if (angle < 3.142f+0.507f) led = 41;
  else if (angle < 3.142f+0.588f) led = 42;
  else if (angle < 3.142f+0.644f) led = 43;
  else if (angle < 3.142f+0.709f) led = 45;
  else if (angle < 3.142f+0.785f) led = 46;
  else if (angle < 3.142f+0.876f) led = 47;
  else if (angle < 3.142f+0.983f) led = 48;
  else if (angle < 3.142f+1.107f) led = 49;
  else if (angle < 3.142f+1.249f) led = 50;
  else if (angle < 3.142f+1.406f) led = 51;
  else if (angle < 3.142f+1.571f) led = 52;
  else if (angle < 6.283f-1.406f) led = 53;
  else if (angle < 6.283f-1.249f) led = 54;
  else if (angle < 6.283f-1.107f) led = 55;
  else if (angle < 6.283f-0.983f) led = 56;
  else if (angle < 6.283f-0.876f) led = 57;
  else if (angle < 6.283f-0.785f) led = 58;
  else if (angle < 6.283f-0.709f) led = 59;
  else if (angle < 6.283f-0.644f) led = 60;
  else if (angle < 6.283f-0.588f) led = 61;
  else if (angle < 6.283f-0.507f) led = 0;
  else if (angle < 6.283f-0.418f) led = 1;
  else if (angle < 6.283f-0.322f) led = 2;
  else if (angle < 6.283f-0.219f) led = 3;
  else if (angle < 6.283f-0.111f) led = 4;
  else led = 5;
  return led;
}
