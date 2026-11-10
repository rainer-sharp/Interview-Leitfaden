"""Einstellungen des Transkriptions-Servers (URL, Modell, API-Schlüssel) und Vorgaben für neue Transkriptionen."""
from fastapi import APIRouter

from app.api.deps import Db
from app.api.schemas import ServerCheckOut, TranscriptionSettingsIn, TranscriptionSettingsOut
from app.services import audit
from app.services import settings as service
from app.services import transcription

router = APIRouter(prefix="/einstellungen/transkription")


def _out(values: service.TranscriptionSettings) -> dict:
    return {**values.public(), "ffmpeg_verfuegbar": transcription.ffmpeg_available()}


@router.get("", response_model=TranscriptionSettingsOut)
def get_settings(db: Db):
    return _out(service.transcription(db))


@router.put("", response_model=TranscriptionSettingsOut)
def update_settings(body: TranscriptionSettingsIn, db: Db):
    values = service.update_transcription(db, body.model_dump(exclude_none=True))
    audit.log(db, "einstellungen", 0, "transkription-geaendert")
    db.commit()
    return _out(values)


@router.post("/test", response_model=ServerCheckOut)
def test_server(body: TranscriptionSettingsIn, db: Db):
    """Prüft die übergebenen (noch nicht gespeicherten) Werte, fehlende Felder kommen aus den Einstellungen."""
    saved = service.transcription(db)
    server = service.TranscriptionSettings(
        url=body.url or saved.url,
        model=body.model or saved.model,
        api_key=body.api_key or saved.api_key,
        modus=saved.modus,
        name_ich=saved.name_ich,
        begriffe=saved.begriffe,
    )
    return transcription.check_server(server)
