"""Vollsicherung als ZIP: konsistente Kopie der SQLite-DB plus CSVs, die ohne die App lesbar sind.

Aufruf von der Kommandozeile: python -m app.services.backup <ziel.zip | ->
"""
import csv
import io
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Group, Interview
from app.services import export


def _sqlite_copy(database_url: str) -> bytes | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "interviews.db"
        source = sqlite3.connect(f"file:{url.database}?mode=ro", uri=True)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)  # konsistent auch bei laufenden Schreibzugriffen
        finally:
            destination.close()
            source.close()
        return target.read_bytes()


def _catalog_csv(catalog) -> str:
    """Im Importformat, damit sich ein Katalog direkt wieder einlesen lässt."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(["abschnitt", "position", "frage", "hinweis", "pflicht", "typ"])
    for q in catalog.questions:
        writer.writerow([q.abschnitt, q.position, q.text, q.hinweis, "ja" if q.pflicht else "nein", q.typ])
    return "﻿" + buffer.getvalue()


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ ." else "_" for c in name).strip() or "unbenannt"


def build_backup(db: Session) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        db_copy = _sqlite_copy(get_settings().database_url)
        if db_copy is not None:
            archive.writestr("interviews.db", db_copy)

        interviews = db.query(Interview).order_by(Interview.id).all()
        all_rows: list[list[str]] = []
        for interview in interviews:
            rows = export.csv_rows(interview)
            all_rows += rows
            archive.writestr(f"interviews/{export.filename(interview, 'csv')}", export.write_csv(rows))
        archive.writestr("alle-interviews.csv", export.write_csv(all_rows))

        for group in db.query(Group).order_by(Group.id).all():
            for catalog in group.questionnaires:
                name = f"kataloge/{_safe(group.name)}/{_safe(catalog.name)}-v{catalog.version}.csv"
                archive.writestr(name, _catalog_csv(catalog))
    return buffer.getvalue()


def backup_filename() -> str:
    return f"interview-backup-{datetime.now():%Y-%m-%d-%H%M}.zip"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python -m app.services.backup <ziel.zip | ->")
    with Session(get_engine()) as session:
        data = build_backup(session)
    if sys.argv[1] == "-":
        sys.stdout.buffer.write(data)
    else:
        Path(sys.argv[1]).write_bytes(data)
