"""Benutzerverwaltung (nur Admins): Konten anlegen, ändern, sperren, Passwort zurücksetzen, Projekte zuordnen."""
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, StringConstraints

from app.api.access import Admin
from app.api.deps import Db, get_or_404
from app.models import Interview, Project, User
from app.services import audit, users

router = APIRouter(prefix="/benutzer")

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[\w.@-]+$")]
Role = Literal["admin", "interviewer"]


class UserIn(BaseModel):
    benutzername: Username
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    passwort: str = Field(max_length=200)
    rolle: Role = "interviewer"
    projekte: list[int] = []


class UserUpdate(BaseModel):
    """None = unverändert."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    rolle: Role | None = None
    aktiv: bool | None = None
    passwort: str | None = Field(default=None, max_length=200)  # setzt ein neues Passwort
    projekte: list[int] | None = None


class UserOut(BaseModel):
    id: int
    benutzername: str
    name: str
    rolle: str
    aktiv: bool
    angelegt_am: datetime
    letzte_anmeldung: datetime | None
    projekte: list[int]
    interviews: int


def _out(db: Db, user: User) -> dict:
    return {
        "id": user.id,
        "benutzername": user.benutzername,
        "name": user.name,
        "rolle": user.rolle,
        "aktiv": user.aktiv,
        "angelegt_am": user.angelegt_am,
        "letzte_anmeldung": user.letzte_anmeldung,
        "projekte": sorted(p.id for p in user.projects),
        "interviews": db.query(Interview).filter(Interview.user_id == user.id).count(),
    }


def _projects(db: Db, ids: list[int]) -> list[Project]:
    found = db.query(Project).filter(Project.id.in_(ids)).all()
    if len(found) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Unbekanntes Projekt in der Liste.")
    return found


def _keep_an_admin(db: Db, user: User, rolle: str | None, aktiv: bool | None) -> None:
    loses_admin = user.is_admin and user.aktiv and ((rolle is not None and rolle != "admin") or aktiv is False)
    if loses_admin and users.active_admins(db) <= 1:
        raise HTTPException(status_code=409, detail="Es muss mindestens ein aktiver Admin bleiben.")


@router.get("", response_model=list[UserOut])
def list_users(db: Db, me: Admin):
    return [_out(db, u) for u in db.query(User).order_by(User.benutzername)]


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserIn, db: Db, me: Admin):
    try:
        user = users.create(db, body.benutzername, body.passwort, body.rolle, body.name)
    except users.UserError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    user.projects = _projects(db, body.projekte)
    audit.log(db, "benutzer", user.id, "angelegt")
    db.commit()
    return _out(db, user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Db, me: Admin):
    user = get_or_404(db, User, user_id)
    _keep_an_admin(db, user, body.rolle, body.aktiv)
    if body.name is not None:
        user.name = body.name or user.benutzername
    if body.rolle is not None:
        user.rolle = body.rolle
    if body.aktiv is not None and body.aktiv != user.aktiv:
        user.aktiv = body.aktiv
        if not body.aktiv:
            user.sitzungs_version += 1  # Sperre wirkt sofort, auch in offenen Browserfenstern
        audit.log(db, "benutzer", user.id, "entsperrt" if body.aktiv else "gesperrt")
    if body.passwort is not None:
        try:
            users.set_password(user, body.passwort)
        except users.UserError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        audit.log(db, "benutzer", user.id, "passwort-zurueckgesetzt")
    if body.projekte is not None:
        user.projects = _projects(db, body.projekte)
    db.commit()
    return _out(db, user)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Db, me: Admin):
    """Nur Konten ohne Interviews; sonst sperren, damit erkennbar bleibt, wer welches Interview geführt hat."""
    user = get_or_404(db, User, user_id)
    if user.id == me.id:
        raise HTTPException(status_code=409, detail="Das eigene Konto kann nicht gelöscht werden.")
    if db.query(Interview).filter(Interview.user_id == user.id).count():
        raise HTTPException(status_code=409, detail="Das Konto hat Interviews. Bitte sperren statt löschen.")
    _keep_an_admin(db, user, None, False)
    audit.log(db, "benutzer", user.id, "geloescht")
    db.delete(user)
    db.commit()
    return Response(status_code=204)
