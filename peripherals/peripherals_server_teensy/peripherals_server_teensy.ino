#include "WS2812Serial.h"

#define NUM_LED 62
#define PIN_LED 1

byte drawing_memory[NUM_LED*3];         //  3 bytes per LED
DMAMEM byte display_memory[NUM_LED*12]; // 12 bytes per LED

WS2812Serial leds(NUM_LED, display_memory, drawing_memory, PIN_LED, WS2812_GRB);

#define LED_STATE_IDLE 0
#define LED_STATE_ACTIVE 1
#define LED_STATE_ERROR 2
char led_state = LED_STATE_IDLE;

int time_last_receive = millis();

void setup() {
  Serial.begin(115200);

  leds.begin();
}

void loop() {
  check_serial();
  update_underglow();

  delay(1);
}

void check_serial() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    time_last_receive = millis();

    if (command.equals("PING")) {
      Serial.println("PONG");

    } else if (command.startsWith("LED ")) {
      command = command.substring(4);

      if (command.equals("IDLE")) {
        led_state = LED_STATE_IDLE;
      } else if (command.equals("ACTIVE")) {
        led_state = LED_STATE_ACTIVE;
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
  switch (led_state) {
    case LED_STATE_IDLE:
      set_all_leds(0x222222);
      break;
    case LED_STATE_ACTIVE:
      color = (millis()%1000 < 500) ? 0xff00ff : 0x000000;
      set_all_leds(color);
      break;
    case LED_STATE_ERROR:
      color = (millis()%500 < 250) ? 0xff0000 : 0x000000;
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
