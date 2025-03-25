# pg.controller.home.py
from .password import (
    console_create_password,
    console_view_password,
    console_list_passwords,
    console_edit_password,
    console_delete_password,
    console_search_password,
    console_import_passwords,
    console_export_passwords
)
from ..utils.visual import clear_screen
from ..data.models import User


def home(user: User):
    clear_screen()
    while True:
        choice = input(
            "Menu principal\n"\
            "\n1. Créer un mot de passe\n"\
            "2. Voir un mot de passe\n"\
            "3. Lister les mots de passe\n"\
            "4. Rechercher un mot de passe\n"\
            "5. Modifier un mot de passe\n"\
            "6. Supprimer un mot de passe\n"\
            "7. Exporter les mots de passe\n"\
            "8. Importer des mots de passe\n"\
            "9. Déconnexion\n"\
            "10. Quitter\n"\
            "\nEntrez votre choix: "
        )
        match choice:
            case "1":
                console_create_password(user)
            case "2":
                console_view_password(user)
            case "3":
                console_list_passwords(user)
            case "4":
                console_search_password(user)
            case "5":
                console_edit_password(user)
            case "6":
                console_delete_password(user)
            case "7":
                console_export_passwords(user)
            case "8":
                console_import_passwords(user)
            case "9":
                from .auth import connect
                connect()
            case "10":
                clear_screen()
                return
            case _:
                clear_screen()
                print("Choix invalide")