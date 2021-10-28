from flask import Flask, flash, jsonify, request, render_template,redirect, session
from flask.helpers import url_for
import traceback
import sys
import os
from pymongo.message import update
from termcolor import colored
import dns
import math
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

    # words=list(db.words.find({"status":"approved"}))
    # json_words= json.loads(json.dumps(words, default=json_util.default))
    
    # Pagination
    limit=20
    if request.args.get("page") is None:
        pageNo=1
    else:
        pageNo=int(request.args.get('page'))
    offset = (pageNo-1)* limit

    word_order=list(db.words.find({"status":"approved"}).sort('upvote',pymongo.DESCENDING))
    totalPages= math.ceil(len(word_order)/limit)
    print(colored(word_order, 'blue'))
    start_id=word_order[offset]['upvote']
    outputWords= list(db.words.find({'upvote':{'$lte': start_id}}).sort('upvote',pymongo.DESCENDING).limit(limit))

    next_page = '?page='+str(pageNo+1)
    prev_page = '?page='+str(pageNo-1)
    return render_template('home.html',json_words=outputWords, totalPages=totalPages,
    pageNo=pageNo,  next_page=next_page, prev_page=prev_page)
    # return json.dumps(words, default=json_util.default)

@app.route("/addword", methods=['POST'])
def post_word():
    try:
        word=request.form['word']
        definition=request.form['def']
        exp=request.form['exp']
        anonCheck=request.form.get('anonCheck')
        print(colored(anonCheck,'red'))
        userHandle=""
        if(anonCheck=="anonTrue"):
            userHandle= "Anonymous"
        else:
            userHandle= session["name"]

        # email= session['email']
        # userHandle=request.form['userHandle']

        # print(colored("word={} , definition={} , exp={} , email={}, userHandle".format(word, definition, exp, email, userHandle), 'red'))
        json= {"word":word,
        "definition":definition,
        "exp":exp,
        "email": session["email"],
        "userHandle": userHandle,
        "upvote":0,
        "downvote":0,
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

@app.route("/search/"
, methods=['GET'])
def search():
    searchString=request.args.get('search').lower()
    print(colored(searchString, 'red'))
    # db.words.create_index([('word', "text" )])
    # # words=list(db.words.find({'word'.lower():searchString}))
    # words=list(db.words.find({'$text':{'$search': searchString}}))


    # json_words= json.loads(json.dumps(words, default=json_util.default))
    # print(colored(json_words,'yellow'))

    # return render_template('searchPage.html',json_words=json_words)
        # Pagination
    limit=6
    if request.args.get("page") is None:
        pageNo=1
    else:
        pageNo=int(request.args.get('page'))
    offset = (pageNo-1)* limit

    word_order=list(db.words.aggregate([{
        "$match": {
            '$text':{'$search': searchString}
        }
    },
    {
        "$sort":{
            "upvote": pymongo.DESCENDING
        }
    
    }]))
    if list(word_order) is not None:
        start_id=word_order[offset]['_id']

    # word_order=list(db.words.find(filter={'$text':{'$search': searchString}},sort=[('upvote',-1)]))
        totalPages= math.ceil(len(word_order)/limit)
        outputWords= list(db.words.aggregate([{
            "$match": {
                '$text':{'$search': searchString}
            }
        },
        {
            "$sort":{
                "upvote":pymongo.DESCENDING
            }
        },
        # {
        #     "$project":{
        #         '_id':1,
        #         'word':1,
        #         'definition':1,
        #         'exp':1,
        #         'email':1,
        #         'userHandle':1,
        #         'upvote':1,
        #         'downvote':1,
        #         'status':1,
        #         'postedDate':1,
        #         "newId":{"$lte":["$_id",start_id]}
        #     }
        # },
        {
            "$limit": limit
        }
        # {"$project":{
        #     'upvote':{"$lte": ["$upvote",start_id]}
        # }
        # }
        ]))

        print(colored(outputWords, 'blue'))
        # outputWords= list(db.words.find({'upvote':{'$lte': start_id}}).sort('upvote',pymongo.DESCENDING).limit(limit))

        next_page = '?search='+searchString+'?page='+str(pageNo+1)
        prev_page = '?search='+searchString+'?page='+str(pageNo-1)
        return render_template('home.html',json_words=outputWords, totalPages=totalPages,
        pageNo=pageNo,  next_page=next_page, prev_page=prev_page)
    else:
        return "No match found"



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