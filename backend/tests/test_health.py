import pytest


def test_health(anon):
    response = anon.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_path_is_404_not_spa(anon):
    assert anon.get("/api/gibt-es-nicht").status_code == 404


def test_no_external_docs(anon):
    assert anon.get("/docs").status_code == 404


def test_refuses_to_start_with_placeholder_secret():
    from app.config import Settings, validate_secrets

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        validate_secrets(Settings("sqlite://", "echt", "bitte-aendern"))
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_secrets(Settings("sqlite://", "", "echt"))
