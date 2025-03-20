# pg.controller.auth.py
import getpass

from ..data.models import User
from ..utils.visual import clear_screen


def connect():
    clear_screen()
    while True:
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        match choice:
            case "1":
                from .user import create_user
                create_user()
            case "2":
                login()
            case "3":
                break
            case _:
                clear_screen()
                print("Option invalide.\n")

def login():
    clear_screen()
    username = input("Nom d'utilisateur: ")

    if (user := User.get_by_username(username)):
        if user.verify_password(getpass.getpass("Mot de passe: ")):
            clear_screen()
            print("Connexion réussie!")
            from .home import home
            home(user)
