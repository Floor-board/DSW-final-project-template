from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash
from markupsafe import Markup
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from flask_oauthlib.client import OAuth
from bson.objectid import ObjectId
import random
import pprint
import os
import time
import pymongo
import sys
import pydealer

app = Flask(__name__)

app.debug = True #Change this to False for production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

EnemyCard = 0
GameState = "Null"

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

#Connect to database
url = os.environ["MONGO_CONNECTION_STRING"]
client = pymongo.MongoClient(url)
db = client[os.environ["MONGO_DBNAME"]]
collection = db['score'] #TODO: put the name of the collection here

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def home():
    if 'user_data' in session:
       gitHubID = session['user_data']['login']
       createAccount(gitHubID)
       
    session["game_started"] = "No"
    return render_template('home.html')

def createAccount(GithubName):
       
        if collection.find_one({"username":GithubName}):
            Player = loadPlayerData(GithubName)
            return render_template('home.html')
        else:
            doc = {"username": GithubName, "wins": 0, "loss": 0, "ties": 0, "stats": "win"}
            collection.insert_one(doc)
            PlayerData = doc
            print("CREATED A CHARACTER!!!")
            return(PlayerData)
            return render_template('home.html')
   
   
def loadPlayerData(gitHubID):
    characterData = collection.find_one({"username": gitHubID})
    return(characterData)
   


#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():  
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out.')
    return redirect('/')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    global GithubName
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args), 'error')      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            message = 'You were successfully logged in as ' + session['user_data']['login'] + '.'
            GithubName = session['user_data']['login']
        except Exception as inst:
            session.clear()
            print(inst)
            message = 'Unable to login, please try again.', 'error'
    return render_template('message.html', message=message)


@app.route('/page1')
def renderPage1():
    if 'user_data' in session:
        user_data_pprint = pprint.pformat(session['user_data'])#format the user data nicely
    else:
        createUserData()
       
        user_data_pprint = '';
    deck = pydealer.Deck()
    deck.shuffle()
    hand = deck.deal(7)
    return render_template('page1.html',dump_user_data=user_data_pprint, hand=hand)

@app.route('/page2')
def renderPage2():
    #if 'user_data' in session:
        #print("anything")
        #for doc in collection.find({"username":str(session['user_data']['login'])}):
            #print(doc)
            #return render_template('page2.html', win=doc["stats"])
    #else:
        #followers = 'no'; #needs fixing
   
    #return render_template('page2.html')
    #old code, kept it just in case if I'll ever need it
   
    if 'user_data' in session:
        for doc in collection.find({"username":str(session['user_data']['login'])}):
            if doc["stats"]=="win":
                return render_template('page2.html',win=doc["wins"],loss=doc["loss"],tie=doc["ties"])
            else:
                return render_template('page2.html')
    else:
        return render_template('page2.html')

@app.route('/Game')
def renderGame():
    global EnemyCard
    #card_values = { 'Ace': 14, 'King': 13, 'Queen': 12, 'Jack': 11, '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2 }
   
    session['PlayerPoints'] = 0
    session['BotPoints'] = 0
   
    #PlayerDeck
    PlayerDeck_list=[]
    cards=5
    for i in range(cards):
        PlayerDeck_list.append(random.randint(1,13))
    print(PlayerDeck_list)
   
    #AIDeck
    cards=1
    for i in range(cards):
        EnemyCard = (random.randint(1,13))
   
    print("SelectedEnemyCard= ", EnemyCard)
   
    PCard1, PCard2, PCard3, PCard4, PCard5 = PlayerDeck_list
    #PCard2 = Card2, PCard3 = Card3, PCard4 = Card4, PCard5 = Card5
    return render_template('Game.html', Card1 = PCard1, Card2 = PCard2, Card3 = PCard3, Card4 = PCard4, Card5 = PCard5,  game_state=GameState)
   
   
   
@app.route('/GamePlay', methods = ["POST","GET"])
def renderGamePlay():
    if 'user_data' in session:
        gitHubID = session['user_data']['login']
        PlayerCard = int(request.form["CardPlayed"])
        print("PLAYERCARD= ",PlayerCard)
        global EnemyCard
        global GameState

        GameState = CalculateWinner(PlayerCard, EnemyCard, gitHubID)
        if GameState == 'Game over!':
            return render_template('page1.html')
       
        #card_values = { 'Ace': 14, 'King': 13, 'Queen': 12, 'Jack': 11, '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2 }
       
        #PlayerDeck
        PlayerDeck_list=[]
        cards=5
        for i in range(cards):
            PlayerDeck_list.append(random.randint(1,13))
       
        #AIDeck
        cards=1
        for i in range(cards):
            EnemyCard = (random.randint(1,13))
       
        print("ENEMYCARD NEXT SELECT= ", EnemyCard)
       
        print("PLAY 1")
       
        PCard1, PCard2, PCard3, PCard4, PCard5 = PlayerDeck_list

        #print(PlayerCard)
        return render_template('Game.html', Card1 = PCard1, Card2 = PCard2, Card3 = PCard3, Card4 = PCard4, Card5 = PCard5, game_state=GameState)
   
def CalculateWinner(PlayerCard, EnemyCard, Username):
    global GithubName
    Game_StateCAL = "Null"
    DEBUGSCORE = PlayerCard - EnemyCard
    print(DEBUGSCORE)
    print("PlayerCard PLAY1= ", PlayerCard)
    print("EnemyCard PLAY1=", EnemyCard)
    GameOver = False
    wins = 0
    loss = 0
    for doc in collection.find({ "username": session["user_data"]["login"]}):
        wins = doc["wins"]
        loss = doc["loss"]
        print(loss)
        print(win)
   
    session['PlayerWin'] = 0
    session['PlayerLoss'] = 0
    if PlayerCard == EnemyCard:
        Game_StateCAL="DRAW"
        session['PlayerPoints'] +=1
        session['BotPoints'] +=1
    else:
        if session['PlayerPoints'] > 20 or session['BotPoints'] > 20:
            Game_StateCAL = "Game over!"
            GameOver = True
        elif PlayerCard > EnemyCard:
            Game_StateCAL="WIN"
            session['PlayerPoints'] +=1
        elif PlayerCard < EnemyCard:
            Game_StateCAL="LOSE"
            session['BotPoints'] +=1
        if GameOver == True:
            session['PlayerPoints'] = 0
            session['BotPoints'] = 0
            print("Game over!")
            if session['PlayerPoints'] == 20 and session['BotPoints'] < 20:
                """wins = wins + 1
                print(wins)
                query = {"username": session["user_data"]["login"]}
                changes = {'$set': {"wins":wins}}
                collection.update_one(query, changes)

                print("WINS " + str(wins))
                updateScore(session["user_data"]["login"], "wins", wins)"""
                session['PlayerWin'] = session['PlayerWin'] + 1
                print("win " + str(win))
                win = win + 1
                updateScore(session["user_data"]["login"], "win", win)
            else:
                session['PlayerLoss'] = session['PlayerLoss'] + 1
                print("LOSS " + str(loss))
                loss = loss + 1
                updateScore(session["user_data"]["login"], "loss", loss)
            print(session['PlayerWin'], session['PlayerLoss'])
    return Game_StateCAL

def updateScore(gitHubID, Key, Value):
    query = collection.find_one({"username": gitHubID})
    changes = {'$set': {Key:Value}}
    collection.update_one(query, changes)

    characterData = query
    return(characterData)

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']

@app.route('/page1', methods=["GET"])
def start_button():
    start = request.form.get('submit')
    return render_template('Game.html')


if __name__ == '__main__':
    app.run()