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
    session["game_started"] = "No"
    return render_template('home.html')

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
    if resp is None:
        session.clear()
        flash('Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args), 'error')      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            message = 'You were successfully logged in as ' + session['user_data']['login'] + '.'
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
    #card_values = { 'Ace': 14, 'King': 13, 'Queen': 12, 'Jack': 11, '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2 }
    
    #PlayerDeck
    PlayerDeck_list=[]
    cards=5
    for i in range(cards):
        PlayerDeck_list.append(random.randint(1,13))
    print(PlayerDeck_list)
    
    #AIDeck
    EnemyDeck_list=[]
    cards=5
    for i in range(cards):
        EnemyDeck_list.append(random.randint(1,13))
    print(EnemyDeck_list)
    
    PCard1, PCard2, PCard3, PCard4, PCard5 = PlayerDeck_list
    #PCard2 = Card2, PCard3 = Card3, PCard4 = Card4, PCard5 = Card5
    return render_template('Game.html', Card1 = PCard1, Card2 = PCard2, Card3 = PCard3, Card4 = PCard4, Card5 = PCard5, Enemy_Deck=EnemyDeck_list)
    
    """print(session)
    deck = pydealer.Deck()
    MyDeck = deck.shuffle()
    PointsAI = 0
    Player = 0
    
    Card1 = deck.deal(1)
    Card2 = deck.deal(1)
    Card3 = deck.deal(1)
    Card4 = deck.deal(1)
    Card5 = deck.deal(1)
    print(pydealer)
    player1_won = pydealer.stack()
    player2_won = pydealer.stack()

    #https://www.perplexity.ai/search/using-pydealer-is-it-possible-EIUXGhKnQsGknlqq.hkxdA
    #this is what we use for the rounds and comparing cards
    round_count = 0
    max_rounds = 20
    
    while round_count < max_rounds:
        round_count += 1
    
    if len(player1_hand) > 0 and len(player2_hand) > 0:
        war_card1 = player1_hand.deal(1)[0]
        war_card2 = player2_hand.deal(1)[0]
        war_pile.extend([war_card1, war_card2])
        print(f"War cards: Player 1 - {war_card1}, Player 2 - {war_card2}")
    if get_card_value(war_card1) > get_card_value(war_card2):
        player1_won.add(war_pile)
        print("Player 1 wins the war")
    elif player2_won.add(war_pile):
        print("Player 2 wins the war")
    elif len(player1_hand) > 0:
        player1_won.add(war_pile)
        print("Player 1 wins the war (Player 2 ran out of cards)")
    else:
        player2_won.add(war_pile)
        print("Player 2 wins the war (Player 1 ran out of cards)")
    print(f"Player 1 has {len(player1_hand) + len(player1_won)} cards, Player 2 has {len(player2_hand) + len(player2_won)} cards")
    , deck=MyDeck, Card1 = Card1, Card2 = Card2, Card3 = Card3, Card4 = Card4, Card5 = Card5
"""
    
@app.route('/GamePlay', methods = ["POST","GET"])
def renderGamePlay():
    PlayerCard = request.form["CardPlayed"]
    #test = request.form
    
    #PlayerDeck
    PlayerDeck_list=[]
    cards=5
    for i in range(cards):
        PlayerDeck_list.append(random.randint(1,13))
    
    #AIDeck
    EnemyDeck_list=[]
    cards=5
    for i in range(cards):
        EnemyDeck_list.append(random.randint(1,13))
    
    PCard1, PCard2, PCard3, PCard4, PCard5 = PlayerDeck_list
    
    print("PLAY 1")
    
    #print(PlayerCard)
    return render_template('Game.html', Card1 = PCard1, Card2 = PCard2, Card3 = PCard3, Card4 = PCard4, Card5 = PCard5, Enemy_Deck=EnemyDeck_list)
    
    


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