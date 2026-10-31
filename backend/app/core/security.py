import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

ALGORITHM = "HS256"
KDF_SALT_BYTES = 16
MAX_VERIFIER_LENGTH = 256

# Le premier hacheur sert aux nouveaux hachages, les suivants à la vérification.
verifier_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

# Vérifié quand le compte n'existe pas, pour égaliser le temps de réponse.
DUMMY_HASH = verifier_hash.hash(secrets.token_urlsafe(32))


def hash_verifier(verifier: str) -> str:
    return verifier_hash.hash(verifier)


def verify_verifier(verifier: str, hashed_verifier: str) -> tuple[bool, str | None]:
    return verifier_hash.verify_and_update(verifier, hashed_verifier)


def create_access_token(subject: uuid.UUID, expires_delta: timedelta) -> str:
    payload = {"sub": str(subject), "exp": datetime.now(UTC) + expires_delta}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None


def derive_decoy_salt(email: str) -> str:
    """Sel stable pour un compte inexistant, indiscernable d'un vrai sel."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(), f"kdf-salt:{email}".encode(), hashlib.sha256
    ).digest()
    return base64.b64encode(digest[:KDF_SALT_BYTES]).decode()
