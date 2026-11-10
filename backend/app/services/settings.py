"""In der App änderbare Einstellungen. Vorgaben kommen aus der Umgebung, sonst aus transcribe_interview.py
(Transkription) bzw. aus den Konstanten hier (KI-Bewertung)."""
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Setting
from app.services import transcribe_interview as script

MODES = ("mix", "tracks")

LLM_URL = "http://192.168.101.94:8000/v1"
# Leer = das erste Modell, das der Server unter /models anbietet (dort läuft genau eines).
LLM_MODEL = ""
LLM_INSTRUCTIONS = """Du bist ein erfahrener Analyst und wertest Interviews aus. Du erhältst den Fragenkatalog mit den \
Notizen des Interviewers, seine Gesamtnotiz und, falls vorhanden, das automatisch erstellte Transkript des Gesprächs.

Erstelle auf Deutsch eine Auswertung in Markdown mit genau diesen Abschnitten (Überschriften mit ##):

## Zusammenfassung
Worum ging es, wer wurde befragt, was sind die wichtigsten Ergebnisse (5–10 Sätze).

## Kernaussagen
Die wichtigsten Aussagen der interviewten Person als Aufzählung, wenn möglich mit Zeitmarke aus dem Transkript.

## Gesamtbewertung
Deine Einschätzung des Interviews insgesamt: Aussagekraft und Vollständigkeit der Antworten, erkennbare Bedarfe, \
Probleme, Chancen und Risiken, Stimmung und Haltung der Person. Schließe mit einer Einstufung des Gesamteindrucks \
(sehr positiv, positiv, neutral, kritisch, sehr kritisch) und einer kurzen Begründung.

## Abweichungen und Lücken
Widersprüche zwischen Notizen und Transkript, unbeantwortete oder nur oberflächlich beantwortete Fragen.

## Offene Punkte und nächste Schritte
Konkrete Folgefragen, Zusagen und Aufgaben als Aufzählung.

Halte dich streng an den Inhalt der Unterlagen und erfinde nichts. Wenn etwas unklar ist oder fehlt, sage es. \
Das Transkript ist maschinell erstellt und kann Hör- und Zuordnungsfehler enthalten. Antworte nur mit der \
Auswertung, ohne Vorrede."""


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


@dataclass(frozen=True)
class LlmSettings:
    url: str
    model: str  # leer = automatisch das erste Modell des Servers
    api_key: str
    anweisung: str  # System-Prompt für die Bewertung

    def public(self) -> dict:
        data = asdict(self)
        data["api_key_gesetzt"] = bool(data.pop("api_key")) and self.api_key != "EMPTY"
        data["anweisung_angepasst"] = self.anweisung != LLM_INSTRUCTIONS
        return data


def _llm_defaults() -> dict[str, str]:
    env = get_settings()
    return {
        "url": env.llm_url or LLM_URL,
        "model": env.llm_model or LLM_MODEL,
        "api_key": env.llm_api_key or "EMPTY",
        "anweisung": LLM_INSTRUCTIONS,
    }


def default_llm_model() -> str:
    return _llm_defaults()["model"]


def _load(db: Session, prefix: str, values: dict[str, str]) -> dict[str, str]:
    for row in db.query(Setting).filter(Setting.schluessel.like(f"{prefix}.%")):
        field = row.schluessel.removeprefix(f"{prefix}.")
        if field in values:
            values[field] = row.wert
    return values


def _store(db: Session, prefix: str, fields: dict[str, str], changes: dict[str, str]) -> None:
    """Speichert geänderte Felder. Ein leerer Wert setzt das Feld auf die Vorgabe zurück."""
    for field, value in changes.items():
        if field not in fields:
            raise KeyError(field)
        key = f"{prefix}.{field}"
        row = db.get(Setting, key)
        if value == "":
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(Setting(schluessel=key, wert=value))
        else:
            row.wert = value
    db.flush()


def transcription(db: Session) -> TranscriptionSettings:
    return TranscriptionSettings(**_load(db, "transkription", _defaults()))


def update_transcription(db: Session, changes: dict[str, str]) -> TranscriptionSettings:
    _store(db, "transkription", _defaults(), changes)
    return transcription(db)


def llm(db: Session) -> LlmSettings:
    return LlmSettings(**_load(db, "llm", _llm_defaults()))


def update_llm(db: Session, changes: dict[str, str]) -> LlmSettings:
    defaults = _llm_defaults()
    # Unveränderte Standard-Anweisung nicht speichern, damit spätere Verbesserungen der Vorgabe ankommen.
    if changes.get("anweisung", "").strip() == defaults["anweisung"].strip():
        changes = {**changes, "anweisung": ""}
    _store(db, "llm", defaults, changes)
    return llm(db)
