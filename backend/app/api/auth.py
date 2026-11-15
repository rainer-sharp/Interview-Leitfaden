"""Anmeldung mit Benutzername und Passwort, Abmeldung, eigenes Konto (Passwort ändern)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.access import Me, optional_user
from app.api.deps import Db
from app.config import get_settings
from app.models import User, now
from app.services import audit, auth, users

router = APIRouter(prefix="/auth")


class LoginIn(BaseModel):
    # Ohne Benutzername: „admin“ – so funktionieren Skripte und Lesezeichen aus der Ein-Passwort-Zeit weiter.
    benutzername: str = users.FIRST_ADMIN
    passwort: str


class PasswordChange(BaseModel):
    altes_passwort: str
    neues_passwort: str = Field(max_length=200)


def user_out(user: User) -> dict:
    return {"id": user.id, "benutzername": user.benutzername, "name": user.name, "rolle": user.rolle}


def _is_https(request: Request) -> bool:
    # Caddy setzt X-Forwarded-Proto; ohne Proxy zählt das Schema der Anfrage.
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def set_session(request: Request, response: Response, user: User) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.create_token(get_settings().secret_key, user.id, user.sitzungs_version),
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
        path="/",
    )


@router.get("/status")
def status(user: User | None = Depends(optional_user)) -> dict:
    if user is None:
        return {"angemeldet": False}
    return {"angemeldet": True, "benutzer": user_out(user)}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Db) -> dict:
    key = request.client.host if request.client else "unbekannt"
    if auth.limiter.blocked(key):
        raise HTTPException(status_code=429, detail="Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen.")
    users.ensure_admin(db)
    user = users.find(db, body.benutzername)
    # Gleiche Meldung für unbekannte Namen und falsche Passwörter: verrät nicht, welche Konten es gibt.
    if user is None or not users.verify_password(body.passwort, user.passwort_hash):
        auth.limiter.failed(key)
        raise HTTPException(status_code=401, detail="Benutzername oder Passwort ist falsch.")
    if not user.aktiv:
        raise HTTPException(status_code=403, detail="Dieses Konto ist gesperrt. Bitte an einen Admin wenden.")
    auth.limiter.succeeded(key)
    user.letzte_anmeldung = now()
    audit.current_user_id.set(user.id)
    audit.log(db, "benutzer", user.id, "angemeldet")
    db.commit()
    set_session(request, response, user)
    return {"angemeldet": True, "benutzer": user_out(user)}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"angemeldet": False}


@router.put("/passwort")
def change_password(body: PasswordChange, me: Me, request: Request, response: Response, db: Db) -> dict:
    """Eigenes Passwort ändern. Andere Sitzungen dieses Kontos verfallen, die aktuelle bleibt angemeldet."""
    user = db.get(User, me.id)
    if not users.verify_password(body.altes_passwort, user.passwort_hash):
        raise HTTPException(status_code=422, detail="Das bisherige Passwort stimmt nicht.")
    try:
        users.set_password(user, body.neues_passwort)
    except users.UserError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    audit.log(db, "benutzer", user.id, "passwort-geaendert")
    db.commit()
    set_session(request, response, user)
    return {"ok": True}
