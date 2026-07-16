"""Test fixtures.

Each test gets a freshly seeded, isolated SQLite database. Environment is set
before importing the app so Settings picks up the test config.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_consulthub.db")
os.environ.setdefault("ESCALATION_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-bytes-long!")
os.environ.setdefault("STORAGE_DIR", "./test_uploads")
os.environ.setdefault("PBKDF2_ITERATIONS", "1000")  # fast hashing for tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    seed()  # creates tables + demo institution/users/patients/clinic
    with TestClient(app) as c:
        yield c


def _token(c, email, password="consulthub"):
    r = c.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert r.status_code == 200, (email, r.status_code, r.text)
    return r.json()["access_token"]


@pytest.fixture()
def auth(client):
    """Return a helper that produces Authorization headers for a seeded user."""

    def make(email="registrar@consulthub.local", password="consulthub"):
        return {"Authorization": f"Bearer {_token(client, email, password)}"}

    return make


# Convenience header fixtures for the common demo users.
@pytest.fixture()
def registrar(auth):
    return auth("registrar@consulthub.local")


@pytest.fixture()
def admin(auth):
    return auth("admin@consulthub.local")


@pytest.fixture()
def superadmin(auth):
    return auth("superadmin@consulthub.local")


@pytest.fixture()
def other_tenant(client, superadmin):
    """A user + headers in a different institution (id 999)."""
    client.post(
        "/api/users",
        headers=superadmin,
        json={
            "full_name": "Outsider",
            "email": "outsider@other.local",
            "password": "consulthub",
            "role": "registrar",
            "institution_id": 999,
        },
    )
    return {
        "Authorization": (
            "Bearer " + _token(client, "outsider@other.local")
        )
    }
