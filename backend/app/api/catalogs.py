from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from app.api import access
from app.api.access import Me
from app.api.deps import Db, get_or_404
from app.api.schemas import (
    GroupIn,
    GroupOut,
    OrderItem,
    QuestionIn,
    QuestionnaireIn,
    QuestionnaireOut,
    QuestionnaireSummary,
    QuestionOut,
)
from app.models import Group, Project, Question, Questionnaire
from app.services import audit, catalog as catalog_service
from app.services import projects as project_service

router = APIRouter()


def summary(catalog: Questionnaire) -> dict:
    return {
        "id": catalog.id,
        "group_id": catalog.group_id,
        "name": catalog.name,
        "version": catalog.version,
        "importiert_am": catalog.importiert_am,
        "fragen": len(catalog.questions),
        "interviews": len(catalog.interviews),
    }


def group_out(group: Group) -> dict:
    return {
        "id": group.id,
        "projekt_id": group.project_id,
        "projekt_name": group.project.name,
        "name": group.name,
        "beschreibung": group.beschreibung,
        "questionnaires": [summary(c) for c in group.questionnaires],
    }


def catalog_out(catalog: Questionnaire) -> dict:
    return {**summary(catalog), "group_name": catalog.group.name, "questions": catalog.questions}


def _commit_or_conflict(db: Db, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from None


DUPLICATE_GROUP = "Eine Gruppe mit diesem Namen gibt es in diesem Projekt schon."


def _question(db: Db, me: Me, question_id: int) -> Question:
    question = get_or_404(db, Question, question_id)
    access.catalog(db, me, question.questionnaire_id)
    return question


@router.get("/groups", response_model=list[GroupOut])
def list_groups(db: Db, me: Me, projekt_id: int | None = None):
    """Ohne projekt_id alle Gruppen aller Projekte."""
    query = db.query(Group)
    if projekt_id is not None:
        query = query.filter(Group.project_id == projekt_id)
    visible = access.visible_project_ids(db, me)
    if visible is not None:
        query = query.filter(Group.project_id.in_(visible))
    return [group_out(g) for g in query.order_by(Group.name, Group.id).all()]


@router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(body: GroupIn, db: Db, me: Me):
    if body.projekt_id is None:
        project = project_service.default_project(db)
        if not access.can_see_project(db, me, project.id):
            raise HTTPException(status_code=422, detail="Bitte ein Projekt angeben.")
    else:
        project = access.project(db, me, body.projekt_id)
    group = Group(project=project, name=body.name, beschreibung=body.beschreibung)
    db.add(group)
    _commit_or_conflict(db, DUPLICATE_GROUP)
    return group_out(group)


@router.get("/groups/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: Db, me: Me):
    return group_out(access.group(db, me, group_id))


@router.put("/groups/{group_id}", response_model=GroupOut)
def update_group(group_id: int, body: GroupIn, db: Db, me: Me):
    group = access.group(db, me, group_id)
    group.name, group.beschreibung = body.name, body.beschreibung
    if body.projekt_id is not None and body.projekt_id != group.project_id:
        # Verschieben: die Interviews der Gruppe wandern mit (sie hängen über den Katalog an der Gruppe)
        group.project = access.project(db, me, body.projekt_id)
    _commit_or_conflict(db, DUPLICATE_GROUP)
    return group_out(group)


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: int, db: Db, me: Me):
    group = access.group(db, me, group_id)
    if any(c.interviews for c in group.questionnaires):
        raise HTTPException(status_code=409, detail="Die Gruppe hat Interviews. Bitte diese zuerst löschen.")
    audit.log(db, "group", group.id, "geloescht")
    db.delete(group)
    db.commit()
    return Response(status_code=204)


@router.post("/groups/{group_id}/questionnaires", response_model=QuestionnaireOut, status_code=201)
def create_questionnaire(group_id: int, body: QuestionnaireIn, db: Db, me: Me):
    group = access.group(db, me, group_id)
    catalog = Questionnaire(group=group, name=body.name, version=catalog_service.next_version(db, group.id, body.name))
    db.add(catalog)
    db.commit()
    return catalog_out(catalog)


@router.get("/questionnaires/{catalog_id}", response_model=QuestionnaireOut)
def get_questionnaire(catalog_id: int, db: Db, me: Me):
    return catalog_out(access.catalog(db, me, catalog_id))


@router.put("/questionnaires/{catalog_id}", response_model=QuestionnaireSummary)
def rename_questionnaire(catalog_id: int, body: QuestionnaireIn, db: Db, me: Me):
    catalog = access.catalog(db, me, catalog_id)
    catalog.name = body.name
    _commit_or_conflict(db, "Diesen Namen hat in dieser Version schon ein anderer Katalog.")
    return summary(catalog)


@router.delete("/questionnaires/{catalog_id}", status_code=204)
def delete_questionnaire(catalog_id: int, db: Db, me: Me):
    catalog = access.catalog(db, me, catalog_id)
    if catalog.interviews:
        raise HTTPException(status_code=409, detail="Der Katalog hat Interviews. Bitte diese zuerst löschen.")
    audit.log(db, "questionnaire", catalog.id, "geloescht")
    db.delete(catalog)
    db.commit()
    return Response(status_code=204)


@router.post("/questionnaires/{catalog_id}/questions", response_model=QuestionOut, status_code=201)
def add_question(catalog_id: int, body: QuestionIn, db: Db, me: Me):
    catalog = access.catalog(db, me, catalog_id)
    question = catalog_service.append_question(catalog, **body.model_dump())
    db.commit()
    return question


@router.put("/questionnaires/{catalog_id}/order", response_model=list[QuestionOut])
def set_order(catalog_id: int, body: list[OrderItem], db: Db, me: Me):
    catalog = access.catalog(db, me, catalog_id)
    try:
        catalog_service.apply_order(catalog, [(item.id, item.abschnitt) for item in body])
    except catalog_service.OrderMismatch:
        raise HTTPException(status_code=422, detail="Die Liste muss genau alle Fragen des Katalogs enthalten.") from None
    db.commit()
    db.refresh(catalog)
    return catalog.questions


@router.put("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, body: QuestionIn, db: Db, me: Me):
    question = _question(db, me, question_id)
    for field, value in body.model_dump().items():
        setattr(question, field, value)
    db.commit()
    return question


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, db: Db, me: Me):
    question = _question(db, me, question_id)
    catalog = question.questionnaire
    catalog.questions.remove(question)
    catalog_service.renumber(catalog)
    db.commit()
    return Response(status_code=204)
