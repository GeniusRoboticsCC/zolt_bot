#include <AccelStepper.h>
#include <SoftwareSerial.h>
#include <Servo.h>
#include <Adafruit_NeoPixel.h>

#define ARM_L_1 2
#define ARM_L_2 3
#define ARM_L_3 4
#define ARM_L_4 5

#define ARM_R_1 6
#define ARM_R_2 7
#define ARM_R_3 8
#define ARM_R_4 9

#define TORSO_1 22
#define TORSO_2 23
#define TORSO_3 24
#define TORSO_4 25

#define HEAD_SERVO_PIN 12

#define VOICE_RX 10  // arduino receives 
#define VOICE_TX 11  // arduino transmits 

// LED eye definitions (add these)
#define LEFT_EYE_PIN 13
#define RIGHT_EYE_PIN 14
#define NUM_LEDS_PER_EYE 8

// State definitions
enum RobotState {
  IDLE,
  LISTENING,
  DANCING
};

SoftwareSerial voiceSerial(VOICE_RX, VOICE_TX);

// Steppers: arms & torso
AccelStepper armL(AccelStepper::FULL4WIRE, ARM_L_1, ARM_L_3, ARM_L_2, ARM_L_4);  
AccelStepper armR(AccelStepper::FULL4WIRE, ARM_R_1, ARM_R_3, ARM_R_2, ARM_R_4);  
AccelStepper torso(AccelStepper::FULL4WIRE, TORSO_1, TORSO_3, TORSO_2, TORSO_4);

// Servo head tilt
Servo headServo;

// LED eyes
Adafruit_NeoPixel leftEye = Adafruit_NeoPixel(NUM_LEDS_PER_EYE, LEFT_EYE_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel rightEye = Adafruit_NeoPixel(NUM_LEDS_PER_EYE, RIGHT_EYE_PIN, NEO_GRB + NEO_KHZ800);

// State variables
RobotState currentState = IDLE;
unsigned long lastEyeUpdate = 0;

// Function declarations
void respondToWake();
void danceRoutine();
void updateEyes();
void setEyeExpression(String expression);
void fillBothEyes(int r, int g, int b);
void blinkEyes();
void happyEyes();
void angryEyes();
void neutralEyes();

void setup() {
  Serial.begin(9600);
  voiceSerial.begin(9600);

  headServo.attach(HEAD_SERVO_PIN);
  headServo.write(90); // start position

  armL.setMaxSpeed(1000);
  armL.setAcceleration(200);
  
  armR.setMaxSpeed(1000);
  armR.setAcceleration(200);
  
  torso.setMaxSpeed(800);
  torso.setAcceleration(150);

  // Initialize LED eyes
  leftEye.begin();
  rightEye.begin();
  leftEye.show();
  rightEye.show();
  
  // Set initial eye expression
  setEyeExpression("neutral");

  Serial.println("Zolt bot initialized");
}

void loop() {
  if (voiceSerial.available()) {
    int command = voiceSerial.read();

    switch (command) {
      case 0x01: // "Hi Zolt"
        respondToWake();
        break;
      case 0x02: // "dance command"
        danceRoutine();
        break;
      // we can add more action cases
    }
  }

  armL.run();
  armR.run();
  torso.run();
  
  updateEyes();
}

void respondToWake() {
  Serial.println("Zolt: I'm listening");
  currentState = LISTENING;
  setEyeExpression("happy");
  
  headServo.write(60); // look up
  delay(1000);
  headServo.write(90); // normal position
  
  currentState = IDLE;
  setEyeExpression("neutral");
}

void danceRoutine() {
  currentState = DANCING;
  setEyeExpression("happy");
  
  for (int i = 0; i < 3; i++) {
    armL.moveTo(100); 
    armR.moveTo(-100); 
    torso.moveTo(50);
    headServo.write(80);
    
    // Wait for movements to complete
    while (armL.isRunning() || armR.isRunning() || torso.isRunning()) {
      armL.run();
      armR.run();
      torso.run();
    }
    delay(500);

    armL.moveTo(-100); 
    armR.moveTo(100); 
    torso.moveTo(-50);
    headServo.write(100);
    
    // Wait for movements to complete
    while (armL.isRunning() || armR.isRunning() || torso.isRunning()) {
      armL.run();
      armR.run();
      torso.run();
    }
    delay(500);
  }

  // Return to neutral position
  armL.moveTo(0); 
  armR.moveTo(0); 
  torso.moveTo(0);
  headServo.write(90); // reset
  
  // Wait for final movements to complete
  while (armL.isRunning() || armR.isRunning() || torso.isRunning()) {
    armL.run();
    armR.run();
    torso.run();
  }

  currentState = IDLE;
  setEyeExpression("neutral");
}

void updateEyes() {
  // Non-blocking animations
  unsigned long currentTime = millis();

  if (currentTime - lastEyeUpdate > 3000) { // blink every 3 seconds 
    blinkEyes();
    lastEyeUpdate = currentTime;
  }
}

void setEyeExpression(String expression) {
  if (expression == "happy") {
    happyEyes();
  } else if (expression == "neutral") {
    neutralEyes();
  } else if (expression == "angry") {
    angryEyes();
  }
}

void fillBothEyes(int r, int g, int b) {
  for (int i = 0; i < NUM_LEDS_PER_EYE; i++) {
    leftEye.setPixelColor(i, leftEye.Color(r, g, b));
    rightEye.setPixelColor(i, rightEye.Color(r, g, b));
  }
  leftEye.show();
  rightEye.show();
}

void blinkEyes() {
  // Turn eyes off
  fillBothEyes(0, 0, 0);
  delay(150);
  
  // Turn on with current expression 
  setEyeExpression("neutral");
}

void happyEyes() {
  // Create a happy expression pattern
  leftEye.clear();
  rightEye.clear();

  // Simple happy pattern 
  for (int i = 0; i < NUM_LEDS_PER_EYE; i++) {
    leftEye.setPixelColor(i, leftEye.Color(0, 255, 0)); // Green for happy
    rightEye.setPixelColor(i, rightEye.Color(0, 255, 0));
  }
  
  leftEye.show();
  rightEye.show();
}

void angryEyes() {
  // Create angry expression pattern 
  leftEye.clear();
  rightEye.clear();
  
  for (int i = 0; i < NUM_LEDS_PER_EYE; i++) {
    leftEye.setPixelColor(i, leftEye.Color(255, 0, 0)); // Red for angry
    rightEye.setPixelColor(i, rightEye.Color(255, 0, 0));
  }
  
  leftEye.show();
  rightEye.show();
}

void neutralEyes() {
  // Create neutral expression pattern 
  leftEye.clear();
  rightEye.clear();
  
  for (int i = 0; i < NUM_LEDS_PER_EYE; i++) {
    leftEye.setPixelColor(i, leftEye.Color(0, 0, 255)); // Blue for neutral
    rightEye.setPixelColor(i, rightEye.Color(0, 0, 255));
  }
  
  leftEye.show();
  rightEye.show();
}