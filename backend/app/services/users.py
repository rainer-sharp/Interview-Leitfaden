"""Benutzerkonten: Passwörter (scrypt, Standardbibliothek), erstes Admin-Konto, Notfall-Kommandozeile.

Kommandozeile (im Container: docker compose exec app python -m app.services.users …):
  python -m app.services.users liste
  python -m app.services.users passwort <benutzername>      setzt ein neues Passwort (fragt danach)
  python -m app.services.users admin <benutzername>         macht das Konto zum aktiven Admin
"""
import base64
import getpass
import hashlib
import hmac
import secrets
import sys

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Interview, User

ROLES = ("admin", "interviewer")
MIN_PASSWORD = 8
FIRST_ADMIN = "admin"
# scrypt-Parameter: ca. 50 ms je Prüfung, 16 MB Speicher
_N, _R, _P = 2**14, 8, 1


class UserError(ValueError):
    pass


# ------------------------------------------------------------------ Passwörter
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def check_password_rules(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise UserError(f"Das Passwort muss mindestens {MIN_PASSWORD} Zeichen haben.")


# ------------------------------------------------------------------ Konten
def normalize_username(name: str) -> str:
    return name.strip().lower()


def find(db: Session, username: str) -> User | None:
    return db.query(User).filter(func.lower(User.benutzername) == normalize_username(username)).first()


def active_admins(db: Session) -> int:
    return db.query(User).filter(User.rolle == "admin", User.aktiv.is_(True)).count()


def create(db: Session, username: str, password: str, rolle: str = "interviewer", name: str = "") -> User:
    username = normalize_username(username)
    if not username:
        raise UserError("Bitte einen Benutzernamen angeben.")
    if rolle not in ROLES:
        raise UserError(f"Unbekannte Rolle: {rolle}")
    if find(db, username) is not None:
        raise UserError(f"Den Benutzernamen „{username}“ gibt es schon.")
    check_password_rules(password)
    user = User(
        benutzername=username, name=name.strip() or username, passwort_hash=hash_password(password), rolle=rolle,
        aktiv=True, sitzungs_version=1,
    )
    db.add(user)
    db.flush()
    return user


def set_password(user: User, password: str) -> None:
    """Neues Passwort; alle Sitzungen des Kontos verfallen."""
    check_password_rules(password)
    user.passwort_hash = hash_password(password)
    user.sitzungs_version += 1


def ensure_admin(db: Session) -> User | None:
    """Gibt es noch kein Konto (neue Installation, Update von der Ein-Passwort-Version oder ein altes Backup),
    wird „admin“ mit ADMIN_PASSWORD angelegt. Interviews ohne Interviewer gehören dann diesem Konto."""
    if db.query(User).count():
        return None
    password = get_settings().admin_password
    admin = User(
        benutzername=FIRST_ADMIN, name="Administrator", passwort_hash=hash_password(password), rolle="admin",
        aktiv=True, sitzungs_version=1,
    )
    db.add(admin)
    db.flush()
    db.query(Interview).filter(Interview.user_id.is_(None)).update({Interview.user_id: admin.id})
    db.commit()
    return admin


# ------------------------------------------------------------------ Kommandozeile
def _main(argv: list[str]) -> int:
    from app.db import get_engine

    usage = "Aufruf: python -m app.services.users liste | passwort <benutzername> | admin <benutzername>"
    if not argv or argv[0] not in ("liste", "passwort", "admin") or (argv[0] != "liste" and len(argv) != 2):
        print(usage, file=sys.stderr)
        return 2
    with Session(get_engine()) as db:
        ensure_admin(db)
        if argv[0] == "liste":
            for user in db.query(User).order_by(User.benutzername):
                state = "" if user.aktiv else " (gesperrt)"
                print(f"{user.benutzername:20} {user.rolle:12} {user.name}{state}")
            return 0
        user = find(db, argv[1])
        if user is None:
            print(f"Benutzer „{argv[1]}“ gibt es nicht.", file=sys.stderr)
            return 1
        if argv[0] == "admin":
            user.rolle, user.aktiv = "admin", True
            db.commit()
            print(f"{user.benutzername} ist jetzt aktiver Admin.")
            return 0
        password = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else getpass.getpass("Neues Passwort: ")
        try:
            set_password(user, password)
        except UserError as exc:
            print(exc, file=sys.stderr)
            return 1
        user.aktiv = True
        db.commit()
        print(f"Passwort für {user.benutzername} gesetzt; das Konto ist aktiv.")
        return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
