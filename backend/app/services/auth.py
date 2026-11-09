"""Ein Admin-Passwort, eine signierte Sitzung im Cookie. Ändert sich das Passwort, verfallen alle Sitzungen."""
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

COOKIE_NAME = "interview_sitzung"
SESSION_SECONDS = 14 * 24 * 3600
MAX_FAILURES = 10
FAILURE_WINDOW = 15 * 60


def _signature(secret_key: str, admin_password: str, expires: int) -> str:
    password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    message = f"admin|{expires}|{password_hash}".encode()
    return hmac.new(secret_key.encode(), message, hashlib.sha256).hexdigest()


def password_matches(given: str, admin_password: str) -> bool:
    return secrets.compare_digest(given.encode(), admin_password.encode())


def create_token(secret_key: str, admin_password: str, now: float | None = None) -> str:
    expires = int(time.time() if now is None else now) + SESSION_SECONDS
    return f"{expires}.{_signature(secret_key, admin_password, expires)}"


def token_valid(token: str | None, secret_key: str, admin_password: str, now: float | None = None) -> bool:
    if not token or "." not in token:
        return False
    expires_raw, signature = token.split(".", 1)
    if not expires_raw.isdigit() or int(expires_raw) < (time.time() if now is None else now):
        return False
    return secrets.compare_digest(signature, _signature(secret_key, admin_password, int(expires_raw)))


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
