import collections
from functools import wraps
from flask.templating import render_template
from termcolor import colored
from app import app
import os
import pymongo
import certifi
import pathlib
import requests
from flask import Flask, session,flash, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

# app.secret_key = "mySecretKeyLol"
ca = certifi.where()
client = pymongo.MongoClient(os.getenv('MONGO_URI'), tlsCAFile=ca)
db=client.UrbanBangla

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/user/callback"
)

def login_is_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return render_template('unauthorized.html')  # Authorization required
        else:
            return function()

    return wrapper


@app.route('/user', methods=['GET'])
def loginpage():
    return render_template('login.html')


@app.route('/user/login', methods=['GET'])
def userlogin():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route('/user/callback', methods=['GET'])
def callback():
    flow.fetch_token(authorization_response=request.url)
    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    print(colored(id_info,'yellow'))
    # adding user data to the session
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    session["picture"] = id_info.get("picture")
    session['email_verified']=id_info.get('email_verified')

    # saving user data to db
    if list(db.users.find_one({"google_id":id_info.get('sub')})) is None:
        userData_json={
            "name":id_info.get('name'),
            "email":id_info.get('email'),
            'google_id': id_info.get('sub'),
            'picture': id_info.get('picture'),
            'email_verified':id_info.get('email_verified'),
            'words_author': [],
            'upvotes': [],
            'downvotes':[]
        }
        print(colored(list(db.users.find({"google_id":id_info.get('sub')})),'red'))
        # db.users.insert_one(userData_json)
    return redirect("/user/protected_area")

@app.route('/user/logout', methods=['GET'])
def userlogout():
    session.clear()
    return redirect("/user")

@app.route('/user/protected_area', methods=['GET'])
@login_is_required
def protected_area():
        flash("logged in successfully")
        if 'url' not in session:
            return redirect('/')
        else:
            return redirect(session['url'])