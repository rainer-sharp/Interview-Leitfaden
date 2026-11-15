"""Einstellungen des Transkriptions-Servers (URL, Modell, API-Schlüssel) und Vorgaben für neue Transkriptionen;
außerdem der LLM-Server für die KI-Bewertung."""
from fastapi import APIRouter

from app.api.access import Admin
from app.api.deps import Db
from app.api.schemas import (
    LlmCheckOut,
    LlmSettingsIn,
    LlmSettingsOut,
    ServerCheckOut,
    TranscriptionSettingsIn,
    TranscriptionSettingsOut,
)
from app.services import audit
from app.services import evaluation
from app.services import settings as service
from app.services import transcription

router = APIRouter(prefix="/einstellungen/transkription")
llm_router = APIRouter(prefix="/einstellungen/llm")


def _out(values: service.TranscriptionSettings) -> dict:
    return {**values.public(), "ffmpeg_verfuegbar": transcription.ffmpeg_available()}


@router.get("", response_model=TranscriptionSettingsOut)
def get_settings(db: Db):
    return _out(service.transcription(db))


@router.put("", response_model=TranscriptionSettingsOut)
def update_settings(body: TranscriptionSettingsIn, db: Db, me: Admin):
    values = service.update_transcription(db, body.model_dump(exclude_none=True))
    audit.log(db, "einstellungen", 0, "transkription-geaendert")
    db.commit()
    return _out(values)


@router.post("/test", response_model=ServerCheckOut)
def test_server(body: TranscriptionSettingsIn, db: Db, me: Admin):
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


@llm_router.get("", response_model=LlmSettingsOut)
def get_llm(db: Db):
    return service.llm(db).public()


@llm_router.put("", response_model=LlmSettingsOut)
def update_llm(body: LlmSettingsIn, db: Db, me: Admin):
    values = service.update_llm(db, body.model_dump(exclude_none=True))
    audit.log(db, "einstellungen", 0, "llm-geaendert")
    db.commit()
    return values.public()


@llm_router.post("/test", response_model=LlmCheckOut)
def test_llm(body: LlmSettingsIn, db: Db, me: Admin):
    """Prüft die Werte aus dem Formular. Leeres Modell = Vorgabe (ohne LLM_MODEL: automatisch)."""
    saved = service.llm(db)
    server = service.LlmSettings(
        url=body.url or saved.url,
        model=saved.model if body.model is None else (body.model or service.default_llm_model()),
        api_key=body.api_key or saved.api_key,
        anweisung=saved.anweisung,
        analyse_anweisung=saved.analyse_anweisung,
    )
    return evaluation.check_server(server)
