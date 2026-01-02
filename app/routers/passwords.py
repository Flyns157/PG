"""
Routeur de gestion des mots de passe FastAPI.

Ce module définit tous les endpoints pour la gestion CRUD
des entrées de mots de passe avec authentification.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.password import (
    PasswordCreate,
    PasswordUpdate,
    PasswordResponse,
    PasswordListResponse,
)
from app.services.password_service import PasswordService


router = APIRouter()

# Scheme de sécurité pour JWT avec auto_error=False pour gérer nous-mêmes l'erreur
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        bearer_scheme)
) -> User:
    """
    Dépendance pour obtenir l'utilisateur actuel à partir du token JWT.

    Args:
        db: Session de base de données.
        credentials: Credentials HTTP Bearer optionnel.

    Returns:
        L'utilisateur correspondant au token.

    Raises:
        HTTPException: Si le token est manquant, invalide ou expiré.
    """
    # Vérifier si le token est présent
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extraire le token
    token = credentials.credentials

    # Décoder le token
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Récupérer l'utilisateur
    user = db.query(User).filter(User.id == int(user_id)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte désactivé",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.get(
    "/",
    response_model=PasswordListResponse,
    summary="Liste des mots de passe",
    description="Récupère la liste paginée des mots de passe de l'utilisateur.",
)
async def list_passwords(
    skip: int = Query(0, ge=0, description="Nombre d'entrées à sauter"),
    limit: int = Query(100, ge=1, le=100,
                       description="Nombre maximum d'entrées"),
    search: Optional[str] = Query(
        None, description="Rechercher par service ou nom d'utilisateur"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les mots de passe de l'utilisateur avec pagination.

    Args:
        skip: Offset pour la pagination.
        limit: Nombre maximum de résultats.
        search: Terme de recherche optionnel.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        Liste des mots de passe avec pagination.
    """
    service = PasswordService(db, current_user.id)
    entries, total = service.get_all(skip=skip, limit=limit, search=search)

    return PasswordListResponse(
        items=[PasswordResponse.model_validate(e) for e in entries],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=PasswordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un mot de passe",
    description="Crée une nouvelle entrée de mot de passe.",
)
async def create_password(
    password_data: PasswordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crée une nouvelle entrée de mot de passe pour l'utilisateur.

    Args:
        password_data: Données du mot de passe à créer.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        L'entrée de mot de passe créée.
    """
    service = PasswordService(db, current_user.id)
    entry = service.create(password_data)

    return PasswordResponse.model_validate(entry)


@router.get(
    "/{entry_id}",
    response_model=PasswordResponse,
    summary="Récupérer un mot de passe",
    description="Récupère une entrée de mot de passe spécifique.",
)
async def get_password(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère une entrée de mot de passe spécifique par son ID.

    Args:
        entry_id: ID de l'entrée à récupérer.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        L'entrée de mot de passe demandée.
    """
    service = PasswordService(db, current_user.id)
    entry = service.get_by_id(entry_id)

    return PasswordResponse.model_validate(entry)


@router.put(
    "/{entry_id}",
    response_model=PasswordResponse,
    summary="Modifier un mot de passe",
    description="Met à jour une entrée de mot de passe existante.",
)
async def update_password(
    entry_id: int,
    update_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour une entrée de mot de passe existante.

    Args:
        entry_id: ID de l'entrée à modifier.
        update_data: Données de mise à jour.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        L'entrée de mot de passe mise à jour.
    """
    service = PasswordService(db, current_user.id)
    entry = service.update(entry_id, update_data)

    return PasswordResponse.model_validate(entry)


@router.patch(
    "/{entry_id}",
    response_model=PasswordResponse,
    summary="Modifier partiellement un mot de passe",
    description="Met à jour partiellement une entrée de mot de passe.",
)
async def partial_update_password(
    entry_id: int,
    update_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour partiellement une entrée de mot de passe.
    Identique à PUT mais permet de ne fournir que les champs à modifier.

    Args:
        entry_id: ID de l'entrée à modifier.
        update_data: Données de mise à jour partielle.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        L'entrée de mot de passe mise à jour.
    """
    service = PasswordService(db, current_user.id)
    entry = service.update(entry_id, update_data)

    return PasswordResponse.model_validate(entry)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un mot de passe",
    description="Supprime une entrée de mot de passe.",
)
async def delete_password(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Supprime une entrée de mot de passe.

    Args:
        entry_id: ID de l'entrée à supprimer.
        db: Session de base de données.
        current_user: Utilisateur connecté.

    Returns:
        Réponse vide avec status 204.
    """
    service = PasswordService(db, current_user.id)
    service.delete(entry_id)

    return None
