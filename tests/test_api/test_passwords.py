"""
Tests d'API pour la gestion des mots de passe.
Teste les endpoints CRUD avec authentification.
"""
import pytest


class TestCreatePassword:
    """Tests pour POST /api/v1/passwords/."""

    def test_create_password_success(self, client, auth_headers):
        """Test la creation d'un mot de passe avec auth."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "username": "testuser",
                "password_value": "MySecretPassword123",
                "notes": "Compte principal",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["service_name"] == "Gmail"
        assert data["username"] == "testuser"
        assert data["notes"] == "Compte principal"
        assert "id" in data
        assert "created_at" in data

    def test_create_password_no_auth(self, client):
        """Test la creation sans authentification."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "username": "testuser",
                "password_value": "password123",
            },
        )
        
        assert response.status_code == 401

    def test_create_password_invalid_token(self, client):
        """Test avec un token invalide."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "username": "testuser",
                "password_value": "password123",
            },
            headers={"Authorization": "Bearer invalidtoken"},
        )
        
        assert response.status_code == 401

    def test_create_password_missing_service(self, client, auth_headers):
        """Test avec un nom de service manquant."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "username": "testuser",
                "password_value": "password123",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 422

    def test_create_password_missing_username(self, client, auth_headers):
        """Test avec un nom d'utilisateur manquant."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "password_value": "password123",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 422

    def test_create_password_missing_password(self, client, auth_headers):
        """Test avec un mot de passe manquant."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "username": "testuser",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 422

    def test_create_password_without_notes(self, client, auth_headers):
        """Test la creation sans notes."""
        response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Facebook",
                "username": "testuser",
                "password_value": "password123",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["notes"] is None


class TestListPasswords:
    """Tests pour GET /api/v1/passwords/."""

    def test_list_passwords_success(self, client, auth_headers, sample_password):
        """Test la liste des mots de passe."""
        response = client.get(
            "/api/v1/passwords/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["items"], list)

    def test_list_passwords_empty(self, client, auth_headers):
        """Test la liste vide."""
        response = client.get(
            "/api/v1/passwords/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_list_passwords_no_auth(self, client):
        """Test la liste sans authentification."""
        response = client.get("/api/v1/passwords/")
        
        assert response.status_code == 401

    def test_list_passwords_pagination(self, client, auth_headers):
        """Test la pagination des resultats."""
        # Creer plusieurs entrees
        for i in range(5):
            client.post(
                "/api/v1/passwords/",
                json={
                    "service_name": f"Service{i}",
                    "username": "user",
                    "password_value": f"pass{i}",
                },
                headers=auth_headers,
            )
        
        # Tester avec limit et skip
        response = client.get(
            "/api/v1/passwords/?skip=0&limit=3",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] >= 5
        assert data["skip"] == 0
        assert data["limit"] == 3

    def test_list_passwords_search(self, client, auth_headers):
        """Test la recherche dans la liste."""
        # Creer des entrees
        client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Gmail",
                "username": "user1",
                "password_value": "pass1",
            },
            headers=auth_headers,
        )
        client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "Facebook",
                "username": "user2",
                "password_value": "pass2",
            },
            headers=auth_headers,
        )
        
        # Rechercher
        response = client.get(
            "/api/v1/passwords/?search=Gmail",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all("Gmail" in item["service_name"] for item in data["items"])

    def test_data_isolation_between_users(self, client, auth_headers, auth_headers_2, db_session, test_user):
        """Test l'isolation des donnees entre utilisateurs."""
        # Utilisateur 1 cree un mot de passe
        response1 = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "PrivateService",
                "username": "user1",
                "password_value": "secret1",
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201
        private_id = response1.json()["id"]
        
        # Utilisateur 2 demande la liste
        response2 = client.get(
            "/api/v1/passwords/",
            headers=auth_headers_2,
        )
        
        assert response2.status_code == 200
        data = response2.json()
        # L'entree de l'utilisateur 1 ne doit pas apparaitre
        for item in data["items"]:
            assert item["id"] != private_id


class TestGetPassword:
    """Tests pour GET /api/v1/passwords/{id}."""

    def test_get_password_success(self, client, auth_headers, sample_password):
        """Test la recuperation d'un mot de passe."""
        response = client.get(
            f"/api/v1/passwords/{sample_password.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_password.id
        assert data["service_name"] == sample_password.service_name

    def test_get_password_not_found(self, client, auth_headers):
        """Test la recuperation d'un mot de passe inexistant."""
        response = client.get(
            "/api/v1/passwords/99999",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    def test_get_password_no_auth(self, client, sample_password):
        """Test la recuperation sans authentification."""
        response = client.get(f"/api/v1/passwords/{sample_password.id}")
        
        assert response.status_code == 401

    def test_get_password_other_user_forbidden(self, client, auth_headers_2, sample_password):
        """Test l'acces refuse a un mot de passe d'un autre utilisateur."""
        response = client.get(
            f"/api/v1/passwords/{sample_password.id}",
            headers=auth_headers_2,
        )
        
        assert response.status_code == 403


class TestUpdatePassword:
    """Tests pour PUT /api/v1/passwords/{id}."""

    def test_update_password_success(self, client, auth_headers, sample_password):
        """Test la mise a jour d'un mot de passe."""
        response = client.put(
            f"/api/v1/passwords/{sample_password.id}",
            json={
                "service_name": "UpdatedService",
                "username": "updateduser",
                "password_value": "newpassword123",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "UpdatedService"
        assert data["username"] == "updateduser"

    def test_update_password_partial(self, client, auth_headers, sample_password):
        """Test la mise a jour partielle."""
        response = client.patch(
            f"/api/v1/passwords/{sample_password.id}",
            json={
                "service_name": "PartiallyUpdated",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "PartiallyUpdated"

    def test_update_password_not_found(self, client, auth_headers):
        """Test la mise a jour d'un mot de passe inexistant."""
        response = client.put(
            "/api/v1/passwords/99999",
            json={
                "service_name": "Test",
                "username": "user",
                "password_value": "pass",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    def test_update_password_no_auth(self, client, sample_password):
        """Test la mise a jour sans authentification."""
        response = client.put(
            f"/api/v1/passwords/{sample_password.id}",
            json={
                "service_name": "Test",
                "username": "user",
                "password_value": "pass",
            },
        )
        
        assert response.status_code == 401

    def test_update_password_other_user_forbidden(self, client, auth_headers_2, sample_password):
        """Test la mise a jour refusee pour un autre utilisateur."""
        response = client.put(
            f"/api/v1/passwords/{sample_password.id}",
            json={
                "service_name": "Hacked",
                "username": "hacker",
                "password_value": "hacked",
            },
            headers=auth_headers_2,
        )
        
        assert response.status_code == 403


class TestDeletePassword:
    """Tests pour DELETE /api/v1/passwords/{id}."""

    def test_delete_password_success(self, client, auth_headers, db_session, test_user):
        """Test la suppression d'un mot de passe."""
        # Creer un mot de passe a supprimer
        create_response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "ToDelete",
                "username": "user",
                "password_value": "pass",
            },
            headers=auth_headers,
        )
        password_id = create_response.json()["id"]
        
        # Supprimer
        response = client.delete(
            f"/api/v1/passwords/{password_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 204
        
        # Verifier la suppression
        get_response = client.get(
            f"/api/v1/passwords/{password_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_password_not_found(self, client, auth_headers):
        """Test la suppression d'un mot de passe inexistant."""
        response = client.delete(
            "/api/v1/passwords/99999",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    def test_delete_password_no_auth(self, client, sample_password):
        """Test la suppression sans authentification."""
        response = client.delete(f"/api/v1/passwords/{sample_password.id}")
        
        assert response.status_code == 401

    def test_delete_password_other_user_forbidden(self, client, auth_headers_2, sample_password):
        """Test la suppression refusee pour un autre utilisateur."""
        response = client.delete(
            f"/api/v1/passwords/{sample_password.id}",
            headers=auth_headers_2,
        )
        
        assert response.status_code == 403


class TestPasswordEndpointsCombined:
    """Tests combines pour les endpoints de mots de passe."""

    def test_full_crud_cycle(self, client, auth_headers):
        """Test un cycle complet CRUD."""
        # 1. Create
        create_response = client.post(
            "/api/v1/passwords/",
            json={
                "service_name": "CRUDTest",
                "username": "cruduser",
                "password_value": "crudpass",
                "notes": "CRUD test entry",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        created_id = create_response.json()["id"]
        
        # 2. Read
        read_response = client.get(
            f"/api/v1/passwords/{created_id}",
            headers=auth_headers,
        )
        assert read_response.status_code == 200
        assert read_response.json()["service_name"] == "CRUDTest"
        
        # 3. Update
        update_response = client.put(
            f"/api/v1/passwords/{created_id}",
            json={
                "service_name": "CRUDUpdated",
                "username": "updateduser",
                "password_value": "updatedpass",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["service_name"] == "CRUDUpdated"
        
        # 4. Delete
        delete_response = client.delete(
            f"/api/v1/passwords/{created_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204
        
        # 5. Verify deletion
        verify_response = client.get(
            f"/api/v1/passwords/{created_id}",
            headers=auth_headers,
        )
        assert verify_response.status_code == 404
