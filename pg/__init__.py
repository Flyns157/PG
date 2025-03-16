from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import getpass
import csv
import os
from datetime import datetime
from typing import Optional, Tuple

from pydantic import EmailStr, ValidationError

# Importation des modèles et fonctions depuis les fichiers précédemment créés
from .data.database import create_database
from .utils.security import hash_password, generate_key, encrypt_password, decrypt_password, supported_algorithms
from .utils.visual import clear_screen

# Modèles SQLAlchemy (à ajouter dans un fichier models.py)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    hash_algorithm = Column(String(50), nullable=False)
    encryption_key = Column(Text, nullable=False)
    
    passwords = relationship("Password", back_populates="user")

class Password(Base):
    __tablename__ = "passwords"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    site = Column(String(255), nullable=False)
    key = Column(String(255), nullable=False)
    password = Column(Text, nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    date_added = Column(DateTime, default=func.now())
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="passwords")

# Importer nos modèles Pydantic
from .models import UserCreate, UserLogin, PasswordCreate, PasswordUpdate

def display_supported_algorithms():
    print("Algorithmes de hachage supportés:")
    for algo in supported_algorithms():
        print(f"- {algo}")

def register(engine):
    clear_screen()
    
    # Demander les informations utilisateur
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    clear_screen()
    display_supported_algorithms()
    algorithm = input("Algorithme de hachage (par défaut: sha256): ") or "sha256"
    
    try:
        # Créer et valider l'utilisateur avec Pydantic
        user_data = UserCreate(username=username, password=password)
        
        # Générer le hash et la clé d'encryption
        password_hash = hash_password(password, algorithm)
        encryption_key = generate_key()
        
        # Créer la session SQLAlchemy
        with Session(engine) as session:
            try:
                # Créer un nouvel utilisateur
                new_user = User(
                    username=user_data.username,
                    password_hash=password_hash,
                    hash_algorithm=algorithm,
                    encryption_key=encryption_key
                )
                
                session.add(new_user)
                session.commit()
                print("Utilisateur enregistré avec succès!")
                
            except Exception as e:
                session.rollback()
                if "UNIQUE constraint" in str(e):
                    print("Ce nom d'utilisateur existe déjà.")
                else:
                    print(f"Erreur lors de l'enregistrement: {e}")
    
    except ValidationError as e:
        print(f"Erreur de validation: {e}")

def login(engine) -> Tuple[Optional[int], Optional[str]]:
    clear_screen()
    
    # Demander les identifiants
    username = input("Nom d'utilisateur: ")
    password = getpass.getpass("Mot de passe: ")
    
    try:
        # Valider les données d'entrée avec Pydantic
        login_data = UserLogin(username=username, password=password)
        
        # Créer une session SQLAlchemy
        with Session(engine) as session:
            # Rechercher l'utilisateur
            stmt = select(User).where(User.username == login_data.username)
            user = session.execute(stmt).scalar_one_or_none()
            
            if not user:
                print("Utilisateur non trouvé.")
                return None, None
            
            # Vérifier le mot de passe
            if hash_password(password, user.hash_algorithm) != user.password_hash:
                print("Mot de passe incorrect.")
                return None, None
            
            clear_screen()
            print("Connexion réussie!")
            return user.id, user.encryption_key
    
    except ValidationError as e:
        print(f"Erreur de validation: {e}")
        return None, None

def save_password(user_id, key, engine):
    site = input("Site web: ")
    site_key = input("Identifiant du site: ")
    password = getpass.getpass("Mot de passe: ")
    email = input("Adresse e-mail (optionnel): ") or None
    phone = input("Numéro de téléphone (optionnel): ") or None
    
    try:
        # Valider les données avec Pydantic
        password_data = PasswordCreate(
            site=site,
            key=site_key,
            password=password,
            email=email,
            phone=phone
        )
        
        # Chiffrer le mot de passe
        encrypted_password = encrypt_password(password, key)
        
        # Sauvegarder dans la base de données
        with Session(engine) as session:
            new_password = Password(
                user_id=user_id,
                site=password_data.site,
                key=password_data.key,
                password=encrypted_password,
                email=password_data.email,
                phone=password_data.phone
            )
            
            session.add(new_password)
            session.commit()
            print("Mot de passe enregistré avec succès!")
    
    except ValidationError as e:
        print(f"Erreur de validation: {e}")

def retrieve_passwords(user_id, key, engine):
    with Session(engine) as session:
        stmt = select(Password).where(Password.user_id == user_id)
        entries = session.execute(stmt).scalars().all()
    
    if not entries:
        print("Aucun mot de passe enregistré.")
        return
    
    print("\nListe des mots de passe enregistrés:")
    for entry in entries:
        decrypted_password = decrypt_password(entry.password, key)
        print(f"\nSite: {entry.site}")
        print(f"Identifiant: {entry.key}")
        print(f"Mot de passe: {decrypted_password}")
        print(f"E-mail: {entry.email or 'Non spécifié'}")
        print(f"Téléphone: {entry.phone or 'Non spécifié'}")
        print(f"Date d'ajout: {entry.date_added}")
        print(f"Dernière mise à jour: {entry.date_updated}")

def search_password(user_id, key, engine):
    search_term = input("Entrez le site ou l'identifiant à rechercher: ")
    
    with Session(engine) as session:
        stmt = select(Password).where(
            Password.user_id == user_id,
            (Password.site.like(f"%{search_term}%") | Password.key.like(f"%{search_term}%"))
        )
        entries = session.execute(stmt).scalars().all()
    
    if not entries:
        print("Aucun mot de passe trouvé pour cette recherche.")
        return
    
    clear_screen()
    print(f"""\nListe des informations de connexion correspondantes à la recherche\n\n-> Recherche: "{search_term}"\n""")
    for entry in entries:
        decrypted_password = decrypt_password(entry.password, key)
        print(f"\nSite: {entry.site}")
        print(f"Identifiant: {entry.key}")
        print(f"Mot de passe: {decrypted_password}")
        print(f"E-mail: {entry.email or 'Non spécifié'}")
        print(f"Téléphone: {entry.phone or 'Non spécifié'}")
        print(f"Date d'ajout: {entry.date_added}")
        print(f"Dernière mise à jour: {entry.date_updated}")

def export_passwords(user_id, key, engine):
    clear_screen()
    
    with Session(engine) as session:
        stmt = select(Password).where(Password.user_id == user_id)
        entries = session.execute(stmt).scalars().all()
    
    if not entries:
        print("Aucun mot de passe enregistré.")
        return
    
    with open("passwords_export.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Site", "Identifiant", "Mot de passe", "Email", "Téléphone", "Date", "Date de mise à jour"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in entries:
            decrypted_password = decrypt_password(entry.password, key)
            writer.writerow({
                "Site": entry.site,
                "Identifiant": entry.key,
                "Mot de passe": decrypted_password,
                "Email": entry.email or "",
                "Téléphone": entry.phone or "",
                "Date": entry.date_added,
                "Date de mise à jour": entry.date_updated
            })
    
    print("Exportation réussie dans passwords_export.csv")

def modify_password(user_id, key, engine):
    clear_screen()
    site = input("Site web à modifier: ")
    
    with Session(engine) as session:
        stmt = select(Password).where(Password.user_id == user_id, Password.site == site)
        entry = session.execute(stmt).scalar_one_or_none()
        
        if not entry:
            print("Aucun enregistrement trouvé pour ce site.")
            return
        
        decrypted_password = decrypt_password(entry.password, key)
        
        print(f"\nIdentifiant actuel: {entry.key}")
        print(f"Mot de passe actuel: {decrypted_password}")
        print(f"Email actuel: {entry.email}")
        print(f"Téléphone actuel: {entry.phone}")
        
        # Collecter les nouvelles informations
        new_key = input(f"Nouvel identifiant ({entry.key} pour conserver): ") or entry.key
        new_password = getpass.getpass("Nouveau mot de passe (laisser vide pour conserver): ") or decrypted_password
        new_email = input(f"Nouvel email ({entry.email} pour conserver): ") or entry.email
        new_phone = input(f"Nouveau téléphone ({entry.phone} pour conserver): ") or entry.phone
        
        try:
            # Valider les données avec Pydantic
            password_update = PasswordUpdate(
                site=site,
                key=new_key,
                password=new_password,
                email=new_email,
                phone=new_phone
            )
            
            # Mettre à jour l'entrée
            encrypted_password = encrypt_password(new_password, key)
            entry.key = password_update.key
            entry.password = encrypted_password
            entry.email = password_update.email
            entry.phone = password_update.phone
            # La date de mise à jour sera automatiquement modifiée par SQLAlchemy
            
            session.commit()
            
            clear_screen()
            print("Informations mises à jour avec succès!")
        
        except ValidationError as e:
            session.rollback()
            print(f"Erreur de validation: {e}")

def import_csv(user_id, key, engine):
    file_path = input("Entrez le chemin du fichier CSV à importer: ")
    
    if not os.path.exists(file_path):
        print(f"Le fichier '{file_path}' n'existe pas.")
        return
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            with Session(engine) as session:
                for row in reader:
                    site = row.get('Site')
                    site_key = row.get('Identifiant')
                    password = row.get('Mot de passe')
                    email = row.get('Email', None)
                    phone = row.get('Téléphone', None)
                    
                    if site and site_key and password:  # Vérifier les données essentielles
                        try:
                            # Valider avec Pydantic
                            password_data = PasswordCreate(
                                site=site,
                                key=site_key,
                                password=password,
                                email=email if email else None,
                                phone=phone if phone else None
                            )
                            
                            # Chiffrer et sauvegarder
                            encrypted_password = encrypt_password(password, key)
                            new_password = Password(
                                user_id=user_id,
                                site=password_data.site,
                                key=password_data.key,
                                password=encrypted_password,
                                email=password_data.email,
                                phone=password_data.phone
                            )
                            
                            session.add(new_password)
                        
                        except ValidationError as e:
                            print(f"Ligne ignorée (erreur de validation): {site} - {e}")
                
                session.commit()
        
        clear_screen()
        print("Importation réussie!")
    
    except Exception as e:
        clear_screen()
        print(f"Erreur lors de l'importation du fichier CSV: {e}")

def main():
    # Création de la base de données avec SQLAlchemy
    connection_string = input("URL de connexion à la base de données (vide pour SQLite par défaut): ") or "sqlite:///password_manager.db"
    engine = create_database(connection_string)
    
    while True:
        clear_screen()
        print("\n1. S'inscrire\n2. Se connecter\n3. Quitter")
        choice = input("Choisissez une option: ")
        
        if choice == "1":
            register(engine)
        elif choice == "2":
            user_id, key = login(engine)
            if user_id:
                while True:
                    print("\n1. Enregistrer un mot de passe\n2. Voir mes mots de passe\n3. Rechercher un mot de passe\n4. Modifier un enregistrement\n5. Exporter mots de passe\n6. Importer mots de passe depuis CSV\n7. Déconnexion")
                    sub_choice = input("Choisissez une option: ")
                    clear_screen()
                    
                    if sub_choice == "1":
                        save_password(user_id, key, engine)
                    elif sub_choice == "2":
                        retrieve_passwords(user_id, key, engine)
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
