"""
Configuration de la base de données SQLAlchemy.

Ce module configure le moteur SQLAlchemy, les sessions,
et les modèles de base pour l'ensemble de l'application.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings


# Création du moteur SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Classe de base pour les modèles
Base = declarative_base()

# Fabricant de sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Générateur de sessions de base de données pour les dépendances FastAPI.

    Usage:
        @app.get("/")
        async def endpoint(db: Session = Depends(get_db)):
            ...

    Yields:
        Session: Une session SQLAlchemy valide.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialise la base de données.

    Crée toutes les tables définies dans les modèles si elles n'existent pas.
    """
    Base.metadata.create_all(bind=engine)
