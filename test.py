from flask import Flask, url_for, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
importj


app = Flask(__name__)
db = SQLAlchemy(app)

#database 
class User(db.Model):
    """ Create user table"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))



@app.route('/login', methods=['POST'])
def login():
   request_data = request.get_json()
   eml = request_data['email']
   passw = request_data['password']
   data = User.query.filter_by(email=eml, password = passw).first() #شيك على المدخلات
   if data is not None: #اذا المدخلات موجودة في الداتابيس
       token = jwt.encode({'email' : eml, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=15)},app.config['SECRET_KEY'])

       return jsonify({'token' : token.decode('UTF-8')})



@app.route('/register/', methods=['GET', 'POST'])
def register():
    """Register Form"""
    if request.method == 'POST':
        new_user = User(
            username=request.form['username'],
            password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        return render_template('login.html')
    return render_template('register.html')