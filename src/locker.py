# ---------------------------------------------------------------------------- #
#                                    Lockers                                   #
# ---------------------------------------------------------------------------- #

import RPi.GPIO as GPIO
import serial
import time
import requests
import datetime
import sqlite3
import rdm6300
from pyairtable import Table
from RPLCD.i2c import CharLCD
from dotenv import dotenv_values

# Init GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Dotenv import
config = dotenv_values(".env")

# Header for Fabman API requests
headers = {"Authorization": "Bearer " + config.get("FABMAN_KEY")}

# Airtable table
api_key = config.get("AIRTABLE_KEY")
table = Table(api_key, 'app3OY1pHBgeuPezj', 'tbllvRdtsRWeO21H1')

# Locker GPIO mapping
lockerGPIO = {
    1: 4,
    2: 27,
    3: 22,
    4: 5,
    5: 6,
    6: 13,
    7: 19,
    8: 26,
    9: 23,
    10: 24,
    11: 25,
    12: 8,
    13: 7,
    14: 12,
    15: 17
}

# Connection status
hasWifi = False

# Init serial with card reader
reader = rdm6300.Reader('/dev/ttyS0')
ser = serial.Serial("/dev/ttyS0", 9600, timeout=0)

# Init LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, dotsize=8,
              charmap='A02',
              auto_linebreaks=True,
              backlight_enabled=True)

# Function that prints given text to the LCD display
def printToLCD(text, line):
    if len(text) < 16:
        text = text + " " * (16 - len(text))
    lcd.cursor_pos = (line - 1, 0)
    lcd.write_string(text)

# Function to fetch member email based on their cardID
def getMemberEmail(cardID):
    printToLCD('Fetching userID ', 1)
    response = requests.get(
        "https://fabman.io/api/v1/members?keyType=em4102&keyToken=" + cardID, headers=headers, timeout=5)
    if response.status_code == 200:
        if response.json() != []:
            return response.json()[0]["emailAddress"]
    return None

# Check if member owns a locker
def getMemberLocker(memberEmail):
    for record in table.all():
        if record["fields"]["Email"] == memberEmail:
            return record["fields"]["Locker"]
    return False

# Opens locker by sending signal to relay
def openLocker(lockerID, GPIO_pin):
    print('Opening locker ' + str(lockerID) + ' for 10 seconds')
    GPIO.output(GPIO_pin, GPIO.LOW)
    for i in range(10):
        printToLCD("Opened locker " + str(lockerID), 1)
        time.sleep(1)
    GPIO.output(GPIO_pin, GPIO.HIGH)
    printToLCD('Waiting For Card', 1)
    return

# Check if wifi is available
def checkForConnection():
    global hasWifi
    try:
        requests.get("https://google.com", timeout=5)
        printToLCD("Online mode", 2)
        hasWifi = True
    except:
        printToLCD("Offline mode", 2)
        hasWifi = False


if __name__ == "__main__":
    # Set up GPIO
    #  Locker 1
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.HIGH)
    #  Locker 2
    GPIO.setup(27, GPIO.OUT)
    GPIO.output(27, GPIO.HIGH)
    #  Locker 3
    GPIO.setup(22, GPIO.OUT)
    GPIO.output(22, GPIO.HIGH)
    #  Locker 4
    GPIO.setup(5, GPIO.OUT)
    GPIO.output(5, GPIO.HIGH)
    #  Locker 5
    GPIO.setup(6, GPIO.OUT)
    GPIO.output(6, GPIO.HIGH)
    #  Locker 6
    GPIO.setup(13, GPIO.OUT)
    GPIO.output(13, GPIO.HIGH)
    #  Locker 7
    GPIO.setup(19, GPIO.OUT)
    GPIO.output(19, GPIO.HIGH)
    #  Locker 8
    GPIO.setup(26, GPIO.OUT)
    GPIO.output(26, GPIO.HIGH)
    #  Locker 9
    GPIO.setup(23, GPIO.OUT)
    GPIO.output(23, GPIO.HIGH)
    #  Locker 10
    GPIO.setup(24, GPIO.OUT)
    GPIO.output(24, GPIO.HIGH)
    #  Locker 11
    GPIO.setup(25, GPIO.OUT)
    GPIO.output(25, GPIO.HIGH)
    #  Locker 12
    GPIO.setup(8, GPIO.OUT)
    GPIO.output(8, GPIO.HIGH)

    # Initiate sqlite database
    conn = sqlite3.connect('database.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lockers(id INTEGER PRIMARY KEY, memberEmail TEXT, cardID TEXT, lockerID INTEGER, lastSeen INTEGER, lastFetched INTEGER)''')
    conn.commit()

    # Print initial text to LCD
    printToLCD('Waiting For Card', 1)
    printToLCD("Offline mode", 2)

    # Check if connected to the internet
    checkForConnection()

    print("Lockers are ready. Waiting for card...")
    # Loop
    while True:
        try:
            # Check for connection
            if hasWifi == False:
                checkForConnection()

            # Card check
            card = reader.read(timeout=0.25)
            print(card)

            if card:
                cardID = "01" + format(card.value, 'x')
                print("Found card with ID: " + cardID)
                
                # Save last seen time
                currentMilis = int(round(time.time() * 1000))
                c.execute("UPDATE lockers SET lastSeen=? WHERE cardID=?",
                          (currentMilis, cardID))
                conn.commit()

                # Check if card exists in database
                c.execute("SELECT * FROM lockers WHERE cardID = ?", (cardID,))
                member = c.fetchone()
                if member is not None:
                    print("Member owns a locker")
                    openLocker(8, 8)
                    continue

                # If locker is not connected to the internet, deny access
                if hasWifi is False:
                    printToLCD('Locker offline', 1)
                    checkForConnection()
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)
                    continue

                # Fetch member from the API
                memberEmail = getMemberEmail(cardID)
                # Exception if member email is not found
                if memberEmail is None:
                    print('Error while fetching member email')
                    printToLCD('Email error', 1)
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)
                    continue

                # Fetch if member owns a locker
                lockerNo = getMemberLocker(memberEmail)
                if lockerNo:
                    print("Member " + str(memberEmail) +
                          " owns a locker " + str(lockerNo))
                    c.execute("INSERT INTO lockers (memberEmail, cardID, lockerID, lastSeen, lastFetched) VALUES (?, ?, ?, ?, ?)", (
                        memberEmail, cardID, lockerNo, currentMilis, currentMilis))
                    conn.commit()
                    openLocker(8, 8)
                    continue
                # Member doesn't own a locker
                else:
                    print('Member with email ' +
                          str(memberEmail) + ' has no access.')
                    printToLCD('No locker', 1)
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)
        except Exception as e:
            print(e)
            checkForConnection()

        # Required to prevent multiple reads
        time.sleep(0.2)
