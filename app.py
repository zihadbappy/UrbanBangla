from flask import Flask, flash, jsonify, request, render_template,redirect, session
from flask.helpers import url_for
import traceback
import sys
import os
from termcolor import colored
import dns
import json
from bson import ObjectId   
import sys
import pymongo
import logging
from pymongo import MongoClient
import certifi
from bson import json_util
from bson.json_util import default, dumps
from werkzeug.utils import redirect
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)                                             

import auth_routes
from auth_routes import login_is_required

ca = certifi.where()
logging.basicConfig(level=logging.DEBUG)

try:
    client = pymongo.MongoClient(os.getenv('MONGO_URI'), tlsCAFile=ca)
    db=client.UrbanBangla
except pymongo.errors.ConnectionFailure as e:
    print(colored(e, 'red'))

# words =[{ "id": "0", 'word': 'nice lagsa', 'definition': "You're looking nice"}]

@app.route("/")
def get_words():
    # aggregatedCur = db.words.aggregate(
    #     [
    #         {
    #         '$project':{
    #         'date':{'$toDate': "$postedDate" } }
    #         }
    #     ]
    # )
    # aggregatedList = list(aggregatedCur)
    # print(colored(aggregatedList,'yellow'))    

    words=list(db.words.find({"status":"approved"}))
    json_words= json.loads(json.dumps(words, default=json_util.default))
    return render_template('home.html',json_words=json_words)
    # return json.dumps(words, default=json_util.default)

@app.route("/addword", methods=['POST'])
def post_word():
    try:
        word=request.form['word']
        definition=request.form['def']
        exp=request.form['exp']
        # email= session['email']
        # userHandle=request.form['userHandle']

        # print(colored("word={} , definition={} , exp={} , email={}, userHandle".format(word, definition, exp, email, userHandle), 'red'))
        json= {"word":word,
        "definition":definition,
        "exp":exp,
        "email": session["email"],
        "userHandle": session["name"],
        "upvote":"0",
        "downvote":"0",
        "status":"pending",
        "postedDate": datetime.now()
        }

        print(colored(json, 'yellow'))
        db.words.insert_one(json)
        # return jsonify(result={"status": 200})
        return redirect("/addword")
    except:
        traceback.print_exc(file=sys.stdout)


@app.route("/addword", methods=['GET'])
@login_is_required
def word_form():
    return render_template('addword.html')

@app.route("/adminDashboard", methods=['GET'])
def dash():
    words=list(db.words.find({'status':'pending'}))
    json_words= json.loads(json.dumps(words, default=json_util.default))
    print(colored(json_words,'yellow'))
    return render_template('adminDashboard.html',json_words=json_words)

@app.route("/adminDashboard/<action>/<word_id>/", methods=['POST'])
def approve_word(action, word_id):
    oid = ObjectId(word_id)
    if(action=="approve"):
        # wordID= db.words.count_documents({"_id": {"$oid":"6162ef8d8dbc49ec785c61c8"}})
        id= db.words.find({"_id": {"$eq": oid}})
        id= json.loads(dumps(id, default=json_util.default))
        print(colored(id,'red'))
        if(id is not None):
            db.words.update_one(
            {"_id":{"$eq":oid}},
            {'$set': {"status":"approved"}})
    if(action=="decline"):

        id= db.words.find({"_id": {"$eq": oid}})
        id= json.loads(dumps(id, default=json_util.default))
        print(colored(id,'red'))
        if(id is not None):
            db.words.update_one(
            {"_id":{"$eq":oid}},
            {'$set': {"status":"declined"}})
    
    return redirect('/adminDashboard')


if __name__ == "__main__":
    app.config['DEBUG'] = True
    app.run('0.0.0.0',port='5000')