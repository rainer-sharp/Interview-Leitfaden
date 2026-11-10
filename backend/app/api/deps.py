from typing import Annotated, TypeVar
from urllib.parse import quote

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db

Db = Annotated[Session, Depends(get_db)]
T = TypeVar("T")


def get_or_404(db: Session, model: type[T], entity_id: int) -> T:
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return entity


def attachment(name: str) -> dict[str, str]:
    """Content-Disposition für Downloads mit Umlauten im Dateinamen."""
    ascii_name = name.encode("ascii", "replace").decode().replace('"', "_").replace("?", "_")
    return {"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"}
