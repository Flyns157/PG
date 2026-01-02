"""
Service métier pour l'authentification.

Ce module contient toute la logique métier liée à l'authentification
des utilisateurs : inscription, connexion et gestion des tokens.
"""
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    CredentialsException,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate


class AuthService:
    """
    Service d'authentification.

    Gère toutes les opérations liées à l'authentification des utilisateurs,
    y compris l'inscription, la connexion et la génération de tokens.
    """

    def __init__(self, db: Session):
        """
        Initialise le service avec une session de base de données.

        Args:
            db: Session SQLAlchemy pour les opérations de base de données.
        """
        self.db = db

    def register(self, user_data: UserCreate) -> User:
        """
        Enregistre un nouvel utilisateur.

        Args:
            user_data: Données de l'utilisateur à créer.

        Returns:
            L'utilisateur créé.

        Raises:
            ConflictException: Si un utilisateur avec cet email existe déjà.
        """
        # Vérifier si l'email existe déjà
        existing_user = self.db.query(User).filter(
            User.email == user_data.email
        ).first()

        if existing_user:
            raise ConflictException(
                detail=f"Un utilisateur avec l'email {user_data.email} existe déjà"
            )

        # Créer le nouvel utilisateur
        hashed_password = hash_password(user_data.password)

        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def authenticate(self, email: str, password: str) -> Token:
        """
        Authentifie un utilisateur et génère un token JWT.

        Args:
            email: Email de l'utilisateur.
            password: Mot de passe en clair.

        Returns:
            Token JWT d'accès.

        Raises:
            CredentialsException: Si les identifiants sont invalides.
        """
        # Récupérer l'utilisateur
        user = self.db.query(User).filter(User.email == email).first()

        if not user:
            raise CredentialsException(
                detail="Email ou mot de passe incorrect")

        if not user.is_active:
            raise CredentialsException(detail="Compte désactivé")

        # Vérifier le mot de passe
        if not verify_password(password, user.hashed_password):
            raise CredentialsException(
                detail="Email ou mot de passe incorrect")

        # Générer le token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Récupère un utilisateur par son ID.

        Args:
            user_id: ID de l'utilisateur à récupérer.

        Returns:
            L'utilisateur trouvé ou None.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son email.

        Args:
            email: Email de l'utilisateur à récupérer.

        Returns:
            L'utilisateur trouvé ou None.
        """
        return self.db.query(User).filter(User.email == email).first()
