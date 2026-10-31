from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.security import (
    DUMMY_HASH,
    MAX_VERIFIER_LENGTH,
    derive_decoy_salt,
    hash_verifier,
    verify_verifier,
)
from app.models import User
from app.schemas.user import KdfParameters, UserRegister


def get_user_by_email(*, session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower()))


def create_user(*, session: Session, user_in: UserRegister) -> User:
    user = User(
        email=user_in.email.lower(),
        hashed_verifier=hash_verifier(user_in.auth_verifier),
        kdf_algorithm=user_in.kdf.algorithm,
        kdf_salt=user_in.kdf.salt,
        kdf_n=user_in.kdf.n,
        kdf_r=user_in.kdf.r,
        kdf_p=user_in.kdf.p,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise EmailAlreadyRegisteredError from None
    session.refresh(user)
    return user


def authenticate(*, session: Session, email: str, verifier: str) -> User:
    # Le formulaire OAuth2 n'impose pas de taille : Argon2 ne doit pas la subir.
    if len(verifier) > MAX_VERIFIER_LENGTH:
        raise InvalidCredentialsError

    user = get_user_by_email(session=session, email=email)
    if user is None:
        verify_verifier(verifier, DUMMY_HASH)
        raise InvalidCredentialsError

    verified, updated_hash = verify_verifier(verifier, user.hashed_verifier)
    if not verified or not user.is_active:
        raise InvalidCredentialsError

    if updated_hash:
        user.hashed_verifier = updated_hash
        session.commit()
    return user


def get_kdf_parameters(*, session: Session, email: str) -> KdfParameters:
    user = get_user_by_email(session=session, email=email)
    if user is None:
        return KdfParameters(salt=derive_decoy_salt(email.lower()))
    return KdfParameters(
        algorithm="scrypt",
        salt=user.kdf_salt,
        n=user.kdf_n,
        r=user.kdf_r,
        p=user.kdf_p,
    )


def delete_user(*, session: Session, user: User) -> None:
    session.delete(user)
    session.commit()
