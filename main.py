import asyncio
from asyncio import Queue
from telegram import Bot
from telegram.ext import Updater
from urllib3.exceptions import ProtocolError
import os
import tweet_scrape as ts
from dotenv import load_dotenv

load_dotenv("keys.env")
token = str(os.getenv("TELEGRAM_BOT"))
twitter_user = str(os.getenv("TWITTER_USER"))
chatid = int(os.getenv("CHAT_ID"))
bearer_token = str(os.getenv("BEARER_TOKEN"))
API_TOKEN = str(os.getenv("TELEGRAM_BOT"))
myBot = Bot(API_TOKEN)

class LimitedQueue(asyncio.Queue):
    def put_nowait(self, item):
        if self.full():
            self.get_nowait()
        super().put_nowait(item)

async def main():
    tweet_queue = LimitedQueue(maxsize=100)

    twitter_stream = ts.TweetBot(myBot, tweet_queue, twitter_user, bearer_token, chatid)

    asyncio.create_task(twitter_stream.process_tweets(tweet_queue))

    async with Updater(myBot, Queue()):
        while True:
            try:
                await loop.run_in_executor(None, twitter_stream.fetch_tweets)
                await asyncio.sleep(60)
            except ProtocolError:
                continue

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())