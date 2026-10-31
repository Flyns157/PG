import os
import tempfile
from collections.abc import Generator
from pathlib import Path

# Toujours une base dédiée : les tests ne doivent pas vider celle du fichier .env.
_sqlite_path = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{_sqlite_path.as_posix()}"
)
os.environ["SECRET_KEY"] = "test-secret-key-with-more-than-32-characters"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["CORS_ORIGINS"] = '["http://localhost:5173"]'

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from tests.utils.user import auth_headers, register_user  # noqa: E402

BACKEND_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "app" / "alembic"))
    return config


@pytest.fixture(scope="session", autouse=True)
def _migrated_database(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


@pytest.fixture(autouse=True)
def db() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_headers(client: TestClient) -> dict[str, str]:
    register_user(client, "alice@example.com")
    return auth_headers(client, "alice@example.com")


@pytest.fixture
def other_user_headers(client: TestClient) -> dict[str, str]:
    register_user(client, "bob@example.com")
    return auth_headers(client, "bob@example.com")
