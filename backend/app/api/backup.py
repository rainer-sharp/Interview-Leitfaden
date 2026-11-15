import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.api.access import Admin
from app.api.deps import Db
from app.services import audit
from app.services import restore
from app.services.backup import backup_filename, build_backup

router = APIRouter()


class RestoreOut(BaseModel):
    gruppen: int
    kataloge: int
    interviews: int
    aufnahmen: int
    fehlende_audiodateien: int
    stand_backup: str
    sicherungskopie: str


class SafetyCopyOut(BaseModel):
    name: str
    groesse: int
    erstellt: datetime


@router.get("/backup")
def download_backup(db: Db, me: Admin) -> Response:
    data = build_backup(db)
    audit.log(db, "backup", 0, "heruntergeladen")
    db.commit()
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{backup_filename()}"'},
    )


def _run(action) -> dict:
    try:
        return asdict(action())
    except restore.RestoreError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/restore", response_model=RestoreOut)
def restore_upload(datei: UploadFile, db: Db, me: Admin):
    """Ersetzt ALLE Daten durch das Backup (ZIP der App oder .db). Der vorherige Stand wird vorher kopiert."""
    db.close()  # die Anfrage-Sitzung darf die Datenbank beim Kopieren nicht sperren
    with tempfile.TemporaryDirectory(prefix="restore_") as tmp:
        source = Path(tmp) / "upload"
        size = 0
        with source.open("wb") as out:
            while chunk := datei.file.read(1024 * 1024):
                size += len(chunk)
                if size > restore.MAX_BYTES:
                    raise HTTPException(status_code=413, detail="Die Datei ist zu groß.")
                out.write(chunk)
        return _run(lambda: restore.restore_file(source))


@router.get("/restore/sicherungskopien", response_model=list[SafetyCopyOut])
def list_safety_copies(me: Admin):
    try:
        return restore.safety_copies()
    except restore.RestoreError:
        return []


@router.post("/restore/sicherungskopien/{name}", response_model=RestoreOut)
def restore_safety_copy(name: str, db: Db, me: Admin):
    """Macht eine Wiederherstellung rückgängig: holt den Stand von davor zurück."""
    db.close()

    def action():
        source = restore.safety_copy_path(name)
        # Die Kopie selbst könnte beim Aufräumen gelöscht werden: vorher in ein Temp-Verzeichnis kopieren.
        with tempfile.TemporaryDirectory(prefix="restore_") as tmp:
            copy = Path(tmp) / "kopie.db"
            shutil.copyfile(source, copy)
            return restore.restore_database(copy)

    return _run(action)
