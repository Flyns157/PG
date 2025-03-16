# pg.auth.py
import sqlite3
import getpass

from .utils.visual import clear_screen, display_supported_algorithms
from .utils.security import hash_password, generate_key

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