"""
Tests unitaires pour le module de securite.
Teste les fonctions de hachage et les tokens JWT.
"""
import pytest
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_secure_token,
)


class TestPasswordHashing:
    """Tests pour les fonctions de hachage de mots de passe."""

    def test_hash_password_returns_string(self):
        """Verifie que hash_password retourne une chaîne."""
        result = hash_password("testpassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_is_different_each_time(self,):
        """Verifie que le hash est different a chaque appel (salt unique)."""
        hash1 = hash_password("testpassword")
        hash2 = hash_password("testpassword")
        assert hash1 != hash2

    def test_hash_password_is_not_plain_text(self):
        """Verifie que le hash ne contient pas le mot de passe en clair."""
        password = "MySecretPassword123"
        hashed = hash_password(password)
        assert password not in hashed
        assert hashed != password

    def test_verify_password_correct(self):
        """Verifie qu'un mot de passe correct retourne True."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verifie qu'un mot de passe incorrect retourne False."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Verifie le comportement avec un mot de passe vide."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False

    def test_verify_password_none(self):
        """Verifie le comportement avec des valeurs None."""
        with pytest.raises(TypeError):
            verify_password(None, "hash")


class TestJWTTokens:
    """Tests pour les fonctions de tokens JWT."""

    def test_create_access_token_returns_string(self):
        """Verifie que create_access_token retourne une chaîne."""
        token = create_access_token(data={"sub": "1", "email": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Verifie la creation de token avec expiration personnalisee."""
        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(hours=1)
        )
        assert isinstance(token, str)

    def test_decode_access_token_valid(self):
        """Verifie le decodage d'un token valide."""
        data = {"sub": "1", "email": "test@example.com"}
        token = create_access_token(data=data)
        decoded = decode_access_token(token)
        
        assert decoded is not None
        assert decoded.get("sub") == "1"
        assert decoded.get("email") == "test@example.com"
        assert "exp" in decoded

    def test_decode_access_token_invalid(self):
        """Verifie le decodage d'un token invalide."""
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_access_token_malformed(self):
        """Verifie le decodage d'un token mal forme."""
        result = decode_access_token("not-a-jwt")
        assert result is None

    def test_decode_access_token_empty(self):
        """Verifie le decodage d'une chaîne vide."""
        result = decode_access_token("")
        assert result is None

    def test_token_contains_required_claims(self):
        """Verifie que le token contient les claims requis."""
        data = {"sub": "123", "email": "user@example.com"}
        token = create_access_token(data=data)
        decoded = decode_access_token(token)
        
        assert "sub" in decoded
        assert "email" in decoded
        assert "exp" in decoded


class TestSecureToken:
    """Tests pour la generation de tokens secures."""

    def test_generate_secure_token_returns_hex(self):
        """Verifie que generate_secure_token retourne de l'hexadecimal."""
        token = generate_secure_token()
        assert isinstance(token, str)
        # Les caracteres hexadecimaux sont 0-9 et a-f
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_secure_token_length(self):
        """Verifie la longueur du token genere."""
        token = generate_secure_token(length=16)
        # La longueur est multipliee par 2 pour l'hexadecimal
        assert len(token) == 32

    def test_generate_secure_token_unique(self):
        """Verifie que chaque token est unique."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        assert token1 != token2

    def test_generate_secure_token_default_length(self):
        """Verifie la longueur par defaut (32 octets -> 64 caracteres)."""
        token = generate_secure_token()
        assert len(token) == 64
