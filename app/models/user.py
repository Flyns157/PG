"""
Modèle SQLAlchemy pour les utilisateurs.

Ce module définit la table des utilisateurs avec les champs nécessaires
à l'authentification et à la gestion des mots de passe.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.database.session import Base


class User(Base):
    """
    Modèle de table pour les utilisateurs.

    Attributes:
        id: Identifiant unique de l'utilisateur.
        email: Adresse email unique de l'utilisateur.
        hashed_password: Mot de passe haché de l'utilisateur.
        is_active: Indique si le compte est actif.
        created_at: Date de création du compte.
        updated_at: Date de dernière modification.
        passwords: Relation avec les entrées de mots de passe.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now,
                        onupdate=datetime.now)

    # Relation avec les entrées de mots de passe
    passwords = relationship(
        "PasswordEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
