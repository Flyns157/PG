from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from pydantic_extra_types.phone_numbers import PhoneNumber

class PasswordBase(BaseModel):
    site: str = Field(..., description="Nom du site ou du service")
    key: str = Field(..., description="Clé ou identifiant pour le site")
    password: str = Field(..., description="Mot de passe chiffré")
    email: EmailStr | None = Field(None, description="Email associé au compte")
    phone: PhoneNumber | None = Field(None, description="Numéro de téléphone associé au compte")

class PasswordCreate(PasswordBase):
    pass

class PasswordUpdate(PasswordBase):
    site: str | None = None
    key: str | None = None
    password: str | None = None

class Password(PasswordBase):
    id: int
    user_id: int
    date_added: datetime
    date_updated: datetime
    
    class Config:
        orm_mode = True