# UrbanBangla

****An app developed to store modern Bengali words that may not be in orthodox dictionaries.****

*Live:*
This will be updated once I deploy the app.

*But*, you can run it in your local machine
	
    git clone https://github.com/zihadbappy/UrbanBangla.git
    cd UrbanBangla
    pip install -r requirements.txt
	flask run
	
Go to your browser and enter

    http://127.0.0.1:5000/

**Tech Stack:** *Flask, Python, GoogleAuth, MongoDB, Jinja*


*Features:*

 - Users can login with google ID and submit words
 - Upon validity check via admin, the words may get approval
 - The backend serves data via a RESTful API
 - Homepage will generate words from the REST API
<br>

*Features that are being added:*
- Upvote and downvote
 - Login via Urban Bangla ID
 - Flagging words
<br>