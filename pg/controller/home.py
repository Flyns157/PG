# pg.controller.home.py
from .password import (
    create_password,
    view_password,
    list_passwords,
    edit_password,
    delete_password,
    search_password
)
from ..utils.visual import clear_screen
from ..data.models import User

def home(user: User):
    clear_screen()
    while True:
        print("Menu principal")
        print("1. Créer un mot de passe")
        print("2. Voir un mot de passe")
        print("3. Lister les mots de passe")
        print("4. Rechercher un mot de passe")
        print("5. Modifier un mot de passe")
        print("6. Supprimer un mot de passe")
        print("7. Quitter")
        choice = input("Entrez votre choix: ")
        match choice:
            case "1":
                create_password(user)
            case "2":
                view_password(user)
            case "3":
                list_passwords(user)
            case "4":
                search_password(user)
            case "5":
                edit_password(user)
            case "6":
                delete_password(user)
            case "7":
                return
            case _:
                print("Choix invalide")