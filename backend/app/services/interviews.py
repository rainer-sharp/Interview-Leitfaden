from datetime import date

from sqlalchemy.orm import Session

from app.models import Answer, Interview, Question, Questionnaire, now


class EmptyCatalog(ValueError):
    pass


def snapshot(question: Question, position: int) -> dict:
    return {
        "question_id": question.id,
        "abschnitt": question.abschnitt,
        "position": position,
        "text": question.text,
        "hinweis": question.hinweis,
        "pflicht": question.pflicht,
        "typ": question.typ,
    }


def start(db: Session, catalog: Questionnaire, person: str, organisation: str, datum: date) -> Interview:
    """Kopiert die Fragen, damit spätere Katalogänderungen dieses Interview nicht verfälschen."""
    if not catalog.questions:
        raise EmptyCatalog
    interview = Interview(questionnaire=catalog, person=person, organisation=organisation, datum=datum)
    for position, question in enumerate(catalog.questions, start=1):
        interview.answers.append(Answer(position=position, question_snapshot=snapshot(question, position)))
    db.add(interview)
    db.flush()
    return interview


def update_answer(answer: Answer, notiz: str | None, status: str | None) -> None:
    """Idempotent: dieselbe Anfrage nochmal ändert weder Inhalt noch Zeitstempel.

    Ohne ausdrücklichen Status folgt er der Notiz: Text macht eine offene Frage zu „beantwortet“,
    Leeren macht eine beantwortete wieder „offen“. „Übersprungen“ und „später“ bleiben stehen.
    """
    new_notiz = answer.notiz if notiz is None else notiz
    new_status = status or answer.status
    if status is None and notiz is not None:
        if answer.status == "offen" and notiz.strip():
            new_status = "beantwortet"
        elif answer.status == "beantwortet" and not notiz.strip():
            new_status = "offen"
    if (new_notiz, new_status) != (answer.notiz, answer.status):
        answer.notiz, answer.status = new_notiz, new_status
        answer.geaendert_am = now()
