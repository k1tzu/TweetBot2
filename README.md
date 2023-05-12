
# CHANGES

I've rewritten the code to work with Twitter's v2 API, incorporating asynchronous queues and the latest versions of Tweepy and Python-Telegram-Bot.
Instead of requiring any keys from Twitter, it now only needs a Bearer token.
What it does:
1. takes a list of users from Google Sheets.
2. saves them to local sqlite database
3. checks latest posted Tweet for every user
4. it the tweet was not processed - fetches it and uses filters to process it
5. forward tweet to telegram channel

credentials.json from Google Sheets API is needed

# TweetBot

A simple Telegram Bot to Stream the tweets from any account from twitter to your telegram channel.  

# Guide
1. Get Twitter API Keys and Access Keys from [here](https://developer.twitter.com/en)
2. Ask for Twitter elevated permissions [here](https://developer.twitter.com/en/portal/products/essential), click at Elevated option and fill the forms
3. Go to [@BotFather](https://t.me/botfather) in telegram and create a Bot
4. Open keys_sample.env and fill the API Keys and Access Keys and Chat ID where you want the bot to send messages.
5. Rename `key_sample.env` to `keys.env`
6. Open `userlist.py` and add the usernames of the person's you want to Stream tweets from for Example:- `userslist = ['elonmusk','nasa']`
7. Run the Bot by executing:
```
pip3 install -r requirements.txt
python3 main.py
```
# Heroku usage
Just do all the things given in the Guide except the 6th part and follow the further steps here for Heroku deployment.
1. Create a Heroku APP
2. Git add and commit the files in the project directory and make sure you have the Heroku CLI installed.
```
git add.  -f
git commit -m "Initial Commit"
git push heroku HEAD:master --force
```
3. Then go to the app page in your heroku dashboard and turn on the dynos.
