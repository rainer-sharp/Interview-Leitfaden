"""In der App änderbare Einstellungen. Vorgaben kommen aus der Umgebung, sonst aus transcribe_interview.py."""
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Setting
from app.services import transcribe_interview as script

MODES = ("mix", "tracks")


@dataclass(frozen=True)
class TranscriptionSettings:
    url: str
    model: str
    api_key: str
    modus: str
    name_ich: str
    begriffe: str  # kommagetrennt oder eine pro Zeile, wie --terms im Skript

    def public(self) -> dict:
        """Ohne API-Schlüssel: der Browser erfährt nur, ob einer gesetzt ist."""
        data = asdict(self)
        data["api_key_gesetzt"] = bool(data.pop("api_key")) and self.api_key != "EMPTY"
        return data


def _defaults() -> dict[str, str]:
    env = get_settings()
    return {
        "url": env.transcribe_url or script.SERVER_URL,
        "model": env.transcribe_model or script.MODEL_NAME,
        "api_key": env.transcribe_api_key or script.API_KEY,
        "modus": "mix",
        "name_ich": script.NAME_ME,
        "begriffe": "",
    }


def _key(field: str) -> str:
    return f"transkription.{field}"


def transcription(db: Session) -> TranscriptionSettings:
    values = _defaults()
    for row in db.query(Setting).filter(Setting.schluessel.like("transkription.%")):
        field = row.schluessel.removeprefix("transkription.")
        if field in values:
            values[field] = row.wert
    return TranscriptionSettings(**values)


def update_transcription(db: Session, changes: dict[str, str]) -> TranscriptionSettings:
    """Speichert geänderte Felder. Ein leerer Wert setzt das Feld auf die Vorgabe zurück."""
    for field, value in changes.items():
        if field not in _defaults():
            raise KeyError(field)
        row = db.get(Setting, _key(field))
        if value == "":
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(Setting(schluessel=_key(field), wert=value))
        else:
            row.wert = value
    db.flush()
    return transcription(db)
