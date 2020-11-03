# AndrewBot

Author: Andrew Mitchell

This is a little personal experiment at creating a Facebook messenger chatbot.

When running, it makes use of an AWS Amazon RDS MySQL database to store players and ongoing games.

The chatbot allows users to participate in asynchronous games of rock-paper-scissors with strangers.
Upon first messaging the chatbot, a user will be asked for a username. 
Once a user has created a username, they can ask about the rules, or request to play a game.
If they request a game and there is a game currently waiting for a player, that game will be joined.
If there isn't a game currently waiting for a second player, one will be created.
Once a waiting game finds a second player, both players will be notified of the other player's username, and prompted for a move (rock, paper, or scissors).
Once both players have input a move, both will be notified of the result, and the game will end.
