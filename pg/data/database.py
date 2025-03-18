# pg.data.database.py
import sqlite3

def create_database():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL,
                        encryption_key TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS password (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        site TEXT NOT NULL,
                        key TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        date_added TEXT DEFAULT CURRENT_TIMESTAMP,
                        date_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )''')
    conn.commit()
    conn.close()


from sqlmodel import create_engine


engine = create_engine('sqlite:///password_manager.db')