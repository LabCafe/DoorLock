// Adafruit_NeoPixel pixels(1, 18, NEO_GRB + NEO_KHZ800);
// Rdm6300 rdm6300;
// LiquidCrystal_I2C lcd(0x27, 2, 16);
// HTTPClient http;
// DynamicJsonDocument doc(2048);

// const char *ssid = "Lab.member";
// const char *password = "createavity";

// boolean connectedToInternet = false;

// void printToLCD(String text) {
//   if (text.length() < 16) {
//     for (int i = text.length(); i < 16; i++) {
//       text += " ";
//     }
//   }
//   lcd.setCursor(0, 0);
//   lcd.print(text);
// }

// void connectToWifi() {
//   WiFi.mode(WIFI_STA);
//   WiFi.begin(ssid, password);
//   Serial.println("Connecting...");
//   printToLCD("Connecting...");
//   while (WiFi.status() != WL_CONNECTED) {
//     Serial.print('.');
//     delay(1000);
//   }
//   if (WiFi.status() == WL_CONNECTED) {
//     Serial.println("WiFi connected");
//     printToLCD("WiFi connected");
//     lcd.setCursor(0, 1);
//     lcd.print("Online mode");
//   }
// }

// int getMemberFromCard(String cardID) {
//   http.begin("https://fabman.io/api/v1/members?keyType=em4102&keyToken=" + cardID);
//   http.addHeader("Authorization", "Bearer 4ffdc9f9-2609-4c8f-80e5-3b2c65f72e2a");
//   http.setTimeout(5000);
//   int httpCode = http.GET();
//   deserializeJson(doc, http.getString());
//   http.end();

//   return doc[0]["id"];
// }

// boolean checkMemberTraining(int memberID) {
//   http.begin("https://fabman.io/api/v1/members/" + String(memberID) + "/trainings");
//   http.addHeader("Authorization", "Bearer 4ffdc9f9-2609-4c8f-80e5-3b2c65f72e2a");
//   http.setTimeout(5000);
//   int httpCode = http.GET();
//   deserializeJson(doc, http.getString());

//   // Loop over all trainings
//   for (int i = 0; i < doc.size(); i++) {
//     if (doc[i]["trainingCourse"] == 1031) {
//       return true;
//     }
//   }

//   return false;
// }

// void setLedColor(int r, int g, int b, int w = 10) {
//   pixels.setPixelColor(0, r, g, b);
//   pixels.setBrightness(w);
//   pixels.show();
// }

// void serialFlush() {
//   while (rdm6300.update()) {
//     char t = rdm6300.get_tag_id();
//   }
// }

// boolean checkInternetConnection() {
//   Serial.println("Checking internet connection...");
//   http.begin("https://www.google.com");
//   int httpCode = http.GET();
//   http.end();
//   if (httpCode == 200) {
//     Serial.println("Internet connection OK");
//     return true;
//   } else {
//     Serial.println("Internet connection failed");
//     return false;
//   }
// }

// void setup() {
//   Serial.begin(9600);
//   rdm6300.begin(44);
//   pixels.begin();
//   lcd.init();
//   lcd.backlight();

//   setLedColor(255, 69, 0);

//   sleep(1);
//   connectToWifi();
//   connectedToInternet = checkInternetConnection();

//   Serial.println("Setup done. Ready to read.");
//   printToLCD("Waiting for card");
// }

// int loopIndex = 0;

// void loop() {
//   setLedColor(0, 0, 255);
//   if (rdm6300.update()) {
//     /* ------------------------------- Card check ------------------------------- */
//     setLedColor(255, 255, 0);
//     String cardID = "01" + String(rdm6300.get_tag_id(), HEX);
//     Serial.println("Found card " + cardID);

//     if (cardID) {
//       /* ------------------------------ Member Check ------------------------------ */
//       printToLCD("Fetching member");
//       Serial.println("Fetching memberID for " + cardID);
//       int memberID = getMemberFromCard(cardID);

//       if (memberID) {
//         /* ------------------------------ Access Check ------------------------------ */
//         printToLCD("Fetching access");
//         Serial.println("Fetching training for member " + String(memberID));
//         boolean training = checkMemberTraining(memberID);

//         if (training) {
//           /* --------------------------------- Opening -------------------------------- */
//           printToLCD("Opening door");
//           Serial.println(training);
//           setLedColor(0, 255, 0);
//           sleep(3);
//           printToLCD("Waiting for card");
//         }
//       }
//     }
//   }

//   serialFlush();
// }
#include <FS.h>
#include <SPI.h>
#include <Wire.h>
#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>

#include "SD.h"

const char *data = "Callback function called";
static int callback(void *data, int argc, char **argv, char **azColName) {
  int i;
  // Serial.printf("%s: ", (const char *)data);
  for (i = 0; i < argc; i++) {
    // Serial.printf("%s = %s\n", azColName[i], argv[i] ? argv[i] : "NULL");
  }
  // Serial.printf("\n");
  return 0;
}

int openDb(const char *filename, sqlite3 **db) {
  int rc = sqlite3_open(filename, db);
  if (rc) {
    Serial.printf("Can't open database: %s\n", sqlite3_errmsg(*db));
    return rc;
  } else {
    Serial.printf("Opened database successfully\n");
  }
  return rc;
}

char *zErrMsg = 0;
int db_exec(sqlite3 *db, const char *sql) {
  Serial.println(sql);
  // Execute SQL statement and return the data
  int rc = sqlite3_exec(db, sql, callback, (void *)data, &zErrMsg);
  
}

void setup() {
  Serial.begin(9600);
  sqlite3 *db1;

  SPI.begin();
  SD.begin();

  sqlite3_initialize();

  if (openDb("/sd/db.sqlite", &db1))
    return;

  Serial.println(db_exec(db1, "Select * from members"));
  sqlite3_close(db1);
}

void loop() {
}