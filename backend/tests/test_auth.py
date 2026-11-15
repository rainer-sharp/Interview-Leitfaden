import pytest

from app.services.auth import LoginLimiter, create_token, read_token

PROTECTED = [
    ("get", "/api/groups"),
    ("post", "/api/groups"),
    ("get", "/api/groups/1"),
    ("delete", "/api/groups/1"),
    ("get", "/api/questionnaires/1"),
    ("put", "/api/questionnaires/1/order"),
    ("put", "/api/questions/1"),
    ("post", "/api/import/vorschau"),
    ("post", "/api/import"),
    ("get", "/api/import/beispiel.csv"),
    ("get", "/api/interviews"),
    ("post", "/api/interviews"),
    ("get", "/api/interviews/1"),
    ("put", "/api/interviews/1/answers/1"),
    ("get", "/api/interviews/1/export.pdf"),
    ("get", "/api/backup"),
]


@pytest.mark.parametrize("method, path", PROTECTED)
def test_without_login_401(anon, method, path):
    assert getattr(anon, method)(path).status_code == 401


def test_health_and_app_shell_need_no_login(anon):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/auth/status").json() == {"angemeldet": False}
    assert anon.get("/api/benutzer").status_code == 401


def test_login_logout_cycle(anon):
    assert anon.post("/api/auth/login", json={"passwort": "falsch"}).status_code == 401
    response = anon.post("/api/auth/login", json={"passwort": "test-passwort"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" not in cookie
    assert anon.get("/api/groups").status_code == 200
    status = anon.get("/api/auth/status").json()
    assert status["angemeldet"] is True and status["benutzer"]["benutzername"] == "admin"
    assert status["benutzer"]["rolle"] == "admin"

    anon.post("/api/auth/logout")
    assert anon.get("/api/groups").status_code == 401


def test_cookie_is_secure_behind_https_proxy(anon):
    response = anon.post("/api/auth/login", json={"passwort": "test-passwort"}, headers={"X-Forwarded-Proto": "https"})
    assert "secure" in response.headers["set-cookie"].lower()


def test_forged_cookie_rejected(anon):
    anon.cookies.set("interview_sitzung", "9999999999.abc")
    assert anon.get("/api/groups").status_code == 401


def test_session_token():
    token = create_token("geheim", 7, 3, now=1000)
    assert read_token(token, "geheim", now=1001) == (7, 3)
    assert read_token(token, "anderes-geheimnis", now=1001) is None
    assert read_token(token, "geheim", now=1000 + 15 * 24 * 3600) is None
    forged = token.replace("7.3.", "8.3.", 1)
    assert read_token(forged, "geheim", now=1001) is None
    assert read_token("kaputt", "geheim") is None


def test_login_rate_limit(anon):
    for _ in range(10):
        assert anon.post("/api/auth/login", json={"passwort": "falsch"}).status_code == 401
    assert anon.post("/api/auth/login", json={"passwort": "test-passwort"}).status_code == 429


def test_limiter_window_expires():
    limiter = LoginLimiter(max_failures=2, window=60)
    limiter.failed("ip", now=0)
    limiter.failed("ip", now=10)
    assert limiter.blocked("ip", now=30)
    assert not limiter.blocked("ip", now=71)
    assert not limiter.blocked("andere-ip", now=30)
