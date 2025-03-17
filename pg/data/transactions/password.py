# pg.data.transactions.password.py
import getpass
import sqlite3

from ...utils.security import encrypt_password, decrypt_password
from ...utils.visual import clear_screen

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
        print(f"\nSite: {site}\nIdentifiant: {site_key}\nMot de passe: {password}\nE-mail: {email or 'Non spécifié'}\nTéléphone: {phone or 'Non spécifié'}\nDate d'ajout: {date}")

def modify_password(user_id, key):
    clear_screen()
    site = input("Site web à modifier: ")
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, site, key, password, email, phone FROM passwords WHERE user_id = ? AND site = ?", (user_id, site))
    entry = cursor.fetchone()
    if not entry:
        print("Aucun enregistrement trouvé pour ce site.")
        conn.close()
        return
    
    entry_id, _, old_key, encrypted_password, old_email, old_phone = entry
    password = decrypt_password(encrypted_password, key)
    
    print(f"\nIdentifiant actuel: {old_key}\nMot de passe actuel: {password}\nEmail actuel: {old_email}\nTéléphone actuel: {old_phone}")
    
    new_key = input(f"Nouvel identifiant ({old_key} pour conserver): ") or old_key
    new_password = getpass.getpass("Nouveau mot de passe (laisser vide pour conserver): ") or password
    new_email = input(f"Nouvel email ({old_email} pour conserver): ") or old_email
    new_phone = input(f"Nouveau téléphone ({old_phone} pour conserver): ") or old_phone
    
    encrypted_password = encrypt_password(new_password, key)
    cursor.execute("UPDATE passwords SET key = ?, password = ?, email = ?, phone = ?, date_updated = CURRENT_TIMESTAMP WHERE id = ?", (new_key, encrypted_password, new_email, new_phone, entry_id))
    conn.commit()
    conn.close()

    clear_screen()
    print("Informations mises à jour avec succès!")