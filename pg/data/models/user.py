# pg.data.models.user.py
"""
Modèle de données pour les utilisateurs
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy import Column, Integer, String

from . import Base
from .password import Password
from ...utils.security import validate_password_strength


class UserORM(Base):
    """
    Modèle SQLAlchemy pour les utilisateurs
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    hash_algorithm = Column(String, nullable=False)
    encryption_key = Column(String, nullable=False)


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nom d'utilisateur unique")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Mot de passe en clair (sera haché)")
    
    @field_validator('password')
    def password_strength(cls, v: str):
        return validate_password_strength(v)

class UserUpdate(BaseModel):
    password: str | None = None
    
    @field_validator('password')
    def password_strength(cls, v: str):
        return validate_password_strength(v)

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    password_hash: str
    hash_algorithm: str
    encryption_key: str
    passwords: list[Password] = []
    
    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str