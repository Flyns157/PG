# pg.services.password.py
import sqlite3

from ..utils.visual import clear_screen
from ..utils.security import decrypt_password


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
        print(f"\nSite: {site}\nIdentifiant: {site_key}\nMot de passe: {password}\nE-mail: {email or 'Non spécifié'}\nTéléphone: {phone or 'Non spécifié'}\nDate d'ajout: {date}")
