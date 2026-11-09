from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.catalogs import catalog_out
from app.api.deps import Db, get_or_404
from app.api.schemas import QuestionnaireOut
from app.importers.parser import ParseResult, parse_file
from app.models import Group, Question, Questionnaire
from app.services import audit, catalog as catalog_service

router = APIRouter(prefix="/import")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
SAMPLE = Path(__file__).resolve().parent.parent / "importers" / "beispiel.csv"


async def _parse_upload(file: UploadFile) -> ParseResult:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Die Datei ist größer als 5 MB.")
    return parse_file(file.filename or "", data)


@router.get("/beispiel.csv")
def sample() -> FileResponse:
    return FileResponse(SAMPLE, media_type="text/csv; charset=utf-8", filename="fragen-beispiel.csv")


@router.post("/vorschau")
async def preview(file: Annotated[UploadFile, File()]) -> dict:
    return (await _parse_upload(file)).to_dict()


@router.post("", response_model=QuestionnaireOut, status_code=201)
async def save(
    db: Db,
    file: Annotated[UploadFile, File()],
    modus: Annotated[Literal["neu", "version", "anhaengen"], Form()],
    group_id: Annotated[int | None, Form()] = None,
    name: Annotated[str, Form(max_length=200)] = "",
    questionnaire_id: Annotated[int | None, Form()] = None,
):
    result = await _parse_upload(file)
    if not result.ok:
        raise HTTPException(status_code=422, detail="Die Datei enthält Fehler und wurde nicht gespeichert.")

    if modus == "neu":
        name = name.strip()
        if group_id is None or not name:
            raise HTTPException(status_code=422, detail="Für einen neuen Katalog fehlen Gruppe oder Name.")
        group = get_or_404(db, Group, group_id)
        if db.query(Questionnaire).filter_by(group_id=group.id, name=name).first():
            raise HTTPException(
                status_code=409, detail=f"Den Katalog „{name}“ gibt es schon. Bitte als neue Version speichern."
            )
        catalog = Questionnaire(group=group, name=name, version=1)
        db.add(catalog)
    else:
        if questionnaire_id is None:
            raise HTTPException(status_code=422, detail="Bitte einen bestehenden Katalog wählen.")
        existing = get_or_404(db, Questionnaire, questionnaire_id)
        if modus == "anhaengen":
            catalog = existing
        else:
            catalog = Questionnaire(
                group=existing.group,
                name=existing.name,
                version=catalog_service.next_version(db, existing.group_id, existing.name),
            )
            db.add(catalog)

    # Im Katalog zählt nur die Reihenfolge: lückenlos nummerieren, beim Anhängen hinter den Bestand.
    offset = max((q.position for q in catalog.questions), default=0)
    for number, row in enumerate(result.rows, start=offset + 1):
        catalog.questions.append(
            Question(
                position=number,
                abschnitt=row.abschnitt,
                text=row.frage,
                hinweis=row.hinweis,
                pflicht=row.pflicht,
                typ=row.typ,
            )
        )
    db.flush()
    audit.log(db, "questionnaire", catalog.id, f"import_{modus}")
    db.commit()
    return catalog_out(catalog)
