"""
Schémas Pydantic pour les utilisateurs et l'authentification.

Ce module définit tous les modèles Pydantic nécessaires pour
la validation des données liées aux utilisateurs et aux tokens.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Schéma de base pour les utilisateurs.

    Contient les champs communs à toutes les opérations sur les utilisateurs.
    """
    email: EmailStr = Field(...,
                            description="Adresse email valide de l'utilisateur")


class UserCreate(UserBase):
    """
    Schéma pour la création d'un nouvel utilisateur.

    Utilisé lors de l'inscription avec validation du mot de passe.
    """
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Mot de passe (8-128 caractères)"
    )

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """
    Schéma pour la connexion d'un utilisateur.

    Utilise le format OAuth2PasswordRequestForm standard de FastAPI.
    """
    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(..., description="Mot de passe de l'utilisateur")

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """
    Schéma pour la réponse contenant les informations d'un utilisateur.

    Ne contient pas le mot de passe哈希é pour des raisons de sécurité.
    """
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """
    Schéma pour la réponse de connexion contenant le token d'accès.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(...,
                            description="Durée de validité du token en secondes")


class TokenData(BaseModel):
    """
    Schéma pour les données extraites du token JWT.
    """
    user_id: Optional[int] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None


class UserUpdate(BaseModel):
    """
    Schéma pour la mise à jour des informations utilisateur.
    """
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
