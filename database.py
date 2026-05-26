import sqlite3
from datetime import datetime
import os

class Database:
    def __init__(self, db_name="bot_state.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instagram_user_id TEXT UNIQUE,
                username TEXT,
                full_name TEXT,
                niche TEXT,
                status TEXT DEFAULT 'discovered',
                last_interaction TIMESTAMP,
                thread_id TEXT,
                bio TEXT,
                ai_generated_message TEXT
            )
        ''')
        self.conn.commit()

    def add_user(self, instagram_user_id, username, full_name, niche, bio=""):
        try:
            self.cursor.execute('''
                INSERT INTO users (instagram_user_id, username, full_name, niche, last_interaction, bio)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (instagram_user_id, username, full_name, niche, datetime.now(), bio))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user_status(self, instagram_user_id, status, thread_id=None, ai_generated_message=None):
        query = 'UPDATE users SET status = ?, last_interaction = ?'
        params = [status, datetime.now()]
        
        if thread_id:
            query += ', thread_id = ?'
            params.append(thread_id)
            
        if ai_generated_message:
            query += ', ai_generated_message = ?'
            params.append(ai_generated_message)
            
        query += ' WHERE instagram_user_id = ?'
        params.append(instagram_user_id)
        
        self.cursor.execute(query, params)
        self.conn.commit()

    def get_user_status(self, instagram_user_id):
        self.cursor.execute('SELECT status FROM users WHERE instagram_user_id = ?', (instagram_user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
        
    def get_users_by_status(self, status):
        self.cursor.execute('SELECT * FROM users WHERE status = ?', (status,))
        return self.cursor.fetchall()
