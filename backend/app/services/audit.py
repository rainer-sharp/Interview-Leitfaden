from sqlalchemy.orm import Session

from app.models import AuditLog


def log(db: Session, entitaet: str, entity_id: int, aktion: str) -> None:
    """Merkt die Aktion in der laufenden Transaktion vor; committen muss der Aufrufer."""
    db.add(AuditLog(entitaet=f"{entitaet}:{entity_id}", aktion=aktion))
