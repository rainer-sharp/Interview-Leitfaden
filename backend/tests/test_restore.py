"""Wiederherstellung aus Backup-ZIP oder .db, Sicherungskopie des vorherigen Stands, Rückgängig, CLI."""
import io
import sqlite3
import zipfile

import pytest

from app.services import restore


def make_interview(client, person="Anna", note="Früh"):
    group_id = client.post("/api/groups", json={"name": f"Gruppe {person}"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "Leitfaden"}).json()
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Erste"})
    interview = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": person, "datum": "2026-11-09"}
    ).json()
    client.put(f"/api/interviews/{interview['id']}/answers/{interview['answers'][0]['id']}", json={"notiz": note})
    return interview


def people(client):
    return sorted(i["person"] for i in client.get("/api/interviews").json())


def upload(client, content, name="backup.zip"):
    return client.post("/api/restore", files={"datei": (name, content)})


def test_restore_zip_replaces_all_data(client, database):
    make_interview(client, "Anna")
    backup = client.get("/api/backup").content
    make_interview(client, "Bernd")
    assert people(client) == ["Anna", "Bernd"]

    response = upload(client, backup)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interviews"] == 1 and body["gruppen"] == 1 and body["stand_backup"] == "0004"
    assert body["sicherungskopie"].startswith("vor-wiederherstellung-")
    assert people(client) == ["Anna"]
    interview = client.get("/api/interviews").json()[0]
    assert client.get(f"/api/interviews/{interview['id']}").json()["answers"][0]["notiz"] == "Früh"
    # Die Sitzung bleibt gültig (Cookie hängt nicht an der Datenbank)
    assert client.get("/api/auth/status").status_code in (200, 404)

    # Rückgängig: der Stand mit Bernd liegt als Sicherungskopie bereit
    copies = client.get("/api/restore/sicherungskopien").json()
    assert [c["name"] for c in copies] == [body["sicherungskopie"]]
    undo = client.post(f"/api/restore/sicherungskopien/{body['sicherungskopie']}")
    assert undo.status_code == 200 and people(client) == ["Anna", "Bernd"]
    assert len(client.get("/api/restore/sicherungskopien").json()) == 2


def test_restore_plain_db_file(client, database, tmp_path):
    make_interview(client, "Anna")
    daily = tmp_path / "interviews-2026-11-14.db"
    with sqlite3.connect(database) as src, sqlite3.connect(daily) as dst:
        src.backup(dst)
    make_interview(client, "Bernd")
    assert upload(client, daily.read_bytes(), "interviews-2026-11-14.db").status_code == 200
    assert people(client) == ["Anna"]


def old_database(path, revision: str):
    """Echte Datenbank auf einem älteren Migrationsstand, mit einer Gruppe, einem Katalog und einem Interview."""
    from alembic import command
    from alembic.config import Config

    from tests.conftest import BACKEND

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.attributes["database_url"] = f"sqlite:///{path}"
    command.upgrade(config, revision)
    with sqlite3.connect(path) as connection:
        connection.execute("insert into \"group\" (id, name, beschreibung) values (1, 'Lager', '')")
        connection.execute(
            "insert into questionnaire (id, group_id, name, version, importiert_am) "
            "values (1, 1, 'Leitfaden', 1, '2026-11-01 10:00:00')"
        )
        connection.execute(
            "insert into interview (id, questionnaire_id, person, organisation, datum, status, gesamtnotiz) "
            "values (1, 1, 'Alt', '', '2026-11-02', 'laufend', 'Notiz von früher')"
        )


def test_older_backup_is_migrated(client, database, tmp_path):
    """Ein Backup vom Stand 0002 (vor KI-Bewertung und Projekten) wird nach dem Einspielen auf head migriert."""
    old = tmp_path / "alt.db"
    old_database(old, "0002")
    make_interview(client, "Neu")
    assert upload(client, old.read_bytes(), "alt.db").json()["stand_backup"] == "0002"
    with sqlite3.connect(database) as connection:
        assert connection.execute("select version_num from alembic_version").fetchone() == ("0004",)
        assert connection.execute("select count(*) from evaluation").fetchone() == (0,)
    interviews = client.get("/api/interviews").json()
    assert [(i["person"], i["projekt_name"], i["group_name"]) for i in interviews] == [
        ("Alt", "Standardprojekt", "Lager")
    ]


@pytest.mark.parametrize(
    "content, message",
    [
        (b"kein backup", "weder ein Backup-ZIP"),
        (b"SQLite format 3\x00" + b"\x00" * 200, "Datenbank"),
    ],
)
def test_invalid_files_are_rejected(client, content, message):
    make_interview(client, "Anna")
    response = upload(client, content)
    assert response.status_code == 422 and message in response.json()["detail"]
    assert people(client) == ["Anna"]
    assert client.get("/api/restore/sicherungskopien").json() == []


def test_zip_without_database(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("alle-interviews.csv", "x")
    response = upload(client, buffer.getvalue())
    assert response.status_code == 422 and "interviews.db" in response.json()["detail"]


def test_foreign_database_and_newer_version(client, database, tmp_path):
    other = tmp_path / "fremd.db"
    with sqlite3.connect(other) as connection:
        connection.execute("create table x (id integer)")
    response = upload(client, other.read_bytes(), "fremd.db")
    assert response.status_code == 422 and "keine Datenbank dieser App" in response.json()["detail"]

    newer = tmp_path / "neu.db"
    with sqlite3.connect(database) as src, sqlite3.connect(newer) as dst:
        src.backup(dst)
    with sqlite3.connect(newer) as connection:
        connection.execute("update alembic_version set version_num = '0099'")
    response = upload(client, newer.read_bytes(), "neu.db")
    assert response.status_code == 422 and "neueren Version" in response.json()["detail"]


def test_refused_while_job_runs(client, database):
    interview = make_interview(client, "Anna")
    backup = client.get("/api/backup").content
    client.post(f"/api/interviews/{interview['id']}/bewertung")
    with sqlite3.connect(database) as connection:
        connection.execute("update evaluation set status = 'laeuft'")
    response = upload(client, backup)
    assert response.status_code == 422 and "läuft" in response.json()["detail"]


def test_running_jobs_from_backup_are_requeued(client, database):
    interview = make_interview(client, "Anna")
    client.post(f"/api/interviews/{interview['id']}/bewertung")
    with sqlite3.connect(database) as connection:
        connection.execute("update evaluation set status = 'laeuft'")
    backup = client.get("/api/backup").content
    with sqlite3.connect(database) as connection:
        connection.execute("delete from evaluation")
    assert upload(client, backup).status_code == 200
    assert client.get(f"/api/interviews/{interview['id']}/bewertung").json()["status"] == "wartend"


def test_missing_audio_is_reported(client):
    interview = make_interview(client, "Anna")
    client.post(f"/api/interviews/{interview['id']}/aufnahmen", files={"datei": ("g.mkv", b"audio")})
    backup = client.get("/api/backup").content
    client.delete(f"/api/interviews/{interview['id']}")  # löscht auch die Audiodatei
    body = upload(client, backup).json()
    assert body["aufnahmen"] == 1 and body["fehlende_audiodateien"] == 1


def test_safety_copies_are_limited_and_names_checked(client, monkeypatch):
    monkeypatch.setattr(restore, "KEEP_SAFETY_COPIES", 2)
    make_interview(client, "Anna")
    backup = client.get("/api/backup").content
    names = iter(f"{restore.SAFETY_PREFIX}2026-11-15-10000{i}.db" for i in range(3))
    real = restore.datetime

    class FakeNow:
        @staticmethod
        def now():
            class Stamp:
                def __format__(self, _spec):
                    return next(names).removeprefix(restore.SAFETY_PREFIX).removesuffix(".db")

            return Stamp()

        fromtimestamp = real.fromtimestamp

    monkeypatch.setattr(restore, "datetime", FakeNow)
    for _ in range(3):
        assert upload(client, backup).status_code == 200
    assert [c["name"] for c in client.get("/api/restore/sicherungskopien").json()] == [
        "vor-wiederherstellung-2026-11-15-100002.db",
        "vor-wiederherstellung-2026-11-15-100001.db",
    ]
    assert client.post("/api/restore/sicherungskopien/..%2Finterviews.db").status_code in (404, 405, 422)
    assert client.post("/api/restore/sicherungskopien/unbekannt.db").status_code == 422


def test_requires_login(anon):
    assert anon.post("/api/restore", files={"datei": ("b.zip", b"x")}).status_code == 401
    assert anon.get("/api/restore/sicherungskopien").status_code == 401


def test_restore_cli(client, database, tmp_path, monkeypatch, capsys):
    import runpy
    import sys

    make_interview(client, "Anna")
    backup = tmp_path / "b.zip"
    backup.write_bytes(client.get("/api/backup").content)
    make_interview(client, "Bernd")
    monkeypatch.setattr(sys, "argv", ["restore", str(backup)])
    runpy.run_module("app.services.restore", run_name="__main__")
    assert "interviews: 1" in capsys.readouterr().out
    assert people(client) == ["Anna"]

    monkeypatch.setattr(sys, "argv", ["restore", str(tmp_path / "fehlt.txt")])
    (tmp_path / "fehlt.txt").write_text("x")
    with pytest.raises(SystemExit, match="weder ein Backup-ZIP"):
        runpy.run_module("app.services.restore", run_name="__main__")
