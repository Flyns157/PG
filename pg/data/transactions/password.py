# pg.data.transactions.password.py
import getpass

from ...utils.security import encrypt_password, decrypt_password
from ...utils.visual import clear_screen

from sqlmodel import Session, select
from ..database import engine
from ..models import Password, PasswordUpdate, User


def save_password(user_id: int):
    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            print("Utilisateur inconnu.")
            return

    url = input("Site web: ")
    key = input("Identifiant du site: ")
    password = getpass.getpass("Mot de passe: ")
    email = input("Adresse e-mail (optionnel): ") or None
    phone = input("Numéro de téléphone (optionnel): ") or None
    clear_screen()

    try:
        with Session(engine) as session:
            new_password = Password(
                user_id=user_id,
                url=url,
                key=key,
                password_encrypted=encrypt_password(
                    password,
                    user.encryption_key
                ),
                email=email,
                phone=phone
            )
            session.add(new_password)
            session.commit()

        print("Mot de passe enregistré avec succès!")
    except Exception as e:
        print(f"Une erreur est survenue: {e}")

def delete_password(user_id: int):
    site = input("Site web à supprimer: ")
    clear_screen()

    with Session(engine) as session:
        statement = select(Password).where(Password.user_id == user_id, Password.url == site)
        book_to_delete = session.exec(statement)
        if book_to_delete:
            session.delete(book_to_delete)
            session.commit()
            print("Mot de passe supprimé avec succès!")
        else:
            print("Aucun enregistrement trouvé pour ce site.")

def retrieve_passwords(user_id: int):
    with Session(engine) as session:
        statement = select(Password).where(Password.user_id == user_id)
        results = session.exec(statement)
        entries = results.all()
    
    if not entries:
        print("Aucun mot de passe enregistré.")
        return
    
    print("\nListe des mots de passe enregistrés:")
    for password in sorted(entries, key=lambda x: x.url):
        print(password)

def modify_password(user_id: int):
    clear_screen()
    enter = input("Site web à modifier (url ou id): ")

    with Session(engine) as session:
        if enter.isdigit():
            statement = select(Password).where(Password.user_id == user_id, Password.id == int(enter))
        else:
            statement = select(Password).where(Password.user_id == user_id, Password.url == enter)
        
        password_to_update = session.exec(statement).first()
        if not password_to_update:
            print("Aucun enregistrement trouvé pour ce site.")
            return
    
    password = decrypt_password(password_to_update.password_encrypted, password_to_update.user.encryption_key)

    print("Laissez un champ vide pour conserver les anciennes valeurs.\n")
    password_updated = PasswordUpdate(
        key=input(f"Nouvel identifiant (actuellement: {password_to_update.key} ): ") or None,
        password_encrypted=encrypt_password(
            getpass.getpass(f"Nouveau mot de passe (actuellement: {password} ): "),
            password_to_update.user.encryption_key
        ) or None,
        email=input(f"Nouvel email (actuellement: {password_to_update.email} ") or None,
        phone=input(f"Nouveau téléphone (actuellement: {password_to_update.phone} ): ") or None
    )
    
    clear_screen()
    try:
        with Session(engine) as session:
            update_infos=password_updated.model_dump()
            for k, v in update_infos.items():
                if v is not None:
                    setattr(password_to_update, k, v)
            session.add(password_to_update)
            session.commit()
            session.refresh(password_to_update)

        print("Informations mises à jour avec succès!")
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
