import pytest


def test_health(anon):
    response = anon.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "entwicklung"}


def test_health_shows_build_version(anon, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "d3e5e46")
    assert anon.get("/api/health").json()["version"] == "d3e5e46"


def test_unknown_api_path_is_404_not_spa(anon):
    assert anon.get("/api/gibt-es-nicht").status_code == 404


def test_no_external_docs(anon):
    # Swagger lädt Skripte von einem CDN; unter /docs darf höchstens die eigene App erscheinen.
    assert "swagger" not in anon.get("/docs").text.lower()
    assert anon.get("/openapi.json").headers.get("content-type", "").startswith("application/json") is False


def test_refuses_to_start_with_placeholder_secret():
    from app.config import Settings, validate_secrets

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        validate_secrets(Settings("sqlite://", "echt", "bitte-aendern"))
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_secrets(Settings("sqlite://", "", "echt"))
