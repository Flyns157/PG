import sqlite3
import hashlib
import getpass
import base64
import os
import sys
import csv
from cryptography.fernet import Fernet

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

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
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def get_cipher(key):
    return Fernet(key.encode())

def encrypt_password(password, key):
    cipher = get_cipher(key)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    cipher = get_cipher(key)
    return cipher.decrypt(encrypted_password.encode()).decode()

def display_supported_algorithms():
    print("Algorithmes de hachage supportés:")
    for algo in sorted(hashlib.algorithms_available):
        print(f"- {algo}")

def register():
    clear_screen()
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    clear_screen()
    display_supported_algorithms()
    algorithm = input("Algorithme de hachage (par défaut: sha256): ") or "sha256"
    password_hash = hash_password(password, algorithm)
    encryption_key = generate_key()
    
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, hash_algorithm, encryption_key) VALUES (?, ?, ?, ?)",
                       (username, password_hash, algorithm, encryption_key))
        conn.commit()
        print("Utilisateur enregistré avec succès!")
    except sqlite3.IntegrityError:
        print("Ce nom d'utilisateur existe déjà.")
    conn.close()

def login():
    clear_screen()
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, hash_algorithm, encryption_key FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        print("Utilisateur non trouvé.")
        return None, None
    user_id, stored_hash, algorithm, encryption_key = user
    if hash_password(password, algorithm) != stored_hash:
        print("Mot de passe incorrect.")
        return None, None
    clear_screen()
    print("Connexion réussie!")
    return user_id, encryption_key

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
    
    print("\nListe des mots de passe enregistrés:")
    for entry in entries:
        site, site_key, encrypted_password, email, phone, date = entry
        password = decrypt_password(encrypted_password, key)
        print(f"\nSite: {site}\nIdentifiant: {site_key}\nMot de passe: {password}\nE-mail: {email}\nTéléphone: {phone}\nDate d'ajout: {date}")

def search_password(user_id, key):
    search_term = input("Entrez le site ou l'identifiant à rechercher: ")
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT site, key, password, email, phone, date_added FROM passwords WHERE user_id = ? AND (site LIKE ? OR key LIKE ?)",
                   (user_id, f"%{search_term}%", f"%{search_term}%"))
    entries = cursor.fetchall()
    conn.close()
    
    if not entries:
        print("Aucun mot de passe trouvé pour cette recherche.")
        return
    
    clear_screen()
    print(f"""\nListe des informations de connections correspondantes à la recherche\n\n-> Recherche: "{search_term}"\n""")
    for entry in entries:
        site, site_key, encrypted_password, email, phone, date = entry
        password = decrypt_password(encrypted_password, key)
        print(f"\nSite: {site}\nIdentifiant: {site_key}\nMot de passe: {password}\nE-mail: {email}\nTéléphone: {phone}\nDate d'ajout: {date}")

def export_passwords(user_id, key):
    clear_screen()
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT site, key, password, email, phone, date_added FROM passwords WHERE user_id = ?", (user_id,))
    entries = cursor.fetchall()
    conn.close()
    
    if not entries:
        print("Aucun mot de passe enregistré.")
        return
    
    with open("passwords_export.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Site", "Identifiant", "Mot de passe", "Email", "Téléphone", "Date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            site, site_key, encrypted_password, email, phone, date = entry
            password = decrypt_password(encrypted_password, key)
            writer.writerow({"Site": site, "Identifiant": site_key, "Mot de passe": password, "Email": email, "Téléphone": phone, "Date": date})
    print("Exportation réussie dans passwords_export.csv")

def main():
    create_database()
    while True:
        clear_screen()
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        if choice == "1":
            register()
        elif choice == "2":
            user_id, key = login()
            if user_id:
                while True:
                    print("\n1. Enregistrer un mot de passe\n2. Voir mes mots de passe\n3. Rechercher un mot de passe\n4. Exporter mots de passe\n5. Déconnexion")
                    sub_choice = input("Choisissez une option: ")
                    clear_screen()
                    if sub_choice == "1":
                        save_password(user_id, key)
                    elif sub_choice == "2":
                        retrieve_passwords(user_id, key)
                    elif sub_choice == "3":
                        search_password(user_id, key)
                    elif sub_choice == "4":
                        export_passwords(user_id, key)
                    elif sub_choice == "5":
                        break
        elif choice == "3":
            break

if __name__ == "__main__":
    main()
