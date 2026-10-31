from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import DUMMY_HASH
from app.models import User
from app.services import user_service
from tests.utils.user import SALT, VERIFIER, login, register_user

PARAMETERS_URL = f"{settings.API_V1_STR}/login/parameters"


def test_login_returns_short_lived_token(client: TestClient) -> None:
    register_user(client, "alice@example.com")

    response = login(client, "alice@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_login_ignores_email_case(client: TestClient) -> None:
    register_user(client, "alice@example.com")

    assert login(client, "ALICE@example.com").status_code == 200


def test_login_failures_are_indistinguishable(client: TestClient, db: Session) -> None:
    register_user(client, "alice@example.com")
    register_user(client, "inactive@example.com")
    inactive = db.scalar(select(User).where(User.email == "inactive@example.com"))
    assert inactive is not None
    inactive.is_active = False
    db.commit()

    responses = [
        login(client, "alice@example.com", "wrong" * 10),
        login(client, "nobody@example.com"),
        login(client, "inactive@example.com"),
    ]

    assert {response.status_code for response in responses} == {401}
    assert len({response.json()["detail"] for response in responses}) == 1
    assert all(r.headers["WWW-Authenticate"] == "Bearer" for r in responses)


def test_unknown_account_still_verifies_a_hash(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    hashes: list[str] = []

    def spy(_: str, hashed: str) -> tuple[bool, None]:
        hashes.append(hashed)
        return False, None

    monkeypatch.setattr(user_service, "verify_verifier", spy)

    login(client, "nobody@example.com")

    assert hashes == [DUMMY_HASH]


def test_oversized_verifier_is_rejected_before_hashing(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    def fail(*_: str) -> None:
        raise AssertionError("le hachage ne doit pas être appelé")

    monkeypatch.setattr(user_service, "verify_verifier", fail)

    assert login(client, "alice@example.com", "x" * 257).status_code == 401


def test_legacy_bcrypt_hash_is_upgraded_at_login(
    client: TestClient, db: Session
) -> None:
    register_user(client, "alice@example.com")
    user = db.scalar(select(User).where(User.email == "alice@example.com"))
    assert user is not None
    user.hashed_verifier = PasswordHash((BcryptHasher(),)).hash(VERIFIER)
    db.commit()

    assert login(client, "alice@example.com").status_code == 200

    db.refresh(user)
    assert user.hashed_verifier.startswith("$argon2")


def test_credentials_in_query_string_are_not_accepted(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        params={"username": "alice@example.com", "password": VERIFIER},
    )

    assert response.status_code == 422


def test_parameters_of_existing_account(client: TestClient) -> None:
    register_user(client, "alice@example.com")

    response = client.post(PARAMETERS_URL, json={"email": "alice@example.com"})

    assert response.status_code == 200
    assert response.json() == {
        "algorithm": "scrypt",
        "salt": SALT,
        "n": 2**15,
        "r": 8,
        "p": 1,
    }


def test_parameters_of_unknown_account_are_a_stable_decoy(client: TestClient) -> None:
    first = client.post(PARAMETERS_URL, json={"email": "nobody@example.com"}).json()
    again = client.post(PARAMETERS_URL, json={"email": "NOBODY@example.com"}).json()
    other = client.post(PARAMETERS_URL, json={"email": "other@example.com"}).json()

    assert first == again
    assert first["salt"] != other["salt"]
    assert first.keys() == {"algorithm", "salt", "n", "r", "p"}


def test_login_is_rate_limited(client: TestClient) -> None:
    limiter.reset()
    limiter.enabled = True
    try:
        statuses = [login(client, "nobody@example.com").status_code for _ in range(6)]
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses == [401] * 5 + [429]
