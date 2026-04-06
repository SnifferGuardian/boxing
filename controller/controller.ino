#include <Adafruit_NeoPixel.h>

// --- Configuration ---
const int PIEZO_THRESHOLD = 50; 
const long BAUD_RATE = 115200;
const int NUM_LEDS_PER_RING = 12;

// --- Hardware Mapping ---
const int LED_PINS[4] = {2, 3, 4, 5};
const int PIEZO_PINS[4] = {A0, A1, A2, A3};

Adafruit_NeoPixel rings[4] = {
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[0], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[1], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[2], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUM_LEDS_PER_RING, LED_PINS[3], NEO_GRB + NEO_KHZ800)
};

// --- State Variables ---
bool isWaitingForHit = false;
unsigned long startTime = 0;
unsigned long testDuration = 0;
int activeTarget = -1;

void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(50);
  
  for(int i = 0; i < 4; i++) {
    rings[i].begin();
    rings[i].setBrightness(100);
    rings[i].show(); 
  }
  Serial.println("SYSTEM_READY"); 
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
        uint32_t targetColor = rings[activeTarget].Color(0, 0, 0);
        
        if (colorChar == 'R') targetColor = rings[activeTarget].Color(255, 0, 0);
        else if (colorChar == 'G') targetColor = rings[activeTarget].Color(0, 255, 0);
        else if (colorChar == 'B') targetColor = rings[activeTarget].Color(0, 0, 255);
        
        setRingColor(activeTarget, targetColor);
        startTime = millis();
        isWaitingForHit = true;
      } else {
        Serial.println("ERROR: Invalid Target Index");
      }
    }
  }

  // 2. Monitor Active Target
  if (isWaitingForHit) {
    int piezoStrength = analogRead(PIEZO_PINS[activeTarget]);

    if (piezoStrength > PIEZO_THRESHOLD) {
      unsigned long reactionTime = millis() - startTime;
      
      setRingColor(activeTarget, rings[activeTarget].Color(0, 0, 0)); 
      isWaitingForHit = false;

      
      Serial.print(reactionTime);
      Serial.print(",");
      Serial.println(piezoStrength);
    }
    else if (millis() - startTime >= testDuration) {
      setRingColor(activeTarget, rings[activeTarget].Color(0, 0, 0)); 
      isWaitingForHit = false;
      Serial.println("0,0"); 
    }
  }
}