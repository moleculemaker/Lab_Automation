int incomingByte;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(12, OUTPUT);
  pinMode(8, OUTPUT);
  pinMode(4, OUTPUT);
  delay(500);
  digitalWrite(12, LOW);
  digitalWrite(8, LOW);
  digitalWrite(4, LOW);

}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available() > 0){
    incomingByte = Serial.read();
    if (incomingByte == 'A'){
      digitalWrite(12, HIGH);
      delay(250);
    }
    if (incomingByte == 'B'){
      digitalWrite(8, HIGH);
      delay(250);
    }
    if (incomingByte == 'C'){
      digitalWrite(4, HIGH);
      delay(250);
    }
    if (incomingByte == 'D'){
      digitalWrite(12, LOW);
      delay(250);
    }
    if (incomingByte == 'E'){
      digitalWrite(8, LOW);
      delay(250);
    }
    if (incomingByte == 'F'){
      digitalWrite(4, LOW);
      delay(250);
    }
  }
}
