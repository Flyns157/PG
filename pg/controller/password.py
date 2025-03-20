# pg.controller.password.py
import getpass

from ..utils.visual import clear_screen

from sqlmodel import Session
from ..data.database import engine
from ..data.models import Password, User


def create_password(user_id: int):
    clear_screen()
    with Session(engine) as session:
        try:
            User.get_by_id(user_id, session=session)
            Password.create(
                session=session,
                user_id=user_id,
                url=input("Site web: "),
                description=input("Description (optionnel): ") or None,
                key=input("Identifiant du site: "),
                password=getpass.getpass("Mot de passe: "),
                email=input("Adresse e-mail (optionnel): ") or None,
                phone=input("Numéro de téléphone (optionnel): ") or None
            )

            print("Mot de passe enregistré avec succès!")
        except Exception as e:
            print(f"Une erreur est survenue: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass

def view_password(user_id: int):
    clear_screen()
    with Session(engine) as session:
        try:
            User.get_by_id(user_id, session=session)
            password_id = input("ID du mot de passe à récupérer: ")
            password = Password.get_by_id(password_id, session=session)
            print(password)
        except Exception as e:
            print(f"Une erreur est survenue: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass

def list_passwords(user_id: int, filtre=lambda x: x.url):
    clear_screen()
    with Session(engine) as session:
        user = User.get_by_id(user_id, session=session)
        print("Liste des mots de passe enregistrés:")
        for password in sorted(user.passwords, key=filtre):
            print(password)

def edit_password(user_id: int):
    clear_screen()
    with Session(engine) as session:
        try:
            User.get_by_id(user_id, session=session)
            password_id = input("ID du mot de passe à modifier: ")
            password = Password.get_by_id(password_id, session=session)
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

def delete_password(user_id: int):
    clear_screen()
    with Session(engine) as session:
        try:
            User.get_by_id(user_id, session=session)
            password_id = input("ID du mot de passe à supprimer: ")
            password = Password.get_by_id(password_id, session=session)
            password.delete(session=session)
            print("Mot de passe supprimé avec succès!")
        except Exception as e:
            print(f"Une erreur est survenue: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass