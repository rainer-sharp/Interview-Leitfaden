"""Wer darf was – an einer Stelle.

- Admin: alles.
- Interviewer: sieht die Projekte, denen er zugeordnet ist, mit allen Gruppen, Katalogen und Interviews darin.
  Er darf dort Gruppen und Kataloge pflegen, Projekte anlegen (und wird dabei Mitglied), Interviews führen und die
  KI-Funktionen nutzen. Interviews anderer darf er nur lesen.
- Nur Admins: Benutzerverwaltung, Projektzuordnung, Projekte löschen, Einstellungen ändern, Sicherung.

Nicht sichtbare Dinge melden 404 (nicht 403), damit niemand fremde Projekte oder Interviews erraten kann.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_engine
from app.models import Group, Interview, Project, ProjectMember, Questionnaire, User
from app.services import audit, auth

NOT_FOUND = HTTPException(status_code=404, detail="Nicht gefunden")


def _load_user(token: str | None) -> User | None:
    parsed = auth.read_token(token, get_settings().secret_key)
    if parsed is None:
        return None
    user_id, version = parsed
    with sessionmaker(bind=get_engine(), expire_on_commit=False)() as db:
        user = db.get(User, user_id)
        if user is None or not user.aktiv or user.sitzungs_version != version:
            return None
        db.expunge(user)
        return user


async def optional_user(request: Request) -> User | None:
    return await run_in_threadpool(_load_user, request.cookies.get(auth.COOKIE_NAME))


async def current_user(request: Request) -> User:
    """Async, damit die Benutzer-ID im Kontext der Anfrage landet und das Audit-Log sie sieht."""
    user = await optional_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Bitte anmelden.")
    audit.current_user_id.set(user.id)
    return user


Me = Annotated[User, Depends(current_user)]


def require_admin(user: Me) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Das darf nur ein Admin.")
    return user


Admin = Annotated[User, Depends(require_admin)]


# ------------------------------------------------------------------ Sichtbarkeit
def visible_project_ids(db: Session, user: User) -> set[int] | None:
    """None = alle (Admin)."""
    if user.is_admin:
        return None
    return {pid for (pid,) in db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id)}


def can_see_project(db: Session, user: User, project_id: int) -> bool:
    ids = visible_project_ids(db, user)
    return ids is None or project_id in ids


def project(db: Session, user: User, project_id: int) -> Project:
    found = db.get(Project, project_id)
    if found is None or not can_see_project(db, user, found.id):
        raise NOT_FOUND
    return found


def group(db: Session, user: User, group_id: int) -> Group:
    found = db.get(Group, group_id)
    if found is None or not can_see_project(db, user, found.project_id):
        raise NOT_FOUND
    return found


def catalog(db: Session, user: User, catalog_id: int) -> Questionnaire:
    found = db.get(Questionnaire, catalog_id)
    if found is None or not can_see_project(db, user, found.group.project_id):
        raise NOT_FOUND
    return found


def interview(db: Session, user: User, interview_id: int) -> Interview:
    found = db.get(Interview, interview_id)
    if found is None or not can_see_project(db, user, found.questionnaire.group.project_id):
        raise NOT_FOUND
    return found


# ------------------------------------------------------------------ Ändern
def can_edit_interview(user: User, item: Interview) -> bool:
    return user.is_admin or item.user_id == user.id


def editable_interview(db: Session, user: User, interview_id: int) -> Interview:
    found = interview(db, user, interview_id)
    if not can_edit_interview(user, found):
        raise HTTPException(
            status_code=403, detail="Dieses Interview führt eine andere Person. Ändern darf nur sie oder ein Admin."
        )
    return found
