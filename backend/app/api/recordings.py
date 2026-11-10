"""Audio-Aufnahmen eines Interviews: hochladen, herunterladen, transkribieren, Transkript lesen und korrigieren.

Aufnahmen und Transkripte sind auch bei abgeschlossenen Interviews änderbar: die Aufnahme wird meist erst nach dem
Gespräch hochgeladen, und Notizen bleiben davon unberührt.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import Db, attachment, get_or_404
from app.api.schemas import RecordingOut, TranscriptionStart, TranscriptUpdate
from app.config import get_settings
from app.models import Interview, Recording
from app.services import audit
from app.services import export
from app.services import settings as settings_service
from app.services import transcription

router = APIRouter(prefix="/interviews/{interview_id}/aufnahmen")


def _recording(db: Db, interview_id: int, recording_id: int) -> Recording:
    recording = get_or_404(db, Recording, recording_id)
    if recording.interview_id != interview_id:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return recording


def _require_idle(recording: Recording) -> None:
    if recording.transkript_status in ("wartend", "laeuft"):
        raise HTTPException(status_code=409, detail="Die Transkription dieser Aufnahme läuft bereits.")


@router.get("", response_model=list[RecordingOut])
def list_recordings(interview_id: int, db: Db):
    return get_or_404(db, Interview, interview_id).recordings


@router.post("", response_model=RecordingOut, status_code=201)
def upload(interview_id: int, datei: UploadFile, db: Db):
    interview = get_or_404(db, Interview, interview_id)
    name = Path(datei.filename or "").name.strip() or "aufnahme"
    if Path(name).suffix.lower() not in transcription.AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(transcription.AUDIO_EXTENSIONS))
        raise HTTPException(status_code=422, detail=f"Dateityp nicht unterstützt. Erlaubt: {allowed}")
    max_mb = get_settings().max_audio_mb
    try:
        path, size = transcription.store_upload(interview.id, name, datei.file, max_mb * 1024 * 1024)
    except ValueError:
        raise HTTPException(status_code=413, detail=f"Die Datei ist größer als {max_mb} MB.") from None
    if size == 0:
        transcription.audio_dir().joinpath(path).unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Die Datei ist leer.")
    recording = Recording(interview=interview, dateiname=name[:255], pfad=path, groesse=size)
    db.add(recording)
    db.flush()
    audit.log(db, "aufnahme", recording.id, "hochgeladen")
    db.commit()
    return recording


@router.get("/{recording_id}", response_model=RecordingOut)
def get_recording(interview_id: int, recording_id: int, db: Db):
    return _recording(db, interview_id, recording_id)


@router.get("/{recording_id}/datei")
def download(interview_id: int, recording_id: int, db: Db):
    recording = _recording(db, interview_id, recording_id)
    path = transcription.file_path(recording)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Die Audiodatei fehlt im Datenverzeichnis.")
    return FileResponse(path, media_type="application/octet-stream", headers=attachment(recording.dateiname))


@router.delete("/{recording_id}", status_code=204)
def delete(interview_id: int, recording_id: int, db: Db):
    recording = _recording(db, interview_id, recording_id)
    audit.log(db, "aufnahme", recording.id, "geloescht")
    db.delete(recording)
    db.commit()
    transcription.remove_file(recording)
    return Response(status_code=204)


@router.post("/{recording_id}/transkription", response_model=RecordingOut, status_code=202)
def start_transcription(interview_id: int, recording_id: int, body: TranscriptionStart, db: Db):
    recording = _recording(db, interview_id, recording_id)
    _require_idle(recording)
    defaults = settings_service.transcription(db)
    recording.transkript_optionen = {
        "modus": body.modus,
        "name_ich": body.name_ich or defaults.name_ich,
        # Ohne Angabe heißt der Gesprächspartner wie die interviewte Person.
        "name_partner": body.name_partner or recording.interview.person,
        "begriffe": transcription.split_terms(body.begriffe),
    }
    recording.transkript_status = "wartend"
    recording.transkript_fehler = ""
    recording.transkript_log = ""
    audit.log(db, "aufnahme", recording.id, "transkription-gestartet")
    db.commit()
    transcription.worker.notify()
    return recording


@router.put("/{recording_id}/transkript", response_model=RecordingOut)
def update_transcript(interview_id: int, recording_id: int, body: TranscriptUpdate, db: Db):
    """Korrekturen am Transkript, z. B. falsch erkannte Namen."""
    recording = _recording(db, interview_id, recording_id)
    _require_idle(recording)
    if recording.transkript != body.transkript:
        recording.transkript = body.transkript
        if recording.transkript_status == "keine" and body.transkript.strip():
            recording.transkript_status = "fertig"
        db.commit()
    return recording


@router.get("/{recording_id}/transkript.md")
def download_transcript(interview_id: int, recording_id: int, db: Db):
    recording = _recording(db, interview_id, recording_id)
    if not recording.transkript.strip():
        raise HTTPException(status_code=404, detail="Noch kein Transkript vorhanden.")
    name = export.filename(recording.interview, "md").replace(".md", f"-transkript-{recording.id}.md")
    return Response(recording.transkript, media_type="text/markdown; charset=utf-8", headers=attachment(name))
