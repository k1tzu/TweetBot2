import asyncio
from asyncio import Queue
from telegram import Bot
from telegram.ext import Updater
from urllib3.exceptions import ProtocolError
import os
import tweet_scrape as ts
from dotenv import load_dotenv
from database import DatabaseManager
from get_google_sheet import GoogleSheets
from loguru import logger

load_dotenv("keys.env")
token = str(os.getenv("TELEGRAM_BOT"))
chatid = int(os.getenv("CHAT_ID"))
bearer_token = str(os.getenv("BEARER_TOKEN"))
google_sheets_key = str(os.getenv("GOOGLE_SHEETS_KEY"))

myBot = Bot(token)

class LimitedQueue(asyncio.Queue):
    def put_nowait(self, item):
        if self.full():
            self.get_nowait()
        super().put_nowait(item)

async def update_usernames_periodically(tweet_bot, interval_seconds=3600):
    google_sheets = GoogleSheets(google_sheets_key)
    while True:
        try:
            new_usernames = await loop.run_in_executor(None, google_sheets.get_usernames)
            tweet_bot.update_twitter_usernames(new_usernames)
            await asyncio.sleep(interval_seconds)
        except ProtocolError:
            continue

async def main():
    tweet_queue = LimitedQueue(maxsize=100)
    db_manager = DatabaseManager('x.db')

    twitter_stream = ts.TweetBot(myBot, tweet_queue, bearer_token, chatid, db_manager)
    google_sheets = GoogleSheets(google_sheets_key)
    new_usernames = await loop.run_in_executor(None, google_sheets.get_usernames)
    if not new_usernames or not len(new_usernames):
        logger.error("No usernames provided")
        raise SystemExit(0)

    twitter_stream.update_twitter_usernames(new_usernames)

    asyncio.create_task(twitter_stream.process_tweets(tweet_queue))

    # Start the periodic update of usernames
    asyncio.create_task(update_usernames_periodically(twitter_stream))

    async with Updater(myBot, Queue()):
        while True:
            try:
                await loop.run_in_executor(None, twitter_stream.fetch_tweets)
                await asyncio.sleep(5*60)
            except ProtocolError:
                continue

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())