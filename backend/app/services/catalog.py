from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models import Question, Questionnaire


class OrderMismatch(ValueError):
    pass


def next_version(db: Session, group_id: int, name: str) -> int:
    versions = db.query(Questionnaire.version).filter_by(group_id=group_id, name=name).all()
    return max((v for (v,) in versions), default=0) + 1


def append_question(catalog: Questionnaire, **fields) -> Question:
    position = max((q.position for q in catalog.questions), default=0) + 1
    question = Question(position=position, **fields)
    catalog.questions.append(question)
    return question


def renumber(catalog: Questionnaire) -> None:
    for position, question in enumerate(sorted(catalog.questions, key=lambda q: q.position), start=1):
        question.position = position


def apply_order(catalog: Questionnaire, order: Sequence[tuple[int, str]]) -> None:
    """Setzt Reihenfolge und Abschnitt; die Liste muss genau alle Fragen des Katalogs enthalten."""
    by_id = {q.id: q for q in catalog.questions}
    ids = [question_id for question_id, _ in order]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise OrderMismatch
    for position, (question_id, abschnitt) in enumerate(order, start=1):
        by_id[question_id].position = position
        by_id[question_id].abschnitt = abschnitt
