#include <Adafruit_QMC5883P.h>

Adafruit_QMC5883P qmc;

void setup() {
  Serial.begin(9600);
  while (!Serial) delay(10);

  if (!qmc.begin()) {
    while (1) delay(10);
  }

  qmc.setMode(QMC5883P_MODE_NORMAL);
  qmc.setODR(QMC5883P_ODR_200HZ);
  qmc.setOSR(QMC5883P_OSR_4);
  qmc.setDSR(QMC5883P_DSR_2);
  qmc.setRange(QMC5883P_RANGE_30G);
  qmc.setSetResetMode(QMC5883P_SETRESET_ON);
}

void loop() {
  if (qmc.isDataReady()) {
    float gx, gy, gz;

    if (qmc.getGaussField(&gx, &gy, &gz)) {
      Serial.print(gx, 3);
      Serial.print(",");
      Serial.print(gy, 3);
      Serial.print(",");
      Serial.println(gz, 3);
    }
  }
  delay(3);
}