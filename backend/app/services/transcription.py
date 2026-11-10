"""Audio-Aufnahmen speichern und mit transcribe_interview.py transkribieren.

transcribe_interview.py ist eine unveränderte Kopie aus dem Projekt „transcription“ und wird hier als Modul
importiert. Das Skript hält den Server in Modulvariablen und beendet sich bei Fehlern mit sys.exit; beides fängt
dieser Adapter ab. Transkribiert wird in einem Hintergrund-Thread, immer nur eine Aufnahme gleichzeitig
(der Server verträgt laut README nur zwei parallele Anfragen, und ein Block kann eine Stunde dauern).
"""
import json
import logging
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_engine
from app.models import Recording, now
from app.services import audit
from app.services import settings as settings_service
from app.services import transcribe_interview as script

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mkv", ".mp4", ".mov", ".webm", ".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".opus", ".flac"}
LOG_LINES = 200
TERMINAL = ("keine", "fertig", "fehler")


class TranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Options:
    modus: str = "mix"
    name_ich: str = script.NAME_ME
    name_partner: str = script.NAME_PARTNER
    begriffe: list[str] = field(default_factory=list)


def split_terms(text: str) -> list[str]:
    """Wie --terms/--terms-file im Skript: Komma oder Zeilenumbruch, #-Zeilen sind Kommentare."""
    parts = (t.strip() for t in text.replace("\n", ",").split(","))
    return list(dict.fromkeys(t for t in parts if t and not t.startswith("#")))


# ------------------------------------------------------------------ Dateien
def audio_dir() -> Path:
    """AUDIO_DIR, sonst „audio“ neben der SQLite-Datei (liegt damit im selben Volume)."""
    settings = get_settings()
    if settings.audio_dir:
        return Path(settings.audio_dir)
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        return Path(url.database).resolve().parent / "audio"
    return Path("data/audio").resolve()


def store_upload(interview_id: int, filename: str, source, max_bytes: int) -> tuple[str, int]:
    """Kopiert den Upload blockweise nach AUDIO_DIR/<interview>/<uuid>.<endung>. Liefert (relativer Pfad, Größe)."""
    suffix = Path(filename).suffix.lower()
    relative = f"{interview_id}/{uuid.uuid4().hex}{suffix}"
    target = audio_dir() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with target.open("wb") as out:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("zu groß")
                out.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return relative, size


def file_path(recording: Recording) -> Path:
    return audio_dir() / recording.pfad


def remove_file(recording: Recording) -> None:
    file_path(recording).unlink(missing_ok=True)


def remove_interview_files(interview_id: int) -> None:
    shutil.rmtree(audio_dir() / str(interview_id), ignore_errors=True)


# ------------------------------------------------------------------ Skript
_script_lock = threading.Lock()


@contextmanager
def _script_configured(server: settings_service.TranscriptionSettings, log: Callable[[str], None]):
    """Setzt Server, Modell und Schlüssel im Skript und leitet dessen Fortschrittsausgaben ins Log um."""
    with _script_lock:
        saved = script.SERVER_URL, script.MODEL_NAME, script.API_KEY
        script.SERVER_URL = server.url.rstrip("/")
        script.MODEL_NAME = server.model
        script.API_KEY = server.api_key or "EMPTY"
        script.print = lambda *args, **_kw: log(" ".join(str(a) for a in args).strip())
        try:
            yield
        except SystemExit as exc:  # das Skript bricht bei Fehlern mit sys.exit(meldung) ab
            raise TranscriptionError(str(exc.code)) from None
        except urllib.error.URLError as exc:
            raise TranscriptionError(f"Transkriptions-Server nicht erreichbar ({server.url}): {exc.reason}") from None
        except TimeoutError:
            raise TranscriptionError(f"Zeitüberschreitung beim Transkriptions-Server ({server.url}).") from None
        finally:
            script.SERVER_URL, script.MODEL_NAME, script.API_KEY = saved
            del script.print


def ffmpeg_available() -> bool:
    return all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe"))


def transcribe_file(
    src: Path,
    display_name: str,
    server: settings_service.TranscriptionSettings,
    options: Options,
    log: Callable[[str], None] = lambda _line: None,
) -> str:
    """Entspricht main() im Skript, liefert das Markdown aber als Text statt es in eine Datei zu schreiben."""
    if not ffmpeg_available():
        raise TranscriptionError("ffmpeg/ffprobe nicht gefunden. Im Container sind sie installiert.")
    if not src.exists():
        raise TranscriptionError("Die Audiodatei fehlt.")
    if options.modus not in settings_service.MODES:
        raise TranscriptionError(f"Unbekannter Modus: {options.modus}")
    terms = list(dict.fromkeys(options.begriffe))
    prompt = (script.PROMPT_SPK if options.modus == "mix" else script.PROMPT_PLAIN) + (
        f" Context terms: {', '.join(terms)}." if terms else ""
    )
    names = (options.name_ich, options.name_partner)
    with _script_configured(server, log):
        n_tracks = script.audio_track_count(src)
        if n_tracks < script.TRACK_MIX:
            raise TranscriptionError("Die Datei enthält keine Audiospur.")
        has_tracks = n_tracks >= script.TRACK_PARTNER
        if options.modus == "tracks" and not has_tracks:
            raise TranscriptionError(
                f"Modus „Spuren getrennt“ braucht {script.TRACK_PARTNER} Audiospuren (OBS), gefunden: {n_tracks}."
            )
        log(f"{display_name}: {n_tracks} Audiospur(en), Modus {options.modus}")
        with tempfile.TemporaryDirectory(prefix="transcribe_") as tmp_dir:
            tmp = Path(tmp_dir)
            if options.modus == "mix":
                words, duration = script.mode_mix(src, tmp, prompt, has_tracks, names)
            else:
                words, duration = script.mode_tracks(src, tmp, prompt, names)
            out = tmp / "transkript.md"
            # write_markdown nutzt vom Pfad nur .name für die Überschrift: dort soll der Originalname stehen.
            script.write_markdown(out, Path(display_name), options.modus, terms, script.build_turns(words), duration)
            return out.read_text(encoding="utf-8")


def check_server(server: settings_service.TranscriptionSettings, timeout: float = 10) -> dict:
    """Fragt /models ab. Liefert ok, Meldung und die angebotenen Modelle."""
    url = server.url.rstrip("/") + "/models"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {server.api_key or 'EMPTY'}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        return {"ok": False, "meldung": f"Server antwortet mit Fehler {exc.code}.", "modelle": []}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"ok": False, "meldung": f"Nicht erreichbar: {reason}", "modelle": []}
    except ValueError:
        return {"ok": False, "meldung": "Antwort ist kein JSON – ist das ein OpenAI-kompatibler Endpunkt?", "modelle": []}
    models = [m.get("id", "") for m in body.get("data", []) if isinstance(m, dict)]
    if server.model not in models:
        return {"ok": False, "meldung": f"Server erreichbar, aber Modell „{server.model}“ fehlt.", "modelle": models}
    return {"ok": True, "meldung": "Server erreichbar, Modell vorhanden.", "modelle": models}


# ------------------------------------------------------------------ Aufträge
Transcriber = Callable[..., str]


def _sessions() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def _append_log(recording_id: int, line: str) -> None:
    with _sessions()() as db:
        recording = db.get(Recording, recording_id)
        if recording is None:
            return
        lines = (recording.transkript_log.splitlines() + [line])[-LOG_LINES:]
        recording.transkript_log = "\n".join(lines)
        db.commit()


def process_next(transcriber: Transcriber = transcribe_file) -> bool:
    """Transkribiert die älteste wartende Aufnahme. False, wenn keine wartet."""
    with _sessions()() as db:
        recording = (
            db.query(Recording).filter(Recording.transkript_status == "wartend").order_by(Recording.id).first()
        )
        if recording is None:
            return False
        recording.transkript_status = "laeuft"
        recording.transkript_start = now()
        recording.transkript_ende = None
        recording.transkript_fehler = ""
        recording.transkript_log = ""
        db.commit()
        recording_id = recording.id
        src, name = file_path(recording), recording.dateiname
        options = Options(**recording.transkript_optionen)
        server = settings_service.transcription(db)

    text, error = "", ""
    try:
        text = transcriber(src, name, server, options, lambda line: _append_log(recording_id, line))
    except TranscriptionError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 – jeder Fehler soll beim Auftrag sichtbar werden, nicht im Thread verpuffen
        logger.exception("Transkription von Aufnahme %s fehlgeschlagen", recording_id)
        error = f"Unerwarteter Fehler: {type(exc).__name__}: {exc}"

    with _sessions()() as db:
        recording = db.get(Recording, recording_id)
        if recording is None:  # während der Transkription gelöscht
            return True
        recording.transkript_ende = now()
        if error:
            recording.transkript_status, recording.transkript_fehler = "fehler", error
        else:
            recording.transkript_status, recording.transkript = "fertig", text
        audit.log(db, "aufnahme", recording_id, "transkript-fehler" if error else "transkribiert")
        db.commit()
    return True


def requeue_interrupted() -> int:
    """Nach einem Neustart: abgebrochene Aufträge wieder einreihen."""
    with _sessions()() as db:
        rows = db.query(Recording).filter(Recording.transkript_status == "laeuft").all()
        for recording in rows:
            recording.transkript_status = "wartend"
            recording.transkript_log += "\nNeustart der App – Auftrag wird wiederholt."
        db.commit()
        return len(rows)


class Worker:
    """Ein Thread, der wartende Aufträge nacheinander abarbeitet. notify() weckt ihn sofort.

    process() erledigt einen Auftrag und liefert False, wenn keiner wartet; recover() reiht beim Start
    abgebrochene Aufträge wieder ein. Die KI-Bewertung nutzt dieselbe Klasse mit eigenen Funktionen.
    """

    def __init__(
        self,
        process: Callable[[], bool] | None = None,
        recover: Callable[[], int] | None = None,
        name: str = "transkription",
    ) -> None:
        self._process = process or (lambda: process_next())
        self._recover = recover or requeue_interrupted
        self._name = name
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._recover()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def notify(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()
            try:
                while not self._stop.is_set() and self._process():
                    pass
            except Exception:  # noqa: BLE001 – z. B. DB kurz gesperrt; der Thread darf nicht sterben
                logger.exception("Fehler im Hintergrund-Thread %s", self._name)
            self._wake.wait(timeout=60)


worker = Worker()
