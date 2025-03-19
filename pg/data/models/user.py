# pg.data.models.user.py
"""
Modèles de données pour les utilisateurs
"""

from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy import Engine
from pydantic import ValidationError

from ...utils.security import generate_key, hash_password
from ...utils.debugging import AutoStrRepr

from ..database import engine, query, insert


class UserBase(SQLModel, AutoStrRepr):
    username: str = Field(min_length=3, max_length=50, unique=True, description="Nom d'utilisateur")

class User(UserBase, table = True):
    id: int = Field(default=None, primary_key=True, description="L'identifiant unique d'un utilisateur")
    password_hash: str = Field(description="Le mot de passe haché")
    hash_algorithm: str = Field(default="sha256", description="Le nom de l'algorith de cryptage à utiliser pour cet utilisateur", allow_mutation=False)
    encryption_key: str = Field(default_factory=generate_key, description="La clef de hachage à utiliser pour cet utilisateur", allow_mutation=False)

    # Relationship to the Password model, setting up a one-to-many relationship
    passwords: list["Password"] = Relationship(back_populates="user")

    def set_password(self, password: str):
        """
        Définit le mot de passe en clair
        """
        self.password_hash = hash_password(password, self.hash_algorithm)
    
    def refresh(self, engine: Engine=engine, session: Session=None):
        """
        Rafraîchit les données de l'utilisateur à partir de la base de données
        """
        if not session:
            with Session(engine) as session:
                session.refresh(self)
        else:
            session.refresh(self)

    def verify_password(self, password: str) -> bool:
        """
        Vérifie si le mot de passe fourni correspond à celui enregistré pour cet utilisateur
        """
        return hash_password(password, self.hash_algorithm) == self.password_hash
    
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
    def create(engine: Engine=engine, **data: "UserCreate") -> "User":
        """
        Crée un nouvel utilisateur dans la base de données
        """
        try:
            user_data = UserCreate.model_validate(data).model_dump()
            user_data["password_hash"] = hash_password(user_data.pop("password"), user_data["hash_algorithm"])
            user = User(**user_data)
            with Session(engine) as session:
                session.add(user)
                session.commit()
                User.model_validate(user)
            return user
        except ValidationError as e:
            raise ValueError(f"Invalid data: {e}")
        
    def update(self, engine: Engine=engine, **data: "UserUpdate") -> "User":
        """
        Met à jour les données de l'utilisateur
        """
        if data:
            try:
                UserUpdate.model_validate(data)
                for key, value in data.items():
                    setattr(self, key, value)
                with Session(engine) as session:
                    session.add(self)
                    session.commit()
                    return self
            except ValidationError as e:
                raise ValueError(f"Invalid data: {e}")
    
    @staticmethod
    def update_by_id(id: int, engine: Engine=engine, **data):
        """
        Met à jour les données d'un utilisateur à partir de son identifiant
        """
        if (user := User.get_by_id(id, engine)):
            user.update(engine, **data)
        else:
            raise ValueError(f"User with id {id} not found")
    
    def delete(self, engine: Engine=engine):
        """
        Supprime l'utilisateur de la base de données
        """
        with Session(engine) as session:
            session.delete(self)
            session.commit()
    
    @staticmethod
    def delete_by_id(id: int, engine: Engine=engine):
        """
        Supprime un utilisateur à partir de son identifiant
        """
        if (user := User.get_by_id(id, engine)):
            user.delete(engine)
        else:
            raise ValueError(f"User with id {id} not found")

class UserLogin(UserBase):
    password: str = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")

class UserCreate(UserLogin):
    hash_algorithm: str = Field(description="Le nom de l'algorith de cryptage à utiliser pour cet utilisateur")

class UserUpdate(SQLModel, AutoStrRepr):
    password: str | None = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")
