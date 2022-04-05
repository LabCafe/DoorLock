import sqlite3, requests, time
from dotenv import dotenv_values

config = dotenv_values(".env")

# Header for API requests
headers = {"Authorization": "Bearer " + config.get("API_KEY")}


def getMemberID(cardID):
    response = requests.get("https://fabman.io/api/v1/members?keyType=em4102&keyToken=" + cardID, headers=headers, timeout=5)
    if response.status_code == 200:
        if response.json() != []:
            return response.json()[0]["id"]
    return None


def checkUserAccess(memberID):
    response = requests.get("https://fabman.io/api/v1/members/" + str(memberID) + "/trainings", headers=headers, timeout=5)
    for training in response.json():
        if training["trainingCourse"] == 1031 :
            return True
    return False


if __name__ == '__main__':
    # Connect to database
    conn = sqlite3.connect("./database.sqlite")
    c = conn.cursor()
    
    # Loop over all members
    members = c.execute("SELECT * FROM members").fetchall()
    for member in members:
        currentMilis = int(round(time.time() * 1000))
        c.execute("UPDATE members SET allowed = ?, lastFetched = ? WHERE id = ?", (checkUserAccess(member[1]), currentMilis, member[0]))
        conn.commit()
    conn.close()
