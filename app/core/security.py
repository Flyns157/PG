"""
Fonctions de sécurité pour l'authentification et le chiffrement.

Ce module contient toutes les fonctions liées à la sécurité :
- Hachage des mots de passe avec bcrypt
- Génération et vérification des tokens JWT
- Fonctions utilitaires de sécurité
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Contexte de hachage bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hache un mot de passe en utilisant bcrypt.

    Args:
        password: Le mot de passe en clair à hacher.

    Returns:
        Le mot de passe haché sous forme de chaîne.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair correspond à un mot de passe haché.

    Args:
        plain_password: Le mot de passe en clair à vérifier.
        hashed_password: Le mot de passe haché à comparer.

    Returns:
        True si les mots de passe correspondent, False sinon.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crée un token JWT d'accès.

    Args:
        data: Les données à encoder dans le token (doit inclure 'sub' pour le sujet).
        expires_delta: Durée optionnelle de validité du token.

    Returns:
        Le token JWT encodé sous forme de chaîne.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Décode et vérifie un token JWT.

    Args:
        token: Le token JWT à décoder.

    Returns:
        Les données décodées si le token est valide, None sinon.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_secure_token(length: int = 32) -> str:
    """
    Génère un token sécurisé aléatoire.

    Args:
        length: La longueur du token en octets (multipliée par 2 pour les caractères hex).

    Returns:
        Une chaîne hexadécimale aléatoire.
    """
    import secrets
    return secrets.token_hex(length)
