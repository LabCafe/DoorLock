# ---------------------------------------------------------------------------- #
#                               RGB Headless Code                              #
# ---------------------------------------------------------------------------- #
#  To be used only with Raspberry Pi without a display, button and LED strip   #
# ---------------------------------------------------------------------------- #

import RPi.GPIO as GPIO
import rdm6300, time, requests, datetime, time, serial, sqlite3, neopixel, board
from dotenv import dotenv_values

config = dotenv_values(".env")

# Header for API requests
headers = {"Authorization": "Bearer " + config.get("API_KEY")}

# Settings
settings = {"trainingID": "1031", "resourceID": "2247", "doorTime": "5"}

# Init GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)

# Init serial with card reader
reader = rdm6300.Reader('/dev/ttyS0')
ser = serial.Serial("/dev/ttyS0", 9600, timeout = 0)

# Connection status
hasWifi = False

# LED strip configuration
pixels = neopixel.NeoPixel(board.D18, 4)

# Function to fetch memberID based on their card ID
def getMemberID(cardID):
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
    pixels.fill((0, 255, 0))
    GPIO.output(6, GPIO.HIGH)
    time.sleep(int(settings['doorTime']))
    GPIO.output(6, GPIO.LOW)
    return

# Sends activity log to API
def sendActivityLog(memberID):
    currentTime = datetime.datetime.now().replace(microsecond=0).isoformat()
    json = {"resource": settings['resourceID'], "member": str(memberID), "createdAt": str(
        currentTime), "stoppedAt": str(currentTime), "idleDurationSeconds": 0, "notes": "Hlavné Dvere", "metadata": {}}
    requests.post("https://fabman.io/api/v1/resource-logs",
                  headers=headers, json=json)

# Check if wifi is available
def checkForConnection():
    global hasWifi
    try:
        requests.get("https://google.com")
        hasWifi = True
    except:
        hasWifi = False
    return

if __name__ == "__main__":
    # Initiate sqlite database
    conn = sqlite3.connect('database.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, memberID TEXT, cardID TEXT, allowed INTEGER, lastSeen INTEGER, lastFetched INTEGER)''')
    conn.commit()

    # Check for internet connection
    checkForConnection()
    print("Door lock is ready. Waiting for card...")

    # Set up LED strip
    pixels.fill((0, 0, 255))

    # Loop of life
    while True:
        # Reset Pixels
        pixels.fill((0, 0, 255))
        # Card check
        card = reader.read(timeout=0.25)
        if card:
            cardID = "01" + format(card.value, 'x')

            currentMilis = int(round(time.time() * 1000))
            c.execute("UPDATE members SET lastSeen=? WHERE cardID=?", (currentMilis, cardID))
            conn.commit()
            print("Found card with ID: " + cardID)

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
                
            else:
                if hasWifi != True:
                    print("No internet connection, waiting for connection")
                    pixels.fill((255, 255, 0))
                    checkForConnection()
                else:
                    memberID = getMemberID(cardID)
                    if memberID is None:
                        print('Found invalid card')

                    elif checkMemberAccess(memberID):
                        print("Opening doors for member " + str(memberID) + " for " + settings["doorTime"] + " seconds")
                        c.execute("INSERT INTO members (memberID, cardID, allowed, lastSeen, lastFetched) VALUES (?, ?, ?, ?, ?)",(memberID, cardID, 1, currentMilis, currentMilis))
                        conn.commit()
                        sendActivityLog(memberID)
                        openDoorLock()
                        print("Closing doors")
                    else:
                        print('Member with ID ' + str(memberID) + ' has no access.')
                        pixels.fill((255, 0, 0))
                        time.sleep(1)

        # Required to prevent multiple reads
        ser.flushInput()
        time.sleep(1)