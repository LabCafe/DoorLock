# ---------------------------------------------------------------------------- #
#                                 Code With LCD                                #
# ---------------------------------------------------------------------------- #
#         To be used only with Raspberry Pi with a display and a button.       #
# ---------------------------------------------------------------------------- #

import RPi.GPIO as GPIO
import serial, time, requests, datetime, json, re, os
from dotenv import dotenv_values
from RPLCD.i2c import CharLCD

config = dotenv_values(".env")

# Init GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

# Init serial with card reader
ser = serial.Serial("/dev/ttyS0", 9600, timeout = 0)


# Header for API requests
headers = {"Authorization": "Bearer " + config.get("API_KEY")}


# User cache, timer and connectionStatus
userCache = {}
timeSinceRefresh = 0;
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

# Function to purge all data stored in buffers and serial
def flushSerial():
    ser.flush()
    ser.flushInput()
    ser.flushOutput()

# Function to read card value
def readCard():
    bytearr = []
    card = []
    i = 0
    # Repeat loop until something is returned.
    while True:
        serial_data = ser.read()
        # Nothing to read. Return to main loop.
        if len(serial_data) == 0:
            return None
        i = i + 1
        if i == 14:
            i = 0
            for byte in bytearr:
                card.append(byte.decode("UTF-8"))
            # After all bytes have been appended to array, join that array and return it.
            return ''.join(card)[1:].lower()
        else:
            # If not all bytes are collected, append them to the encoded bytearray
            bytearr.append(serial_data)

# Function to check if RFID card is available
def checkForCard(readCard):
    readCard = readCard()
    # Check if there is something to read
    if readCard is None or str(readCard) is "000000000000" or readCard is 000000000000 or not re.search("^[a-zA-Z0-9_]*$", readCard):
        return None

    # Return read card ID
    else:
        printToLCD('Reading card..  ', 1)
        print('Found Card With ID: ' + readCard)
        return readCard

# Function to fetch memberID based on their card ID
def getUserID(cardID):
    printToLCD('Fetching userID', 1)
    response = requests.get("https://fabman.io/api/v1/members?keyType=em4102&keyToken=" + cardID + "&limit=50", headers=headers)
    if not response.json():
        return None
    for responseItem in response.json():
        for key, value in responseItem.items():
            if key == 'id':
                return value
            else:
                pass

# Check if member has access
def checkMemberAccess(memberID):
    response = requests.get("https://fabman.io/api/v1/members/" + str(memberID) + "/trainings", headers=headers)
    if not response.json():
        return False
    for responseItem in response.json():
        for key, value in responseItem.items():
            if key == 'trainingCourse':
                if value == int(settings['trainingID']):
                    print("Member " + str(memberID) + " is allowed to open doors.")
                    return True
            else:
                pass
    return False

# Opens door lock by sending signal to relay
def openDoorLock():
    global timeSinceRefresh

    printToLCD('Opening door.   ', 1)
    print('Opening door '+ settings['doorTime'] +'s timer before resume')
    GPIO.output(26, GPIO.HIGH)
    timeSinceRefresh += int(settings['doorTime'])
    time.sleep(int(settings['doorTime']))
    GPIO.output(26, GPIO.LOW)
    printToLCD('Waiting For Card', 1)
    return

# Sends activity log to API
def sendActivityLog(userID):
    currentTime = datetime.datetime.now().replace(microsecond=0).isoformat() 
    currentTime = currentTime + "+01:00"
    json = {"resource":settings['resourceID'],"member": str(userID),"createdAt": str(currentTime),"stoppedAt": str(currentTime),"idleDurationSeconds":0,"notes":"Hlavné Dvere","metadata":{}}
    requests.post("https://fabman.io/api/v1/resource-logs", headers=headers, json=json)

# Renew cache
def renewCache():
    print("Starting cache renew")
    printToLCD('Please wait..   ', 1)
    cacheBuffer = {}
    for cardID, userID in userCache.items():
        if checkMemberAccess(userID):
            cacheBuffer[cardID] = userID
        else:
            pass
    print("Cache renew has finished successfully.")
    printToLCD('Waiting For Card', 1)
    return cacheBuffer


# Check if wifi is available
def checkForConnection():
    global hasWifi
    hostname = "google.com"
    response = os.system("ping -c 1 " + hostname)
    if response == 0:
        printToLCD("Online mode     ", 2)
        hasWifi = True
    else:
        printToLCD("Offline mode    ", 2)
        hasWifi = False
    return

printToLCD('Waiting For Card', 1)
printToLCD("Offline mode    ", 2)
checkForConnection()

# Loop of life
while True:
    # Read setting from JSON every loop
    json_file = open("./settings.json")
    settings = json.load(json_file)
    json_file.close()

    # Every 5 mins
    if timeSinceRefresh > 300:
        if hasWifi:
            userCache = renewCache()
        checkForConnection()
        timeSinceRefresh = 0

    # Button check
    if GPIO.input(6) == GPIO.HIGH:
        openDoorLock()

    # Card check
    cardID = checkForCard(readCard)

    if cardID:
        if cardID in userCache:
            openDoorLock()
            sendActivityLog(userCache.get(cardID))
            
        elif hasWifi is False:
                printToLCD('Lock Is Offline ', 1)
                flushSerial()
                timeSinceRefresh += 1
                time.sleep(1)
                printToLCD('Waiting For Card', 1)
        else:
            userID = getUserID(cardID)
            if userID is None:
                print('Found invalid card')
                printToLCD('Invalid card    ', 1)
                flushSerial()
                timeSinceRefresh += 1
                time.sleep(1)
                printToLCD('Waiting For Card', 1)
                
            elif checkMemberAccess(userID):
                userCache[str(cardID)] = userID;
                sendActivityLog(userID)
                openDoorLock()
            else:
                print('User with ID ' + str(userID) + ' has no access.')
                printToLCD('No permission   ', 1)
                flushSerial()
                timeSinceRefresh += 1
                time.sleep(1)
                printToLCD('Waiting For Card', 1)

    flushSerial()
    timeSinceRefresh += 0.2
    time.sleep(0.2)

