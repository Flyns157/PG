# pg.__init__.py
from .utils.visual import clear_screen
from .data.database import create_database
from .auth import register, login
from .data.transactions.password import save_password, retrieve_passwords, modify_password
from .services.csv import export_passwords, import_csv
from .services.password import search_password


def main():
    create_database()
    while True:
        clear_screen()
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        if choice == "1":
            register()
        elif choice == "2":
            user_id, key = login()
            if user_id:
                while True:
                    print("\n1. Enregistrer un mot de passe\n2. Voir mes mots de passe\n3. Rechercher un mot de passe\n4. Modifier un enregistrement\n5. Exporter mots de passe\n6. Importer mots de passe depuis CSV\n7. Déconnexion")
                    sub_choice = input("Choisissez une option: ")
                    clear_screen()
                    if sub_choice == "1":
                        save_password(user_id, key)
                    elif sub_choice == "2":
                        retrieve_passwords(user_id, key)
                    elif sub_choice == "3":
                        search_password(user_id, key)
                    elif sub_choice == "4":
                        modify_password(user_id, key)
                    elif sub_choice == "5":
                        export_passwords(user_id, key)
                    elif sub_choice == "6":
                        import_csv(user_id, key)
                    elif sub_choice == "7":
                        break
        elif choice == "3":
            break
