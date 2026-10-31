import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models import User, VaultEntry
from tests.utils.user import SALT, VERIFIER, auth_headers, register_user, signup_payload
from tests.utils.vault_entry import entry_payload

USERS_URL = f"{settings.API_V1_STR}/users"
ENTRIES_URL = f"{settings.API_V1_STR}/vault-entries/"


def test_signup_never_exposes_or_stores_the_verifier(
    client: TestClient, db: Session
) -> None:
    body = register_user(client, "Alice@Example.com")

    assert body["email"] == "alice@example.com"
    assert body.keys() == {"id", "email", "is_active", "created_at"}
    user = db.get(User, uuid.UUID(body["id"]))
    assert user is not None
    assert user.hashed_verifier.startswith("$argon2")
    assert VERIFIER not in user.hashed_verifier


def test_signup_with_existing_email_conflicts(client: TestClient) -> None:
    register_user(client, "alice@example.com")

    response = client.post(
        f"{USERS_URL}/signup", json=signup_payload("ALICE@example.com")
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"auth_verifier": "short"},
        {"email": "not-an-email"},
        {"password": "extra-field"},
        {"kdf": {"salt": "pas du base64!"}},
        {"kdf": {"salt": "c2hvcnQ="}},
        {"kdf": {"salt": SALT, "n": 2**14}},
        {"kdf": {"salt": SALT, "n": 2**15 + 1}},
        {"kdf": {"salt": SALT, "r": 1}},
        {"kdf": {"salt": SALT, "algorithm": "md5"}},
    ],
)
def test_signup_rejects_invalid_payloads(
    client: TestClient, overrides: dict[str, Any]
) -> None:
    payload = signup_payload("alice@example.com", **overrides)

    assert client.post(f"{USERS_URL}/signup", json=payload).status_code == 422


def test_read_me(client: TestClient, user_headers: dict[str, str]) -> None:
    response = client.get(f"{USERS_URL}/me", headers=user_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def _token_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get(f"{USERS_URL}/me").status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        create_access_token(uuid.uuid4(), timedelta(minutes=5)),
        create_access_token(uuid.uuid4(), timedelta(minutes=-5)),
    ],
    ids=["malformed", "unknown-user", "expired"],
)
def test_me_rejects_invalid_tokens(client: TestClient, token: str) -> None:
    response = client.get(f"{USERS_URL}/me", headers=_token_headers(token))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_deactivated_user_loses_access(
    client: TestClient, db: Session, user_headers: dict[str, str]
) -> None:
    user = db.scalar(select(User).where(User.email == "alice@example.com"))
    assert user is not None
    user.is_active = False
    db.commit()

    assert client.get(f"{USERS_URL}/me", headers=user_headers).status_code == 401


def test_delete_me_removes_the_whole_vault(
    client: TestClient, db: Session, user_headers: dict[str, str]
) -> None:
    client.post(ENTRIES_URL, json=entry_payload(), headers=user_headers)

    response = client.delete(f"{USERS_URL}/me", headers=user_headers)

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(VaultEntry)) == 0
    assert client.get(f"{USERS_URL}/me", headers=user_headers).status_code == 401
    # L'adresse redevient disponible.
    register_user(client, "alice@example.com")
    assert auth_headers(client, "alice@example.com")
