import copy
from flask import Flask, request
from pymessenger.bot import Bot
import mysql.connector

app = Flask(__name__)
connectionInfo = readConnInfo("andrewbotdata.txt")
ACCESS_TOKEN = connectionInfo["ACCESS_TOKEN"]
VERIFY_TOKEN = connectionInfo["VERIFY_TOKEN"]
DBHOST = connectionInfo["DBHOST"]
DBUSER = connectionInfo["DBUSER"]
DBPASSWORD = connectionInfo["DBPASSWORD"]
DBDATABASE = connectionInfo["DBDATABASE"]
MYID = connectionInfo["MYID"]
bot = Bot(ACCESS_TOKEN)
MOVES = {"rock":1,"r":1,"paper":2,"p":2,"scissors":3,"s":3}
MOVENAMES = {1:"ROCK",2:"PAPER",3:"SCISSORS"}

@app.route("/", methods=['GET','POST'])
def receive_message():
	if request.method == 'GET':
		token_sent = request.args.get("hub.verify_token")
		return verify_fb_token(token_sent)
	else:
		output = request.get_json()
		for event in output['entry']:
			messaging = event['messaging']
			for message in messaging:
				if message.get('message'):
					try:
						process_message(message['sender']['id'],message['message']['text']).execute()
						#message_dump(message['sender']['id'],message['message']['text']).execute()
					except:
						return "Message Error"
	return "Message Processed"

def message_dump(pid,text):
	results = Results()
	results.addMessage(MYID,"Message dumped - sender: " + pid + " - message: " + text)
	return results

def process_message(pid, text):
	commands = {"rules":process_rps,"start game":process_rps,"rock":process_rps,"r":process_rps,"paper":process_rps,"p":process_rps,"scissors":process_rps,"s":process_rps,"quit":process_rps}
	data = Data(pid)
	if not data.playerExists():
		return process_new(pid,text,data)
	if not data.playerNamed():
		return process_name(pid,text,data)
	if text.lower() in commands:
		return commands[text](pid,text,data)
	return process_notUnderstood(pid,text,data)

def process_new(pid,text,data):
	results = Results()
	results.addChange("INSERT INTO Players (pid) VALUES ('" + pid + "');")
	results.addMessage(pid,"Welcome to AndrewBot!\nWhat would you like your username to be?")
	return results

def process_name(pid,text,data):
	results = Results()
	results.addChange("UPDATE Players SET username = '" + text + "' WHERE pid = '" + pid + "';")
	results.addMessage(pid,"Welcome, " + text + "!")
	return results

def process_notUnderstood(pid,text,data):
	results = Results()
	results.addMessage(pid,"I don't understand!")
	return results

def process_rps_rules(pid,text,data):
	results = Results()
	results.addMessage(pid,"To start a game of rock-paper-scissors, say START GAME\nIf no opponents are waiting, I will ask you to wait, then inform you when an opponent is found.\nWhen an opponent is found, I will prompt you for your move. Valid moves are:\nROCK, R\nPAPER, P\nSCISSORS, S\nOnce both players enter their moves, I will inform both players of the results.\nHave fun!")
	return results

def process_rps_play(pid,text,data):
	results = Results()
	currentGame = data.getGame()
	position = currentGame.getPosition(pid)
	player = data.getPlayer()
	opponent = data.getOpp()
	if text == "quit":
		results.addChange("DELETE FROM Games WHERE " + position + "id = '" + pid + "';")
		results.addMessage(pid,"Game quit!")
		if data.hasOpp():
			results.addMessage(opponent.id(),player.username() + " has quit the game!")
		return results
	if currentGame.isWaiting(pid) or not currentGame.canMove(pid):
		results.addMessage(pid,"Still waiting...")
		return results
	if text in MOVES and currentGame.canMove(pid):
		over = currentGame.move(pid,text)
		if not over:
			results.addChange("UPDATE Games SET " + position + "move = " + MOVES[text] + " WHERE " + position + "id = '" + pid + "';")
			results.addMessage(pid,"You chose " + MOVENAMES[MOVES[text]] + "! Waiting on your opponent...")
			return results
		results.addChange("DELETE FROM Games WHERE " + position + "id = '" + pid + "';")
		if over == 1:
			results.addMessage(pid,"You win!")
			results.addMessage(opponent.pid(),"You lose!")
			return results
		if over == 2:
			results.addMessage(pid,"You lose!")
			results.addMessage(opponent.pid(),"You win!")
			return results
		results.addMessage(pid,"Draw!")
		results.addMessage(opponent.pid(),"Draw!")
		return results
	results.addMessage(pid,"I don't understand! Valid moves are:\nROCK, R\nPAPER, P\nSCISSORS, S")
	return results

def process_rps_new(pid,text,data):
	results = Results()
	if data.isWaiting():
		opp = data.getOpp()
		player = data.getPlayer()
		results.addChange("UPDATE Games SET p2id = '" + pid + "' WHERE p1id = '" + opp.id() + "';")
		results.addMessage(pid,"Game found! Your opponent is: " + opp.username() + "\nMake your move.")
		results.addMessage(opp.id(),"Opponent found!\nYour opponent is: " + player.username() +"\nMake your move.")
		return results
	results.addChange("INSERT INTO Games (p1id) VALUES ('" + pid + "');")
	results.addMessage(pid,"Game started! Waiting for opponent...")
	return results

def process_rps(pid,text,data):
	text = text.lower()
	if data.inGame():
		return process_rps_play(pid,text,data)
	if text == "start game":
		return process_rps_new(pid,text,data)
	if text == "rules":
		return process_rps_rules(pid,text,data)
	return process_notUnderstood(pid,text,data)

class Data:
	def __init__(self,pid):
		dbconnection = dbConnect()
		dbcursor = dbconnection.cursor()
		dbcursor.execute("SELECT pid, username FROM Players WHERE pid = '" + pid + "' LIMIT 1;")
		dbplayer = dbcursor.fetchall()
		if not dbplayer:
			self.player = None
			self.opp = None
			self.game = None
			self.waiting = None
		else:
			self.player = Player(dbplayer[0][0],dbplayer[0][1])
			dbcursor.execute("SELECT p1id, p2id, p1move, p2move FROM Games WHERE p1id = '" + pid + "' OR p2id = '" + pid + "' LIMIT 1;")
			dbgame = dbcursor.fetchall()
			if not dbgame:
				self.game = None
				dbcursor.execute("SELECT p1id, p2id, p1move, p2move FROM Games WHERE p2id = '0' ORDER BY created ASC LIMIT 1;")
				dbwaiting = dbcursor.fetchall()
				if not dbwaiting:
					self.waiting = None
					self.opp = None
				else:
					self.waiting = Game(dbwaiting[0][0],dbwaiting[0][1],dbwaiting[0][2],dbwaiting[0][3])
					dbcursor.execute("SELECT pid, username FROM Players WHERE pid = '" + self.waiting.getp1() + "' LIMIT 1;")
					dbopp = dbcursor.fetchall()
					self.opp = Player(dbopp[0][0],dbopp[0][1])
			else:
				self.game = Game(dbgame[0][0],dbgame[0][1],dbgame[0][2],dbgame[0][3])
				self.waiting = None
				dbcursor.execute("SELECT pid, username FROM Players WHERE pid = '" + self.game.getOpponent(pid) + "' LIMIT 1;")
				dbopp = dbcursor.fetchall()
				if not dbopp:
					self.opp = None
				else:
					self.opp = Player(dbopp[0][0],dbopp[0][1])
		dbcursor.close()
		dbconnection.close()
	def getPlayer(self):
		return self.player
	def getOpp(self):
		return self.opp
	def getGame(self):
		return self.game
	def getWaiting(self):
		return self.waiting
	def playerExists(self):
		return self.player != None
	def playerNamed(self):
		return self.player.isNamed()
	def inGame(self):
		return self.game != None
	def hasOpp(self):
		return self.opp != None
	def isWaiting(self):
		return self.waiting != None

class Results:
	def __init__(self):
		self.changes = Changes()
		self.messages = Messages()
	def addChange(self,change):
		self.changes.addChange(change)
	def addMessage(self,recipient,text):
		self.messages.addMessage(recipient,text)
	def execute(self):
		self.changes.execute()
		self.messages.execute()

class Changes:
	def __init__(self):
		self.changes = []
	def addChange(self,change):
		self.changes.append(change)
	def execute(self):
		dbconnection = dbConnect()
		dbcursor = dbconnection.cursor()
		for change in self.changes:
			dbcursor.execute(change)
		dbconnection.commit()
		dbcursor.close()
		dbconnection.close()

class Messages:
	def __init__(self):
		self.messages = []
	def addMessage(self,recipient,text):
		self.messages.append(Message(recipient,text))
	def execute(self):
		for message in self.messages:
			message.send()

class Message:
	def __init__(self,recipient,text):
		self.recipient = recipient
		self.text = text
	def send(self):
		bot.send_text_message(self.recipient, self.text)

class Player:
	def __init__(self,pid,username):
		self.pid = pid
		self.username = username
	def pid(self):
		return self.pid
	def username(self):
		return username
	def isNamed(self):
		return self.username != None

class Game:
	def __init__(self, p1id, p2id="", p1move=0, p2move=0):
		self.p1id = p1id
		self.p2id = p2id
		self.p1move = p1move
		self.p2move = p2move
	def save(self):
		return (str(self.p1id) + "," + str(self.p2id) + "," + str(self.p1move) + "," + str(self.p2move))
	def getp1(self):
		return self.p1id
	def getp2(self):
		return self.p2id
	def getOwnMove(self,pid):
		if self.p1id == pid:
			return self.p1move
		return self.p2move
	def getOppMove(self,pid):
		if self.p1id == pid:
			return self.p2move
		return self.p1move
	def addp2(self, p2id):
		self.p2id = p2id
		return 1
	def isWaiting(self,pid):
		return pid == self.p1id and self.p2id == ""
	def canMove(self,p):
		if self.p1id == p and self.p1move == 0:
			return 1
		if self.p2id == p and self.p2move == 0:
			return 1
		return 0
	def getPlayer(self,pid):
		if self.p1id == pid:
			return 1
		return 2
	def getOpponent(self,pid):
		if self.p1id == pid:
			if self.p2id != None:
				return self.p2id
			return ""
		return self.p1id
	def move(self,pid,move):
		if self.p1id == pid:
			self.p1move = MOVES[move.lower()]
		elif self.p2id == pid:
			self.p2move = MOVES[move.lower()]
		if self.p1move != 0 and self.p2move != 0:
			if self.p1move == self.p2move:
				return 3
			if (self.p1move == 1 and self.p2move == 3) or (self.p1move == 2 and self.p2move == 1) or (self.p1move == 3 and self.p2move == 2):
				if self.p1id == pid:
					return 1
				return 2
			if self.p1id == pid:
				return 2
			return 1
		return 0
	def getPosition(self,pid):
		if self.p1id == pid:
			return "p1"
		return "p2"

def readConnInfo(file):
	f = open(file,"r")
	contents = f.read()
	f.close()
	lines = contents.splitlines()
	info = {}
	for i in range(0,len(lines),2):
		info[lines[i]] = lines[i+1]
	return info

def dbConnect():
	db = mysql.connector.connect(
		host=DBHOST,
		user=DBUSER,
		password=DBPASSWORD,
		database=DBDATABASE
	)
	return db

def verify_fb_token(token_sent):
	if token_sent == VERIFY_TOKEN:
		return request.args.get("hub.challenge")
	return 'Invalid verification token'

if __name__ == '__main__':
	print(readConnInfo("andrewbotdata.txt"))
	app.run()