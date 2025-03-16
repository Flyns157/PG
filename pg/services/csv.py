# pg.services.csv.py
import csv
import sqlite3

from ..utils.visual import clear_screen
from ..utils.security import encrypt_password, decrypt_password


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


def import_csv(user_id, key):
    file_path = input("Entrez le chemin du fichier CSV à importer: ")
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            conn = sqlite3.connect("password_manager.db")
            cursor = conn.cursor()
            
            for row in reader:
                site = row.get('Site')
                site_key = row.get('Identifiant')
                password = row.get('Mot de passe')
                email = row.get('Email', None)
                phone = row.get('Téléphone', None)

                if site and site_key and password:  # S'assurer que les données essentielles sont présentes
                    encrypted_password = encrypt_password(password, key)
                    cursor.execute("""
                        INSERT INTO passwords (user_id, site, key, password, email, phone) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, site, site_key, encrypted_password, email, phone))
            
            conn.commit()
            conn.close()

            clear_screen()
            print("Importation réussie!")
    except Exception as e:
        clear_screen()
        print(f"Erreur lors de l'importation du fichier CSV: {e}")