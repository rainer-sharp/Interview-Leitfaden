import os
from dataclasses import dataclass
from functools import lru_cache

PLACEHOLDER = "bitte-aendern"


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    admin_password: str
    audio_dir: str = ""
    max_audio_mb: int = 4096
    transcribe_url: str = ""
    transcribe_model: str = ""
    transcribe_api_key: str = ""
    transcription_worker: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./data/interviews.db"),
        secret_key=os.environ.get("SECRET_KEY", ""),
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
        audio_dir=os.environ.get("AUDIO_DIR", ""),
        max_audio_mb=int(os.environ.get("MAX_AUDIO_MB", "4096")),
        # Vorgaben für die Transkription; in der App unter „Einstellungen“ änderbar (gespeichert in der DB).
        transcribe_url=os.environ.get("TRANSCRIBE_URL", ""),
        transcribe_model=os.environ.get("TRANSCRIBE_MODEL", ""),
        transcribe_api_key=os.environ.get("TRANSCRIBE_API_KEY", ""),
        transcription_worker=os.environ.get("TRANSCRIPTION_WORKER", "1") != "0",
    )


def validate_secrets(settings: Settings) -> None:
    """Interviewnotizen sind personenbezogen: ohne echte Zugangsdaten startet die App nicht."""
    for name, value in (("SECRET_KEY", settings.secret_key), ("ADMIN_PASSWORD", settings.admin_password)):
        if not value or value == PLACEHOLDER:
            raise RuntimeError(f"{name} ist nicht gesetzt. Bitte in der .env einen eigenen Wert eintragen.")
