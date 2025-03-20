# pg.services.password.py
from typing_extensions import deprecated

from ..utils.visual import clear_screen
from ..utils.search_engine import similar_passwords

from ..data.database import engine
from ..data.models import User

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
