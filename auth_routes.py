import collections
from functools import wraps
from flask.templating import render_template
from termcolor import colored
from app import app
import os
import pathlib
import requests
from flask import Flask, session,flash, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

# app.secret_key = "mySecretKeyLol"

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
    print(colored(session["state"],'red'))
    print(colored(request.args["state"],'red'))
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

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    session["picture"] = id_info.get("picture")
    print(colored(id_info,'red'))
    return redirect("/user/protected_area")

@app.route('/user/logout', methods=['GET'])
def userlogout():
    session.clear()
    return redirect("/user")

@app.route('/user/protected_area', methods=['GET'])
@login_is_required
def protected_area():
    flash("logged in successfully")
    return redirect('/addword')