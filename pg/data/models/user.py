# pg.data.models.user.py
"""
Modèles de données pour les utilisateurs
"""

from sqlmodel import SQLModel, Field, Relationship
from pydantic import ValidationError

from ...utils.security import decrypt_password, generate_key
from ...utils.debugging import AutoStrRepr


class UserBase(SQLModel, AutoStrRepr):
    username: str = Field(min_length=3, max_length=50, description="Nom d'utilisateur")

class User(UserBase, table = True):
    id: int = Field(default=None, primary_key=True, description="L'identifiant unique d'un utilisateur")
    password_hash: str = Field(description="Le mot de passe haché")
    hash_algorithm: str = Field(description="Le nom de l'algorith de cryptage à utiliser pour cet utilisateur")
    encryption_key: str = Field(default_factory=generate_key, description="La clef de hachage à utiliser pour cet utilisateur")

    # Relationship to the Password model, setting up a one-to-many relationship
    passwords: list["Password"] = Relationship(back_populates="user")

    def __init__(self, **data):
        try:
            validated_data = UserBase.model_validate(data)
            super().__init__(**validated_data.model_dump())
        except ValidationError as e:
            raise ValueError(f"Invalid data: {e}")

    def verify_password(self, password: str) -> bool:
        """
        Vérifie si le mot de passe fourni correspond à celui enregistré pour cet utilisateur
        """
        return decrypt_password(self.password_hash, self.hash_algorithm) == password

class UserLogin(UserBase):
    password: str = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")

class UserCreate(UserLogin):
    hash_algorithm: str = Field(description="Le nom de l'algorith de cryptage à utiliser pour cet utilisateur")

class UserUpdate(SQLModel, AutoStrRepr):
    password: str | None = Field(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$', min_length=8, description="Mot de passe en clair (sera haché)")
