#include <avr/wdt.h>

const int sensorPins[] = {A0, A1, A2, A3, A4, A5};
const int ledPins[] = {7, 8, 9, 10, 11, 12};
const int numSensors = 6;
const int threshold = 700;

enum GameMode { IDLE, FREE_PLAY, RUN_SEQUENCE, RAND_GAME, ELECTRO };
GameMode currentMode = IDLE;

bool activeTargets[numSensors] = {false, false, false, false, false, false};
unsigned long targetStartTimes[numSensors] = {0, 0, 0, 0, 0, 0};
int targetDurations[numSensors] = {0, 0, 0, 0, 0, 0};
bool targetWasHit[numSensors] = {false, false, false, false, false, false};

const int ledSequence[] = {0, 1, 2, 3, 4, 5, 4, 3, 2, 1}; 
const int numSteps = sizeof(ledSequence) / sizeof(ledSequence[0]);
int currentStep = 0;
unsigned long lastStepTime = 0;
const int waitTime = 300; 

unsigned long lastElectroPulse = 0;
int electroBPM = 127;               
long electroInterval = 60000 / 127; 

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < numSensors; i++) {
    pinMode(ledPins[i], OUTPUT);
    pinMode(sensorPins[i], INPUT);
    digitalWrite(ledPins[i], LOW);
  }
  randomSeed(analogRead(A7));
  Serial.println("System Ready - Enter BPM or Mode Command.");
}

void loop() {
  listenSerial();     
  updatePunchLogic(); 

  switch (currentMode) {
    case FREE_PLAY:      handleFreePlay();      break;
    case RUN_SEQUENCE:   handleRunSequence();   break;
    case RAND_GAME:      handleRandGame();      break;
    case ELECTRO:        handleElectrodynamix(); break;
    case IDLE:           break;
  }
}


void handleFreePlay() {
  for (int i = 0; i < numSensors; i++) {
    if (!activeTargets[i] && analogRead(sensorPins[i]) > threshold) {
      startPunch(i + 1, 200); 
    }
  }
}

void handleRunSequence() {
  unsigned long now = millis();
  if (now - lastStepTime >= waitTime) {
    startPunch(ledSequence[currentStep] + 1, waitTime - 50); 
    currentStep = (currentStep + 1) % numSteps;
    lastStepTime = now;
  }
}

void handleRandGame() {
  bool anyActive = false;
  for(int i=0; i < numSensors; i++) {
    if(activeTargets[i]) anyActive = true;
  }

  if (!anyActive) {
    startPunch(random(1, 4), random(600, 1000)); 
    startPunch(random(4, 7), random(800, 1200));
  }
}

void handleElectrodynamix() {
  bar(); 
}



int randPin(){
  int pick; 
  do {
    pick = random(2, 7); 
  } while (pick == 4); // No four
  return pick;
}

void startPunch(int peripheral, int duration) {
  if (peripheral < 1 || peripheral > 6) return;
  int idx = peripheral - 1;
  if (activeTargets[idx]) return;

  activeTargets[idx] = true;
  targetWasHit[idx] = false;
  targetStartTimes[idx] = millis();
  targetDurations[idx] = duration;

  digitalWrite(ledPins[idx], HIGH);
}

void blockingPunch(int peripheral, int duration) {
  if (peripheral < 1 || peripheral > 6) return;
  int idx = peripheral - 1;

  unsigned long startTime = millis();
  bool hitDetected = false;
  digitalWrite(ledPins[idx], HIGH);

  while (millis() - startTime < (unsigned long)duration) {
    if (!hitDetected && analogRead(sensorPins[idx]) > threshold) {
      hitDetected = true;
      digitalWrite(ledPins[idx], LOW); 
      int score = duration - (int)(millis() - startTime);
      Serial.println(score);
    }
    listenSerial(); 
    if (currentMode == IDLE) break; 
  }

  if (!hitDetected) {
    digitalWrite(ledPins[idx], LOW);
    int score = -30;
    Serial.println(score);
  }
}

void updatePunchLogic() {
  unsigned long now = millis();
  for (int i = 0; i < numSensors; i++) {
    if (!activeTargets[i]) continue;

    if (!targetWasHit[i] && analogRead(sensorPins[i]) > threshold) {
      targetWasHit[i] = true;
      digitalWrite(ledPins[i], LOW);
      int score = targetDurations[i] - (int)(now - targetStartTimes[i]);
      Serial.println(score);
    } 
    
    if (now - targetStartTimes[i] >= (unsigned long)targetDurations[i]) {
      if (!targetWasHit[i]) {
        digitalWrite(ledPins[i], LOW);
      }
      activeTargets[i] = false; 
    }
  }
}


void listenSerial() {
  static String inputBuffer = ""; 
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      inputBuffer.trim(); 
      if (inputBuffer.length() > 0) {
        
        int numInput = inputBuffer.toInt();
        
        if (numInput >= 40 && numInput <= 1000000000000) { // very good range
          electroBPM = numInput;
          electroInterval = 60000L / electroBPM;
          currentMode = ELECTRO;
          lastElectroPulse = millis();
          resetGameState();
          Serial.print("BPM set to: "); Serial.println(electroBPM);
        }
        else if (inputBuffer.indexOf("free") >= 0) {
          resetGameState();
          currentMode = FREE_PLAY;
        } 
        else if (inputBuffer.indexOf("electro") >= 0) {
          resetGameState();
          currentMode = ELECTRO;
          lastElectroPulse = millis();
        }
        else if (inputBuffer.indexOf("rand") >= 0) {
          resetGameState();
          currentMode = RAND_GAME;
        }
        else if (inputBuffer.indexOf("run") >= 0) {
          resetGameState();
          currentMode = RUN_SEQUENCE;
        }
        else if (inputBuffer.indexOf("off") >= 0) {
          resetGameState();
          wdt_enable(WDTO_15MS);
          while(1);
        }
        inputBuffer = ""; 
      }
    } else {
      inputBuffer += c;
    }
  }
}

void resetGameState() {
  for (int i = 0; i < numSensors; i++) {
    digitalWrite(ledPins[i], LOW);
    activeTargets[i] = false;
    targetWasHit[i] = false;
  }
  Serial.println("State Reset.");
}

void bar() {
  unsigned long now = millis();
  
  // bar is 4 beats long
  if (now - lastElectroPulse >= (electroInterval * 4)) { 
    lastElectroPulse = now; 
    float beatsLeft = 4.0; 

    while (beatsLeft >= 0.5) { 
      int noteType = random(0, 2); 
      float noteValue;

      if (noteType == 0 && beatsLeft >= 1.0) {
        noteValue = 1.0;  
      } else {
        noteValue = 0.5;  
      }

      int duration = (int)(electroInterval * noteValue) - 20;

      blockingPunch(randPin(), duration);
      beatsLeft -= noteValue;
      delay(20); 
      
      if (currentMode != ELECTRO) return;
    }
  }
}