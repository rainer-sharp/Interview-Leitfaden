from fastapi import APIRouter, Response

from app.api.deps import Db
from app.services import audit
from app.services.backup import backup_filename, build_backup

router = APIRouter()


@router.get("/backup")
def download_backup(db: Db) -> Response:
    data = build_backup(db)
    audit.log(db, "backup", 0, "heruntergeladen")
    db.commit()
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{backup_filename()}"'},
    )
