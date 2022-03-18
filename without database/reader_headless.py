# ---------------------------------------------------------------------------- #
#                                 Headless Code                                #
# ---------------------------------------------------------------------------- #
#       To be used only with Raspberry Pi without a display and a button.      #
# ---------------------------------------------------------------------------- #

import RPi.GPIO as GPIO
import rdm6300, time, requests, datetime, time, serial

# Header for API requests
headers = {"Authorization": "Bearer 4ffdc9f9-2609-4c8f-80e5-3b2c65f72e2a"}

# Settings
settings = {"trainingID": "1031", "resourceID": "2247", "doorTime": "5"}

# Init GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)

# Init serial with card reader
reader = rdm6300.Reader('/dev/ttyS0')
ser = serial.Serial("/dev/ttyS0", 9600, timeout = 0)

# User cache, timer and connectionStatus
userCache = {}
hasWifi = False

# Function to fetch memberID based on their card ID
def getUserID(cardID):
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
    GPIO.output(6, GPIO.HIGH)
    time.sleep(int(settings['doorTime']))
    GPIO.output(6, GPIO.LOW)
    return

# Sends activity log to API
def sendActivityLog(userID):
    currentTime = datetime.datetime.now().replace(microsecond=0).isoformat()
    json = {"resource": settings['resourceID'], "member": str(userID), "createdAt": str(
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
    # Check for internet connection
    checkForConnection()
    print("Door lock is ready. Waiting for card...")

    # Loop of life
    while True:
        # Card check
        card = reader.read()
        if card:
            cardID = "01" + format(card.value, 'x')
            print("Found card with ID: " + cardID)

            if cardID in userCache:
                print("Card " + cardID + " found in cache, opening doors for " + settings["doorTime"] + " seconds")
                if hasWifi:
                    sendActivityLog(userCache.get(cardID))
                openDoorLock()
                print("Closing doors")
            else:
                if hasWifi != True:
                    print("No internet connection, waiting for connection")
                    checkForConnection()
                else:
                    userID = getUserID(cardID)
                    if userID is None:
                        print('Found invalid card')

                    elif checkMemberAccess(userID):
                        print("Opening doors for user " + str(userID) + " for " + settings["doorTime"] + " seconds")
                        userCache[str(cardID)] = userID
                        sendActivityLog(userID)
                        openDoorLock()
                        print("Closing doors")
                    else:
                        print('User with ID ' + str(userID) + ' has no access.')
                        time.sleep(1)

        # Required to prevent multiple reads
        ser.flushInput()
        time.sleep(1)