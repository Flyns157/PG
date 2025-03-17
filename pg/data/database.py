# pg.data.database.py
import sqlite3

def create_database():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL,
                        encryption_key TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS passwords (
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


from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet

# Génération d'une clé de chiffrement (à stocker en sécurité !)
KEY = Fernet.generate_key()
cipher = Fernet(KEY)

# Création de la base de données
from .models import Base, PasswordORM

def get_database_session():
    engine = create_engine('sqlite:///password_manager.db')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def save_password(username: str, service: str, password: str):
    with get_database_session() as session:
        encrypted_password = cipher.encrypt(password.encode()).decode()
        new_entry = PasswordORM(
            username=username,
            service=service,
            password_encrypted=encrypted_password
        )
        session.add(new_entry)
        session.commit()

def retrieve_passwords(username: str):
    session = get_database_session()
    passwords = session.query(PasswordORM).filter_by(username=username).all()
    session.close()
    return [
        {
            'service': pwd.service,
            'password': cipher.decrypt(pwd.password_encrypted.encode()).decode(),
            'date_added': pwd.date_added,
            'date_updated': pwd.date_updated
        }
        for pwd in passwords
    ]

def modify_password(username: str, service: str, new_password: str):
    session = get_database_session()
    password_entry = session.query(PasswordORM).filter_by(username=username, service=service).first()
    if password_entry:
        password_entry.password_encrypted = cipher.encrypt(new_password.encode()).decode()
        password_entry.date_updated = datetime.now()
        session.commit()
    session.close()

