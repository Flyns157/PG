# pg.data.models.password.py
"""
Modèle de données pour les mots de passe
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber
from datetime import datetime

from pg.utils.security import encrypt_password
from . import Base


class PasswordValidator(BaseModel):
    id: int | None = Field(..., description="Identifiant de l'enregistrement d'informations de connection")
    site: str | HttpUrl = Field(..., description="Nom / URL du site ou du service")
    key: str = Field(..., description="Clé ou identifiant pour le site")
    password_encrypted: str = Field(..., description="Mot de passe chiffré")
    email: EmailStr | None = Field(None, description="Email associé au compte")
    phone: PhoneNumber | None = Field(None, description="Numéro de téléphone associé au compte")
    date_added: datetime = Field(default_factory=datetime.now, description="Date de création du mot de passe")
    date_updated: datetime = Field(default_factory=datetime.now, description="Date de dernière modification du mot de passe")

    def to_ORM(self):
        return PasswordORM(
            id=self.id,
            user_id=None,
            site=self.site,
            key=self.key,
            password_encrypted=self.password_encrypted,
            email=self.email,
            phone=self.phone,
            date_added=self.date_added,
            date_updated=self.date_updated
        )

class PasswordORM(Base):
    """
    Modèle SQLAlchemy pour les mots de passe
    """
    __tablename__ = 'passwords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    site = Column(String, nullable=False)
    key = Column(String, nullable=False)
    password_encrypted = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    date_added = Column(DateTime, default=datetime.now())
    date_updated = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    def to_validator(self):
        return PasswordValidator(
            id=self.id,
            site=self.site,
            key=self.key,
            password_encrypted=self.password_encrypted,
            email=self.email,
            phone=self.phone,
            date_added=self.date_added,
            date_updated=self.date_updated
        )

class PasswordCreate(PasswordValidator):
    def __init__(
            self,
            *,
            site: str | HttpUrl, 
            key: str, password: str, 
            email: EmailStr | None, 
            phone: PhoneNumber | None,
            user_key: str | bytes,
        ) -> None:
        super().__init__(
            site=site,
            key=key,
            password_encrypted=encrypt_password(password, user_key),
            email=email,
            phone=phone
        )
    

class PasswordUpdate(PasswordCreate):
    # TODO: Implement update password
    ...
