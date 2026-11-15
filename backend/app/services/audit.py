from contextvars import ContextVar

from sqlalchemy.orm import Session

from app.models import AuditLog

# Wird bei jeder angemeldeten Anfrage gesetzt (app.api.access.current_user); Hintergrund-Threads: None.
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def log(db: Session, entitaet: str, entity_id: int, aktion: str) -> None:
    """Merkt die Aktion in der laufenden Transaktion vor; committen muss der Aufrufer."""
    db.add(AuditLog(entitaet=f"{entitaet}:{entity_id}", aktion=aktion, benutzer_id=current_user_id.get()))
