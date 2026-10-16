"""Shared test fixtures.

Tests run against a real PostgreSQL at TEST_DATABASE_URL (default: a local PGlite server on port 5433,
see docs/implementation-notes.md). The ambient DATABASE_URL is deliberately ignored: tests truncate every table.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/postgres?sslmode=disable")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-secret-key-test-secret-key-0123456789"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ENVIRONMENT"] = "test"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import shared.db as db_module  # noqa: E402
from shared.config import get_settings  # noqa: E402

BACKEND_DIR = Path(__file__).parent

# PGlite serves one connection at a time and shares one backend session between connections, so tests
# must not pool connections or let psycopg auto-prepare statements (names would collide across connections).
_test_engine = create_engine(
    get_settings().sqlalchemy_url, poolclass=NullPool, connect_args={"prepare_threshold": None}
)
db_module.get_engine = lambda: _test_engine  # type: ignore[assignment]
db_module.get_sessionmaker.cache_clear()


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


@pytest.fixture(scope="session")
def engine() -> Engine:
    engine = _test_engine
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    return engine


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Empties every table, then hands out short-lived sessions. Use `with session_factory() as db:`."""
    with engine.begin() as conn:
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        ).scalars()
        conn.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " CASCADE"))
    yield sessionmaker(bind=engine, expire_on_commit=False)


from dataclasses import dataclass  # noqa: E402
from uuid import UUID  # noqa: E402

from shared.models import User  # noqa: E402
from shared.security import ACCESS, create_token  # noqa: E402


@dataclass
class TestUser:
    __test__ = False

    id: UUID
    email: str
    token: str
    jti: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def make_user(session_factory):
    def _make(email: str = "user@example.com") -> TestUser:
        with session_factory() as db:
            user = User(email=email, password_hash="not-a-real-hash")
            db.add(user)
            db.commit()
        token, claims = create_token(user.id, ACCESS)
        return TestUser(id=user.id, email=email, token=token, jti=claims.jti)

    return _make
