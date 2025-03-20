# pg.services.password.py
from typing_extensions import deprecated
from pathlib import Path
import csv
from datetime import datetime

from ..utils.visual import clear_screen
from ..utils.search_engine import similar_passwords

from ..data.database import engine
from ..data.models import User, Password

from sqlmodel import Session, select

@deprecated("No longer used, use the new function provided in the password controller")
def search_password(user_id):
    search_term = input("Entrez le site ou l'identifiant à rechercher: ")
    clear_screen()

    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            print("Utilisateur inconnu.")
            return

        nearest_password=similar_passwords(user.passwords, search_term)[0]

    print(f"""\nInformations de connections similaires à la recherche\n\n-> Recherche: "{search_term}"\n""")
    print(nearest_password)

def import_passwords(user: User, file_path: str | Path, session: Session=None) -> None:
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for record in reader:
            Password.create(
                session=session,
                user_id=user.id,
                url=record["url"],
                description=record["description"],
                key=record["key"],
                password=record["password"],
                email=record["email"],
                phone=record["phone"],
                # Convertion les chaînes de caractères en objets datetime (à cause du format ISO utilisé par le CSV)
                date_added=datetime.fromisoformat(record["date_added"]),
                date_updated=datetime.fromisoformat(record["date_updated"])
            )

def export_passwords(user: User, file_path: str | Path, session: Session=None) -> None:
    user = User.get_by_id(user.id, session=session)
    
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames={*Password.__fields__.keys(), "password"} - {"id", "user_id", "password_encrypted"})
        writer.writeheader()
        for password in user.passwords:
            password_data: dict = password.model_dump(exclude=("id", "user_id", "password_encrypted"))
            password_data["password"] = password.password
            writer.writerow(password_data)