#include <FastLED.h>

#define LED_PIN     2       // Pin connected to the DIN of the LED strip
#define NUM_LEDS    12      // Number of LEDs in your strip
#define BRIGHTNESS  64      // Set brightness (0-255)
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB     // WS2812B typically uses Green-Red-Blue order

CRGB leds[NUM_LEDS];

void setup() {
  // Safety delay for power up
  delay(2000); 
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(BRIGHTNESS);
}

void loop() {
  static uint8_t initialHue = 0;
  
  // fill_rainbow(led array, number of leds, starting hue, hue increment per led)
  fill_rainbow(leds, NUM_LEDS, initialHue, 7);
  
  FastLED.show();
  
  // Speed of the rainbow motion
  initialHue += 2; 
  
  delay(20); 
}
