import re
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

client = pymongo.MongoClient(os.getenv('MONGO_URI'), tlsCAFile=ca)
db=client.UrbanBangla
# except pymongo.errors.ConnectionFailure as e:
#     print(colored(e, 'red'))



@app.route("/")
def get_words():
    if request.args.get('page') is not None:
        session['url']='/?page='+request.args.get('page')
    else: session['url']='/'

    # Pagination
    limit=8
    if request.args.get("page") is None:
        pageNo=1
    else:
        pageNo=int(request.args.get('page'))
    offset = (pageNo-1)* limit

    word_order=list(db.words.find({"status":"approved"}))
    totalPages= math.ceil(len(word_order)/limit)
    outputWords=[]
    # when the user is not logged in
    if 'google_id' not in session:
        outputWords= list(db.words.aggregate([
        {
        "$sort":{ "upvote": pymongo.DESCENDING,
        "_id": pymongo.DESCENDING}
        },
        {"$match":{"$and":[
            {'status':"approved"},
            ]}
        },
        {"$skip": offset},
        {"$limit":limit}
        ]))
        print(colored(len(outputWords), 'blue'))
    # user logged in
    else:
        # get user upvotes and downvotes list
        user_upvotes= list(db.users.find({}, {'_id':0, 'upvotes':1}))[0]['upvotes']
        user_downvotes= list(db.users.find({}, {'_id':0, 'downvotes':1}))[0]['downvotes']

        def status(_id):
            print(colored(_id, 'red'))
            print(colored(_id in user_upvotes, 'red'))
            return _id in user_upvotes

        outputWords=list(db.words.aggregate([   
        {
        "$sort":{ "upvote": pymongo.DESCENDING,
        "_id": pymongo.DESCENDING}
        },
        {"$match":{"$and":[
            {'status':"approved"},
            ]}
        },
        {"$skip": offset},
        {"$limit":limit}
        ]))

        word_id_collection=[]
        upvote_status=[]
        downvote_status=[]
        for x in outputWords:
            word_id_collection.append(str(x['_id']))

        for x in word_id_collection:
            if x in user_upvotes:
                upvote_status.append(True)
            else:
                upvote_status.append(False)
            if x in user_downvotes:
                downvote_status.append(True)
            else:
                downvote_status.append(False)

        for idx, val in enumerate(outputWords):
            val['upvote_status']= upvote_status[idx]
            val['downvote_status']= downvote_status[idx]
            

    next_page = '?page='+str(pageNo+1)
    prev_page = '?page='+str(pageNo-1)
    return render_template('home.html',json_words=outputWords, totalPages=totalPages,
    pageNo=pageNo,  next_page=next_page, prev_page=prev_page)
    

@app.route("/addword", methods=['POST'])
def post_word():
    session['url']='/addword'
    # Gather necessary data for db
    try:
        word=request.form['word']
        definition=request.form['def']
        exp=request.form['exp']
        anonCheck=request.form.get('anonCheck')
        authorID=session['google_id']
        userHandle=""
        if(anonCheck=="anonTrue"):
            userHandle= "Anonymous"
        else:
            userHandle= session["name"]

        json= {"word":word,
        "definition":definition,
        "exp":exp,
        "email": session["email"],
        "userHandle": userHandle,
        "upvote":0,
        "downvote":0,
        "status":"pending",
        'authorID':authorID,
        "postedDate": datetime.now()
        }

        # insert word to words table 
        print(colored(json, 'yellow'))
        db.words.insert_one(json)

        # get the word id to ref it to the author
        word_id=list(db.words.find(filter={}, sort=[('_id',-1)]).limit(1))
        print(colored(word_id[0]['_id'], 'red'))

        # append the word to the words_author array in users table
        db.users.update(
            {'google_id':authorID},
            {'$push':{'words_author':word_id[0]['_id']}}
        )

        return redirect("/addword")
    except:
        traceback.print_exc(file=sys.stdout)


@app.route('/upvote/<word_id>', methods=['POST'])
def upvote_word(word_id):
    if 'google_id' not in session:
        return redirect('/user')
    else:
        # update upvote in words table
        db.words.update_one(
                {"_id":{"$eq":ObjectId(word_id)}},
                {'$inc': {"upvote":1}})

        # add upvote to the user upvote array in users table
        db.users.update(
                {'google_id':session['google_id']},
                {'$addToSet':{'upvotes':word_id}}
            )
        return redirect(session['url'])


# Undo upvote on click of the like button
# logged in
@app.route('/undo_upvote/<word_id>', methods=['POST'])
def undo_upvote(word_id):
    # if 'google_id' not in session:
    #     return redirect('/user')
    # else:
        # update upvote in words table
        db.words.update_one(
                {"_id":{"$eq":ObjectId(word_id)}},
                {'$inc': {"upvote":-1}})

        # add upvote to the user upvote array in users table
        db.users.update(
                {'google_id':session['google_id']},
                {'$pull':{'upvotes':word_id}}
            )
        return redirect(session['url'])

@app.route('/undo_downvote/<word_id>', methods=['POST'])
def undo_downvote(word_id):
    # if 'google_id' not in session:
    #     return redirect('/user')
    # else:
        # update upvote in words table
        db.words.update_one(
                {"_id":{"$eq":ObjectId(word_id)}},
                {'$inc': {"downvote":-1}})

        # add upvote to the user upvote array in users table
        db.users.update(
                {'google_id':session['google_id']},
                {'$pull':{'downvotes':word_id}}
            )
        return redirect(session['url'])

@app.route('/downvote/<word_id>', methods=['POST'])
def downvote_word(word_id):
    if 'google_id' not in session:
        return redirect('/user')
    else:

        # update downvote in words table
        db.words.update_one(
                {"_id":{"$eq":ObjectId(word_id)}},
                {'$inc': {"downvote":1}})

        # add downvote to the user downvote array in users table
        db.users.update(
                {'google_id':session['google_id']},
                {'$addToSet':{'downvotes':word_id}}
            )
        return redirect(session['url'])

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

@app.route("/search/", methods=['GET'])
def search():
    searchString=request.args.get('search').lower()
    # Pagination
    limit=2
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
    if word_order is not None:
    # word_order=list(db.words.find(filter={'$text':{'$search': searchString}},sort=[('upvote',-1)]))
        totalPages= math.ceil(len(word_order)/limit)
        outputWords= list(db.words.aggregate([
    {"$match":{
        "$and":[
        {'status':"approved"},
        {'$text':{'$search': searchString}}
        ]}
    },
    {
    "$sort":{ "upvote": pymongo.DESCENDING,
    "_id": pymongo.DESCENDING}
    },
    {"$skip": offset},
    {"$limit":limit}
    ]))
        # print(colored(outputWords, 'blue'))
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