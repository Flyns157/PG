# pg.controller.auth.py
import getpass

from ..data.models import User
from ..utils.visual import clear_screen


def connect():
    clear_screen()
    while True:
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        if choice == "1":
            from .user import create_user
            create_user()
        elif choice == "2":
            login()
        elif choice == "3":
            break

def login():
    clear_screen()
    username = input("Nom d'utilisateur: ")

    if (user := User.get_by_username(username)):
        if user.verify_password(getpass.getpass("Mot de passe: ")):
            clear_screen()
            print("Connexion réussie!")
            from .home import home
            home(user)
