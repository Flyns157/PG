import base64
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import VaultEntry
from tests.utils.vault_entry import entry_payload

URL = f"{settings.API_V1_STR}/vault-entries/"


def _create(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(URL, json=entry_payload(), headers=headers)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def test_full_cycle(client: TestClient, user_headers: dict[str, str]) -> None:
    payload = entry_payload()
    created = client.post(URL, json=payload, headers=user_headers).json()
    entry_url = f"{URL}{created['id']}"

    read = client.get(entry_url, headers=user_headers)
    assert read.status_code == 200
    assert read.json()["ciphertext"] == payload["ciphertext"]
    assert read.json()["nonce"] == payload["nonce"]

    replacement = entry_payload()
    replaced = client.put(entry_url, json=replacement, headers=user_headers)
    assert replaced.status_code == 200
    assert replaced.json()["ciphertext"] == replacement["ciphertext"]
    assert replaced.json()["nonce"] == replacement["nonce"]

    assert client.delete(entry_url, headers=user_headers).status_code == 204
    assert client.get(entry_url, headers=user_headers).status_code == 404


def test_server_stores_only_what_the_client_encrypted(
    client: TestClient, db: Session, user_headers: dict[str, str]
) -> None:
    payload = entry_payload()
    client.post(URL, json=payload, headers=user_headers)

    entry = db.scalar(select(VaultEntry))

    assert entry is not None
    assert entry.ciphertext == payload["ciphertext"]
    assert not {"service_name", "username", "password_value", "notes"} & set(
        VaultEntry.__table__.columns.keys()
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"service_name": "Gmail"},
        {"password_value": "en-clair"},
        {"ciphertext": "pas du base64!"},
        {"ciphertext": base64.b64encode(b"court").decode()},
        {"ciphertext": base64.b64encode(b"x" * (64 * 1024 + 1)).decode()},
        {"nonce": base64.b64encode(b"court").decode()},
        {"algorithm": "ROT13"},
    ],
    ids=[
        "plain-service",
        "plain-password",
        "not-base64",
        "too-short",
        "too-long",
        "bad-nonce",
        "bad-algorithm",
    ],
)
def test_invalid_payloads_are_rejected(
    client: TestClient, user_headers: dict[str, str], overrides: dict[str, Any]
) -> None:
    response = client.post(URL, json=entry_payload(**overrides), headers=user_headers)

    assert response.status_code == 422


def test_routes_require_authentication(client: TestClient) -> None:
    entry_url = f"{URL}{uuid.uuid4()}"

    assert client.get(URL).status_code == 401
    assert client.post(URL, json=entry_payload()).status_code == 401
    assert client.get(entry_url).status_code == 401
    assert client.put(entry_url, json=entry_payload()).status_code == 401
    assert client.delete(entry_url).status_code == 401


def test_list_is_isolated_between_users(
    client: TestClient,
    user_headers: dict[str, str],
    other_user_headers: dict[str, str],
) -> None:
    _create(client, user_headers)

    response = client.get(URL, headers=other_user_headers)

    assert response.json() == {"data": [], "count": 0}


def test_other_users_entry_looks_missing(
    client: TestClient,
    user_headers: dict[str, str],
    other_user_headers: dict[str, str],
) -> None:
    entry_url = f"{URL}{_create(client, user_headers)['id']}"
    missing = client.get(f"{URL}{uuid.uuid4()}", headers=other_user_headers)

    responses = [
        client.get(entry_url, headers=other_user_headers),
        client.put(entry_url, json=entry_payload(), headers=other_user_headers),
        client.delete(entry_url, headers=other_user_headers),
    ]

    for response in responses:
        assert response.status_code == 404
        assert response.json() == missing.json()
    assert client.get(entry_url, headers=user_headers).status_code == 200


def test_pagination(client: TestClient, user_headers: dict[str, str]) -> None:
    ids = {_create(client, user_headers)["id"] for _ in range(3)}

    first = client.get(URL, params={"limit": 2}, headers=user_headers).json()
    second = client.get(
        URL, params={"skip": 2, "limit": 2}, headers=user_headers
    ).json()

    assert first["count"] == second["count"] == 3
    assert len(first["data"]) == 2
    assert {entry["id"] for entry in first["data"] + second["data"]} == ids


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"skip": -1}])
def test_pagination_bounds(
    client: TestClient, user_headers: dict[str, str], params: dict[str, int]
) -> None:
    response = client.get(URL, params=params, headers=user_headers)

    assert response.status_code == 422
