"""
Configuration globale des tests pytest.
Contient les fixtures partagees pour tous les tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import Base, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.password import PasswordEntry


# Configuration de la base de donnees en memoire pour les tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override de la dependance get_db pour les tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Application des overrides
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Fixture pour la session de base de donnees."""
    # Creation des tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Nettoyage apres chaque test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Fixture pour le client de test FastAPI."""
    def override_get_db_test():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db_test
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Fixture pour creer un utilisateur de test."""
    # Verification si l'utilisateur existe deja
    existing = db_session.query(User).filter(User.email == "test@example.com").first()
    if existing:
        return existing
    
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_2(db_session):
    """Fixture pour creer un deuxieme utilisateur de test."""
    from app.core.security import hash_password
    
    user = User(
        email="test2@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user):
    """Fixture pour generer un token JWT valide."""
    return create_access_token(data={"sub": str(test_user.id), "email": test_user.email})


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Fixture pour les headers d'authentification."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def auth_headers_2(test_user_2):
    """Fixture pour les headers d'authentification du deuxieme utilisateur."""
    token = create_access_token(data={"sub": str(test_user_2.id), "email": test_user_2.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_password(db_session, test_user):
    """Fixture pour creer un mot de passe de test."""
    password = PasswordEntry(
        user_id=test_user.id,
        service_name="TestService",
        username="testuser",
        password_value="testpassword123",
        notes="Test notes",
    )
    db_session.add(password)
    db_session.commit()
    db_session.refresh(password)
    return password
