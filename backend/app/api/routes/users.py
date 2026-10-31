from typing import Any

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.user import UserPublic, UserRegister
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register_user(
    request: Request,  # noqa: ARG001
    session: SessionDep,
    user_in: UserRegister,
) -> Any:
    """
    Crée un compte à partir du vérificateur et des paramètres de dérivation.
    """
    return user_service.create_user(session=session, user_in=user_in)


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Compte connecté.
    """
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> None:
    """
    Supprime le compte connecté et tout son coffre.
    """
    user_service.delete_user(session=session, user=current_user)
