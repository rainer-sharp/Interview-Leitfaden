import io
import sqlite3
import zipfile


def test_backup_zip_contains_db_and_csvs(client, testdata, tmp_path):
    group_id = client.post("/api/groups", json={"name": "Lager/Team"}).json()["id"]
    files = {"file": ("f.csv", (testdata / "fragen_utf8.csv").read_bytes())}
    catalog = client.post("/api/import", files=files, data={"modus": "neu", "group_id": group_id, "name": "Leitfaden"}).json()
    interview = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": "Anna", "datum": "2026-11-09"}
    ).json()
    client.put(f"/api/interviews/{interview['id']}/answers/{interview['answers'][0]['id']}", json={"notiz": "Früh"})

    response = client.get("/api/backup")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert {
        "interviews.db",
        "alle-interviews.csv",
        "interviews/interview-1-2026-11-09-anna.csv",
        "kataloge/Lager_Team/Leitfaden-v1.csv",
    } <= names

    db_file = tmp_path / "restore.db"
    db_file.write_bytes(archive.read("interviews.db"))
    with sqlite3.connect(db_file) as connection:
        assert connection.execute("select notiz from answer where position = 1").fetchone() == ("Früh",)

    assert "Früh" in archive.read("alle-interviews.csv").decode("utf-8-sig")
    # Der gesicherte Katalog lässt sich direkt wieder importieren.
    restored = client.post("/api/import/vorschau", files={"file": ("k.csv", archive.read("kataloge/Lager_Team/Leitfaden-v1.csv"))})
    assert restored.json()["ok"] and len(restored.json()["rows"]) == 3


def test_backup_cli(database, tmp_path, monkeypatch):
    import runpy
    import sys

    target = tmp_path / "out.zip"
    monkeypatch.setattr(sys, "argv", ["backup", str(target)])
    runpy.run_module("app.services.backup", run_name="__main__")
    assert "alle-interviews.csv" in zipfile.ZipFile(target).namelist()
