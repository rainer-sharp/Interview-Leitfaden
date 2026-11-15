"""Projekte: Standardprojekt, Kopieren mit Gruppen und Katalogen, Anweisung für die KI-Bewertung."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Group, Interview, Project, Question, Questionnaire
from app.services import settings as settings_service


def default_project(db: Session) -> Project:
    """Das älteste Projekt; ohne Projekt wird eins angelegt (z. B. nach dem Löschen aller Gruppen per DB)."""
    project = db.query(Project).order_by(Project.id).first()
    if project is None:
        project = Project(name="Standardprojekt", beschreibung="", ki_anweisung="", ki_analyse_anweisung="")
        db.add(project)
        db.flush()
    return project


def interview_count(db: Session, project_id: int) -> int:
    return (
        db.query(func.count(Interview.id))
        .join(Questionnaire, Interview.questionnaire_id == Questionnaire.id)
        .join(Group, Questionnaire.group_id == Group.id)
        .filter(Group.project_id == project_id)
        .scalar()
    )


def copy_name(db: Session, name: str) -> str:
    """„Name (Kopie)“, bei Bedarf „Name (Kopie 2)“ usw."""
    taken = {n for (n,) in db.query(Project.name)}
    candidate, n = f"{name} (Kopie)", 1
    while candidate in taken:
        n += 1
        candidate = f"{name} (Kopie {n})"
    return candidate[:200]


def copy_project(db: Session, source: Project, name: str, beschreibung: str | None = None) -> Project:
    """Kopiert das Projekt mit allen Gruppen, Katalogen (alle Versionen) und Fragen. Interviews bleiben im Original."""
    copy = Project(
        name=name,
        beschreibung=source.beschreibung if beschreibung is None else beschreibung,
        ki_anweisung=source.ki_anweisung,
        ki_analyse_anweisung=source.ki_analyse_anweisung,
    )
    for group in source.groups:
        new_group = Group(name=group.name, beschreibung=group.beschreibung)
        for catalog in group.questionnaires:
            new_catalog = Questionnaire(name=catalog.name, version=catalog.version, importiert_am=catalog.importiert_am)
            new_catalog.questions = [
                Question(
                    abschnitt=q.abschnitt, position=q.position, text=q.text, hinweis=q.hinweis, pflicht=q.pflicht,
                    typ=q.typ,
                )
                for q in catalog.questions
            ]
            new_group.questionnaires.append(new_catalog)
        copy.groups.append(new_group)
    db.add(copy)
    db.flush()
    return copy


def instructions_for(db: Session, interview: Interview) -> tuple[str, str]:
    """Anweisung für die KI-Bewertung: die des Projekts, sonst die allgemeine. Liefert (Text, Quelle)."""
    own = interview.questionnaire.group.project.ki_anweisung.strip()
    if own:
        return own, "projekt"
    return settings_service.llm(db).anweisung, "allgemein"
