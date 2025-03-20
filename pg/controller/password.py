# pg.controller.password.py
import csv
import getpass
from sqlmodel import Session, select

from ..utils.visual import clear_screen
from ..utils.search_engine import similar_passwords

from ..data.database import engine
from ..data.models import Password, User

from ..services.password import import_passwords, export_passwords


def create_password(user: User):
    clear_screen()
    try:
        Password.create(
            user_id=user.id,
            url=input("Site web: "),
            description=input("Description (optionnel): ") or None,
            key=input("Identifiant du site: "),
            password=getpass.getpass("Mot de passe: "),
            email=input("Adresse e-mail (optionnel): ") or None,
            phone=input("Numéro de téléphone (optionnel): ") or None
        )
        clear_screen()
        print("Mot de passe enregistré avec succès!", end="\n\n")
    except Exception as e:
        print(f"Une erreur est survenue: {e}", end="\n\n")

def view_password(user: User):
    clear_screen()
    try:
        while not (password_id := input("ID du mot de passe à récupérer: ")).isnumeric():...
        
        password = Password.get_by_id(password_id)
        if password is None:
            clear_screen()
            print(f"Le mot de passe d'ID {password_id} n'existe pas.", end="\n\n")
            return
        if password.user_id != user.id:
            clear_screen()
            print(f"Le mot de passe d'ID {password_id} ne vous appartient pas.", end="\n\n")
            return
        clear_screen()
        print(f">> Mot de passe d'ID {password_id}", end="\n\n")
        print(password, end="\n\n")
    except Exception as e:
        print(f"Une erreur est survenue: {e}", end="\n\n")

def list_passwords(user: User, filtre=lambda x: x.url):
    clear_screen()
    with Session(engine) as session:
        user = User.get_by_id(user.id, session=session)
        print("Liste des mots de passe enregistrés:", end="\n\n")
        for password in sorted(user.passwords, key=filtre):
            print(password, end="\n\n")

def edit_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            password_id = input("ID du mot de passe à modifier: ")
            password = Password.get_by_id(password_id, session=session)
            if password is None:
                clear_screen()
                print(f"Le mot de passe d'ID {password_id} n'existe pas.", end="\n\n")
                return
            if password.user_id != user.id:
                clear_screen()
                print(f"Le mot de passe d'ID {password_id} ne vous appartient pas.", end="\n\n")
                return
            password.update(
                session=session,
                description=input("Nouvelle description (optionnel): ") or None,
                key=input("Nouvelle clé (optionnel): ") or None,
                password=getpass.getpass("Nouveau mot de passe (optionnel): ") or None,
                email=input("Nouvelle adresse e-mail (optionnel): ") or None,
                phone=input("Nouveau numéro de téléphone (optionnel): ") or None
            )
            print("Mot de passe modifié avec succès!", end="\n\n")
    except Exception as e:
        print(f"Une erreur est survenue: {e}", end="\n\n")

def delete_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            password_id = input("ID du mot de passe à supprimer: ")
            password = Password.get_by_id(password_id, session=session)
            if password is None:
                clear_screen()
                print(f"Le mot de passe d'ID {password_id} n'existe pas.", end="\n\n")
                return
            if password.user_id != user.id:
                print(f"Le mot de passe d'ID {password_id} ne vous appartient pas.", end="\n\n")
                return
            password.delete(session=session)
            clear_screen()
            print("Mot de passe supprimé avec succès!", end="\n\n")
    except Exception as e:
        print(f"Une erreur est survenue: {e}", end="\n\n")
    finally:
        try:
            session.close()
        except Exception:
            pass

def search_password(user: User):
    clear_screen()
    try:
        with Session(engine) as session:
            user = User.get_by_id(user.id, session=session)
            search_term = input("Terme de recherche: ")
            nearest_url = similar_passwords(user.passwords, search_term)[0].url
            nearest_domaine_name=str(nearest_url).split("/")[2]
            statement = select(Password).where(Password.url.like(f'%{nearest_domaine_name}%') & Password.user_id == user.id)
            nearest_passwords = session.exec(statement).fetchall()

            clear_screen()
            print(f"""\nInformations de connections similaires à la recherche\n-> Recherche: "{search_term}"\n\n""")
            for password in nearest_passwords:
                print(password, end="\n\n")
    except ValueError as e:
        print(f"Une erreur est survenue: {e}", end="\n\n")
    finally:
        try:
            session.close()
        except Exception:
            pass

def export_passwords(user: User):
    clear_screen()
    try:
        file_path = input("Entrez le chemin du fichier CSV à exporter: ") or "passwords_export.csv"
        export_passwords(user, file_path)

        clear_screen()
        print("Exportation réussie dans passwords_export.csv", end="\n\n")
    except Exception as e:
        print(f"Erreur lors de l'exportation des mots de passes: {e}", end="\n\n")

def import_passwords(user: User):
    file_path = input("Entrez le chemin du fichier CSV à importer: ")
    clear_screen()
    try:
        import_passwords(user, file_path)

        clear_screen()
        print("Importation réussie!", end="\n\n")
    except Exception as e:
        print(f"Erreur lors de l'importation du fichier CSV: {e}", end="\n\n")