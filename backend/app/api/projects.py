"""Projekte: anlegen, ändern (inkl. Anweisung für die KI-Bewertung), kopieren, löschen."""
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from app.api.deps import Db, get_or_404
from app.api.schemas import ProjectCopyIn, ProjectIn, ProjectOut
from app.models import Project
from app.services import audit
from app.services import projects as service

router = APIRouter(prefix="/projekte")
DUPLICATE = "Ein Projekt mit diesem Namen gibt es schon."


def project_out(db: Db, project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "beschreibung": project.beschreibung,
        "ki_anweisung": project.ki_anweisung,
        "angelegt_am": project.angelegt_am,
        "gruppen": len(project.groups),
        "kataloge": sum(len(g.questionnaires) for g in project.groups),
        "interviews": service.interview_count(db, project.id),
    }


def _commit(db: Db) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE) from None


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Db):
    service.default_project(db)  # es gibt immer mindestens eins
    db.commit()
    return [project_out(db, p) for p in db.query(Project).order_by(Project.name).all()]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Db):
    project = Project(name=body.name, beschreibung=body.beschreibung, ki_anweisung=body.ki_anweisung.strip())
    db.add(project)
    _commit(db)
    audit.log(db, "projekt", project.id, "angelegt")
    db.commit()
    return project_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Db):
    return project_out(db, get_or_404(db, Project, project_id))


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectIn, db: Db):
    project = get_or_404(db, Project, project_id)
    project.name, project.beschreibung = body.name, body.beschreibung
    project.ki_anweisung = body.ki_anweisung.strip()
    _commit(db)
    return project_out(db, project)


@router.post("/{project_id}/kopie", response_model=ProjectOut, status_code=201)
def copy_project(project_id: int, body: ProjectCopyIn, db: Db):
    """Neues Projekt mit Kopien aller Gruppen, Kataloge und Fragen; Interviews werden nicht kopiert."""
    source = get_or_404(db, Project, project_id)
    name = body.name or service.copy_name(db, source.name)
    if db.query(Project).filter(Project.name == name).first() is not None:
        raise HTTPException(status_code=409, detail=DUPLICATE)
    copy = service.copy_project(db, source, name, body.beschreibung)
    _commit(db)
    audit.log(db, "projekt", copy.id, f"kopiert-von-{source.id}")
    db.commit()
    return project_out(db, copy)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Db):
    project = get_or_404(db, Project, project_id)
    if service.interview_count(db, project.id):
        raise HTTPException(status_code=409, detail="Das Projekt hat Interviews. Bitte diese zuerst löschen.")
    if db.query(Project).count() == 1:
        raise HTTPException(status_code=409, detail="Das letzte Projekt kann nicht gelöscht werden.")
    audit.log(db, "projekt", project.id, "geloescht")
    db.delete(project)
    db.commit()
    return Response(status_code=204)
