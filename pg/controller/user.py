# pg.controller.user.py
import getpass
from sqlmodel import Session

from ..utils.visual import clear_screen
from ..utils.security import supported_algorithms

from ..data.database import engine
from ..data.models import User

from .home import home


def create_user():
    clear_screen()
    try:
        with Session(engine) as session:
            user = User.create(
                session=session,
                username=input("Nom d'utilisateur: "),
                password=getpass.getpass("Mot de passe: "),
                hash_algorithm=input(f"\nAlgorithme de hashage à utiliser\n-> {', '.join(supported_algorithms())}\n(optionnel): ") or "sha256"
            )
            # clear_screen()
            # print(f"Utilisateur {user.username} créé avec succès!")
            home(user)
    except Exception as e:
        clear_screen()
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass