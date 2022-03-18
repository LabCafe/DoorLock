# ---------------------------------------------------------------------------- #
#                                 Code With LCD                                #
# ---------------------------------------------------------------------------- #
#         To be used only with Raspberry Pi with a display and a button.       #
# ---------------------------------------------------------------------------- #

import RPi.GPIO as GPIO
import serial, time, requests, datetime, json, re, os, sqlite3, rdm6300
from RPLCD.i2c import CharLCD
from dotenv import dotenv_values

config = dotenv_values(".env")

# Init GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

# Init serial with card reader
reader = rdm6300.Reader('/dev/ttyS0')
ser = serial.Serial("/dev/ttyS0", 9600, timeout = 0)


# Header for API requests
headers = {"Authorization": "Bearer " + config.get("API_KEY")}

# Settings
settings = {"trainingID": "1031", "resourceID": "2247", "doorTime": "5"}
# Connection status
hasWifi = False

# Init LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, dotsize=8,
              charmap='A02',
              auto_linebreaks=True,
              backlight_enabled=True)

# Function that prints given text to the LCD display
def printToLCD(text, line):
    lcd.cursor_pos = (line -1, 0)
    lcd.write_string(text)

# Function to fetch memberID based on their cardID
def getMemberID(cardID):
    printToLCD('Fetching memberID', 1)
    response = requests.get("https://fabman.io/api/v1/members?keyType=em4102&keyToken=" + cardID + "&limit=50", headers=headers)
    if response.status_code == 200:
        if response.json() != []:
            return response.json()[0]["id"]
    return None

# Check if member has access
def checkMemberAccess(memberID):
    response = requests.get("https://fabman.io/api/v1/members/" + str(memberID) + "/trainings", headers=headers)
    for training in response.json():
        if training["trainingCourse"] == int(settings['trainingID']) :
            return True
    return False

# Opens door lock by sending signal to relay
def openDoorLock():
    printToLCD('Opening door.   ', 1)
    print('Opening door '+ settings['doorTime'] +'s timer before resume')
    GPIO.output(26, GPIO.HIGH)
    time.sleep(int(settings['doorTime']))
    GPIO.output(26, GPIO.LOW)
    printToLCD('Waiting For Card', 1)
    return

# Sends activity log to API
def sendActivityLog(memberID):
    currentTime = datetime.datetime.now().replace(microsecond=0).isoformat() 
    currentTime = currentTime + "+01:00"
    json = {"resource":settings['resourceID'],"member": str(memberID),"createdAt": str(currentTime),"stoppedAt": str(currentTime),"idleDurationSeconds":0,"notes":"Hlavné Dvere","metadata":{}}
    requests.post("https://fabman.io/api/v1/resource-logs", headers=headers, json=json)

# Check if wifi is available
def checkForConnection():
    global hasWifi
    try:
        requests.get("https://google.com", timeout=5)
        hasWifi = True
    except:
        hasWifi = False


if __name__ == "__main__":
    # Initiate sqlite database
    conn = sqlite3.connect('database.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, memberID TEXT, cardID TEXT, allowed INTEGER, last_seen INTEGER, last_fetched INTEGER)''')
    conn.commit()

    # Print initial text to LCD
    printToLCD('Waiting For Card', 1)
    printToLCD("Offline mode    ", 2)

    # Check if connected to the internet
    checkForConnection()

    # Loop
    while True:
        # Button check
        if GPIO.input(6) == GPIO.HIGH:
            openDoorLock()

        # Card check
        card = reader.read()

        if card:
            cardID = "01" + format(card.value, 'x')
            print("Found card with ID: " + cardID)
            currentMilis = int(round(time.time() * 1000))
            c.execute("UPDATE members SET lastSeen=? WHERE cardID=?", (currentMilis, cardID))
            conn.commit()
            
            # Check if card exists in database
            c.execute("SELECT * FROM members WHERE cardID = ?", (cardID,))
            member = c.fetchone();
            if member is not None:
                if member[3] == 1:
                    print("Member is allowed to open doors")
                    if hasWifi:
                        sendActivityLog(member[1])
                    openDoorLock()
                else:
                    print("Member is not allowed to open doors")
                    printToLCD('No permission   ', 1)
                    time.sleep(2)

            # Check if lock is not connected to the internet
            elif hasWifi is False:
                    printToLCD('Lock Is Offline ', 1)
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)
            # Fetch member from the API
            else:
                memberID = getMemberID(cardID)
                if memberID is None:
                    print('Found invalid card')
                    printToLCD('Invalid card    ', 1)
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)
                    
                elif checkMemberAccess(memberID):
                    print("Member " + str(memberID) + " is allowed to open doors.")
                    c.execute("INSERT INTO members (memberID, cardID, allowed, last_seen, last_fetched) VALUES (?, ?, ?, ?, ?)",(memberID, cardID, 1, currentMilis, currentMilis))
                    conn.commit()
                    sendActivityLog(memberID)
                    openDoorLock()
                else:
                    print('Member with ID ' + str(memberID) + ' has no access.')
                    printToLCD('No permission   ', 1)
                    time.sleep(1)
                    printToLCD('Waiting For Card', 1)

        ser.flushInput()
        time.sleep(0.2)

    