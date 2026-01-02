"""
Tests d'integration pour la base de donnees.
Teste la connexion et les operations de base.
"""
import pytest
from sqlalchemy import inspect

from app.database.session import engine, Base, get_db
from app.models.user import User
from app.models.password import PasswordEntry


class TestDatabaseConnection:
    """Tests pour la connexion a la base de donnees."""

    def test_engine_connected(self):
        """Verifie que le moteur est connecte."""
        assert engine.connect() is not None

    def test_tables_exist(self, db_session):
        """Verifie que les tables existent."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "users" in tables
        assert "password_entries" in tables

    def test_session_is_active(self, db_session):
        """Verifie que la session est active."""
        # Executer une requete simple
        result = db_session.execute("SELECT 1").fetchone()
        assert result[0] == 1

    def test_foreign_key_constraint(self, db_session, test_user):
        """Test la contrainte de cle etrangere."""
        from sqlalchemy.exc import IntegrityError
        
        entry = PasswordEntry(
            user_id=99999,  # ID inexistant
            service_name="InvalidFK",
            username="user",
            password_value="pass",
        )
        db_session.add(entry)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestDatabaseSession:
    """Tests pour la session de base de donnees."""

    def test_get_db_dependency(self, client):
        """Test la dependance get_db."""
        # La dependance doit fonctionner via le client de test
        response = client.get("/health")
        assert response.status_code == 200

    def test_transaction_rollback(self, db_session):
        """Test le rollback des transactions."""
        # Creer un utilisateur
        from app.core.security import hash_password
        
        user = User(
            email="rollback@test.com",
            hashed_password=hash_password("pass"),
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id
        
        # Rollback
        db_session.rollback()
        
        # Verifier que l'utilisateur n'existe pas
        found = db_session.query(User).filter_by(id=user_id).first()
        assert found is None


class TestBaseMetadata:
    """Tests pour les metadonnees de la base."""

    def test_base_is_declarative(self):
        """Verifie que Base est declaratif."""
        from sqlalchemy.ext.declarative import declarative_base
        
        assert Base is declarative_base()

    def test_user_table_name(self):
        """Verifie le nom de la table User."""
        assert User.__tablename__ == "users"

    def test_password_entry_table_name(self):
        """Verifie le nom de la table PasswordEntry."""
        assert PasswordEntry.__tablename__ == "password_entries"


class TestSchemaCreation:
    """Tests pour la creation du schema."""

    def test_create_all_tables(self, db_session):
        """Test la creation de toutes les tables."""
        # Les tables doivent exister (teste dans test_tables_exist)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert len(tables) >= 2
        assert "users" in tables
        assert "password_entries" in tables

    def test_indexes_exist(self, db_session):
        """Test que les index sont crees."""
        inspector = inspect(engine)
        
        # Verifier les index de users
        user_indexes = inspector.get_indexes("users")
        index_names = [idx["name"] for idx in user_indexes]
        
        # Doit y avoir un index sur email et id
        assert "ix_users_id" in index_names or any("id" in name for name in index_names)
        assert "ix_users_email" in index_names or any("email" in name for name in index_names)

    def test_password_entry_indexes(self, db_session):
        """Test les index de password_entries."""
        inspector = inspect(engine)
        indexes = inspector.get_indexes("password_entries")
        index_names = [idx["name"] for idx in indexes]
        
        # Doit y avoir un index sur user_id
        assert any("user_id" in name or "user" in name for name in index_names)
