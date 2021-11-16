from itertools import count
import json
import os
from json import dumps,load
from functools import wraps
from re import S, split
import re
from flask import Flask, render_template, Response, request, redirect, url_for, session, flash
from pyrebase.pyrebase import Storage
from werkzeug.utils import secure_filename
#from flask_ngrok import run_with_ngrok
from datetime import datetime
import pyrebase


#google translate for arabic version
from googletrans import Translator, constants

#from AITrianer import generate_frames, releaseWebCam
from firebase import firebase


#TODO:: i need to craete a data base for each user containes every day data for each user's
# meals
#   breakfast 
#   launch 
#   dinner 
#   snacks 
# weight
# workout
# workout duration
# and pass all this data to dashboard :UPDATE ALL DONE BUT THIS

firebase = firebase.FirebaseApplication('https://ai-coach1-default-rtdb.europe-west1.firebasedatabase.app/', None)

firebaseConfig = {
    'apiKey': "AIzaSyBrrnyw9FKRNyFVafrWLaPLxFtl8qvm3LE",

  'authDomain': "ai-coach1.firebaseapp.com",

  'databaseURL': "https://ai-coach1-default-rtdb.europe-west1.firebasedatabase.app",

  'projectId': "ai-coach1",

  'storageBucket': "ai-coach1.appspot.com",

  'messagingSenderId': "564554479727",

  'appId': "1:564554479727:web:0c2db75d234539cdb6359a",

  'measurementId': "G-T2Y9TV1G2B"
}


firebase_app = pyrebase.initialize_app(firebaseConfig)
auth = firebase_app.auth()
db = firebase_app.database()
storage = firebase_app.storage()




# data base for users and trainers
person= {"is_logged_in": False, "name": "", "email": "", "uid": "", 'is_trainer': False}


#analytics = getAnalytics(app);



#configure upload varibales
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
UPLOAD_FOLDER_VIDEOS = os.path.join(APP_ROOT, 'static/uploads/videos')
ALLOWED_EXTENSIONS = set(['mp4', 'png', 'jpg', 'jpeg'])




app = Flask(__name__)
app.config['SECRET_KEY'] = "thisismysecretkey"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#run_with_ngrok(app)

# workouts lists {workoutName:rightSidePoints, leftSidePoints, maxAngle, minAngle, videoPath, thumbNailPath0}
workouts = {'squat':[[23, 25, 27],[ 24, 26, 28],250, 190, 'images/Export/day1-1.mp4'],
  'bridge': [[11, 23, 25], [12, 24, 26], 150, 120, 'images/Export/day1-2.mp4'],
  'spider': [[ 23, 25, 27], [ 24, 26, 28], 160, 60, 'images/Export/day1-6.mp4']
 }

# webcam switch
global switch 
switch = 0

countMealGridRange = 0
countWorkoutRange =0

workoutNavbarList = []
mealNavbarList = []

PlanCatagory = None
meals = None

workoutArray = ['squat', 'bridge', 'spider'] 
indx = 0
#result = firebase.post('ai-coach1-default-rtdb/workouts',workouts)



@app.route("/test")
def test():
    db.child("test").push({"test":'id', "todayDate":"date"})
    return "hello world"

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session["is_logged_in"] and session["is_trainer"]:
            return f(*args, **kwargs)
        else:
            flash("warining","you need to be logged in")  
            return redirect(url_for('signin_trainer'))  
    return wrap

@app.route('/meal-plans')
def meal_plans():

    trainerID = db.child("users").child(session["uid"]).child("personal_trainer").child("id").get().val()

    plans =db.child('users').child(session["uid"]).child("mealPlans").get().val()
    plans = plans["plansNames"]
    

    plansDict = {}
    for plan in plans:
        planName, name = plan.split(",",1)
        plan =db.child('trainers').child(trainerID).child("mealPlans").child(planName).child(name).get().val()
        plansDict[name]  = json.loads(json.dumps(plan))
    print(plansDict)
    return render_template("meal-plans.html", plans = plansDict)

@app.route('/payment/<id>', methods =["POST", "GET"])
def payment(id):
    if "is_logged_in" in session and not session["is_trainer"]:
        if request.method == "POST":      
            #get today's date 
            todayDate = datetime.today().strftime('%Y-%m-%d')
            #add personal trainer to user databbase
            db.child("users").child(session["uid"]).child("personal_trainer").child("id").set(id)
            db.child("users").child(session["uid"]).child("personal_trainer").child("date").set(todayDate)

            #add subcriber to trainer database
            db.child("trainers").child(id).child("subscribers").push({"id":session['uid'], "date":todayDate})

            return redirect(url_for("dashboard"))

        if "trainer_id" in session:
            id = session["trainer_id"]
        else:    
            session["trainer_id"] = id
        

    
        #return render_template("payment.html" , id= id)
        return redirect(url_for("dashboard"))   

    else:
        return redirect(url_for("signin_user"))   
    
         

@app.route('/trainers')
def trainers_list():
    trainers = db.child("trainers").get()
    trainers = json.loads(json.dumps(trainers.val()))
    return render_template('trainer-list.html', trainers= trainers)

@app.route('/')
def index():
    # if "is_logged_in" in session:
    #     if  session['is_trainer']:
    #         return redirect(url_for('trainer_dashboard'))
    #     return redirect(url_for('dashboard'))    

    #get trainers info
    trainers = db.child("trainers").get()

    #transalte to arabic
    translator = Translator()

    for trainer in trainers.each():
        
        trainer.val()['profile']['bio'] = translator.translate(trainer.val()['profile']['bio'], dest='ar').text
        trainer.val()['profile']['introduction'] = translator.translate(trainer.val()['profile']['introduction'], dest='ar').text
        trainer.val()['profile']['trainingStyle'] = translator.translate(trainer.val()['profile']['trainingStyle'], dest='ar').text
        trainer.val()['profile']['firstName'] = translator.translate(trainer.val()['profile']['firstName'], dest='ar').text
        trainer.val()['profile']['lastName'] = translator.translate(trainer.val()['profile']['lastName'], dest='ar').text

   
    

    trainers = json.loads(json.dumps(trainers.val()))
    return render_template('arabic/index.html', trainers= trainers)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

############## for trainer #######################    
@app.route('/signup')
def signup():
    return render_template('sign-up.html')

@app.route('/signin')
def signin():
    print(session)
    return render_template('sign-in.html')

#If someone clicks on login, they are redirected to /result
@app.route("/signin-trainer", methods = ["POST", "GET"])
def signin_trainer():
    if request.method == "POST":        #Only if data has been posted
        result = request.form           #Get the data
        email = result["email"]
        password = result["pass"]
        try:
            login_fun("trainers",email, password) 
            #Redirect to welcome page
            session["is_trainer"] = True
            return redirect(url_for('trainer_dashboard'))
        except Exception as error:
            #If there is any error, redirect to register
            print('Caught this error: ' + repr(error))
            return render_template("sign-in.html")
    else:
        if "is_logged_in" in session and session["is_trainer"]: 
            return redirect(url_for('trainer_dashboard'))
        else:
            return render_template("sign-in.html")



#If someone clicks on register, they are redirected to /register
@app.route("/register-trainer", methods = ["POST", "GET"])
def register_trainer():
    if request.method == "POST":        #Only listen to POST
        result = request.form           #Get the data submitted
        email = result["email"]
        password = result["pass"]
        try:
            register_('trainers',email, password)
            #Go to welcome page
            return redirect(url_for('trainer_profile_edit'))
        except Exception as error:
            #If there is any error, redirect to register_
            print('Caught this error: ' + repr(error))
            
            return redirect(url_for('signup'))

    else:
        if session["is_logged_in"] == True:
            return redirect(url_for('trainer_profile_edit'))
        else:
            print("error")

            return redirect(url_for('signup'))



@app.route('/trainer-profile/<id>' ,  methods = ["POST", "GET"])
def trainer_profile(id):

    firstName = get_profile("trainers",id).val()['firstName']
    lastName = get_profile("trainers",id).val()['lastName']
    intro = get_profile("trainers",id).val()['introduction']
    bio = get_profile("trainers",id).val()['bio']
    training = get_profile("trainers",id).val()['trainingStyle']
    #TODO add reusme
    return render_template('trainer-profile.html', firstName= firstName,
                                                   lastName = lastName,
                                                   intro= intro,
                                                   bio =bio,
                                                   training= training)    

@app.route('/trainer-profile-edit')
@login_required
def trainer_profile_edit():
    return render_template('trainer-profile-edit.html') 
    
       

@app.route('/update_trainer-profile', methods = ["POST", "GET"])
@login_required
def update_trainer_profile():
     if request.method == "POST":       
        result = request.form           #Get the data submitted
        firstName = result["firstName"]
        lastName = result["lastName"]
        bio = result["bio"]
        birthday = result["birthday"]
        #language  = result["language"] TODO: AJAX because it's a list idk how to do it with POST
        introduction = result["introduction"]
        trainingStyle = result["Tstyle"]
        
        # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)

        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            print('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        try:
            update_profile('trainers','firstName', firstName )
            update_profile('trainers','lastName',lastName )
            update_profile('trainers', 'bio', bio)
            update_profile('trainers', 'birthday', birthday)
            update_profile('trainers', 'introduction', introduction)
            update_profile('trainers', 'trainingStyle', trainingStyle)

            return redirect(url_for('trainer_dashboard'))
        except Exception as error:
            #If there is any error, redirect to register
            print('Caught this error: ' + repr(error))    
            return redirect (url_for('trainer_profile_edit'))

     return redirect (url_for('trainer_profile_edit'))            

@app.route('/trainer-dashboard')
@login_required
def trainer_dashboard():
    contacts = {}
    contact  = db.child("trainers").child(session["uid"]).child("contacts").get()
    contact = json.loads(json.dumps(contact.val())) 
    for key in contact.keys():
        contacts[key] = json.loads(json.dumps(get_profile("trainers", key).val())) 

    #get subscribers    
    subscribersDictionary = get_subscribers() 

    return render_template('trainer-dashboard.html',contactId = key, subscribers = subscribersDictionary)



@app.route('/meal-planner', methods=['GET','POST'])
@login_required
def meal_planner():
    global PlanCatagory
    global meals
    mealsAppend = {}
    mealarr = []
    try:
         if request.method == "POST":        #Only if data has been posted
            print("fucking here")
            result = request.form
            if "PlanCatagory" in result and "planName" in result:
                PlanCatagory = result["PlanCatagory"]
                planName = result["planName"]
                meals = db.child('trainers').child(session["uid"]).child("mealPlans").child(str(PlanCatagory)).child(planName).get()
            
            
            #if trainer send meal plans to user 
            if "subID" in result:
                #get plans names in list 
                plansNames = request.form.getlist('plans')
                subID = result['subID']
                #add plansnames to user 
                db.child('users').child(subID).child("mealPlans").update({"plansNames": plansNames})

    except Exception as e:
            error =e

    #get inputed meal        
    mealTime  = request.form.get('mealTimeInfo')
    meal = request.form.get("mealInfo")
    

    #add meal to the database
    try:
        if(PlanCatagory is not None and planName is not None):
            #if there is meals 
            if meals.val() is not None:
                for m in meals.each():
                    mealsAppend[m.key()] = m.val()

                mealsAppend = list(mealsAppend.values()) 

                # if meal time is already there in database get previous meals and append them
                if mealTime in mealsAppend[0]:
                    mealarr = mealsAppend[0] [mealTime]['meals']
                    print("mealarr" + str(mealarr))
            
            if (mealTime is not None):
                mealarr.append(meal)   
                db.child('trainers').child(session["uid"]).child("mealPlans").child(PlanCatagory).child(planName).child('mealTime').child(mealTime).update({"meals":mealarr})
            else:
                db.child('trainers').child(session["uid"]).child("mealPlans").child(PlanCatagory).child(planName).child('mealTime').child("breakfast").update({"meals":[1]})

    except Exception as e:
        print("error" + str(e))     

    #get catagories fromfirebase
    catagories = db.child('trainers').child(session["uid"]).child("mealPlans").get()
   

    #for plans catagories names
    catagoriesArray = []


    #extract plans names and catagories names from firebase
    for catagory in catagories.each():
        catagoriesArray.append(catagory.key())
        
    catagories =  json.loads(json.dumps(catagories.val()))

    #get subscribers    
    subscribersDictionary = get_subscribers() 
 
        
    return render_template('meal-planner.html',  catagoriesArray =catagoriesArray, catagories = catagories, subscribers = subscribersDictionary)
      


@app.route('/workout-planner',  methods=['GET','POST'])
def workout_planner():
    global countWorkoutRange
    global workoutNavbarList 
    #upload files 
    try:
        if request.method == 'POST':
            #get forms info 
            result = request.form
            workoutName = result['workoutName']
            targetMuscle  = result['tragetMuscle']
            workoutNavbarList.append(targetMuscle)
            workoutNavbarList = list(dict.fromkeys(workoutNavbarList))

            get_uploaded_file(UPLOAD_FOLDER_VIDEOS)
    except Exception as e:
        e = 0
    #TODO all of those to the friebase database

    print('here')
    loopRange = request.form.get('gridRangeInfo')
    print(loopRange)

    #if nav plus button is clicked add new card in html
    if(loopRange != None ):
         countWorkoutRange+=1 
         return render_template('workouts-planner.html', x =countWorkoutRange, navbarList = workoutNavbarList)                
    
    #if nav plus button was't clicked just send the old looprange 
    elif(loopRange == None):
        print(mealNavbarList)
        return render_template('workouts-planner.html', x =countWorkoutRange, navbarList = workoutNavbarList)


    else:#TODO change this function wrapper is a must here
        return redirect(url_for('signin'))    

############## for trainer end #######################   


@app.route('/messages/<id>',  methods=['GET','POST'])
def messages(id):
    contacts = {}
    contactId = id

    #get today's date 
    todayDate = datetime.today().strftime('%Y-%m-%d  %H:%M:%S')
    if not session['is_logged_in']:
        return redirect(url_for('signin_user'))

    #get message from ajax
    message  = request.form.get("messageInfo") 

    if message != None:
        add_message_to_database(id, todayDate, message, session['is_trainer']) 
    if session['is_trainer']:
        messagesDict = db.child("trainers").child(session["uid"]).child("contacts").child(id).child("messages").get().val()
    else:         
        messagesDict = db.child("users").child(session["uid"]).child("contacts").child(id).child("messages").get().val() 
    
    if messagesDict != None:
        remove_default_message(id)
    else:
        add_default_message(id)    
    
    messagesDict = json.loads(json.dumps(messagesDict))

    try: 
       
       #if the contact is not is database  create a new one
        if session['is_trainer']:
             contact  = db.child("trainers").child(session["uid"]).child("contacts").get()
             contact = json.loads(json.dumps(contact.val())) 
             print(session["uid"])
             print("here" + str(contact))
             #isTrainer = True
        else:
             #get contact messages  
            contact  = db.child("users").child(session["uid"]).child("contacts").get()
            contact = json.loads(json.dumps(contact.val())) 
       
        
        
        #get all contacts
        for key in contact.keys():
            if session['is_trainer']:
                 contacts[key] = json.loads(json.dumps(get_profile("users", key).val())) 
            else:     
                contacts[key] = json.loads(json.dumps(get_profile("trainers", key).val()))  

        
         
        #for k in  messagesDict:
            #print(f"key={k}, value={messagesDict[k]}")
        return render_template('messages-test.html' , contacts = contacts, messages = messagesDict, contactId = contactId )
   
    except Exception as e:
        print(e)
    
    return render_template('messages-test.html' , contacts = contacts, messages = None, contactId = contactId )
  


        
@app.route('/dashboard', methods =['POST','GET'])
def dashboard():
   

    mealsAppend ={} 
    mealarr = []
    #close webcam
    # global switch
    # if switch == 1:
    #     releaseWebCam() 
    #switch = 0
    if  'is_logged_in' in session and  "is_trainer" in session :
        #get today's date 
        todayDate = datetime.today().strftime('%Y-%m-%d')
        #get info (mealTime, meal) from js 
        mealTime  = request.form.get('mealTimeInfo')
        meal = request.form.get("mealInfo")
        #add meal to the database
        if(meal != None):
            #get meals from database
            meals = db.child('users').child(session["uid"]).child("mealTime").child(todayDate).get()
            #if there is meals 
            if meals.val() != None:
                for m in meals.each():
                    mealsAppend[m.key()] = m.val() 

                mealsAppend = list(mealsAppend.values())  
                if mealTime in mealsAppend[0]:
                    mealarr = mealsAppend[0][mealTime]['meals']
              

            mealarr.append(meal)   
            db.child('users').child(session["uid"]).child('mealTime').child(todayDate).child(mealTime).update({"meals":mealarr})

        #update wieght
        wieght = request.form.get('wieghtInfo')    
        if wieght != None  :
            db.child('users').child(session["uid"]).child("wieght").child(todayDate).update({"wieght":wieght})


        meals = db.child('users').child(session["uid"]).child("mealTime").child(todayDate).get()  
        #for m in meals.each():
            #print("this is a key " + str(m.key()))

        meals = json.loads(json.dumps(meals.val())) 
        print(meals)
        
        wieght = db.child('users').child(session["uid"]).child("wieght").get()
        wieght = json.loads(json.dumps(wieght.val())) 


        trainerID =  db.child("users").child("665bOkvbKFX62E68FPemoqtVqVe2").child("personal_trainer").child("id").get().val()

        return render_template('dashboard.html', workouts = workouts, meals = meals, trainerID = trainerID) 
    elif "is_trainer" in session:
        return redirect(url_for("trainer_dashboaard"))
    else:
        return redirect(url_for("signin_user"))   
   
@app.route('/today-workout', methods =['POST','GET'] ) 
def todayWorkout():
    #get duration (workoutDuration) from js
    workoutDuration = request.form.get('duration')
    #get today's date 
    todayDate = datetime.today().strftime('%Y-%m-%d')
    #add workout duration to database
    if(workoutDuration != None):
        db.child('users').child(person["uid"]).child(todayDate).update({"workoutDuration":[workoutDuration]})
    #get info (index) from js 
    indx = request.form.get('info')
    if(indx == None):
        indx = 0
    
    #call global camera switch
    global switch
    #if start workout btn is clicked on front end and camera is off
    if request.form.get('start') == 'start' :
            #set camera on
            switch = 1 
    return render_template('todayWorkout.html', workouts = workouts)

@app.route('/video')
def video():
    global switch
    
    return Response(generate_frames(workouts[workoutArray[int(indx)]][0], 
    workouts[workoutArray[int(indx)]][1]),
    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/signup/user')
def signup_user():
    return render_template('signup.html')

@app.route('/signin/user')
def signin_user():
    print(session)
    return render_template('signin.html')

#If someone clicks on login, they are redirected to /result
@app.route("/result", methods = ["POST", "GET"])
def result():
    if request.method == "POST":        #Only if data has been posted
        result = request.form           #Get the data
        email = result["email"]
        password = result["pass"]
        try:
            login_fun("users",email, password) 
            print("trainer_id" in session)
            if "trainer_id" in session:
                return redirect(url_for('payment', id = session["trainer_id"]))
            return redirect(url_for('dashboard'))
        except Exception as error:
            #If there is any error, redirect to register
            print('Caught this error: ' + repr(error))
            return redirect(url_for('index'))
    else:
        if session["is_logged_in"] == True:
            print("trainer_id" in session)
            if "trainer_id" in session:
                return redirect(url_for('payment'))
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))


#If someone clicks on register, they are redirected to /register
@app.route("/register", methods = ["POST", "GET"])
def register():
    if request.method == "POST":        #Only listen to POST
        result = request.form           #Get the data submitted
        email = result["email"]
        password = result["pass"]
        name = result["name"]
        try:
            register_("users",email, password)
            #Go to welcome page
            return redirect(url_for('dashboard'))
        except Exception as error:
            #If there is any error, redirect to register
            print('Caught this error: ' + repr(error))
            
            return redirect(url_for('test'))

    else:
        if session["is_logged_in"] == True:
            if "trainer_id" in session:
                return redirect(url_for('payment'))
            return redirect(url_for('dashboard'))
        else:
            print("error")

            return redirect(url_for('index'))

@app.route('/logout')
def logout():
    #remove user data from session
    session.clear()
    auth.current_user = None
    return redirect(url_for('index'))

@app.route('/user-profile')
def user_profile():
    
    if "is_logged_in" in session and not session["is_trainer"]:
        return render_template('user-profile.html')
    else:    
        return redirect(url_for('index'))

               
@app.route('/update-profile', methods=['POST'])
def update_profile():
    
    if request.method == "POST" and "is_logged_in" in session and not session["is_trainer"]:        #Only listen to POST
        result = request.form           #Get the data submitted
        firstName = result['firstName']
        lastName = result['lastName']
        email = result['email']#TODO add phone number and Email vervcation
        birthday = result['birthday']
        wieght = result['wieght']
        wieghtIsKg = "OFF"
        if 'checkbox-wieght' in result:
            wieghtIsKg = result['checkbox-wieght'] #todo this
        hieght = result['hieght']
        hieghtIsCm = "OFF"
        if 'checkbox-hieght' in result:
            hieghtIsCm = result['checkbox-hieght']
        #TODO gender
                 

        update_profile ("users", "firstName", firstName)
        update_profile ("users","lastName" , lastName)
        update_profile ("users", "email", email)
        update_profile ("users", "birthday", birthday)
        update_profile ("users", "wieght", wieght)
        update_profile ("users","wieghtIsKg", wieghtIsKg)
        update_profile ("users","hieght", hieght)
        update_profile ("users","hieghtIsCm", hieghtIsCm)
        


        
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('index'))

@app.route('/upload',methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for("workout_planner"))

    return render_template("upload.html") #TODO change this       



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# get workout index info from front end
@app.route('/postmethod', methods = ['POST'])
def get_post_javascript_data():
    indx = request.form.get('info')
    #print(workouts[workoutArray[int(indx)]][0])
    return indx
 
#register function for both users and trainers
def register_(member,email, password):
    #Try creating the user account using the provided data
    auth.create_user_with_email_and_password(email, password)
            #Login the user
    user = auth.sign_in_with_email_and_password(email, password)
            #Add data to global person
    global person
    person["is_logged_in"] = True
    person["email"] = user["email"]
    person["uid"] = user["localId"]
    #check if trainer 
    if member == "tariners":
        person["is_trainer"]=True 

    #make a session for this  user
    session['uid'] = user["localId"]
    session["is_logged_in"] = person["is_logged_in"]
    session["is_trainer"] = person['is_trainer']
  

    #Append data to the firebase realtime database
    data = {"email": email}
    db.child(member).child(person["uid"]).set(data)

def login_fun(member,email, password):
    auth.current_user = None
            #Try signing in the user with the given information
    user = auth.sign_in_with_email_and_password(email, password)
            #print(user)
            #Insert the user data in the global personUser
    global person
    person["is_logged_in"] = True
    person["email"] = user["email"]
    person["uid"] = user["localId"]
    #check if trainer 
    if member == "tariners":
        person["is_trainer"]=True 
    #data = db.child("users").get()
    all_users = db.child("trainers").get()
       
    #make a session for this  user
    session['uid'] = user["localId"]
    session["is_logged_in"] = person["is_logged_in"]
    session["is_trainer"] = person['is_trainer']



#a function to update profile database for users and trainers
def update_profile (member, field, data):
    db.child(member).child(session["uid"]).child("profile").update({field: data })

def get_profile (member, uid):
    return db.child(member).child(uid).child("profile").get()



#messages helper functions
def add_message_to_database(id, todayDate, message, isTrainer):
    data = {'message' : message, 'sender': session['uid'], 'receiver': id}
    if isTrainer:
        db.child("trainers").child(session["uid"]).child("contacts").child(id).child("messages").child(todayDate).update(data)   
        db.child("users").child(id).child("contacts").child(session["uid"]).child("messages").child(todayDate).update(data)
    else:
        db.child("users").child(session["uid"]).child("contacts").child(id).child("messages").child(todayDate).update(data)   
        db.child("trainers").child(id).child("contacts").child(session["uid"]).child("messages").child(todayDate).update(data)

def remove_default_message(id):
    db.child("users").child(session["uid"]).child("contacts").child(id).child("messages").child("default").remove()  
    db.child("trainers").child(id).child("contacts").child(session["uid"]).child("messages").child("default").remove()

def add_default_message(id):
    db.child("users").child(session["uid"]).child("contacts").child(id).child("messages").child("default").update({"default":"send your first message"})   
    db.child("trainers").child(id).child("contacts").child(session["uid"]).child("messages").child("default").update({"default":"send your first message"})
   
def get_subscribers():
    subscribersDictionary = {}
    subscribers = db.child("trainers").child(session["uid"]).child("subscribers").get()   
    for sub in subscribers.each():
        id = sub.val()['id']
        subscribersDictionary[id] = json.loads(json.dumps(get_profile("users", id).val()))
    return subscribersDictionary

#upload file function
#todo file name
def get_uploaded_file(UPLOAD_FOLDER):
    
    print("here")
    if 'file' not in request.files:
        # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)

        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            print('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__=="__main__":
    app.run(debug=True)
    #app.run()
