# pg.data.models.user.py
"""
Modèles de données pour les utilisateurs
"""

from sqlmodel import SQLModel, Field

from ...utils.debugging import AutoStrRepr


class UserBase(SQLModel, AutoStrRepr):
    username: str = Field(min_length=3, max_length=50, description="Nom d'utilisateur")

class User(UserBase, table = True):
    id: int = Field(default=None, primary_key=True, description="L'identifiant unique d'un utilisateur")
    password_hash: str = Field(description="Le mot de passe haché")
    hash_algorithm: str = Field(description="Le nom de l'algorith de crypptage à utiliser pour cet utilisateur")
    encryption_key: str = Field(description="La clef de hachage à utiliser pour cet utilisateur")

class UserLogin(UserBase):
    password: str = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")

class UserCreate(UserLogin):
    ...

class UserUpdate(SQLModel, AutoStrRepr):
    password: str | None = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")
