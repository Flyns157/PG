from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PLACEHOLDER_SECRET = "changethis"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Fichier .env à la racine du dépôt, un niveau au-dessus de backend/
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "PG API"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0, le=60)

    DATABASE_URL: str

    CORS_ORIGINS: list[str] = []

    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT: str = "5/minute"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                return value.replace(scheme, "postgresql+psycopg://", 1)
        return value

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _reject_wildcard_origin(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS doit lister des origines explicites")
        return value

    @model_validator(mode="after")
    def _reject_placeholder_secrets(self) -> Self:
        database_password = make_url(self.DATABASE_URL).password
        for name, value in (
            ("SECRET_KEY", self.SECRET_KEY),
            ("DATABASE_URL", database_password),
        ):
            if value and PLACEHOLDER_SECRET in str(value):
                raise ValueError(f"{name} contient encore une valeur d'exemple")
        return self


settings = Settings()  # type: ignore[call-arg]
