# STONKS (Stock Trading Over News Knowledge Sources)
The goal for this project is to determine if a news article can be used when making a buy or sell decision for day traders. To keep things simple we've focused our data collection on bio firms. Effectively, what we're making is our own text classification tool. 

# Imports
Contians a lit of commands to be run in the terminal to import all of the necessary packages (setup.py coming later?)

# RSSconsumer
A script that runs continuously. It will poll the selected RSS feeds every 30 seconds. This will record a link to the article, and the time it was published. The key to getting the article from the database is just a hash of the link.

# Post-Processing
A script that handles collecting the price at publish time, the high price, the time when it hits the high price, as well as an array of the article's text.
