"""
Tests d'integration pour les models de base de donnees.
Teste la creation, lecture et relations des models.
"""
import pytest
from datetime import datetime

from app.models.user import User
from app.models.password import PasswordEntry
from app.core.security import hash_password


class TestUserModel:
    """Tests pour le modele User."""

    def test_create_user(self, db_session):
        """Test la creation d'un utilisateur."""
        user = User(
            email="newuser@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.hashed_password != "password123"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)

    def test_user_email_unique(self, db_session, test_user):
        """Test la contrainte d'unicite de l'email."""
        from sqlalchemy.exc import IntegrityError
        
        user2 = User(
            email=test_user.email,  # Email deja utilise
            hashed_password=hash_password("password123"),
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_user_password_is_hashed(self, db_session):
        """Test que le mot de passe est hache."""
        plain_password = "MySecretPassword123"
        user = User(
            email="hash@test.com",
            hashed_password=hash_password(plain_password),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.hashed_password != plain_password
        assert len(user.hashed_password) > len(plain_password)

    def test_user_default_active(self, db_session):
        """Test que is_active est True par defaut."""
        user = User(
            email="default@test.com",
            hashed_password="hash",
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active is True

    def test_user_repr(self, test_user):
        """Test la representation de l'utilisateur."""
        repr_str = repr(test_user)
        assert "User" in repr_str
        assert str(test_user.id) in repr_str
        assert test_user.email in repr_str


class TestPasswordEntryModel:
    """Tests pour le modele PasswordEntry."""

    def test_create_password_entry(self, db_session, test_user):
        """Test la creation d'une entre de mot de passe."""
        entry = PasswordEntry(
            user_id=test_user.id,
            service_name="TestService",
            username="testuser",
            password_value="secretpassword123",
            notes="Test notes",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        assert entry.id is not None
        assert entry.user_id == test_user.id
        assert entry.service_name == "TestService"
        assert entry.username == "testuser"
        assert entry.password_value == "secretpassword123"
        assert entry.notes == "Test notes"
        assert isinstance(entry.created_at, datetime)

    def test_password_entry_without_notes(self, db_session, test_user):
        """Test la creation sans notes."""
        entry = PasswordEntry(
            user_id=test_user.id,
            service_name="NoNotes",
            username="user",
            password_value="pass",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        
        assert entry.notes is None

    def test_password_entry_foreign_key(self, db_session, test_user):
        """Test la cle etrangere vers User."""
        entry = PasswordEntry(
            user_id=test_user.id,
            service_name="FKTest",
            username="user",
            password_value="pass",
        )
        db_session.add(entry)
        db_session.commit()
        
        assert entry.user_id == test_user.id

    def test_password_entry_repr(self, sample_password):
        """Test la representation de l'entree."""
        repr_str = repr(sample_password)
        assert "PasswordEntry" in repr_str
        assert str(sample_password.id) in repr_str
        assert sample_password.service_name in repr_str


class TestUserPasswordRelation:
    """Tests pour la relation User -> PasswordEntry."""

    def test_user_passwords_relationship(self, db_session, test_user, sample_password):
        """Test la relation entre User et PasswordEntry."""
        db_session.refresh(test_user)
        
        assert sample_password in test_user.passwords.all()

    def test_cascade_delete(self, db_session, test_user):
        """Test la suppression en cascade."""
        entry = PasswordEntry(
            user_id=test_user.id,
            service_name="CascadeTest",
            username="user",
            password_value="pass",
        )
        db_session.add(entry)
        db_session.commit()
        entry_id = entry.id
        
        # Supprimer l'utilisateur
        db_session.delete(test_user)
        db_session.commit()
        
        # Verifier que l'entree est supprimee
        deleted_entry = db_session.query(PasswordEntry).filter_by(id=entry_id).first()
        assert deleted_entry is None

    def test_multiple_passwords_for_user(self, db_session, test_user):
        """Test que plusieurs entrees peuvent appartenir au meme utilisateur."""
        entries = []
        for i in range(3):
            entry = PasswordEntry(
                user_id=test_user.id,
                service_name=f"Service{i}",
                username="user",
                password_value=f"pass{i}",
            )
            db_session.add(entry)
            entries.append(entry)
        
        db_session.commit()
        
        for entry in entries:
            db_session.refresh(entry)
            assert entry.user_id == test_user.id
