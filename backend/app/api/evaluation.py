"""KI-Bewertung eines Interviews: starten, Ergebnis lesen und korrigieren, als Markdown oder PDF herunterladen.

Wie bei Aufnahmen auch für abgeschlossene Interviews möglich: die Bewertung entsteht meist erst nach dem Gespräch.
"""
from fastapi import APIRouter, HTTPException, Response

from app.api.deps import Db, attachment, get_or_404
from app.api.schemas import EvaluationOut, EvaluationUpdate
from app.models import Interview
from app.services import audit
from app.services import evaluation as service
from app.services import export

router = APIRouter(prefix="/interviews/{interview_id}/bewertung")


def _out(interview: Interview) -> dict:
    current = interview.evaluation
    data = {
        "hat_transkript": bool(export.transcripts(interview)),
        "transkription_laeuft": any(r.transkript_status in ("wartend", "laeuft") for r in interview.recordings),
    }
    if current is None:
        return {**data, "status": "keine"}
    fields = ("status", "text", "fehler", "modell", "mit_transkript", "bearbeitet", "gestartet_am", "fertig_am")
    return {**data, **{field: getattr(current, field) for field in fields}}


def _require_idle(interview: Interview) -> None:
    if interview.evaluation is not None and interview.evaluation.status in service.BUSY:
        raise HTTPException(status_code=409, detail="Die Bewertung dieses Interviews läuft bereits.")


@router.get("", response_model=EvaluationOut)
def get_evaluation(interview_id: int, db: Db):
    return _out(get_or_404(db, Interview, interview_id))


@router.post("", response_model=EvaluationOut, status_code=202)
def start_evaluation(interview_id: int, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    _require_idle(interview)
    if not service.has_content(interview):
        raise HTTPException(status_code=422, detail="Es gibt noch nichts zu bewerten: keine Notizen und kein Transkript.")
    service.start(db, interview)
    audit.log(db, "bewertung", interview.id, "bewertung-gestartet")
    db.commit()
    service.worker.notify()
    return _out(interview)


@router.put("", response_model=EvaluationOut)
def update_evaluation(interview_id: int, body: EvaluationUpdate, db: Db):
    """Korrekturen an der Bewertung; sie gelten dann auch im Export."""
    interview = get_or_404(db, Interview, interview_id)
    _require_idle(interview)
    if interview.evaluation is None or not interview.evaluation.text:
        raise HTTPException(status_code=404, detail="Noch keine Bewertung vorhanden.")
    if interview.evaluation.text != body.text:
        interview.evaluation.text = body.text
        interview.evaluation.bearbeitet = True
        db.commit()
    return _out(interview)


@router.delete("", status_code=204)
def delete_evaluation(interview_id: int, db: Db):
    """Verwirft die Bewertung, auch eine laufende (deren Ergebnis wird dann nicht mehr gespeichert)."""
    interview = get_or_404(db, Interview, interview_id)
    if interview.evaluation is not None:
        db.delete(interview.evaluation)
        audit.log(db, "bewertung", interview.id, "bewertung-geloescht")
        db.commit()
    return Response(status_code=204)


DOWNLOADS = {
    "md": ("text/markdown; charset=utf-8", export.evaluation_markdown),
    "pdf": ("application/pdf", export.evaluation_pdf),
}


@router.get(".{fmt}")
def download(interview_id: int, fmt: str, db: Db):
    if fmt not in DOWNLOADS:
        raise HTTPException(status_code=404, detail="Unbekanntes Format")
    interview = get_or_404(db, Interview, interview_id)
    if not export.evaluation_text(interview):
        raise HTTPException(status_code=404, detail="Noch keine Bewertung vorhanden.")
    media_type, render = DOWNLOADS[fmt]
    name = export.filename(interview, fmt).replace(f".{fmt}", f"-bewertung.{fmt}")
    return Response(render(interview), media_type=media_type, headers=attachment(name))
