from fastapi import APIRouter, HTTPException, Response

from app.api.deps import Db, get_or_404
from app.api.schemas import AnswerOut, AnswerUpdate, InterviewIn, InterviewOut, InterviewSummary, InterviewUpdate
from app.models import Answer, Interview, Questionnaire
from app.services import audit
from app.services import interviews as service

router = APIRouter(prefix="/interviews")


def summary(interview: Interview) -> dict:
    catalog = interview.questionnaire
    return {
        "id": interview.id,
        "questionnaire_id": interview.questionnaire_id,
        "person": interview.person,
        "organisation": interview.organisation,
        "datum": interview.datum,
        "status": interview.status,
        "group_name": catalog.group.name,
        "questionnaire_name": catalog.name,
        "version": catalog.version,
        "fragen": len(interview.answers),
        "bearbeitet": sum(a.status != "offen" for a in interview.answers),
    }


def detail(interview: Interview) -> dict:
    return {**summary(interview), "gesamtnotiz": interview.gesamtnotiz, "answers": interview.answers}


def _require_running(interview: Interview) -> None:
    if interview.status != "laufend":
        raise HTTPException(status_code=409, detail="Das Interview ist abgeschlossen. Zum Ändern bitte wieder öffnen.")


@router.get("", response_model=list[InterviewSummary])
def list_interviews(db: Db):
    rows = db.query(Interview).order_by(Interview.datum.desc(), Interview.id.desc()).all()
    return [summary(i) for i in rows]


@router.post("", response_model=InterviewOut, status_code=201)
def create_interview(body: InterviewIn, db: Db):
    catalog = get_or_404(db, Questionnaire, body.questionnaire_id)
    try:
        interview = service.start(db, catalog, body.person, body.organisation, body.datum)
    except service.EmptyCatalog:
        raise HTTPException(status_code=422, detail="Der Katalog enthält noch keine Fragen.") from None
    audit.log(db, "interview", interview.id, "gestartet")
    db.commit()
    return detail(interview)


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: int, db: Db):
    return detail(get_or_404(db, Interview, interview_id))


@router.put("/{interview_id}", response_model=InterviewOut)
def update_interview(interview_id: int, body: InterviewUpdate, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    _require_running(interview)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(interview, field, value)
    db.commit()
    return detail(interview)


@router.delete("/{interview_id}", status_code=204)
def delete_interview(interview_id: int, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    audit.log(db, "interview", interview.id, "geloescht")
    db.delete(interview)
    db.commit()
    return Response(status_code=204)


@router.put("/{interview_id}/answers/{answer_id}", response_model=AnswerOut)
def update_answer(interview_id: int, answer_id: int, body: AnswerUpdate, db: Db):
    answer = get_or_404(db, Answer, answer_id)
    if answer.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    _require_running(answer.interview)
    service.update_answer(answer, body.notiz, body.status)
    db.commit()
    return answer


@router.post("/{interview_id}/abschliessen", response_model=InterviewOut)
def finish(interview_id: int, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    if interview.status != "abgeschlossen":
        interview.status = "abgeschlossen"
        audit.log(db, "interview", interview.id, "abgeschlossen")
        db.commit()
    return detail(interview)


@router.post("/{interview_id}/wiederoeffnen", response_model=InterviewOut)
def reopen(interview_id: int, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    if interview.status != "laufend":
        interview.status = "laufend"
        audit.log(db, "interview", interview.id, "wiedergeoeffnet")
        db.commit()
    return detail(interview)
