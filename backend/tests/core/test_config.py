from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID = {
    "SECRET_KEY": "x" * 32,
    "DATABASE_URL": "postgresql://user:password@localhost/app",
}


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **(VALID | overrides))  # type: ignore[call-arg]


def test_valid_settings_use_psycopg() -> None:
    assert _settings().DATABASE_URL.startswith("postgresql+psycopg://")


def test_postgres_scheme_is_normalized() -> None:
    settings = _settings(DATABASE_URL="postgres://user:password@localhost/app")

    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    "overrides",
    [
        {"SECRET_KEY": "too-short"},
        {"SECRET_KEY": "changethis" * 4},
        {"DATABASE_URL": "postgresql://user:changethis@localhost/app"},
        {"CORS_ORIGINS": ["*"]},
        {"ACCESS_TOKEN_EXPIRE_MINUTES": 60 * 24 * 8},
    ],
    ids=["short-key", "placeholder-key", "placeholder-db", "wildcard", "long-token"],
)
def test_unsafe_settings_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_secret_key_has_no_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_URL=VALID["DATABASE_URL"])  # type: ignore[call-arg]
