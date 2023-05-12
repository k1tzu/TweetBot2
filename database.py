import sqlite3
from loguru import logger

DEBUG = False

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        if DEBUG:
            logger.debug("Initializing database manager")
        self.initialize_db()

    def initialize_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twitter_users (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    most_recent_tweet_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def add_user(self, user_id, user_name, most_recent_tweet_id=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO twitter_users (user_id, user_name, most_recent_tweet_id)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                user_name = excluded.user_name,
                most_recent_tweet_id = excluded.most_recent_tweet_id;
            """, (user_id, user_name, most_recent_tweet_id))
            conn.commit()

    def update_most_recent_tweet_id(self, user_id, most_recent_tweet_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE twitter_users
                SET most_recent_tweet_id = ?
                WHERE user_id = ?;
            """, (most_recent_tweet_id, user_id))
            conn.commit()

    def get_user(self, identifier):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if str(identifier).isdigit():
                cursor.execute("SELECT user_id, user_name, most_recent_tweet_id FROM twitter_users WHERE user_id = ?;", (identifier,))
            else:
                cursor.execute("SELECT user_id, user_name, most_recent_tweet_id FROM twitter_users WHERE user_name = ?;", (identifier,))
            return cursor.fetchone()

    def get_all_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, user_name, most_recent_tweet_id FROM twitter_users;")
            return cursor.fetchall()

    def remove_user(self, identifier):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if str(identifier).isdigit():
                cursor.execute("DELETE FROM twitter_users WHERE user_id = ?;", (identifier,))
            else:
                cursor.execute("DELETE FROM twitter_users WHERE user_name = ?;", (identifier,))
            conn.commit()

    def get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)  # Adjust timeout as needed
