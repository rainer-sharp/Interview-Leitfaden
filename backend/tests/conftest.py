import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parent.parent
TESTDATA = BACKEND.parent / "testdata"

os.environ.update(SECRET_KEY="test-geheimnis", ADMIN_PASSWORD="test-passwort")


def _reset_caches() -> None:
    from app.config import get_settings
    from app.db import get_engine

    if get_settings.cache_info().currsize and get_engine.cache_info().currsize:
        get_engine().dispose()
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def database(tmp_path, monkeypatch):
    """Frische DB je Test, aufgebaut durch die echte Migration."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    _reset_caches()
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(config, "head")
    yield tmp_path / "test.db"
    _reset_caches()


@pytest.fixture
def anon(database):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(anon):
    response = anon.post("/api/auth/login", json={"passwort": "test-passwort"})
    assert response.status_code in (200, 404)  # 404, solange Paket 10 fehlt
    return anon


@pytest.fixture
def testdata() -> Path:
    return TESTDATA
