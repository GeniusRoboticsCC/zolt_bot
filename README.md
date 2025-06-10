
Left Arm Stepper:
- IN1 → Arduino Pin 2
- IN2 → Arduino Pin 3  
- IN3 → Arduino Pin 4
- IN4 → Arduino Pin 5

Right Arm Stepper:
- IN1 → Arduino Pin 6
- IN2 → Arduino Pin 7
- IN3 → Arduino Pin 8  
- IN4 → Arduino Pin 9

Torso Stepper:
- IN1 → Arduino Pin 22
- IN2 → Arduino Pin 23
- IN3 → Arduino Pin 24
- IN4 → Arduino Pin 25


servo motor

Head Servo:
- Signal → Arduino Pin 12
- VCC → 5V
- GND → GND

voice module 
Voice Recognition Module:
- RX → Arduino Pin 11 (TX)
- TX → Arduino Pin 10 (RX)  
- VCC → 5V
- GND → GND

LED eyes
Left Eye NeoPixels:
- Data In → Arduino Pin 13
- VCC → 5V
- GND → GND

Right Eye NeoPixels:  
- Data In → Arduino Pin 14
- VCC → 5V
- GND → GND

12V Supply:
├── Stepper Motor Drivers (12V input)
└── 5V Buck Converter
    ├── Arduino Mega (5V)
    ├── Servo Motor (5V)  
    ├── Voice Module (5V)
    └── NeoPixel LEDs (5V)
