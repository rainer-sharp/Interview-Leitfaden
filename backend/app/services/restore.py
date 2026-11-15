"""Wiederherstellung aus einem Backup: Backup-ZIP der App (enthält interviews.db) oder eine .db-Datei aus der
täglichen Sicherung (backups/interviews-<datum>.db).

Ablauf: Datei prüfen (SQLite, Integrität, bekannte Migration) → Sicherungskopie des aktuellen Stands unter
<daten>/wiederherstellung/ → Inhalt per SQLite-Backup-API in die laufende Datenbank kopieren → Migrationen auf den
aktuellen Stand → unterbrochene Aufträge wieder einreihen. Die App muss dafür nicht gestoppt werden.

Audiodateien sind nicht im Backup; vorhandene Dateien unter data/audio/ bleiben unangetastet.

Aufruf von der Kommandozeile: python -m app.services.restore <backup.zip | backup.db | ->
"""
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Evaluation, ProjectAnalysis, Recording
from app.services import audit

BACKEND = Path(__file__).resolve().parents[2]
SQLITE_MAGIC = b"SQLite format 3\x00"
DB_IN_ZIP = "interviews.db"
MAX_BYTES = 4 * 1024**3
KEEP_SAFETY_COPIES = 5
SAFETY_PREFIX = "vor-wiederherstellung-"
REQUIRED_TABLES = {"group", "questionnaire", "question", "interview", "answer", "alembic_version"}


class RestoreError(ValueError):
    pass


@dataclass
class RestoreResult:
    gruppen: int
    kataloge: int
    interviews: int
    aufnahmen: int
    fehlende_audiodateien: int
    stand_backup: str  # Migration, auf der das Backup stand
    sicherungskopie: str  # Dateiname der Kopie des vorherigen Stands


# ------------------------------------------------------------------ Pfade
def live_database() -> Path:
    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RestoreError("Wiederherstellen geht nur mit einer SQLite-Datenbankdatei.")
    return Path(url.database).resolve()


def safety_dir() -> Path:
    return live_database().parent / "wiederherstellung"


def safety_copies() -> list[dict]:
    """Kopien der Stände vor früheren Wiederherstellungen, neueste zuerst."""
    folder = safety_dir()
    if not folder.is_dir():
        return []
    files = sorted(folder.glob(f"{SAFETY_PREFIX}*.db"), key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    return [
        {"name": f.name, "groesse": f.stat().st_size, "erstellt": datetime.fromtimestamp(f.stat().st_mtime)}
        for f in files
    ]


def safety_copy_path(name: str) -> Path:
    """Nur Namen aus der Liste: kein Pfad von außen."""
    if name not in {c["name"] for c in safety_copies()}:
        raise RestoreError("Diese Sicherungskopie gibt es nicht.")
    return safety_dir() / name


# ------------------------------------------------------------------ Prüfen
def _alembic_config() -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    return config


def extract_database(source: Path, work_dir: Path) -> Path:
    """Liefert den Pfad einer SQLite-Datei: die Datei selbst oder interviews.db aus dem ZIP."""
    with source.open("rb") as handle:
        head = handle.read(len(SQLITE_MAGIC))
    if head == SQLITE_MAGIC:
        return source
    if not zipfile.is_zipfile(source):
        raise RestoreError("Die Datei ist weder ein Backup-ZIP noch eine SQLite-Datenbank (.db).")
    with zipfile.ZipFile(source) as archive:
        try:
            info = archive.getinfo(DB_IN_ZIP)
        except KeyError:
            raise RestoreError(f"Im ZIP fehlt {DB_IN_ZIP} – ist das ein Backup dieser App?") from None
        if info.file_size > MAX_BYTES:
            raise RestoreError("Die Datenbank im ZIP ist zu groß.")
        target = work_dir / "backup.db"
        with archive.open(info) as packed, target.open("wb") as out:
            shutil.copyfileobj(packed, out, 1024 * 1024)
    return target


def inspect(path: Path) -> tuple[str, dict[str, int]]:
    """Prüft das Backup. Liefert (Migrationsstand, Anzahl Gruppen/Kataloge/Interviews/Aufnahmen)."""
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise RestoreError(f"Datenbank lässt sich nicht öffnen: {exc}") from None
    try:
        if connection.execute("pragma integrity_check").fetchone()[0] != "ok":
            raise RestoreError("Die Datenbank im Backup ist beschädigt (integrity_check).")
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type = 'table'")}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise RestoreError(f"Das ist keine Datenbank dieser App (es fehlen: {', '.join(sorted(missing))}).")
        row = connection.execute("select version_num from alembic_version").fetchone()
        revision = row[0] if row else ""

        def count(table: str) -> int:
            return connection.execute(f'select count(*) from "{table}"').fetchone()[0] if table in tables else 0

        counts = {
            "gruppen": count("group"),
            "kataloge": count("questionnaire"),
            "interviews": count("interview"),
            "aufnahmen": count("recording"),
        }
    except sqlite3.DatabaseError as exc:
        raise RestoreError(f"Datenbank lässt sich nicht lesen: {exc}") from None
    finally:
        connection.close()

    known = {script.revision for script in ScriptDirectory.from_config(_alembic_config()).walk_revisions()}
    if revision not in known:
        raise RestoreError(
            f"Das Backup hat den Datenbankstand „{revision or '?'}“, den diese App-Version nicht kennt "
            "(vermutlich aus einer neueren Version). Bitte erst die App aktualisieren."
        )
    return revision, counts


def _running_jobs(db: Session) -> int:
    return (
        db.query(Recording).filter(Recording.transkript_status == "laeuft").count()
        + db.query(Evaluation).filter(Evaluation.status == "laeuft").count()
        + db.query(ProjectAnalysis).filter(ProjectAnalysis.status == "laeuft").count()
    )


# ------------------------------------------------------------------ Wiederherstellen
def _sqlite_copy(source: Path, target: Path) -> None:
    """Kopiert per Backup-API: konsistent und auch in eine Datei, die gerade geöffnet ist."""
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(target, timeout=30)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _make_safety_copy(live: Path) -> str:
    folder = safety_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = f"{SAFETY_PREFIX}{datetime.now():%Y-%m-%d-%H%M%S}"
    name, n = f"{stamp}.db", 1
    while (folder / name).exists():  # zwei Wiederherstellungen in derselben Sekunde (z. B. sofort rückgängig)
        n += 1
        name = f"{stamp}-{n}.db"
    _sqlite_copy(live, folder / name)
    for old in safety_copies()[KEEP_SAFETY_COPIES:]:
        (folder / old["name"]).unlink(missing_ok=True)
    return name


def restore_database(backup_db: Path) -> RestoreResult:
    from app.services import evaluation, project_analysis, transcription  # spät: importieren Worker/DB-Zugriff

    live = live_database()
    revision, counts = inspect(backup_db)
    with Session(get_engine()) as db:
        if _running_jobs(db):
            raise RestoreError(
                "Gerade läuft eine Transkription oder KI-Bewertung. Bitte warten, bis sie fertig ist."
            )

    safety_name = _make_safety_copy(live)
    get_engine().dispose()  # keine offenen Verbindungen aus dem Pool während des Kopierens
    try:
        _sqlite_copy(backup_db, live)
    except sqlite3.Error as exc:
        raise RestoreError(f"Wiederherstellen fehlgeschlagen, der vorherige Stand ist unverändert: {exc}") from None
    finally:
        get_engine().dispose()
    command.upgrade(_alembic_config(), "head")  # ältere Backups auf den aktuellen Stand bringen

    # Aufträge, die beim Sichern liefen, neu einreihen und die Threads wecken.
    transcription.requeue_interrupted()
    evaluation.requeue_interrupted()
    project_analysis.requeue_interrupted()
    transcription.worker.notify()
    evaluation.worker.notify()

    with Session(get_engine()) as db:
        missing_audio = sum(not transcription.file_path(r).is_file() for r in db.query(Recording))
        audit.log(db, "backup", 0, "wiederhergestellt")
        db.commit()
    return RestoreResult(
        **counts,
        fehlende_audiodateien=missing_audio,
        stand_backup=revision,
        sicherungskopie=safety_name,
    )


def restore_file(source: Path) -> RestoreResult:
    """Backup-ZIP oder .db-Datei wiederherstellen."""
    with tempfile.TemporaryDirectory(prefix="restore_") as tmp:
        return restore_database(extract_database(source, Path(tmp)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python -m app.services.restore <backup.zip | backup.db | ->")
    try:
        if sys.argv[1] == "-":  # z. B. docker compose exec -T app python -m app.services.restore - < backup.zip
            with tempfile.TemporaryDirectory(prefix="restore_") as tmp_dir:
                upload = Path(tmp_dir) / "upload"
                with upload.open("wb") as out:
                    shutil.copyfileobj(sys.stdin.buffer, out, 1024 * 1024)
                result = restore_file(upload)
        else:
            result = restore_file(Path(sys.argv[1]))
    except RestoreError as exc:
        sys.exit(f"Fehler: {exc}")
    for key, value in asdict(result).items():
        print(f"{key}: {value}")
    print("Wiederhergestellt. Bei laufender App: Seite im Browser neu laden.")
