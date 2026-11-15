from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from app.api import access
from app.api.access import Me
from app.api.deps import Db, get_or_404
from app.models import User
from app.api.schemas import AnswerOut, AnswerUpdate, InterviewIn, InterviewOut, InterviewSummary, InterviewUpdate
from app.models import Answer, Group, Interview, Questionnaire
from app.services import audit
from app.services import export
from app.services import interviews as service
from app.services import transcription

router = APIRouter(prefix="/interviews")


def summary(interview: Interview, me: User) -> dict:
    catalog = interview.questionnaire
    interviewer = interview.interviewer
    return {
        "id": interview.id,
        "questionnaire_id": interview.questionnaire_id,
        "person": interview.person,
        "organisation": interview.organisation,
        "datum": interview.datum,
        "status": interview.status,
        "projekt_id": catalog.group.project_id,
        "projekt_name": catalog.group.project.name,
        "group_name": catalog.group.name,
        "questionnaire_name": catalog.name,
        "version": catalog.version,
        "fragen": len(interview.answers),
        "bearbeitet": sum(a.status != "offen" for a in interview.answers),
        "interviewer_id": interview.user_id,
        "interviewer_name": interviewer.name if interviewer else "(Konto gelöscht)",
        "darf_bearbeiten": access.can_edit_interview(me, interview),
    }


def detail(interview: Interview, me: User) -> dict:
    return {
        **summary(interview, me),
        "gesamtnotiz": interview.gesamtnotiz,
        "answers": interview.answers,
        "aufnahmen": interview.recordings,
    }


def _require_running(interview: Interview) -> None:
    if interview.status != "laufend":
        raise HTTPException(status_code=409, detail="Das Interview ist abgeschlossen. Zum Ändern bitte wieder öffnen.")


@router.get("", response_model=list[InterviewSummary])
def list_interviews(db: Db, me: Me, projekt_id: int | None = None):
    """Ohne projekt_id alle Interviews aller Projekte."""
    query = db.query(Interview)
    if projekt_id is not None:
        query = (
            query.join(Questionnaire, Interview.questionnaire_id == Questionnaire.id)
            .join(Group, Questionnaire.group_id == Group.id)
            .filter(Group.project_id == projekt_id)
        )
    visible = access.visible_project_ids(db, me)
    if visible is not None:
        if projekt_id is None:
            query = query.join(Questionnaire, Interview.questionnaire_id == Questionnaire.id).join(
                Group, Questionnaire.group_id == Group.id
            )
        query = query.filter(Group.project_id.in_(visible))
    rows = query.order_by(Interview.datum.desc(), Interview.id.desc()).all()
    return [summary(i, me) for i in rows]


@router.post("", response_model=InterviewOut, status_code=201)
def create_interview(body: InterviewIn, db: Db, me: Me):
    catalog = access.catalog(db, me, body.questionnaire_id)
    try:
        interview = service.start(db, catalog, body.person, body.organisation, body.datum)
        interview.user_id = me.id
    except service.EmptyCatalog:
        raise HTTPException(status_code=422, detail="Der Katalog enthält noch keine Fragen.") from None
    audit.log(db, "interview", interview.id, "gestartet")
    db.commit()
    return detail(interview, me)


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, db: Db, me: Me):
    return detail(access.interview(db, me, interview_id), me)


@router.put("/{interview_id}", response_model=InterviewOut)
def update_interview(interview_id: int, body: InterviewUpdate, db: Db, me: Me):
    interview = access.editable_interview(db, me, interview_id)
    _require_running(interview)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(interview, field, value)
    db.commit()
    return detail(interview, me)


@router.delete("/{interview_id}", status_code=204)
def delete_interview(interview_id: int, db: Db, me: Me):
    interview = access.editable_interview(db, me, interview_id)
    audit.log(db, "interview", interview.id, "geloescht")
    db.delete(interview)
    db.commit()
    transcription.remove_interview_files(interview_id)
    return Response(status_code=204)


@router.put("/{interview_id}/answers/{answer_id}", response_model=AnswerOut)
def update_answer(interview_id: int, answer_id: int, body: AnswerUpdate, db: Db, me: Me):
    access.editable_interview(db, me, interview_id)
    answer = get_or_404(db, Answer, answer_id)
    if answer.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    _require_running(answer.interview)
    service.update_answer(answer, body.notiz, body.status)
    db.commit()
    return answer


@router.post("/{interview_id}/abschliessen", response_model=InterviewOut)
def finish(interview_id: int, db: Db, me: Me):
    interview = access.editable_interview(db, me, interview_id)
    if interview.status != "abgeschlossen":
        interview.status = "abgeschlossen"
        audit.log(db, "interview", interview.id, "abgeschlossen")
        db.commit()
    return detail(interview, me)


@router.post("/{interview_id}/wiederoeffnen", response_model=InterviewOut)
def reopen(interview_id: int, db: Db, me: Me):
    interview = access.editable_interview(db, me, interview_id)
    if interview.status != "laufend":
        interview.status = "laufend"
        audit.log(db, "interview", interview.id, "wiedergeoeffnet")
        db.commit()
    return detail(interview, me)


EXPORTS = {
    "md": ("text/markdown; charset=utf-8", export.to_markdown),
    "csv": ("text/csv; charset=utf-8", export.to_csv),
    "pdf": ("application/pdf", export.to_pdf),
}


@router.get("/{interview_id}/export.{fmt}")
def export_interview(interview_id: int, fmt: str, db: Db, me: Me):
    if fmt not in EXPORTS:
        raise HTTPException(status_code=404, detail="Unbekanntes Exportformat")
    interview = access.interview(db, me, interview_id)
    media_type, render = EXPORTS[fmt]
    name = export.filename(interview, fmt)
    return Response(
        content=render(interview),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=\"{name}\"; filename*=UTF-8''{quote(name)}"},
    )
