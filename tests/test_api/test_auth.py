"""
Tests d'API pour l'authentification.
Teste les endpoints d'inscription et de connexion.
"""
import pytest


class TestSignupEndpoint:
    """Tests pour l'endpoint POST /auth/signup."""

    def test_signup_success(self, client):
        """Test l'inscription avec des donnees valides."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "StrongPass123!",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data
        assert data["is_active"] is True

    def test_signup_duplicate_email(self, client, test_user):
        """Test l'inscription avec un email deja utilise."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user.email,
                "password": "StrongPass123!",
            }
        )
        
        assert response.status_code == 409
        assert "existe déjà" in response.json()["detail"]

    def test_signup_invalid_email(self, client):
        """Test l'inscription avec un email invalide."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "invalid-email",
                "password": "StrongPass123!",
            }
        )
        
        assert response.status_code == 422

    def test_signup_short_password(self, client):
        """Test l'inscription avec un mot de passe trop court."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user@example.com",
                "password": "short",
            }
        )
        
        assert response.status_code == 422

    def test_signup_empty_password(self, client):
        """Test l'inscription avec un mot de passe vide."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user@example.com",
                "password": "",
            }
        )
        
        assert response.status_code == 422

    def test_signup_missing_email(self, client):
        """Test l'inscription sans email."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "password": "StrongPass123!",
            }
        )
        
        assert response.status_code == 422

    def test_signup_missing_password(self, client):
        """Test l'inscription sans mot de passe."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user@example.com",
            }
        )
        
        assert response.status_code == 422

    def test_signup_multiple_users(self, client):
        """Test la creation de plusieurs utilisateurs."""
        # Premier utilisateur
        response1 = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user1@example.com",
                "password": "Pass123456!",
            }
        )
        assert response1.status_code == 201
        
        # Deuxieme utilisateur
        response2 = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user2@example.com",
                "password": "Pass123456!",
            }
        )
        assert response2.status_code == 201
        
        # Les emails doivent etre differents
        assert response1.json()["email"] != response2.json()["email"]


class TestLoginEndpoint:
    """Tests pour l'endpoint POST /auth/login (form data)."""

    def test_login_success(self, client, test_user):
        """Test la connexion avec des identifiants valides."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_wrong_password(self, client, test_user):
        """Test la connexion avec un mauvais mot de passe."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test la connexion avec un utilisateur inexistant."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123",
            }
        )
        
        assert response.status_code == 401

    def test_login_empty_password(self, client, test_user):
        """Test la connexion avec un mot de passe vide."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "",
            }
        )
        
        assert response.status_code == 401


class TestLoginJsonEndpoint:
    """Tests pour l'endpoint POST /auth/login/json (JSON body)."""

    def test_login_json_success(self, client, test_user):
        """Test la connexion JSON avec des identifiants valides."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_json_wrong_password(self, client, test_user):
        """Test la connexion JSON avec un mauvais mot de passe."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            }
        )
        
        assert response.status_code == 401


class TestHealthEndpoint:
    """Tests pour les endpoints de sante."""

    def test_root_endpoint(self, client):
        """Test l'endpoint racine."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "documentation" in data

    def test_health_endpoint(self, client):
        """Test l'endpoint de sante."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
