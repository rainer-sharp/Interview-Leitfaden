"""KI-Bewertung eines Interviews: Zusammenfassung und Gesamteinschätzung durch ein LLM.

Das LLM läuft auf einem OpenAI-kompatiblen Server (vLLM). Ohne eingestelltes Modell wird das erste Modell genommen,
das der Server unter /models anbietet. Eingabe sind Fragen mit Notizen, die Gesamtnotiz und – falls vorhanden – die
Transkripte der Aufnahmen. Die Anfrage kann bei langen Transkripten und einem Reasoning-Modell mehrere Minuten
dauern; sie läuft deshalb wie die Transkription in einem Hintergrund-Thread.
"""
import json
import logging
import re
from dataclasses import replace
import urllib.error
import urllib.request
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.db import get_engine
from app.models import Evaluation, Interview, now
from app.services import audit
from app.services import export
from app.services import projects as project_service
from app.services import settings as settings_service
from app.services.transcription import Worker

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 30 * 60
MAX_TOKENS = 32_000  # inklusive Reasoning; die Auswertung selbst ist meist unter 3 000 Tokens
# Etwa 150 000 Tokens. Längere Transkripte werden gekürzt, damit Prompt und Antwort ins Kontextfenster passen.
MAX_TRANSCRIPT_CHARS = 500_000
TEMPERATURE = 0.3
BUSY = ("wartend", "laeuft")


class EvaluationError(RuntimeError):
    pass


# ------------------------------------------------------------------ Eingabe
def has_content(interview: Interview) -> bool:
    return bool(
        interview.gesamtnotiz.strip()
        or any(a.notiz.strip() for a in interview.answers)
        or export.transcripts(interview)
    )


def build_prompt(interview: Interview) -> tuple[str, bool]:
    """Unterlagen für das LLM als Markdown. Liefert (Text, ob ein Transkript enthalten ist)."""
    catalog = interview.questionnaire
    lines = [
        "# Interview",
        "",
        f"- Interviewte Person: {interview.person}",
    ]
    if interview.organisation:
        lines.append(f"- Organisation: {interview.organisation}")
    lines += [
        f"- Datum: {interview.datum.strftime('%d.%m.%Y')}",
        f"- Projekt: {catalog.group.project.name}",
        f"- Gruppe: {catalog.group.name}",
        f"- Fragenkatalog: {catalog.name} (Version {catalog.version})",
        "",
        "# Fragen und Notizen des Interviewers",
    ]
    section = None
    for answer in interview.answers:
        question = answer.question_snapshot
        if question["abschnitt"] != section:
            section = question["abschnitt"]
            lines += ["", f"## {section}"]
        title = f"### {answer.position}. {question['text']}"
        if question.get("pflicht"):
            title += " (Pflichtfrage)"
        lines += ["", title]
        if question.get("hinweis"):
            lines.append(f"Hinweis für den Interviewer: {question['hinweis']}")
        if answer.status != "beantwortet":
            lines.append(f"Status: {export.STATUS_LABEL[answer.status]}")
        lines.append(f"Notiz: {answer.notiz.strip() or '(keine Notiz)'}")
    lines += ["", "# Gesamtnotiz des Interviewers", "", interview.gesamtnotiz.strip() or "(keine Gesamtnotiz)"]

    transcripts = export.transcripts(interview)
    budget = MAX_TRANSCRIPT_CHARS
    for name, text in transcripts:
        lines += ["", f"# Transkript der Aufnahme {name}", ""]
        if budget <= 0:
            lines.append("(weggelassen: Transkripte zu lang)")
            continue
        if len(text) > budget:
            text = text[:budget] + "\n\n(… Transkript an dieser Stelle gekürzt, zu lang)"
        budget -= len(text)
        lines.append(text)
    if not transcripts:
        lines += ["", "(Zu diesem Interview gibt es kein Transkript, nur die Notizen.)"]
    return "\n".join(lines), bool(transcripts)


# ------------------------------------------------------------------ Server
def _request(server: settings_service.LlmSettings, path: str, body: dict | None, timeout: float) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        server.url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {server.api_key or 'EMPTY'}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise EvaluationError(f"LLM-Server antwortet mit Fehler {exc.code}: {detail}") from None
    except (urllib.error.URLError, OSError) as exc:  # TimeoutError ist ein OSError
        reason = getattr(exc, "reason", None) or type(exc).__name__
        raise EvaluationError(f"LLM-Server nicht erreichbar ({server.url}): {reason}") from None
    except ValueError:
        raise EvaluationError("Antwort ist kein JSON – ist das ein OpenAI-kompatibler Endpunkt?") from None


def list_models(server: settings_service.LlmSettings, timeout: float = 10) -> list[str]:
    body = _request(server, "/models", None, timeout)
    return [m.get("id", "") for m in body.get("data", []) if isinstance(m, dict) and m.get("id")]


def resolve_model(server: settings_service.LlmSettings) -> str:
    if server.model:
        return server.model
    models = list_models(server)
    if not models:
        raise EvaluationError("Der LLM-Server bietet kein Modell an.")
    return models[0]


def check_server(server: settings_service.LlmSettings) -> dict:
    """Fragt /models ab. Liefert ok, Meldung, angebotene Modelle und das Modell, das verwendet würde."""
    try:
        models = list_models(server)
    except EvaluationError as exc:
        return {"ok": False, "meldung": str(exc), "modelle": [], "modell": ""}
    if not models:
        return {"ok": False, "meldung": "Server erreichbar, bietet aber kein Modell an.", "modelle": [], "modell": ""}
    if not server.model:
        return {"ok": True, "meldung": f"Server erreichbar, verwendet wird „{models[0]}“.", "modelle": models,
                "modell": models[0]}
    if server.model not in models:
        return {"ok": False, "meldung": f"Server erreichbar, aber Modell „{server.model}“ fehlt.", "modelle": models,
                "modell": ""}
    return {"ok": True, "meldung": "Server erreichbar, Modell vorhanden.", "modelle": models, "modell": server.model}


_THINK = re.compile(r"<think>.*?</think>", re.S)


def clean_answer(text: str) -> str:
    """Entfernt Reasoning, falls der Server es nicht abtrennt, und einen umschließenden ```markdown-Block."""
    text = _THINK.sub("", text)
    if "</think>" in text:  # Anfang des Reasoning steckte im Chat-Template
        text = text.split("</think>", 1)[1]
    text = text.strip()
    fenced = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*)\n```", text, re.S)
    return (fenced.group(1) if fenced else text).strip()


def generate(server: settings_service.LlmSettings, model: str, prompt: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": server.anweisung},
            {"role": "user", "content": prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    response = _request(server, "/chat/completions", body, REQUEST_TIMEOUT_S)
    try:
        choice = response["choices"][0]
        text = choice["message"].get("content") or ""
    except (KeyError, IndexError, TypeError):
        raise EvaluationError("Unerwartete Antwort des LLM-Servers.") from None
    text = clean_answer(text)
    if not text:
        if choice.get("finish_reason") == "length":
            raise EvaluationError("Das Modell hat das Token-Limit erreicht, bevor eine Antwort kam.")
        raise EvaluationError("Das Modell hat eine leere Antwort geliefert.")
    return text


# ------------------------------------------------------------------ Aufträge
Generator = Callable[[settings_service.LlmSettings, str, str], str]


def _sessions() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def start(db: Session, interview: Interview) -> Evaluation:
    """Reiht die Bewertung ein (ersetzt eine vorhandene). Der Aufrufer committet und weckt den Worker."""
    evaluation = interview.evaluation
    if evaluation is None:
        evaluation = Evaluation(interview=interview, text="", fehler="", modell="")
        db.add(evaluation)
    evaluation.status = "wartend"
    evaluation.fehler = ""
    evaluation.gestartet_am = None  # fertig_am bleibt: es gehört zum noch angezeigten letzten Ergebnis
    return evaluation


def process_next(generator: Generator = generate) -> bool:
    """Bewertet das älteste wartende Interview. False, wenn keines wartet."""
    with _sessions()() as db:
        evaluation = db.query(Evaluation).filter(Evaluation.status == "wartend").order_by(Evaluation.id).first()
        if evaluation is None:
            return False
        evaluation.status = "laeuft"
        evaluation.gestartet_am = now()
        db.commit()
        evaluation_id = evaluation.id
        # Die Unterlagen werden jetzt gelesen, damit auch kurz vorher eingetragene Transkripte dabei sind.
        prompt, with_transcript = build_prompt(evaluation.interview)
        # Die Anweisung des Projekts geht der allgemeinen aus den Einstellungen vor.
        instructions, _source = project_service.instructions_for(db, evaluation.interview)
        server = replace(settings_service.llm(db), anweisung=instructions)

    text, error, model = "", "", server.model
    try:
        model = resolve_model(server)
        text = generator(server, model, prompt)
    except EvaluationError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 – jeder Fehler soll beim Auftrag sichtbar werden
        logger.exception("KI-Bewertung %s fehlgeschlagen", evaluation_id)
        error = f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"

    with _sessions()() as db:
        evaluation = db.get(Evaluation, evaluation_id)
        if evaluation is None or evaluation.status != "laeuft":  # inzwischen gelöscht
            return True
        if error:  # ein älteres Ergebnis bleibt mit seinen Angaben stehen
            evaluation.status, evaluation.fehler = "fehler", error
        else:
            evaluation.status, evaluation.text, evaluation.modell = "fertig", text, model
            evaluation.mit_transkript, evaluation.bearbeitet = with_transcript, False
            evaluation.fertig_am = now()
        audit.log(db, "bewertung", evaluation.interview_id, "bewertung-fehler" if error else "bewertet")
        db.commit()
    return True


def requeue_interrupted() -> int:
    with _sessions()() as db:
        rows = db.query(Evaluation).filter(Evaluation.status == "laeuft").all()
        for evaluation in rows:
            evaluation.status = "wartend"
        db.commit()
        return len(rows)


def _process_any() -> bool:
    """Ein Thread für alle LLM-Aufträge: erst Interviews, dann Projekt-Analysen."""
    from app.services import project_analysis  # spät: das Modul importiert dieses

    return process_next() or project_analysis.process_next()


def _recover_all() -> int:
    from app.services import project_analysis

    return requeue_interrupted() + project_analysis.requeue_interrupted()


worker = Worker(process=_process_any, recover=_recover_all, name="ki-bewertung")
