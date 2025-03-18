# pg.data.models.password.py
"""
Modèles de données pour les mots de passe
"""

from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic import EmailStr, HttpUrl
from datetime import datetime

from sqlmodel import SQLModel, Field

from ...utils.debugging import AutoStrRepr


class PasswordBase(SQLModel, AutoStrRepr):
    url: HttpUrl = Field(description="URL du site / service")
    description: str = Field(description="Description par l'utilisateur du site / service")
    key: str = Field(description="Clé / identifiant")
    password_encrypted: str = Field(..., description="Mot de passe chiffré")
    email: EmailStr | None = Field(description="Email associé")
    phone: PhoneNumber | None = Field(description="Numéro de téléphone associé")

class Password(PasswordBase):
    id: int | None = Field(..., description="Identifiant de l'enregistrement d'informations de connection")
    date_added: datetime = Field(default_factory=datetime.now, description="Date de création du mot de passe")
    date_updated: datetime = Field(default_factory=datetime.now, description="Date de dernière modification du mot de passe")
    
    def __str__(self):
        attrs = ', '.join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    def __repr__(self):
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

class PasswordCreate(PasswordBase):
    ...

class PasswordUpdate(SQLModel, AutoStrRepr):
    """Modèle pour la mise à jour d'un mot de passe (sans `site`)"""
    key: str | None = None
    password_encrypted: str | None = None
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
