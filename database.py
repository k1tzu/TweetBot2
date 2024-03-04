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
                    most_recent_tweet_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Table for storing current request count
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_count (
                    id INTEGER PRIMARY KEY,
                    count INTEGER NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Initialize the request count row if not exists
            cursor.execute("""
                INSERT INTO request_count (id, count) VALUES (1, 0)
                ON CONFLICT(id) DO NOTHING;
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

    def save_current_request_count(self, count):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE request_count SET count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1;
            """, (count,))
            conn.commit()

    def get_current_request_count(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT count FROM request_count WHERE id = 1;
            """)
            row = cursor.fetchone()
            if row:
                return row[0]
            return 0

    def get_most_recent_tweet_id(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(most_recent_tweet_id)
                FROM twitter_users;
            """)
            result = cursor.fetchone()
            if result and result[0]:
                return result[0]
            else:
                # Handle the case where there are no records or most_recent_tweet_id values are NULL
                return None

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
