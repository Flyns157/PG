# pg.data.models.password.py
"""
Modèle de données pour les mots de passe
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from pydantic import BaseModel, ConfigDict, Field, EmailStr, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber
from datetime import datetime

from pg.utils.security import encrypt_password, decrypt_password
from . import Base


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
    date_added = Column(DateTime, default=datetime.now)
    date_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __pre_init__(self, **kwargs):
        Password(**kwargs)
    
    
    @validates('password_encrypted')
    def encrypt_password_field(self, key, password: str):
        return encrypt_password(password)

    @property
    def password(self):
        return decrypt_password(self.password_encrypted)

    @password.setter
    def password(self, value: str):
        self.password_encrypted = encrypt_password(value)

    def to_validator(self):
        return Password.model_validate(self)


class PasswordBase(BaseModel):
    site: str | HttpUrl = Field(..., description="Nom / URL du site ou du service")
    key: str = Field(..., description="Clé ou identifiant pour le site")
    password_encrypted: str = Field(..., description="Mot de passe chiffré")
    email: EmailStr | None = Field(None, description="Email associé au compte")
    phone: PhoneNumber | None = Field(None, description="Numéro de téléphone associé au compte")

class Password(PasswordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(..., description="Identifiant de l'enregistrement d'informations de connection")
    date_added: datetime = Field(default_factory=datetime.now, description="Date de création du mot de passe")
    date_updated: datetime = Field(default_factory=datetime.now, description="Date de dernière modification du mot de passe")

    def to_orm(self):
        return PasswordORM(**self.model_dump())
    
    def __str__(self):
        return f"Password(id={self.id}, site={self.site}, email={self.email}, phone={self.phone})"

    def __repr__(self):
        return f"Password(id={self.id!r}, site={self.site!r}, email={self.email!r}, phone={self.phone!r})"

class PasswordCreate(PasswordBase):
    ...
    

class PasswordUpdate(BaseModel):
    """Modèle pour la mise à jour d'un mot de passe (sans `site`)"""
    key: str | None = None
    password_encrypted: str | None = None
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
