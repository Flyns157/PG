import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_verifier,
    verify_verifier,
)


def test_token_round_trip() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id, timedelta(minutes=5))

    assert decode_access_token(token) == user_id


def test_token_contains_no_personal_data() -> None:
    token = create_access_token(uuid.uuid4(), timedelta(minutes=5))

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    assert payload.keys() == {"sub", "exp"}


def test_token_signed_with_another_key_is_rejected() -> None:
    expire = datetime.now(UTC) + timedelta(minutes=5)
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": expire}, "k" * 32, algorithm=ALGORITHM
    )

    assert decode_access_token(forged) is None


def test_unsigned_token_is_rejected() -> None:
    expire = datetime.now(UTC) + timedelta(minutes=5)
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": expire}, key=None, algorithm="none"
    )

    assert decode_access_token(forged) is None


def test_token_without_expiry_is_rejected() -> None:
    token = jwt.encode(
        {"sub": str(uuid.uuid4())}, settings.SECRET_KEY, algorithm=ALGORITHM
    )

    assert decode_access_token(token) is None


def test_token_with_invalid_subject_is_rejected() -> None:
    expire = datetime.now(UTC) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "not-a-uuid", "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM
    )

    assert decode_access_token(token) is None


def test_verifier_hashing() -> None:
    hashed = hash_verifier("v" * 64)

    assert hashed.startswith("$argon2")
    assert verify_verifier("v" * 64, hashed) == (True, None)
    assert verify_verifier("w" * 64, hashed)[0] is False


def test_long_verifier_is_not_truncated() -> None:
    hashed = hash_verifier("v" * 100 + "a")

    assert verify_verifier("v" * 100 + "b", hashed)[0] is False
