import asyncio
import tweepy
from telegram.constants import ParseMode
from loguru import logger
import requests
import datetime
import math
from types import SimpleNamespace

from collections.abc import Iterable
import types
from typing import Any, Dict

class TweetBot():
    def __init__(self, myBot, tweet_queue, bearer_token, chatid, db_manager, new_usernames):
        self.bot = myBot
        self.tweet_queue = tweet_queue
        self.bearer_token = bearer_token
        self.chatid = chatid
        self.db_manager = db_manager
        self.tweets = None
        self.client = tweepy.Client(bearer_token)
        # Constants
        self.total_users = len(new_usernames)
        self.usernames = new_usernames
        self.average_users_per_request = 23
        self.monthly_cap = 10000
        self.monthly_tweets_cap = 10000
        self.calculate_initial_fetch_frequency()
        self.current_request_count = self.db_manager.get_current_request_count()

    def update_twitter_usernames(self, new_usernames):
        self.usernames = new_usernames
        self.total_users = len(new_usernames)


    def check_user_for_updates(self, user):
        if user and 'most_recent_tweet_id' in user:
            # Fetch the latest tweet ID from the API response
            most_recent_tweet_id = user['most_recent_tweet_id']

            # Get user details from the database
            db_user = self.db_manager.get_user(user.id)

            # Check if the user is new or the tweet ID is updated
            if not db_user or db_user[2] != most_recent_tweet_id:
                if most_recent_tweet_id not in self.tweets:
                    self.tweets.append(most_recent_tweet_id)
        else:
            logger.debug("No data found for the user.")
            return None

    async def process_tweets(self, tweet_queue):
        while True:
            tweet = await tweet_queue.get()

            try:
                logger.debug(f'processing {tweet}')
                tb = self

                d = tweet

                user = self.db_manager.get_user(d.author_id)

                if not user:
                    self.db_manager.add_user(d.author_id, d.username, 0)
                    user = d.username

                logger.debug(user)
                twitter_user = user[1]

                if not twitter_user:
                    continue

                has_media = True

                if d.attachments is None:
                    has_media = False

                reply = 'None'

                if hasattr(d, 'in_reply_to_user_id'):
                    reply = d.in_reply_to_user_id
                elif hasattr(d.data, 'in_reply_to_user_id'):
                    reply = d.data.in_reply_to_user_id

                tweet_id = d.id
                tweet_user_link = "https://twitter.com/" + twitter_user
                tweet_link = "https://twitter.com/" + twitter_user + "/status/" + str(tweet_id)
                logger.debug(tweet_link)

                tg_text = d.text

                if (str(reply) == 'None'):
                    if ('RT @' not in tg_text):
                        if has_media:
                            await tb.bot.sendMessage(chat_id=self.chatid,
                                                     text="Tweet by:" + twitter_user + "\n\n" + tg_text + "\n\n" + "Like and Retweet" + ":\n" + tweet_link,
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

    def query_new_tweets(self, usernames):
        #change to your needs
        base_query_terms = 'MATCHSOMETHING OR SOMETHINGELSE'

        max_query_length = 512

        # Function to generate queries
        def generate_queries():
            queries = []
            current_query_usernames = []
            current_query_length = len(base_query_terms) + 5  # initial length with allowances for syntax

            counter1 = 0

            for username in usernames:
                addition = f' OR from:{username}'
                if current_query_length + len(addition) > max_query_length:
                    counter1 = 0
                    # Build the query with the current list and reset for the next batch
                    queries.append(f"({base_query_terms}) ({' OR '.join(current_query_usernames)})")
                    current_query_usernames = [f'from:{username}']
                    current_query_length = len(base_query_terms) + 5 + len(addition)
                else:
                    counter1 += 1
                    current_query_usernames.append(f'from:{username}')
                    current_query_length += len(addition)

            # Add the last batch if any usernames remain
            if current_query_usernames:
                queries.append(f"({base_query_terms}) ({' OR '.join(current_query_usernames)})")
            return queries

        # Execute searches for each generated query
        for query in generate_queries():
            try:
                since_id = self.db_manager.get_most_recent_tweet_id()
                response = self.client.search_recent_tweets(query=query, since_id=since_id,
                                                            tweet_fields=['author_id', 'created_at', 'lang', 'geo'],
                                                            user_fields=['id', 'name', 'username', 'url',
                                                                         'public_metrics'],
                                                            expansions=['author_id', 'attachments.media_keys'],
                                                            max_results=100)
            except Exception as e:
                logger.error(f"search_recent_tweets {type(e).__name__}, {str(e)}, {str(e.args)}")
                pass

            try:
                if response and response.data:
                    for tweet, user in zip(response.data, response.includes['users']):
                        tweet_info = SimpleNamespace(
                            id=tweet.id,
                            data=tweet,
                            created_at=tweet.created_at,
                            author_id=tweet.author_id,
                            text=tweet.text,
                            source=tweet.source,
                            attachments=tweet.attachments,
                            name=user.name,
                            username=user.username,
                            location=user.location,
                            verified=user.verified,
                            description=user.description
                        )
                        self.current_request_count += 1

                        self.db_manager.add_user(tweet_info.author_id, tweet_info.username, tweet_info.id)

                        self.db_manager.save_current_request_count(self.current_request_count)
                        self.tweet_queue.put_nowait(tweet_info)
                else:
                    logger.debug(f"got empty response {response}")

            except Exception as e:
                logger.error(f"search_recent_tweets got {type(e).__name__}, {str(e)}, {str(e.args)}")
                pass

    def split_into_chunks(self, list_to_split, chunk_size=100):
        """Split a list into smaller lists of up to chunk_size elements."""
        for i in range(0, len(list_to_split), chunk_size):
            yield list_to_split[i:i + chunk_size]

    def calculate_initial_fetch_frequency(self):
        total_requests_needed = self.total_users / self.average_users_per_request
        updates_frequency = self.monthly_cap / total_requests_needed
        self.updates_per_day = updates_frequency / 30  # Assuming an average month length
        self.sleep_time_between_fetches = (24 * 60 * 60) / self.updates_per_day  # in seconds

    def get_tweets_usage(self):
        url = "https://api.twitter.com/2/usage/tweets"
        headers = {"Authorization": f"Bearer {self.bearer_token}", "User-Agent": "v2TweetUsagePython"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error: {response.status_code}, {response.text}")
            return None

    def adjust_fetch_frequency_based_on_usage(self):
        usage_info = self.get_tweets_usage()
        if usage_info:
            current_tweets_matched = int(usage_info['data']['project_usage'])
            cap_reset_day = int(usage_info['data']['cap_reset_day'])

            # Calculate the number of days until the cap is reset
            today = datetime.date.today()
            current_month = today.month
            current_year = today.year
            # Determine the next reset date
            if today.day > cap_reset_day:
                # The next reset day is in the next month
                if current_month == 12:  # December, so roll over to January next year
                    next_reset_date = datetime.date(current_year + 1, 1, cap_reset_day)
                else:
                    next_reset_date = datetime.date(current_year, current_month + 1, cap_reset_day)
            else:
                # The next reset day is in the current month
                next_reset_date = datetime.date(current_year, current_month, cap_reset_day)

            if current_tweets_matched == 0 and cap_reset_day == today.day and self.current_request_count > 100:
                self.current_request_count = 0
                self.db_manager.save_current_request_count(self.current_request_count)

            remaining_days_until_reset = (next_reset_date - today).days

            remaining_requests = self.monthly_cap - self.current_request_count
            remaining_tweets_cap = self.monthly_tweets_cap - current_tweets_matched

            # Calculate adjustments based on the more restrictive limit
            if remaining_requests < remaining_tweets_cap:
                self.sleep_time_between_fetches = (remaining_days_until_reset * 24 * 60 * 60) / remaining_requests
            else:
                # Adjust based on tweets matched if it's the limiting factor
                estimated_requests_needed_for_remaining_tweets = math.ceil(
                    remaining_tweets_cap / self.average_users_per_request)
                self.sleep_time_between_fetches = (
                                                          remaining_days_until_reset * 24 * 60 * 60) / estimated_requests_needed_for_remaining_tweets


    def fetch_users_and_tweets(self):
        # logger.debug(f"self.usernames {len(self.usernames)}")
        if self.usernames is None or not len(self.usernames):
            return

        self.adjust_fetch_frequency_based_on_usage()

        self.query_new_tweets(self.usernames)
        return self.sleep_time_between_fetches
