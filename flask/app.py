from flask import Flask, render_template, redirect, request, flash, abort
from flask import session as userSession
import requests, json, os
import dateutil.parser as dp
import requests.sessions
from dotenv import dotenv_values

config = dotenv_values(".env") 

# Header for API requests
headers = {"Authorization": "Bearer " + config.get("API_KEY")} 

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(10)

@app.route('/login',methods=['GET', 'POST'])
def logIn():
    if request.method == 'POST':
        if request.form['username'] == "admin":
            if request.form['password'] == "heslo":
                userSession['user'] = 'admin'
                flash('Succesfully logged in.', 'success')    
                return redirect('/')
            flash('The password is not correct.')
            return redirect('/login')
        flash('The username is not correct.')
        return redirect('/login')
    else:
        if "user" in userSession:
            return redirect('/')
        else:
            return render_template('login.html')

@app.route('/')
def index():
    if "user" not in userSession:
        return redirect('/login', code=302)

    logs = []
    name_cache = {}
    resourceList = []
    trainingList = []

    def dateConvert(date):
        return dp.parse(date).strftime("%H:%M @ %e/%b/%y")

    def nameFromID(sess: requests.Session, userID):
        if userID is None:
            return "Unknown"
        response = sess.get(f"https://fabman.io/api/v1/members/{userID}")
        response.raise_for_status()
        data = response.json()
        return "{firstName} {lastName}".format_map(data)

    def updateResourceList(sess: requests.Session):
        response = sess.get("https://fabman.io/api/v1/resources?limit=50&orderBy=name&order=asc")
        response.raise_for_status()
        for response in response.json():
            resourceList.append([response["name"], response["id"]])

    def updateTrainingList(sess: requests.Session):
        response = sess.get("https://fabman.io/api/v1/training-courses?limit=50&archived=false")
        response.raise_for_status()
        for response in response.json():
            trainingList.append([response["title"], response["id"]])

    def retrieveValues():
        with open('settings.json') as json_file:
            data = json.load(json_file)
            return data
        
    with requests.Session() as sess:
        sess.headers.update(headers)

        updateResourceList(sess)
        updateTrainingList(sess)

        response = sess.get("https://fabman.io/api/v1/resource-logs?resource=2247&status=all&order=desc&limit=50")
        for response in response.json():
            member_id = response["member"]
            name = name_cache.get(member_id)
            if not name:
                name = name_cache[member_id] = nameFromID(sess, member_id)
            logs.append([name, dateConvert(response["createdAt"])])

    return render_template('index.html', logs=logs, resourceList=resourceList, trainingList=trainingList, savedValues=retrieveValues())

@app.route('/save', methods=['GET', 'POST'])
def save():
    with open('settings.json', 'w') as f:
        json.dump(request.form, f)
    flash('Succesfully saved config.', 'success')    
    return redirect('/', code=302)

@app.route('/logout', methods=['GET', 'POST'])
def logOut():
    return
    
if __name__ == "__main__":
    app.run(debug=True)
