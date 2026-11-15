"""Projekte: anlegen, ändern (inkl. Anweisung für die KI-Bewertung), kopieren, löschen."""
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from app.api import access
from app.api.access import Admin, Me
from app.api.deps import Db, attachment, get_or_404
from app.api.schemas import (
    ProjectAnalysisOut,
    ProjectAnalysisUpdate,
    ProjectCopyIn,
    ProjectIn,
    ProjectOut,
)
from app.models import Project, User
from app.services import audit
from app.services import evaluation as evaluation_service
from app.services import export
from app.services import project_analysis
from app.services import project_export
from app.services import projects as service

router = APIRouter(prefix="/projekte")
DUPLICATE = "Ein Projekt mit diesem Namen gibt es schon."


def project_out(db: Db, project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "beschreibung": project.beschreibung,
        "ki_anweisung": project.ki_anweisung,
        "ki_analyse_anweisung": project.ki_analyse_anweisung,
        "angelegt_am": project.angelegt_am,
        "gruppen": len(project.groups),
        "kataloge": sum(len(g.questionnaires) for g in project.groups),
        "interviews": service.interview_count(db, project.id),
        "mitglieder": [{"id": u.id, "name": u.name, "benutzername": u.benutzername} for u in project.members],
    }


def _commit(db: Db) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE) from None


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Db, me: Me):
    service.default_project(db)  # es gibt immer mindestens eins
    db.commit()
    query = db.query(Project)
    visible = access.visible_project_ids(db, me)
    if visible is not None:
        query = query.filter(Project.id.in_(visible))
    return [project_out(db, p) for p in query.order_by(Project.name).all()]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Db, me: Me):
    project = Project(
        name=body.name,
        beschreibung=body.beschreibung,
        ki_anweisung=body.ki_anweisung.strip(),
        ki_analyse_anweisung=(body.ki_analyse_anweisung or "").strip(),
    )
    project.members.append(db.get(User, me.id))  # wer anlegt, sieht das Projekt auch
    db.add(project)
    _commit(db)
    audit.log(db, "projekt", project.id, "angelegt")
    db.commit()
    return project_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Db, me: Me):
    return project_out(db, access.project(db, me, project_id))


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectIn, db: Db, me: Me):
    project = access.project(db, me, project_id)
    project.name, project.beschreibung = body.name, body.beschreibung
    project.ki_anweisung = body.ki_anweisung.strip()
    if body.ki_analyse_anweisung is not None:
        project.ki_analyse_anweisung = body.ki_analyse_anweisung.strip()
    _commit(db)
    return project_out(db, project)


@router.post("/{project_id}/kopie", response_model=ProjectOut, status_code=201)
def copy_project(project_id: int, body: ProjectCopyIn, db: Db, me: Me):
    """Neues Projekt mit Kopien aller Gruppen, Kataloge und Fragen; Interviews werden nicht kopiert."""
    source = access.project(db, me, project_id)
    name = body.name or service.copy_name(db, source.name)
    if db.query(Project).filter(Project.name == name).first() is not None:
        raise HTTPException(status_code=409, detail=DUPLICATE)
    copy = service.copy_project(db, source, name, body.beschreibung)
    copy.members.append(db.get(User, me.id))
    _commit(db)
    audit.log(db, "projekt", copy.id, f"kopiert-von-{source.id}")
    db.commit()
    return project_out(db, copy)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Db, me: Admin):
    project = access.project(db, me, project_id)
    if service.interview_count(db, project.id):
        raise HTTPException(status_code=409, detail="Das Projekt hat Interviews. Bitte diese zuerst löschen.")
    if db.query(Project).count() == 1:
        raise HTTPException(status_code=409, detail="Das letzte Projekt kann nicht gelöscht werden.")
    audit.log(db, "projekt", project.id, "geloescht")
    db.delete(project)
    db.commit()
    return Response(status_code=204)


@router.put("/{project_id}/mitglieder", response_model=ProjectOut)
def set_members(project_id: int, body: list[int], db: Db, me: Admin):
    """Legt fest, welche Benutzer das Projekt sehen (für Admins ohne Wirkung, sie sehen alles)."""
    project = access.project(db, me, project_id)
    members = db.query(User).filter(User.id.in_(body)).all()
    if len(members) != len(set(body)):
        raise HTTPException(status_code=422, detail="Unbekannter Benutzer in der Liste.")
    project.members = members
    audit.log(db, "projekt", project.id, "mitglieder-geaendert")
    db.commit()
    return project_out(db, project)


# ------------------------------------------------------------------ Sammelexport
EXPORTS = {
    "md": ("text/markdown; charset=utf-8", project_export.to_markdown),
    "json": ("application/json; charset=utf-8", project_export.to_json),
}


@router.get("/{project_id}/export.{fmt}")
def export_project(project_id: int, fmt: str, db: Db, me: Me, nur_transkripte: bool = False):
    """Alle Interviews des Projekts in einer Datei (Markdown oder JSON); nur_transkripte=true: nur Transkripte."""
    if fmt not in EXPORTS:
        raise HTTPException(status_code=404, detail="Unbekanntes Exportformat")
    project = access.project(db, me, project_id)
    media_type, render = EXPORTS[fmt]
    name = project_export.filename(project, fmt, "-transkripte" if nur_transkripte else "-interviews")
    return Response(render(db, project, nur_transkripte), media_type=media_type, headers=attachment(name))


# ------------------------------------------------------------------ KI-Analyse des Projekts
def _analysis_out(db: Db, project: Project) -> dict:
    interviews = [i for i in project_export.interviews_of(db, project) if project_analysis.has_content(i)]
    data = {
        "interviews_jetzt": len(interviews),
        "mit_transkript": sum(bool(export.transcripts(i)) for i in interviews),
        "mit_bewertung": sum(bool(i.evaluation and i.evaluation.text.strip()) for i in interviews),
        "anweisung_quelle": project_analysis.instructions_for(db, project)[1],
    }
    analysis = project.analysis
    if analysis is None:
        return {**data, "status": "keine"}
    fields = (
        "status", "analyse", "kurzfassung", "fehler", "fortschritt", "modell", "interviews", "umfang", "bearbeitet",
        "gestartet_am", "fertig_am",
    )
    return {**data, **{field: getattr(analysis, field) for field in fields}}


def _require_idle(project: Project) -> None:
    if project.analysis is not None and project.analysis.status in project_analysis.BUSY:
        raise HTTPException(status_code=409, detail="Die Analyse dieses Projekts läuft bereits.")


@router.get("/{project_id}/analyse", response_model=ProjectAnalysisOut)
def get_analysis(project_id: int, db: Db, me: Me):
    return _analysis_out(db, access.project(db, me, project_id))


@router.post("/{project_id}/analyse", response_model=ProjectAnalysisOut, status_code=202)
def start_analysis(project_id: int, db: Db, me: Me):
    project = access.project(db, me, project_id)
    _require_idle(project)
    if not any(project_analysis.has_content(i) for i in project_export.interviews_of(db, project)):
        raise HTTPException(status_code=422, detail="Das Projekt hat noch keine Interviews mit Notizen oder Transkript.")
    project_analysis.start(db, project)
    audit.log(db, "projekt-analyse", project.id, "analyse-gestartet")
    db.commit()
    evaluation_service.worker.notify()
    return _analysis_out(db, project)


@router.put("/{project_id}/analyse", response_model=ProjectAnalysisOut)
def update_analysis(project_id: int, body: ProjectAnalysisUpdate, db: Db, me: Me):
    project = access.project(db, me, project_id)
    _require_idle(project)
    analysis = project.analysis
    if analysis is None or not (analysis.analyse or analysis.kurzfassung):
        raise HTTPException(status_code=404, detail="Noch keine Analyse vorhanden.")
    for field in ("analyse", "kurzfassung"):
        value = getattr(body, field)
        if value is not None and value != getattr(analysis, field):
            setattr(analysis, field, value)
            analysis.bearbeitet = True
    db.commit()
    return _analysis_out(db, project)


@router.delete("/{project_id}/analyse", status_code=204)
def delete_analysis(project_id: int, db: Db, me: Me):
    project = access.project(db, me, project_id)
    if project.analysis is not None:
        db.delete(project.analysis)
        audit.log(db, "projekt-analyse", project.id, "analyse-geloescht")
        db.commit()
    return Response(status_code=204)


ANALYSIS_DOWNLOADS = {
    "md": ("text/markdown; charset=utf-8", export.analysis_markdown),
    "pdf": ("application/pdf", export.analysis_pdf),
}


@router.get("/{project_id}/analyse.{fmt}")
def download_analysis(project_id: int, fmt: str, db: Db, me: Me):
    if fmt not in ANALYSIS_DOWNLOADS:
        raise HTTPException(status_code=404, detail="Unbekanntes Format")
    project = access.project(db, me, project_id)
    analysis = project.analysis
    if analysis is None or not (analysis.analyse.strip() or analysis.kurzfassung.strip()):
        raise HTTPException(status_code=404, detail="Noch keine Analyse vorhanden.")
    media_type, render = ANALYSIS_DOWNLOADS[fmt]
    return Response(
        render(project), media_type=media_type, headers=attachment(project_export.filename(project, fmt, "-analyse"))
    )
