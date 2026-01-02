"""
Tests unitaires pour le module de configuration.
Teste le chargement des variables d'environnement.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.core.config import Settings, get_settings


class TestSettings:
    """Tests pour la classe de configuration."""

    def test_settings_has_required_attributes(self):
        """Verifie que Settings a tous les attributs requis."""
        settings = Settings()
        
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "SECRET_KEY")
        assert hasattr(settings, "ALGORITHM")
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        assert hasattr(settings, "DEBUG")
        assert hasattr(settings, "API_V1_PREFIX")
        assert hasattr(settings, "CORS_ORIGINS")
        assert hasattr(settings, "PASSWORD_MIN_LENGTH")

    def test_settings_default_values(self):
        """Verifie les valeurs par defaut."""
        settings = Settings()
        
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.DEBUG is False
        assert settings.PASSWORD_MIN_LENGTH == 8

    def test_database_url_default(self):
        """Verifie l'URL de base de donnees par defaut."""
        settings = Settings()
        assert "sqlite" in settings.DATABASE_URL

    def test_cors_origins_default(self):
        """Verifie les origines CORS par defaut."""
        settings = Settings()
        assert isinstance(settings.CORS_ORIGINS, list)
        assert "*" in settings.CORS_ORIGINS

    def test_settings_from_env(self):
        """Verifie le chargement depuis les variables d'environnement."""
        env_vars = {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "SECRET_KEY": "test-secret-key",
            "DEBUG": "true",
        }
        
        with patch.dict("os.environ", env_vars):
            settings = Settings()
            
            assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
            assert settings.SECRET_KEY == "test-secret-key"
            assert settings.DEBUG is True

    def test_get_settings_caching(self):
        """Verifie que get_settings utilise le cache."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

    def test_algorithm_is_hs256(self):
        """Verifie que l'algorithme par defaut est HS256."""
        settings = Settings()
        assert settings.ALGORITHM == "HS256"

    def test_token_expiry_minutes_is_positive(self):
        """Verifie que la duree d'expiration est positive."""
        settings = Settings()
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_api_v1_prefix(self):
        """Verifie le prefixe d'API par defaut."""
        settings = Settings()
        assert settings.API_V1_PREFIX == "/api/v1"

    def test_password_min_length(self):
        """Verifie la longueur minimale de mot de passe."""
        settings = Settings()
        assert settings.PASSWORD_MIN_LENGTH >= 8
