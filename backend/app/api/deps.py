from typing import Annotated, TypeVar

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
