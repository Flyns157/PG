import base64
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings

VERIFIER = "a" * 64
SALT = base64.b64encode(b"0123456789abcdef").decode()


def signup_payload(address: str, **overrides: Any) -> dict[str, Any]:
    return {
        "email": address,
        "auth_verifier": VERIFIER,
        "kdf": {"algorithm": "scrypt", "salt": SALT, "n": 2**15, "r": 8, "p": 1},
    } | overrides


def register_user(client: TestClient, email: str) -> dict[str, Any]:
    response = client.post(
        f"{settings.API_V1_STR}/users/signup", json=signup_payload(email)
    )
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def login(client: TestClient, email: str, verifier: str = VERIFIER) -> Any:
    return client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": verifier},
    )


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    token = login(client, email).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
