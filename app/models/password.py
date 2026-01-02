"""
Modèle SQLAlchemy pour les entrées de mots de passe.

Ce module définit la table des entrées de mots de passe avec
les informations de service et les identifiants stockés.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class PasswordEntry(Base):
    """
    Modèle de table pour les entrées de mots de passe.

    Chaque entrée appartient à un utilisateur et contient les
    informations de connexion pour un service spécifique.

    Attributes:
        id: Identifiant unique de l'entrée.
        user_id: Clé étrangère vers l'utilisateur propriétaire.
        service_name: Nom du service (ex: "Gmail", "Facebook").
        username: Nom d'utilisateur pour ce service.
        password_value: Le mot de passe (stocké en clair, chiffré en production).
        notes: Notes optionnelles pour l'entrée.
        created_at: Date de création de l'entrée.
        updated_at: Date de dernière modification.
        user: Relation avec l'utilisateur propriétaire.
    """
    __tablename__ = "password_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False, index=True)
    service_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password_value = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now,
                        onupdate=datetime.now)

    # Relation avec l'utilisateur
    user = relationship("User", back_populates="passwords")

    def __repr__(self):
        return f"<PasswordEntry(id={self.id}, service={self.service_name}, user={self.username})>"
