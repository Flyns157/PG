from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.exceptions import (
    DomainError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    VaultEntryNotFoundError,
)

STATUS_CODES: dict[type[Exception], int] = {
    EmailAlreadyRegisteredError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    VaultEntryNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    status_code = STATUS_CODES[type(exc)]
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if status_code == status.HTTP_401_UNAUTHORIZED
        else None
    )
    return JSONResponse(
        status_code=status_code, content={"detail": str(exc)}, headers=headers
    )


def _handle_rate_limit(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Trop de tentatives, réessayez plus tard"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
