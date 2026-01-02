"""
Configuration de l'application via Pydantic Settings.

Ce module gère toutes les variables d'environnement de l'application
de manière type-safe grâce à Pydantic BaseSettings.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration globale de l'application.

    Les valeurs sont chargées depuis le fichier .env ou les variables
    d'environnement du système.
    """
    # Configuration de la base de données
    DATABASE_URL: str = "sqlite:///./password_manager.db"

    # Configuration JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Configuration du serveur
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Configuration CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Paramètres de sécurité
    PASSWORD_MIN_LENGTH: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Fonction de caching pour les paramètres.

    Utilise lru_cache pour éviter de relire le fichier .env à chaque appel.
    Ceci est particulièrement utile en production où les paramètres
    ne changent pas pendant l'exécution.
    """
    return Settings()


# Instance globale des paramètres (utilisation directe)
settings = get_settings()
