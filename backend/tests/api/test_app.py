from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_health_check(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/utils/health-check")

    assert response.status_code == 200
    assert response.json() is True


def test_openapi_operation_ids_are_stable(client: TestClient) -> None:
    schema = client.get(f"{settings.API_V1_STR}/openapi.json").json()

    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    ]

    assert "login-login_access_token" in operation_ids
    assert len(operation_ids) == len(set(operation_ids))


def test_cors_allows_only_configured_origins(client: TestClient) -> None:
    allowed = client.options(
        f"{settings.API_V1_STR}/vault-entries/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    refused = client.options(
        f"{settings.API_V1_STR}/vault-entries/",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in refused.headers
    assert "access-control-allow-credentials" not in allowed.headers


def test_no_unversioned_api_routes() -> None:
    paths = app.openapi()["paths"]

    assert all(path.startswith(settings.API_V1_STR) for path in paths)
