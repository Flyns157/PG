"""
Routeur d'authentification FastAPI.

Ce module définit tous les endpoints liés à l'authentification :
inscription, connexion et gestion des tokens.
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.auth_service import AuthService


router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un nouvel utilisateur",
    description="Crée un nouveau compte utilisateur avec email et mot de passe.",
)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint d'inscription d'un nouvel utilisateur.

    Args:
        user_data: Données de l'utilisateur à créer.
        db: Session de base de données.

    Returns:
        L'utilisateur créé sans le mot de passe.
    """
    auth_service = AuthService(db)
    user = auth_service.register(user_data)

    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Connexion utilisateur",
    description="Authentifie un utilisateur et retourne un token JWT.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint de connexion avec OAuth2PasswordRequestForm standard.

    Args:
        form_data: Formulaire de connexion standard (username/password).
        db: Session de base de données.

    Returns:
        Token JWT d'accès.
    """
    auth_service = AuthService(db)
    token = auth_service.authenticate(
        email=form_data.username,  # OAuth2 utilise 'username' pour l'email
        password=form_data.password
    )

    return token


@router.post(
    "/login/json",
    response_model=Token,
    summary="Connexion utilisateur (JSON)",
    description="Authentifie un utilisateur avec un corps JSON et retourne un token JWT.",
)
async def login_json(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint de connexion alternatif avec JSON body.

    Utile pour les clients qui ne supportent pas OAuth2 form.

    Args:
        email: Email de l'utilisateur.
        password: Mot de passe de l'utilisateur.
        db: Session de base de données.

    Returns:
        Token JWT d'accès.
    """
    auth_service = AuthService(db)
    token = auth_service.authenticate(email=email, password=password)

    return token
