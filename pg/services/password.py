# pg.services.password.py
import csv
from pathlib import Path
from datetime import datetime
from sqlmodel import Session
from fuzzywuzzy import process

from ..data.models import User, Password


def import_passwords(user: User, file_path: str | Path, session: Session=None) -> None:
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for record in reader:
            Password.create(
                session=session,
                user_id=user.id,
                url=record["url"],
                description=record["description"] or None,
                key=record["key"],
                password=record["password"],
                email=record["email"] or None,
                phone=record["phone"] or None,
                # Convertion les chaînes de caractères en objets datetime (à cause du format ISO utilisé par le CSV)
                date_added=datetime.fromisoformat(record["date_added"]),
                date_updated=datetime.fromisoformat(record["date_updated"])
            )

def export_passwords(user: User, file_path: str | Path, session: Session) -> None:
    user = User.get_by_id(user.id, session=session)
    
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames={*Password.__fields__.keys(), "password"} - {"id", "user_id", "password_encrypted"})
        writer.writeheader()
        for password in user.passwords:
            password_data: dict = password.model_dump(exclude=("id", "user_id", "password_encrypted"))
            password_data["password"] = password.password
            writer.writerow(password_data)

def similar_passwords(user: User, session: Session, query: str, limit: int=10) -> list[Password]:
    user = User.get_by_id(user.id, session=session)

    # Trouver les correspondances avec leurs scores
    correspondances = process.extract(query=query, choices=[pwd.url for pwd in user.passwords], limit=limit)

    # Trier les objets en fonction des scores
    return sorted(
        user.passwords,
        key=lambda obj: next(score for url, score in correspondances if url == obj.url),
        reverse=True
    )