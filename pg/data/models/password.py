# pg.data.models.password.py
"""
Modèles de données pour les mots de passe
"""

from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic import EmailStr, ValidationError, HttpUrl
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship, Column, Session, select
from sqlalchemy import Engine

from ...utils.debugging import AutoStrRepr
from ...utils.type import HttpUrlType
from ...utils.security import encrypt_password, decrypt_password

from ..database import engine, query, insert, delete


class PasswordBase(SQLModel, AutoStrRepr):
    user_id: int = Field(foreign_key="user.id", description="Identifiant de l'utilisateur", allow_mutation=False)
    url: HttpUrl = Field(sa_column=Column(HttpUrlType), description="URL du site / service")
    description: str | None = Field(None, description="Description par l'utilisateur du site / service")
    key: str = Field(description="Clé / identifiant")
    password_encrypted: str = Field(None, description="Mot de passe chiffré")
    email: EmailStr | None = Field(None, description="Email associé")
    phone: PhoneNumber | None = Field(None, description="Numéro de téléphone associé")

class Password(PasswordBase, table=True):
    id: int = Field(default=None, primary_key=True , description="Identifiant de l'enregistrement d'informations de connection")
    date_added: datetime = Field(default_factory=datetime.now, description="Date de création du mot de passe")
    date_updated: datetime = Field(default_factory=datetime.now, description="Date de dernière modification du mot de passe")

    # Relationship to the User model, setting up a one-to-many relationship
    user: "User" = Relationship(back_populates="passwords")

    @property
    def loaded_user(self):
        """
        Retourne l'utilisateur complet (contournement de l'import paresseux depuis la base de données)
        """
        from ..models.user import User
        # TODO : trouver une manière de vérifier si l'import est passeux
        # if isinstance(self.user, User):  # Si l'utilisateur est déjà chargé, on le retourne directement
        #     return self.user
        return User.get_by_id(self.user_id)
    
    @property
    def password(self):
        """
        Retourne le mot de passe en clair
        """
        return decrypt_password(self.password_encrypted, self.loaded_user.encryption_key)
    
    @password.setter
    def password(self, password: str):
        """
        Définit le mot de passe en clair
        """
        self.password_hash = encrypt_password(password, self.loaded_user.encryption_key)
    
    def refresh(self, engine: Engine=engine, session: Session=None):
        """
        Rafraîchit les données de l'utilisateur à partir de la base de données
        """
        if not session:
            with Session(engine) as session:
                session.refresh(self)
        else:
            session.refresh(self)

    @staticmethod
    def get_by_id(id: int, engine: Engine=engine, session: Session|None=None) -> "Password":
        """
        Retourne un mot de passe à partir de son identifiant
        """
        return query(
            engine=engine,
            session=session,
            statement = select(Password).where(Password.id == id)
        )
    
    @staticmethod
    def get_by_url(url: str | HttpUrl, engine: Engine=engine, session: Session|None=None) -> "Password":
        """
        Retourne un mot de passe à partir de l'URL du site / service
        """
        return query(
            engine=engine,
            session=session,
            statement = select(
                Password
            ).where(
                # TODO : prendre en compte l'utilisateur...
                # (Password.user_id == user_id) &
                ((Password.url.contains(url)) | (Password.key.contains(url)))
            )
        )
    
    @staticmethod
    def create(engine: Engine=engine, session: Session|None=None, **data: "PasswordCreate") -> "Password":
        """
        Crée un nouveau mot de passe
        """
        try:
            password = Password(**data)
            password.password = data.get("password")
            return insert(
                engine=engine,
                session=session,
                orm_instance=password
            )
        except ValidationError as e:
            raise ValueError(str(e))
    
    def update(self, engine: Engine=engine, session: Session|None=None, **data: "PasswordUpdate") -> "Password":
        """
        Met à jour un mot de passe existant
        """
        try:
            PasswordUpdate.model_validate(**data)
            for key, value in data.items():
                if key == "password":
                    self.password = value
                else:
                    setattr(self, key, value)
            return insert(
                engine=engine,
                session=session,
                orm_instance=self
            )
        except ValidationError as e:
            raise ValueError(str(e))
    
    @staticmethod
    def update_by_id(id: int, engine: Engine=engine, session: Session|None=None, **data: "PasswordUpdate") -> "Password":
        """
        Met à jour un mot de passe existant à partir de son identifiant
        """
        password = Password.get_by_id(id, engine=engine)
        return password.update(engine=engine, session=session, **data)
    
    def delete(self, engine: Engine=engine, session: Session|None=None):
        """
        Supprime un mot de passe
        """
        return delete(
            orm_instance=self,
            engine=engine,
            session=session
        )
    
    @staticmethod
    def delete_by_id(id: int, engine: Engine=engine, session: Session|None=None):
        """
        Supprime un mot de passe à partir de son identifiant
        """
        password = Password.get_by_id(id=id, engine=engine, session=session)
        return password.delete(engine=engine)
    
    def __str__(self):
        return  f"Site web: {self.url} (id: {self.id})\n" \
                f"Description: {self.description or 'Non spécifié'}\n" \
                f"Identifiant: {self.key}\n" \
                f"Mot de passe: {self.password}\n" \
                f"Email: {self.email or 'Non spécifié'}\n" \
                f"Téléphone: {(self.phone or '    Non spécifié')[4:]}\n" \
                f"Date de création: {self.date_added}\n" \
                f"Date de dernière modification: {self.date_updated}"

class PasswordCreate(PasswordBase):
    ...

class PasswordUpdate(SQLModel, AutoStrRepr):
    """Modèle pour la mise à jour d'un mot de passe (sans `site`)"""
    description: str | None = None
    key: str | None = None
    password_encrypted: str | None = None
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
