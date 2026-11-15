"""KI-Analyse über alle Interviews eines Projekts: erst die ausführliche Analyse, daraus die Kurzzusammenfassung.

Eingabe je Interview: Kopfdaten, Fragen mit Notizen, Gesamtnotiz, KI-Bewertung (falls vorhanden) und Transkripte.
Passt das nicht ins Kontextfenster des Modells, wird in Stufen gekürzt:
  1. vollständig
  2. Transkripte nur noch bei Interviews ohne KI-Bewertung (die Bewertung fasst das Transkript ja schon zusammen)
  3. zusätzlich die verbleibenden Transkripte gleichmäßig gekürzt
  4. ganz ohne Transkripte
Was gekürzt wurde, steht im Ergebnis („umfang“), damit niemand eine Vollständigkeit annimmt, die es nicht gab.

Läuft im selben Hintergrund-Thread wie die KI-Bewertung einzelner Interviews (ein LLM-Server, eine Anfrage zur Zeit).
"""
import logging
from dataclasses import replace

from sqlalchemy.orm import Session, sessionmaker

from app.db import get_engine
from app.models import Interview, Project, ProjectAnalysis, now
from app.services import audit
from app.services import evaluation as interview_evaluation
from app.services import export
from app.services import project_export
from app.services import settings as settings_service

logger = logging.getLogger(__name__)

# Etwa 170 000 Tokens bei 262 144 Tokens Kontext: Platz für Anweisung, Reasoning und Antwort.
MAX_PROMPT_CHARS = 600_000
BUSY = ("wartend", "laeuft")


def has_content(interview: Interview) -> bool:
    return interview_evaluation.has_content(interview) or bool(
        interview.evaluation and interview.evaluation.text.strip()
    )


def _interview_block(number: int, interview: Interview, transcript_chars: int | None) -> str:
    """transcript_chars: None = vollständig, 0 = ohne Transkript, sonst so viele Zeichen je Interview."""
    catalog = interview.questionnaire
    lines = [f"## Interview {number}: {interview.person}"]
    if interview.organisation:
        lines.append(f"- Organisation: {interview.organisation}")
    lines += [
        f"- Datum: {interview.datum.strftime('%d.%m.%Y')}",
        f"- Gruppe: {catalog.group.name}",
        f"- Fragenkatalog: {catalog.name} (Version {catalog.version})",
        "",
        "### Notizen des Interviewers",
    ]
    for answer in interview.answers:
        note = answer.notiz.strip()
        status = "" if answer.status == "beantwortet" else f" [{export.STATUS_LABEL[answer.status]}]"
        lines.append(f"- {answer.position}. {answer.question_snapshot['text']}{status}: {note or '(keine Notiz)'}")
    lines += ["", "### Gesamtnotiz", "", interview.gesamtnotiz.strip() or "(keine Gesamtnotiz)"]
    if interview.evaluation and interview.evaluation.text.strip():
        lines += ["", "### KI-Bewertung dieses Interviews", "", export.demote(interview.evaluation.text.strip(), 2)]
    for name, text in export.transcripts(interview):
        if transcript_chars == 0:
            lines += ["", f"### Transkript {name}", "", "(weggelassen, Unterlagen zu umfangreich)"]
            continue
        if transcript_chars is not None and len(text) > transcript_chars:
            text = text[:transcript_chars] + "\n\n(… gekürzt)"
        lines += ["", f"### Transkript {name}", "", text]
    return "\n".join(lines)


def build_prompt(project: Project, interviews: list[Interview], limit: int = MAX_PROMPT_CHARS) -> tuple[str, str]:
    """Liefert (Unterlagen, Umfang)."""
    header = [f"# Projekt: {project.name}"]
    if project.beschreibung:
        header += ["", project.beschreibung]
    header += ["", f"Anzahl Interviews: {len(interviews)}", ""]

    def render(chars_for) -> str:
        blocks = [_interview_block(n, i, chars_for(i)) for n, i in enumerate(interviews, start=1)]
        return "\n".join(header) + "\n\n" + "\n\n---\n\n".join(blocks)

    has_eval = {i.id: bool(i.evaluation and i.evaluation.text.strip()) for i in interviews}
    full = render(lambda _i: None)
    if len(full) <= limit:
        return full, "vollständig"

    reduced = render(lambda i: 0 if has_eval[i.id] else None)
    if len(reduced) <= limit:
        return reduced, "Transkripte nur bei Interviews ohne KI-Bewertung"

    # Platz, der ohne jedes Transkript bleibt, gleichmäßig auf die Interviews ohne Bewertung verteilen
    without = render(lambda _i: 0)
    open_ones = [i for i in interviews if not has_eval[i.id] and export.transcripts(i)]
    room = limit - len(without)
    if open_ones and room > 2_000 * len(open_ones):
        per_transcript = room // sum(len(export.transcripts(i)) for i in open_ones) - 200
        cut = render(lambda i: 0 if has_eval[i.id] else per_transcript)
        if len(cut) <= limit:
            return cut, f"Transkripte gekürzt auf je {per_transcript:,} Zeichen".replace(",", ".")
    if len(without) <= limit:
        return without, "ohne Transkripte (zu umfangreich)"
    return without[:limit] + "\n\n(… Unterlagen hier abgeschnitten, zu umfangreich)", "stark gekürzt (zu umfangreich)"


# ------------------------------------------------------------------ Aufträge
def _sessions() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def instructions_for(db: Session, project: Project) -> tuple[str, str]:
    own = project.ki_analyse_anweisung.strip()
    if own:
        return own, "projekt"
    return settings_service.llm(db).analyse_anweisung, "allgemein"


def start(db: Session, project: Project) -> ProjectAnalysis:
    analysis = project.analysis
    if analysis is None:
        analysis = ProjectAnalysis(
            project=project, analyse="", kurzfassung="", fehler="", fortschritt="", modell="", interviews=0, umfang=""
        )
        db.add(analysis)
    analysis.status = "wartend"
    analysis.fehler = ""
    analysis.fortschritt = ""
    analysis.gestartet_am = None
    return analysis


def _progress(analysis_id: int, text: str) -> None:
    with _sessions()() as db:
        analysis = db.get(ProjectAnalysis, analysis_id)
        if analysis is not None:
            analysis.fortschritt = text
            db.commit()


def process_next(generator: interview_evaluation.Generator = interview_evaluation.generate) -> bool:
    """Analysiert das älteste wartende Projekt. False, wenn keines wartet."""
    with _sessions()() as db:
        analysis = (
            db.query(ProjectAnalysis).filter(ProjectAnalysis.status == "wartend").order_by(ProjectAnalysis.id).first()
        )
        if analysis is None:
            return False
        analysis.status = "laeuft"
        analysis.gestartet_am = now()
        analysis.fortschritt = "Unterlagen werden zusammengestellt"
        db.commit()
        analysis_id = analysis.id
        project = analysis.project
        interviews = [i for i in project_export.interviews_of(db, project) if has_content(i)]
        prompt, scope = build_prompt(project, interviews)
        instructions, _source = instructions_for(db, project)
        server = settings_service.llm(db)
        project_id = project.id

    text, short, error, model = "", "", "", server.model
    try:
        if not interviews:
            raise interview_evaluation.EvaluationError("Das Projekt hat keine Interviews mit Notizen oder Transkript.")
        model = interview_evaluation.resolve_model(server)
        _progress(analysis_id, f"Schritt 1 von 2: Analyse über {len(interviews)} Interviews")
        text = generator(replace(server, anweisung=instructions), model, prompt)
        _progress(analysis_id, "Schritt 2 von 2: Kurzzusammenfassung")
        short = generator(
            replace(server, anweisung=settings_service.LLM_SHORT_INSTRUCTIONS), model,
            f"# Analyse des Projekts {project.name}\n\n{text}",
        )
    except interview_evaluation.EvaluationError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 – jeder Fehler soll beim Auftrag sichtbar werden
        logger.exception("Projekt-Analyse %s fehlgeschlagen", analysis_id)
        error = f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"

    with _sessions()() as db:
        analysis = db.get(ProjectAnalysis, analysis_id)
        if analysis is None or analysis.status != "laeuft":  # inzwischen verworfen
            return True
        analysis.fortschritt = ""
        if error:  # ein älteres Ergebnis bleibt stehen
            analysis.status, analysis.fehler = "fehler", error
        else:
            analysis.status, analysis.analyse, analysis.kurzfassung = "fertig", text, short
            analysis.modell, analysis.interviews, analysis.umfang = model, len(interviews), scope
            analysis.bearbeitet = False
            analysis.fertig_am = now()
        audit.log(db, "projekt-analyse", project_id, "analyse-fehler" if error else "analysiert")
        db.commit()
    return True


def requeue_interrupted() -> int:
    with _sessions()() as db:
        rows = db.query(ProjectAnalysis).filter(ProjectAnalysis.status == "laeuft").all()
        for analysis in rows:
            analysis.status = "wartend"
        db.commit()
        return len(rows)
