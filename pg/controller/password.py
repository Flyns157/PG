# pg.controller.password.py
import getpass
from sqlmodel import Session

from ..utils.visual import clear_screen
from ..utils.search_engine import similar_passwords

from ..data.database import engine
from ..data.models import Password, User


def create_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            Password.create(
                session=session,
                user_id=user.id,
                url=input("Site web: "),
                description=input("Description (optionnel): ") or None,
                key=input("Identifiant du site: "),
                password=getpass.getpass("Mot de passe: "),
                email=input("Adresse e-mail (optionnel): ") or None,
                phone=input("Numéro de téléphone (optionnel): ") or None
            )
            clear_screen()
            print("Mot de passe enregistré avec succès!")
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass

def view_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            password_id = input("ID du mot de passe à récupérer: ")
            password = Password.get_by_id(password_id, session=session)
            if password.user_id != user.id:
                clear_screen()
                print(f"Le mot de passe d'ID {password_id} ne vous appartient pas.")
                return
            clear_screen()
            print(password)
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass

def list_passwords(user: User, filtre=lambda x: x.url):
    clear_screen()
    with Session(engine) as session:
        print("Liste des mots de passe enregistrés:")
        for password in sorted(user.passwords, key=filtre):
            print(password)

def edit_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            password_id = input("ID du mot de passe à modifier: ")
            password = Password.get_by_id(password_id, session=session)
            if password.user_id != user.id:
                clear_screen()
                print(f"Le mot de passe d'ID {password_id} ne vous appartient pas.")
                return
            password.update(
                session=session,
                description=input("Nouvelle description (optionnel): ") or None,
                key=input("Nouvelle clé (optionnel): ") or None,
                password=getpass.getpass("Nouveau mot de passe (optionnel): ") or None,
                email=input("Nouvelle adresse e-mail (optionnel): ") or None,
                phone=input("Nouveau numéro de téléphone (optionnel): ") or None
            )
            print("Mot de passe modifié avec succès!")
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass

def delete_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            password_id = input("ID du mot de passe à supprimer: ")
            password = Password.get_by_id(password_id, session=session)
            if password.user_id != user.id:
                print("Ce mot de passe ne vous appartient pas.")
                return
            password.delete(session=session)
            clear_screen()
            print("Mot de passe supprimé avec succès!")
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass

def search_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            search_term = input("Terme de recherche: ")
            nearest_password = similar_passwords(user.passwords, search_term)[0]
            clear_screen()
            print(f"""\nInformations de connections similaires à la recherche\n\n-> Recherche: "{search_term}"\n""")
            print(nearest_password)
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass