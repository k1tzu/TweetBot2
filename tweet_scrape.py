import asyncio
import tweepy
from telegram.constants import ParseMode
from loguru import logger


class TweetBot():
    def __init__(self, myBot, tweet_queue, bearer_token, chatid, db_manager):
        self.bot = myBot
        self.tweet_queue = tweet_queue
        self.bearer_token = bearer_token
        self.chatid = chatid
        self.db_manager = db_manager
        self.usernames = None
        self.tweets = None
        self.client = tweepy.Client(bearer_token)

    def update_twitter_usernames(self, new_usernames):
        self.usernames = new_usernames

    async def process_tweets(self, tweet_queue):
        while True:
            tweet = await tweet_queue.get()

            try:
                logger.debug(f'processing {tweet} attachments {tweet.attachments}')
                tb = self

                d = tweet

                user = self.db_manager.get_user(d.author_id)
                logger.debug(user)
                twitter_user = user[1]

                if not twitter_user:
                    continue

                has_media = True

                if d.attachments is None:
                    has_media = False

                reply = 'None'

                if 'in_reply_to_user_id' in d['data']:
                    reply = d['data']['in_reply_to_user_id']

                tweet_id = d['data']['id']
                tweet_user_link = "https://twitter.com/" + twitter_user
                tweet_link = "https://twitter.com/" + twitter_user + "/status/" + str(tweet_id)
                logger.debug(tweet_link)

                tg_text = d['data']['text']

                if not self.match_text(tg_text):
                    continue

                if (str(reply) == 'None'):
                    if ('RT @' not in tg_text):
                        if has_media:
                            await tb.bot.sendMessage(chat_id=self.chatid,
                                                     text="Tweet by: <a href='" + tweet_user_link + "'>" + twitter_user + "</a>\n\n" + tg_text + "\n\n" + "Like and Retweet" + ":\n" + tweet_link,
                                                     read_timeout=200,
                                                     write_timeout=200,
                                                     connect_timeout=200,
                                                     pool_timeout=300,
                                                     disable_web_page_preview=False, parse_mode=ParseMode.HTML)
                        else:
                            await tb.bot.sendMessage(chat_id=self.chatid,
                                                     text="Tweet by: <a href='" + tweet_user_link + "'>" + twitter_user + "</a>\n\n" + tg_text + "\n\n" + "Like and Retweet" + ":\n" + tweet_link,
                                                     read_timeout=200,
                                                     write_timeout=200,
                                                     connect_timeout=200,
                                                     pool_timeout=300,
                                                     disable_web_page_preview=True, parse_mode=ParseMode.HTML)
                    else:
                        logger.warning("It's a retweet so not posting it")
                else:
                    logger.warning("It's a reply so not posting that")
            except Exception as e:
                logger.error(f"{type(e).__name__}, {str(e)}, {str(e.args)}")
        await asyncio.sleep(3)

    def match_text(self, text):
        if 'some string' in text.casefold():
            return True
        if 'another match' in text.casefold():
            return True
        return False

    def check_user_for_updates(self, user):
        if user and 'most_recent_tweet_id' in user:
            # Fetch the latest tweet ID from the API response
            most_recent_tweet_id = user['most_recent_tweet_id']

            # Get user details from the database
            db_user = self.db_manager.get_user(user.id)

            if not db_user:
                self.db_manager.add_user(user.id, user.username, 0)

            # Check if the user is new or the tweet ID is updated
            if not db_user or db_user[2] != most_recent_tweet_id:
                if most_recent_tweet_id not in self.tweets:
                    self.tweets.append(most_recent_tweet_id)
        else:
            logger.debug("No data found for the user.")
            return None

    def get_new_tweets(self):
        try:
            response = self.client.get_tweets(self.tweets, expansions=['author_id', 'attachments.media_keys'])
        except Exception as e:
            logger.error(f"{type(e).__name__}, {str(e)}, {str(e.args)}")
            return
        if response and response.data:
            for tweet in response.data:
                logger.debug(tweet.data)
                self.db_manager.update_most_recent_tweet_id(tweet.author_id, tweet.id)
                self.tweet_queue.put_nowait(tweet)

    def split_into_chunks(self, list_to_split, chunk_size=100):
        """Split a list into smaller lists of up to chunk_size elements."""
        for i in range(0, len(list_to_split), chunk_size):
            yield list_to_split[i:i + chunk_size]

    def fetch_users_and_tweets(self):
        logger.debug(f"self.usernames {len(self.usernames)}")
        if self.usernames is None or not len(self.usernames):
            return

        # Split usernames into chunks of 100
        username_chunks = list(self.split_into_chunks(self.usernames))

        self.tweets = []

        for chunk in username_chunks:
            try:
                response = self.client.get_users(usernames=chunk,
                                                 user_fields=["id", "username", "most_recent_tweet_id"])

                if not response or not response.data:
                    continue

                for user in response.data:
                    self.check_user_for_updates(user)
            except Exception as e:
                logger.error(f"{type(e).__name__}, {str(e)}, {str(e.args)}")
                continue

        # now we have an array with tweets to fetch
        self.get_new_tweets()
