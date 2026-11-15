"""Mehrbenutzer: Konten, Rollen, Projektzuordnung, wer was sehen und ändern darf."""
import pytest
from fastapi.testclient import TestClient

from app.services import users


def login(app_client: TestClient, username: str, password: str):
    return app_client.post("/api/auth/login", json={"benutzername": username, "passwort": password})


@pytest.fixture
def setup(client):
    """Admin (client) legt zwei Projekte an, mit Gruppe, Katalog und je einem Interview des Admins."""
    ids = {}
    for name in ("Alpha", "Beta"):
        project = client.post("/api/projekte", json={"name": name}).json()
        group = client.post("/api/groups", json={"name": "Einkauf", "projekt_id": project["id"]}).json()
        catalog = client.post(f"/api/groups/{group['id']}/questionnaires", json={"name": "Leitfaden"}).json()
        client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Frage"})
        interview = client.post(
            "/api/interviews", json={"questionnaire_id": catalog["id"], "person": f"Admin-{name}", "datum": "2026-11-15"}
        ).json()
        ids[name] = {"project": project["id"], "group": group["id"], "catalog": catalog["id"], "interview": interview}
    anna = client.post(
        "/api/benutzer",
        json={"benutzername": "Anna", "name": "Anna Berg", "passwort": "anna-passwort", "projekte": [ids["Alpha"]["project"]]},
    )
    assert anna.status_code == 201, anna.text
    ids["anna"] = anna.json()
    return ids


@pytest.fixture
def anna(client, setup):
    """Zweiter Browser: als Interviewerin Anna angemeldet."""
    from app.main import app

    with TestClient(app) as other:
        assert login(other, "anna", "anna-passwort").status_code == 200  # Benutzername ohne Groß/Klein
        yield other


# ------------------------------------------------------------------ Konten
def test_first_admin_and_login(client):
    me = client.get("/api/auth/status").json()["benutzer"]
    assert me["benutzername"] == "admin" and me["rolle"] == "admin"
    accounts = client.get("/api/benutzer").json()
    assert [a["benutzername"] for a in accounts] == ["admin"]


def test_wrong_credentials_same_message(anon, setup):
    unknown = login(anon, "niemand", "egal-egal")
    wrong = login(anon, "anna", "falsches-passwort")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_password_hashing():
    stored = users.hash_password("geheim-123")
    assert stored.startswith("scrypt$") and "geheim" not in stored
    assert users.verify_password("geheim-123", stored)
    assert not users.verify_password("geheim-124", stored)
    assert not users.verify_password("x", "kaputt")


def test_create_user_validation(client, setup):
    assert client.post("/api/benutzer", json={"benutzername": "anna", "passwort": "lang-genug"}).status_code == 422
    assert client.post("/api/benutzer", json={"benutzername": "bob", "passwort": "kurz"}).status_code == 422
    assert client.post("/api/benutzer", json={"benutzername": "bob mit leer", "passwort": "lang-genug"}).status_code == 422
    assert client.post("/api/benutzer", json={"benutzername": "bob", "passwort": "lang-genug", "projekte": [999]}).status_code == 422


def test_lock_and_password_reset_end_sessions(client, setup, anna):
    anna_id = setup["anna"]["id"]
    assert anna.get("/api/groups").status_code == 200
    client.put(f"/api/benutzer/{anna_id}", json={"aktiv": False})
    assert anna.get("/api/groups").status_code == 401
    assert login(anna, "anna", "anna-passwort").status_code == 403

    client.put(f"/api/benutzer/{anna_id}", json={"aktiv": True, "passwort": "neues-passwort"})
    assert login(anna, "anna", "anna-passwort").status_code == 401
    assert login(anna, "anna", "neues-passwort").status_code == 200


def test_own_password_change(client, setup, anna):
    bad = anna.put("/api/auth/passwort", json={"altes_passwort": "falsch", "neues_passwort": "noch-neuer"})
    assert bad.status_code == 422
    ok = anna.put("/api/auth/passwort", json={"altes_passwort": "anna-passwort", "neues_passwort": "noch-neuer"})
    assert ok.status_code == 200
    assert anna.get("/api/groups").status_code == 200  # aktuelle Sitzung bleibt
    assert login(client, "anna", "noch-neuer").status_code == 200


def test_last_admin_is_protected(client, setup):
    admin_id = client.get("/api/auth/status").json()["benutzer"]["id"]
    assert client.put(f"/api/benutzer/{admin_id}", json={"rolle": "interviewer"}).status_code == 409
    assert client.put(f"/api/benutzer/{admin_id}", json={"aktiv": False}).status_code == 409
    assert client.delete(f"/api/benutzer/{admin_id}").status_code == 409


def test_delete_user_only_without_interviews(client, setup, anna):
    anna_id = setup["anna"]["id"]
    alpha = setup["Alpha"]
    anna.post("/api/interviews", json={"questionnaire_id": alpha["catalog"], "person": "X", "datum": "2026-11-15"})
    assert client.delete(f"/api/benutzer/{anna_id}").status_code == 409
    bob = client.post("/api/benutzer", json={"benutzername": "bob", "passwort": "lang-genug"}).json()
    assert client.delete(f"/api/benutzer/{bob['id']}").status_code == 204


def test_audit_log_records_user(client, setup, database):
    import sqlite3

    with sqlite3.connect(database) as connection:
        rows = connection.execute("select benutzer_id, aktion from audit_log where aktion = 'angelegt'").fetchall()
    assert rows and all(user_id is not None for user_id, _ in rows)


# ------------------------------------------------------------------ Sichtbarkeit
def test_interviewer_sees_only_assigned_projects(client, setup, anna):
    alpha, beta = setup["Alpha"], setup["Beta"]
    assert [p["name"] for p in anna.get("/api/projekte").json()] == ["Alpha"]
    assert {g["projekt_id"] for g in anna.get("/api/groups").json()} == {alpha["project"]}
    assert [i["person"] for i in anna.get("/api/interviews").json()] == ["Admin-Alpha"]
    # Fremdes Projekt: nicht vorhanden (404), auch über alle Umwege
    for path in (
        f"/api/projekte/{beta['project']}",
        f"/api/projekte/{beta['project']}/export.md",
        f"/api/projekte/{beta['project']}/analyse",
        f"/api/groups/{beta['group']}",
        f"/api/questionnaires/{beta['catalog']}",
        f"/api/interviews/{beta['interview']['id']}",
        f"/api/interviews/{beta['interview']['id']}/export.md",
        f"/api/interviews/{beta['interview']['id']}/aufnahmen",
        f"/api/interviews/{beta['interview']['id']}/bewertung",
    ):
        assert anna.get(path).status_code == 404, path
    assert anna.get(f"/api/interviews?projekt_id={beta['project']}").json() == []
    assert anna.post("/api/interviews", json={"questionnaire_id": beta["catalog"], "person": "X", "datum": "2026-11-15"}).status_code == 404


def test_interviewer_reads_but_cannot_change_others_interviews(client, setup, anna):
    other = setup["Alpha"]["interview"]
    url = f"/api/interviews/{other['id']}"
    data = anna.get(url).json()
    assert data["darf_bearbeiten"] is False and data["interviewer_name"] == "Administrator"
    assert anna.get(f"{url}/export.md").status_code == 200
    answer = other["answers"][0]["id"]
    for method, path, body in (
        ("put", url, {"gesamtnotiz": "x"}),
        ("put", f"{url}/answers/{answer}", {"notiz": "x"}),
        ("post", f"{url}/abschliessen", None),
        ("delete", url, None),
        ("post", f"{url}/bewertung", None),
    ):
        response = getattr(anna, method)(path, **({"json": body} if body is not None else {}))
        assert response.status_code == 403, (method, path)
    upload = anna.post(f"{url}/aufnahmen", files={"datei": ("a.mkv", b"x")})
    assert upload.status_code == 403


def test_interviewer_runs_own_interview(client, setup, anna):
    alpha = setup["Alpha"]
    mine = anna.post("/api/interviews", json={"questionnaire_id": alpha["catalog"], "person": "Kunde", "datum": "2026-11-15"}).json()
    assert mine["darf_bearbeiten"] is True and mine["interviewer_name"] == "Anna Berg"
    url = f"/api/interviews/{mine['id']}"
    assert anna.put(f"{url}/answers/{mine['answers'][0]['id']}", json={"notiz": "Fax"}).status_code == 200
    assert anna.post(f"{url}/aufnahmen", files={"datei": ("a.mkv", b"x")}).status_code == 201
    assert anna.post(f"{url}/bewertung").status_code == 202
    assert anna.post(f"{url}/abschliessen").status_code == 200
    # Admin darf auch fremde Interviews ändern
    assert client.post(f"{url}/wiederoeffnen").status_code == 200
    assert client.get(url).json()["darf_bearbeiten"] is True


def test_interviewer_creates_project_and_maintains_catalogs(client, setup, anna):
    created = anna.post("/api/projekte", json={"name": "Annas Projekt"})
    assert created.status_code == 201 and [m["benutzername"] for m in created.json()["mitglieder"]] == ["anna"]
    project_id = created.json()["id"]
    group = anna.post("/api/groups", json={"name": "Lager", "projekt_id": project_id}).json()
    catalog = anna.post(f"/api/groups/{group['id']}/questionnaires", json={"name": "K"}).json()
    assert anna.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "F"}).status_code == 201
    copy = anna.post(f"/api/projekte/{project_id}/kopie", json={}).json()
    assert {p["name"] for p in anna.get("/api/projekte").json()} == {"Alpha", "Annas Projekt", "Annas Projekt (Kopie)"}
    # Gruppe in ein nicht zugewiesenes Projekt verschieben: geht nicht
    beta = setup["Beta"]["project"]
    assert anna.put(f"/api/groups/{group['id']}", json={"name": "Lager", "projekt_id": beta}).status_code == 404
    # Ohne Projektangabe landet eine Gruppe im Standardprojekt – das sieht Anna nicht
    assert anna.post("/api/groups", json={"name": "Ohne"}).status_code == 422
    assert anna.put(f"/api/projekte/{copy['id']}", json={"name": "Umbenannt"}).status_code == 200


def test_admin_only_endpoints(client, setup, anna):
    alpha = setup["Alpha"]["project"]
    for method, path in (
        ("get", "/api/benutzer"),
        ("post", "/api/benutzer"),
        ("get", "/api/backup"),
        ("get", "/api/restore/sicherungskopien"),
        ("post", "/api/restore"),
        ("put", "/api/einstellungen/transkription"),
        ("post", "/api/einstellungen/transkription/test"),
        ("put", "/api/einstellungen/llm"),
        ("post", "/api/einstellungen/llm/test"),
        ("delete", f"/api/projekte/{alpha}"),
        ("put", f"/api/projekte/{alpha}/mitglieder"),
    ):
        assert getattr(anna, method)(path).status_code in (403, 422), (method, path)
        if method == "get":
            assert getattr(anna, method)(path).status_code == 403, path
    # Lesen der Einstellungen (Vorgaben für Transkription, allgemeine Anweisungen) ist erlaubt
    assert anna.get("/api/einstellungen/transkription").status_code == 200
    assert "api_key" not in anna.get("/api/einstellungen/llm").json()


def test_admin_assigns_projects(client, setup, anna):
    beta = setup["Beta"]["project"]
    anna_id = setup["anna"]["id"]
    project = client.put(f"/api/projekte/{beta}/mitglieder", json=[anna_id]).json()
    assert [m["benutzername"] for m in project["mitglieder"]] == ["anna"]
    assert {p["name"] for p in anna.get("/api/projekte").json()} == {"Alpha", "Beta"}
    client.put(f"/api/benutzer/{anna_id}", json={"projekte": []})
    assert anna.get("/api/projekte").json() == []
    assert client.put(f"/api/projekte/{beta}/mitglieder", json=[999]).status_code == 422


def test_users_cli(client, setup, monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("cli-passwort\n"))
    assert users._main(["passwort", "anna"]) == 0
    assert login(client, "anna", "cli-passwort").status_code == 200
    assert users._main(["liste"]) == 0
    assert "anna" in capsys.readouterr().out
    assert users._main(["passwort", "niemand"]) == 1
    assert users._main([]) == 2
