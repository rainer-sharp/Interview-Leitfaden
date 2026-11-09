from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import get_settings
from app.services import auth

router = APIRouter(prefix="/auth")


class LoginIn(BaseModel):
    passwort: str


def is_authenticated(request: Request) -> bool:
    settings = get_settings()
    return auth.token_valid(request.cookies.get(auth.COOKIE_NAME), settings.secret_key, settings.admin_password)


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Bitte anmelden.")


def _is_https(request: Request) -> bool:
    # Caddy setzt X-Forwarded-Proto; ohne Proxy zählt das Schema der Anfrage.
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


@router.get("/status")
def status(request: Request) -> dict[str, bool]:
    return {"angemeldet": is_authenticated(request)}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response) -> dict[str, bool]:
    settings = get_settings()
    key = request.client.host if request.client else "unbekannt"
    if auth.limiter.blocked(key):
        raise HTTPException(status_code=429, detail="Zu viele Fehlversuche. Bitte in 15 Minuten erneut versuchen.")
    if not auth.password_matches(body.passwort, settings.admin_password):
        auth.limiter.failed(key)
        raise HTTPException(status_code=401, detail="Das Passwort ist falsch.")
    auth.limiter.succeeded(key)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.create_token(settings.secret_key, settings.admin_password),
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
        path="/",
    )
    return {"angemeldet": True}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"angemeldet": False}
