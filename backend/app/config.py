import os
from dataclasses import dataclass
from functools import lru_cache

PLACEHOLDER = "bitte-aendern"


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    admin_password: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./data/interviews.db"),
        secret_key=os.environ.get("SECRET_KEY", ""),
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
    )


def validate_secrets(settings: Settings) -> None:
    """Interviewnotizen sind personenbezogen: ohne echte Zugangsdaten startet die App nicht."""
    for name, value in (("SECRET_KEY", settings.secret_key), ("ADMIN_PASSWORD", settings.admin_password)):
        if not value or value == PLACEHOLDER:
            raise RuntimeError(f"{name} ist nicht gesetzt. Bitte in der .env einen eigenen Wert eintragen.")
