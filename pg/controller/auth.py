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
                from .user import console_create_user
                console_create_user()
            case "2":
                consol_login()
            case "3":
                clear_screen()
                exit()
            case _:
                clear_screen()
                print("Option invalide.")

def consol_login():
    clear_screen()
    username = input("Nom d'utilisateur: ")

    if (user := User.get_by_username(username)):
        if user.verify_password(getpass.getpass("Mot de passe: ")):
            clear_screen()
            print("Connexion réussie!")
            from .home import home
            home(user)

def login(username: str, password: str) -> User|None:
    if (user := User.get_by_username(username)):
        if user.verify_password(password):
            return user
    return None
