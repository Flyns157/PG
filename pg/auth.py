# pg.auth.py
import getpass

from .utils.visual import clear_screen, display_supported_algorithms
from .utils.security import hash_password, validate_password_strength

from sqlmodel import Session, select
from .data.database import engine
from .data.models import User

def register():
    clear_screen()
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    def vp(password):
        try:
            return validate_password_strength(password)
        except ValueError as e:
            print(e)
            return False
    while vp(password) is False:
        password = getpass.getpass("Mot de passe: ")

    clear_screen()
    display_supported_algorithms()
    algorithm = input("Algorithme de hachage (par défaut: sha256): ") or "sha256"
    password_hash = hash_password(password, algorithm)
    
    try:
        with Session(engine) as session:
            new_user = User(
                username=username, 
                password_hash=password_hash,
                hash_algorithm=algorithm
            )
            
            session.add(new_user)
            session.commit()

        print("Utilisateur enregistré avec succès!")
    except Exception as e:
        print(e)
        input("Appuyez sur entrée pour continuer...")

def login():
    clear_screen()
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")

    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()

    if not user:
        print("Utilisateur non trouvé.")
        return None, None

    if hash_password(password, user.hash_algorithm) != user.password_hash:
        print("Mot de passe incorrect.")
        return None, None
    
    clear_screen()
    print("Connexion réussie!")
    return user.id, user.encryption_key