"""Sitzung im signierten Cookie: Benutzer, Sitzungsversion und Ablauf. Eine Passwortänderung oder Sperre erhöht die
Sitzungsversion des Kontos; damit verfallen alle bestehenden Sitzungen dieses Kontos."""
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

COOKIE_NAME = "interview_sitzung"
SESSION_SECONDS = 14 * 24 * 3600
MAX_FAILURES = 10
FAILURE_WINDOW = 15 * 60


def _signature(secret_key: str, user_id: int, version: int, expires: int) -> str:
    message = f"benutzer|{user_id}|{version}|{expires}".encode()
    return hmac.new(secret_key.encode(), message, hashlib.sha256).hexdigest()


def create_token(secret_key: str, user_id: int, version: int, now: float | None = None) -> str:
    expires = int(time.time() if now is None else now) + SESSION_SECONDS
    return f"{user_id}.{version}.{expires}.{_signature(secret_key, user_id, version, expires)}"


def read_token(token: str | None, secret_key: str, now: float | None = None) -> tuple[int, int] | None:
    """(Benutzer-ID, Sitzungsversion) aus einem gültigen, nicht abgelaufenen Token, sonst None."""
    parts = (token or "").split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts[:3]):
        return None
    user_id, version, expires = (int(p) for p in parts[:3])
    if expires < (time.time() if now is None else now):
        return None
    if not secrets.compare_digest(parts[3], _signature(secret_key, user_id, version, expires)):
        return None
    return user_id, version


class LoginLimiter:
    """Bremst Passwort-Raten: nach zu vielen Fehlversuchen je Absender eine Weile gesperrt."""

    def __init__(self, max_failures: int = MAX_FAILURES, window: int = FAILURE_WINDOW):
        self.max_failures = max_failures
        self.window = window
        self.failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str, now: float) -> deque[float]:
        attempts = self.failures[key]
        while attempts and attempts[0] < now - self.window:
            attempts.popleft()
        return attempts

    def blocked(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return len(self._recent(key, now)) >= self.max_failures

    def failed(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._recent(key, now).append(now)

    def succeeded(self, key: str) -> None:
        self.failures.pop(key, None)


limiter = LoginLimiter()
