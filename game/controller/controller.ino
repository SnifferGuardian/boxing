#include <Adafruit_NeoPixel.h>

const int PIEZO_THRESHOLD = 100;
const long BAUD_RATE = 115200;
const int NUM_LEDS_PER_RING = 12;

const int LED_PINS[4] = {2, 3, 4, 5};
const int PIEZO_PINS[4] = {A0, A1, A2, A3};

Adafruit_NeoPixel rings[4] = {
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[0], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[1], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[2], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[3], NEO_GRB + NEO_KHZ800)
};

bool isWaitingForHit = false;
unsigned long startTime = 0;
unsigned long testDuration = 0;
int activeTarget = -1;

void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(100); 
  
  for(int i = 0; i < 4; i++) {
    rings[i].begin();
    rings[i].setBrightness(100);
    rings[i].show(); 
  }
  Serial.println("start"); 
}

void setRingColor(int targetIndex, uint32_t color) {
  for(int i = 0; i < NUM_LEDS_PER_RING; i++) {
    rings[targetIndex].setPixelColor(i, color);
  }
  rings[targetIndex].show();
}

void loop() {
  if (Serial.available() > 0 && !isWaitingForHit) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    int firstComma = input.indexOf(',');
    int secondComma = input.indexOf(',', firstComma + 1);

    if (firstComma > 0 && secondComma > 0) {
      activeTarget = input.substring(0, firstComma).toInt();
      String colorStr = input.substring(firstComma + 1, secondComma);
      char colorChar = colorStr[0];
      testDuration = input.substring(secondComma + 1).toInt();

      if(activeTarget >= 0 && activeTarget < 4) {
      uint32_t targetColor = (colorChar == 'R') ? rings[activeTarget].Color(255, 0, 0) : 
                              (colorChar == 'G') ? rings[activeTarget].Color(0, 255, 0) : 
                              (colorChar == 'B') ? rings[activeTarget].Color(0,0,255) :
                              (colorChar == 'Y') ? rings[activeTarget].Color(255,255,0):
                              (colorChar == 'M') ? rings[activeTarget].Color(255,0,255):
                              (colorChar == 'C') ? rings[activeTarget].Color(0,255,255):
                              (colorChar == 'W') ? rings[activeTarget].Color(255,255,255):
                              rings[activeTarget].Color(0,0,0);

        
        setRingColor(activeTarget, targetColor);
        
        delay(50); 
        
        startTime = millis();
        isWaitingForHit = true;
      }
    }
  }

  if (isWaitingForHit) {
    int piezoStrength = analogRead(PIEZO_PINS[activeTarget]);
    

    if (piezoStrength > PIEZO_THRESHOLD) {
      unsigned long reactionTime = millis() - startTime;
      setRingColor(activeTarget, rings[activeTarget].Color(0, 0, 0)); 
      isWaitingForHit = false;
      Serial.print(piezoStrength);
      Serial.print(",");
      Serial.println(reactionTime);
    }
    else if (millis() - startTime >= testDuration) {
      setRingColor(activeTarget, rings[activeTarget].Color(0, 0, 0)); 
      isWaitingForHit = false;
      Serial.println("0,0"); 
    }
  }
}