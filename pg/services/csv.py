# pg.services.csv.py
import csv

from typing_extensions import deprecated

from ..utils.visual import clear_screen
from ..utils.security import encrypt_password, decrypt_password

from ..data.database import engine
from ..data.models import Password, User

from sqlmodel import Session, select
from datetime import datetime


@deprecated("No longer used, use the new function provided in the password controller")
def export_passwords(user_id):
    clear_screen()

    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            print("Utilisateur inconnu.")
            return
        
        with open("passwords_export.csv", "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames={*Password.__fields__.keys(), "password"} - {"id", "user_id", "password_encrypted"})
            print("Exportation en cours...")
            writer.writeheader()
            for password in user.passwords:
                password_data: dict = password.model_dump(exclude=("id", "user_id"))
                password_data["password"] = decrypt_password(password_data.pop("password_encrypted"), user.encryption_key)
                writer.writerow(password_data)
    
    print("Exportation réussie dans passwords_export.csv")


@deprecated("No longer used, use the new function provided in the password controller")
def import_csv(user_id):
    file_path = input("Entrez le chemin du fichier CSV à importer: ")
    clear_screen()
    
    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            print("Utilisateur inconnu.")
            return
    
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for record in reader:
                    record["password_encrypted"]=encrypt_password(record.pop("password"), user.encryption_key)
                    # Convertir les chaînes de caractères en objets datetime (à cause du format ISO utilisé par le CSV)
                    record["date_added"] = datetime.fromisoformat(record["date_added"])
                    record["date_updated"] = datetime.fromisoformat(record["date_updated"])

                    session.add(Password(**{k:v for k, v in record.items() if v}, user_id=user_id))
                session.commit()

            print("Importation réussie!")
        except Exception as e:
            print(f"Erreur lors de l'importation du fichier CSV: {e}")