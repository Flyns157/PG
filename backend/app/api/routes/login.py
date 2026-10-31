from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.schemas.user import KdfParameters, KdfParametersRequest, Token
from app.services import user_service

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/parameters")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def read_kdf_parameters(
    request: Request,  # noqa: ARG001
    session: SessionDep,
    body: KdfParametersRequest,
) -> KdfParameters:
    """
    Paramètres de dérivation d'un compte, à appeler avant la connexion.

    Un compte inexistant reçoit un sel leurre stable, pour ne pas révéler son absence.
    """
    return user_service.get_kdf_parameters(session=session, email=body.email)


@router.post("/access-token")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login_access_token(
    request: Request,  # noqa: ARG001
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    Connexion OAuth2 : `username` est l'email, `password` le vérificateur dérivé.
    """
    user = user_service.authenticate(
        session=session, email=form_data.username, verifier=form_data.password
    )
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(user.id, expires),
        expires_in=int(expires.total_seconds()),
    )
