# pg.data.models.user.py
"""
Modèles de données pour les utilisateurs
"""

from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy import Engine
from pydantic import ValidationError

from hmac import compare_digest

from ...utils.security import (
    KDF_ALGORITHM,
    decrypt_password,
    derive_credentials,
    encrypt_password,
    generate_salt,
    hash_password,
    store_key
)
from ...utils.debugging import AutoStrRepr

from ..database import engine, query, insert, delete


class UserBase(SQLModel, AutoStrRepr):
    username: str = Field(min_length=3, max_length=50, unique=True, description="Nom d'utilisateur")

class User(UserBase, table = True):
    id: int = Field(default=None, primary_key=True, description="L'identifiant unique d'un utilisateur")
    password_hash: str = Field(description="Le vérificateur du mot de passe maître")
    hash_algorithm: str = Field(default=KDF_ALGORITHM, description="L'algorithme de dérivation du mot de passe maître")
    kdf_salt: str = Field(default="", description="Le sel de dérivation du mot de passe maître")
    encryption_key: str = Field(default="", description="La clé héritée d'un compte pas encore migré, vide ensuite")

    # Relationship to the Password model, setting up a one-to-many relationship
    passwords: list["Password"] = Relationship(back_populates="user")

    def refresh(self, engine: Engine=engine, session: Session=None):
        """
        Rafraîchit les données de l'utilisateur à partir de la base de données
        """
        if not session:
            with Session(engine) as session:
                session.refresh(self)
        else:
            session.refresh(self)

    def unlock(self, password: str, engine: Engine=engine) -> bool:
        """
        Vérifie le mot de passe fourni et, s'il est correct, garde en mémoire la clé de chiffrement de l'utilisateur.
        Un compte encore protégé par l'ancien schéma est migré à cette occasion.
        """
        if self.hash_algorithm != KDF_ALGORITHM:
            if not compare_digest(hash_password(password, self.hash_algorithm), self.password_hash):
                return False
            self._migrate(password, engine)
            return True

        key, verifier = derive_credentials(password, self.kdf_salt)
        if not compare_digest(verifier, self.password_hash):
            return False
        store_key(self.id, key)
        return True

    def _migrate(self, password: str, engine: Engine=engine):
        """
        Rechiffre les mots de passe avec une clé dérivée du mot de passe maître, puis efface l'ancienne clé
        """
        salt = generate_salt()
        key, verifier = derive_credentials(password, salt)
        with Session(engine) as session:
            session.add(self)
            for entry in self.passwords:
                entry.password_encrypted = encrypt_password(decrypt_password(entry.password_encrypted, self.encryption_key), key)
            self.password_hash = verifier
            self.hash_algorithm = KDF_ALGORITHM
            self.kdf_salt = salt
            self.encryption_key = ""
            session.commit()
            session.refresh(self)
        store_key(self.id, key)
        # VACUUM retire du fichier les pages libérées, qui contiennent encore l'ancienne clé
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.exec_driver_sql("VACUUM")

    @staticmethod
    def get_by_id(id: int, engine: Engine=engine, session: Session|None=None) -> "User":
        """
        Retourne un utilisateur à partir de son identifiant
        """
        return query(
            engine=engine,
            session=session,
            statement = select(User).where(User.id == id)
        )

    @staticmethod
    def get_by_username(username: str, engine: Engine=engine, session: Session|None=None) -> "User":
        """
        Retourne un utilisateur à partir de son nom d'utilisateur
        """
        return query(
            engine=engine,
            session=session,
            statement = select(User).where(User.username == username)
        )
    
    @staticmethod
    def create(engine: Engine=engine, session: Session|None=None, **data: "UserCreate") -> "User":
        """
        Crée un nouvel utilisateur dans la base de données
        """
        try:
            user_data = UserCreate.model_validate(data).model_dump()
            if User.get_by_username(user_data["username"], engine, session):
                raise ValueError(f"Username {user_data['username']} already exists")
            salt = generate_salt()
            key, verifier = derive_credentials(user_data.pop("password"), salt)
            user = insert(
                orm_instance=User(**user_data, password_hash=verifier, kdf_salt=salt),
                engine=engine,
                session=session
            )
            store_key(user.id, key)
            return user
        except ValidationError as e:
            raise ValueError(f"Invalid data: {e}")
        
    def update(self, engine: Engine=engine, session: Session|None=None, **data: "UserUpdate") -> "User":
        """
        Met à jour les données de l'utilisateur
        """
        if data:
            try:
                UserUpdate.model_validate(data)
                for key, value in data.items():
                    setattr(self, key, value)
                return insert(
                    orm_instance=self,
                    session=session,
                    engine=engine
                )
            except ValidationError as e:
                raise ValueError(f"Invalid data: {e}")
    
    @staticmethod
    def update_by_id(id: int, engine: Engine=engine, session: Session|None=None, **data: "UserUpdate"):
        """
        Met à jour les données d'un utilisateur à partir de son identifiant
        """
        if (user := User.get_by_id(id, engine, session)):
            user.update(engine, session, **data)
        else:
            raise ValueError(f"User with id {id} not found")
    
    def delete(self, engine: Engine=engine, session: Session|None=None):
        """
        Supprime l'utilisateur de la base de données
        """
        delete(
            orm_instance=self,
            session=session,
            engine=engine
        )
    
    @staticmethod
    def delete_by_id(id: int, engine: Engine=engine, session: Session|None=None):
        """
        Supprime un utilisateur à partir de son identifiant
        """
        if (user := User.get_by_id(id, engine, session)):
            user.delete(engine, session)
        else:
            raise ValueError(f"User with id {id} not found")

class UserLogin(UserBase):
    password: str = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")

class UserCreate(UserLogin):
    ...

class UserUpdate(SQLModel, AutoStrRepr):
    password: str | None = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")
