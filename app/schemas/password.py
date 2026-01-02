"""
Schémas Pydantic pour les entrées de mots de passe.

Ce module définit tous les modèles Pydantic nécessaires pour
la validation des données liées aux mots de passe stockés.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PasswordBase(BaseModel):
    """
    Schéma de base pour les entrées de mots de passe.

    Contient les champs communs à toutes les opérations.
    """
    service_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nom du service (ex: Gmail, Facebook)"
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nom d'utilisateur pour le service"
    )


class PasswordCreate(PasswordBase):
    """
    Schéma pour la création d'une nouvelle entrée de mot de passe.

    Contient le mot de passe en clair qui sera stocké.
    """
    password_value: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Mot de passe à stocker"
    )
    notes: Optional[str] = Field(None, description="Notes optionnelles")

    class Config:
        from_attributes = True


class PasswordUpdate(BaseModel):
    """
    Schéma pour la mise à jour partielle d'une entrée de mot de passe.

    Tous les champs sont optionnels pour permettre une mise à jour partielle.
    """
    service_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Nouveau nom du service"
    )
    username: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Nouveau nom d'utilisateur"
    )
    password_value: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Nouveau mot de passe"
    )
    notes: Optional[str] = Field(None, description="Nouvelles notes")

    class Config:
        from_attributes = True


class PasswordResponse(PasswordBase):
    """
    Schéma pour la réponse contenant une entrée de mot de passe.

    Inclut les informations de l'entrée et les métadonnées.
    """
    id: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PasswordListResponse(BaseModel):
    """
    Schéma pour la réponse paginée de liste de mots de passe.
    """
    items: list[PasswordResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True
