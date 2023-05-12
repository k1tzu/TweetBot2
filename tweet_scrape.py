import asyncio
import tweepy as tp
from telegram.constants import ParseMode
import json

class TwitterStream(tp.StreamingClient):
    def __init__(self, tweetBot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tweetBot = tweetBot

    def on_data(self, data):
        self.tweetBot.tweet_queue.put_nowait(data)
        self.disconnect()
        return True

    # def on_error(self, status):
    #     print('status', status.text)

    def on_error(self, status_code):
        if status_code == 420:
            return False

    # def on_status(self, status):
        # print("status", status)  # prints every tweet received


class TweetBot():
    def __init__(self, myBot,  tweet_queue, twitter_user, bearer_token, chatid):
        self.bot = myBot
        self.tweet_queue = tweet_queue
        self.twitter_user = twitter_user
        self.bearer_token = bearer_token
        self.chatid = chatid
        pass

    def get_twitter_user(self, json_data):
        try:
            twitter_user = json_data['users'][0]['username']
            return twitter_user
        except:
            return False

    async def process_tweets(self, tweet_queue):
        while True:
            tweet = await tweet_queue.get()
            try:
                tb = self

                d = json.loads(tweet)

                if 'data' not in d:
                    continue

                twitter_user = tb.get_twitter_user(json_data=d['includes'])

                if not twitter_user:
                    continue

                has_media = tb.tweet_has_media(json_data=d['includes'])

                reply = 'None'

                if 'in_reply_to_screen_name' in d['data']:
                    reply = d['data']['in_reply_to_screen_name']

                tweet_id = d['data']['id']
                tweet_link = "https://twitter.com/" + twitter_user + "/status/" + tweet_id

                if 'extended_tweet' in d['data']:
                    tg_text = d['data']['extended_tweet']['full_text']
                else:
                    tg_text = d['data']['text']

                if (str(reply) == 'None'):
                    if ('RT @' not in tg_text):
                        if has_media:
                            await tb.bot.sendMessage(chat_id=self.chatid,
                                                     text=tg_text + "\n\n" + "Via" + "|" + "<a href='" + tweet_link + "'>" + twitter_user + "</a>" + "|",
                                                     read_timeout=200,
                                                     write_timeout=200,
                                                     connect_timeout=200,
                                                     pool_timeout=300,
                                                     disable_web_page_preview=False, parse_mode=ParseMode.HTML)
                        else:
                            await tb.bot.sendMessage(chat_id=self.chatid,
                                                     text=tg_text + "\n\n" + "Via" + "|" + "<a href='" + tweet_link + "'>" + twitter_user + "</a>" + "|",
                                                     read_timeout=200,
                                                     write_timeout=200,
                                                     connect_timeout=200,
                                                     pool_timeout=300,
                                                     disable_web_page_preview=True, parse_mode=ParseMode.HTML)
                    else:
                        print("It's a retweet so not posting it")
                else:
                    print("It's a reply so not posting that")
            except Exception as e:
                print('error', e)
        await asyncio.sleep(3)

    def check_rules(self, client) -> None:
        if client.get_rules()[3]['result_count'] != 0:
            n_rules = client.get_rules()[0]
            ids = [n_rules[i_tuple[0]][2] for i_tuple in enumerate(n_rules)]
            client.delete_rules(ids)
            client.add_rules(tp.StreamRule("from:" + self.twitter_user))
        else:
            client.add_rules(tp.StreamRule("from:" + self.twitter_user))

    def fetch_tweets(self):

        stream_tweet = TwitterStream(self, self.bearer_token, wait_on_rate_limit=True)
        self.check_rules(stream_tweet)
        stream_tweet.filter(expansions=['author_id', 'in_reply_to_user_id', 'attachments.media_keys'])

    def get_tweet_url(self, json_data):
        tweet_url = ''
        try:
            if 'urls' not in json_data['entities']:
                return tweet_url
            for url in json_data['entities']['urls']:
                if not 'https://twitter.com' in url['expanded_url']:
                    tweet_url = tweet_url + "\n" + str(url['expanded_url'])
        except:
            tweet_url = ''
        return tweet_url

    def tweet_has_media(self, json_data):
        try:
            if len(json_data['media']):
                return True
        except:
            return False
        return False
