import sqlite3
import hashlib
import getpass
import base64
import os
from cryptography.fernet import Fernet

def create_database():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        hash_algorithm TEXT NOT NULL
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
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )''')
    conn.commit()
    conn.close()

def hash_password(password, algorithm="sha256"):
    if algorithm not in hashlib.algorithms_available:
        raise ValueError("Algorithme non supporté")
    hasher = hashlib.new(algorithm)
    hasher.update(password.encode('utf-8'))
    return hasher.hexdigest()

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32))

def get_cipher(key):
    return Fernet(key)

def encrypt_password(password, key):
    cipher = get_cipher(key)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    cipher = get_cipher(key)
    return cipher.decrypt(encrypted_password.encode()).decode()

def register():
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    algorithm = input("Algorithme de hachage (par défaut: sha256): ") or "sha256"
    password_hash = hash_password(password, algorithm)
    
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, hash_algorithm) VALUES (?, ?, ?)",
                       (username, password_hash, algorithm))
        conn.commit()
        print("Utilisateur enregistré avec succès!")
    except sqlite3.IntegrityError:
        print("Ce nom d'utilisateur existe déjà.")
    conn.close()

def login():
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, hash_algorithm FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        print("Utilisateur non trouvé.")
        return None
    user_id, stored_hash, algorithm = user
    if hash_password(password, algorithm) != stored_hash:
        print("Mot de passe incorrect.")
        return None
    print("Connexion réussie!")
    return user_id

def save_password(user_id, key):
    site = input("Site web: ")
    site_key = input("Identifiant du site: ")
    password = getpass.getpass("Mot de passe: ")
    email = input("Adresse e-mail (optionnel): ") or None
    phone = input("Numéro de téléphone (optionnel): ") or None
    
    encrypted_password = encrypt_password(password, key)
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO passwords (user_id, site, key, password, email, phone) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, site, site_key, encrypted_password, email, phone))
    conn.commit()
    conn.close()
    print("Mot de passe enregistré avec succès!")

def retrieve_passwords(user_id, key):
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT site, key, password, email, phone, date_added FROM passwords WHERE user_id = ?", (user_id,))
    entries = cursor.fetchall()
    conn.close()
    
    if not entries:
        print("Aucun mot de passe enregistré.")
        return
    
    for entry in entries:
        site, site_key, encrypted_password, email, phone, date = entry
        password = decrypt_password(encrypted_password, key)
        print(f"\nSite: {site}\nIdentifiant: {site_key}\nMot de passe: {password}\nE-mail: {email}\nTéléphone: {phone}\nDate d'ajout: {date}")

def main():
    create_database()
    while True:
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        if choice == "1":
            register()
        elif choice == "2":
            user_id = login()
            if user_id:
                key = generate_key()
                while True:
                    print("\n1. Enregistrer un mot de passe\n2. Voir mes mots de passe\n3. Déconnexion")
                    sub_choice = input("Choisissez une option: ")
                    if sub_choice == "1":
                        save_password(user_id, key)
                    elif sub_choice == "2":
                        retrieve_passwords(user_id, key)
                    elif sub_choice == "3":
                        break
        elif choice == "3":
            break

if __name__ == "__main__":
    main()
