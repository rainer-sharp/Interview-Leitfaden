"""Projekte: Standardprojekt, Gruppen und Interviews je Projekt, Kopieren, Löschen, Anweisung für die KI-Bewertung."""
import pytest

from app.services import evaluation
from app.services import settings as settings_service


def new_project(client, name, **fields):
    response = client.post("/api/projekte", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def new_group(client, project, name="Lager"):
    response = client.post("/api/groups", json={"name": name, "projekt_id": project["id"]})
    assert response.status_code == 201, response.text
    return response.json()


def new_catalog(client, group, name="Leitfaden", questions=("Erste", "Zweite")):
    catalog = client.post(f"/api/groups/{group['id']}/questionnaires", json={"name": name}).json()
    for text in questions:
        client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": text, "hinweis": f"zu {text}"})
    return catalog


def new_interview(client, catalog, person="Anna"):
    return client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": person, "datum": "2026-11-15"}
    ).json()


@pytest.fixture
def project(client):
    return new_project(client, "Lieferanten 2026", beschreibung="Befragung der Lieferanten")


# ------------------------------------------------------------------ Grundlagen
def test_default_project_exists(client):
    projects = client.get("/api/projekte").json()
    assert [p["name"] for p in projects] == ["Standardprojekt"]
    # Gruppen ohne Projektangabe landen dort (wie vor den Projekten)
    group = client.post("/api/groups", json={"name": "Lager"}).json()
    assert group["projekt_id"] == projects[0]["id"] and group["projekt_name"] == "Standardprojekt"


def test_create_update_and_duplicate_names(client, project):
    assert project["gruppen"] == 0 and project["interviews"] == 0 and project["ki_anweisung"] == ""
    assert client.post("/api/projekte", json={"name": "Lieferanten 2026"}).status_code == 409
    assert client.post("/api/projekte", json={"name": "  "}).status_code == 422
    updated = client.put(
        f"/api/projekte/{project['id']}", json={"name": "Lieferanten", "beschreibung": "", "ki_anweisung": " Kurz. "}
    ).json()
    assert updated["name"] == "Lieferanten" and updated["ki_anweisung"] == "Kurz."
    assert client.put("/api/projekte/999", json={"name": "x"}).status_code == 404


def test_groups_and_interviews_per_project(client, project):
    other = new_project(client, "Kunden")
    catalog = new_catalog(client, new_group(client, project))
    new_interview(client, catalog, "Anna")
    new_interview(client, new_catalog(client, new_group(client, other)), "Bernd")

    # Gleicher Gruppenname in einem anderen Projekt ist erlaubt, im selben nicht
    assert client.post("/api/groups", json={"name": "Lager", "projekt_id": project["id"]}).status_code == 409
    assert client.post("/api/groups", json={"name": "x", "projekt_id": 999}).status_code == 404

    groups = client.get(f"/api/groups?projekt_id={project['id']}").json()
    assert [(g["name"], g["projekt_name"]) for g in groups] == [("Lager", "Lieferanten 2026")]
    assert len(client.get("/api/groups").json()) == 2

    interviews = client.get(f"/api/interviews?projekt_id={project['id']}").json()
    assert [(i["person"], i["projekt_name"]) for i in interviews] == [("Anna", "Lieferanten 2026")]
    assert len(client.get("/api/interviews").json()) == 2
    assert client.get(f"/api/projekte/{project['id']}").json()["interviews"] == 1


def test_move_group_to_other_project(client, project):
    other = new_project(client, "Kunden")
    group = new_group(client, project)
    interview = new_interview(client, new_catalog(client, group))
    moved = client.put(f"/api/groups/{group['id']}", json={"name": "Lager", "projekt_id": other["id"]}).json()
    assert moved["projekt_id"] == other["id"]
    assert client.get(f"/api/interviews/{interview['id']}").json()["projekt_name"] == "Kunden"
    # Name kollidiert im Zielprojekt
    new_group(client, project, "Lager")
    clash = client.put(f"/api/groups/{group['id']}", json={"name": "Lager", "projekt_id": project["id"]})
    assert clash.status_code == 409


# ------------------------------------------------------------------ Kopieren
def test_copy_project_copies_groups_and_catalogs(client, project):
    client.put(f"/api/projekte/{project['id']}", json={**project, "ki_anweisung": "Eigene Anweisung"})
    group = new_group(client, project)
    catalog = new_catalog(client, group)
    client.post(f"/api/groups/{group['id']}/questionnaires", json={"name": "Leitfaden"})  # Version 2
    new_group(client, project, "Einkauf")
    new_interview(client, catalog)

    copy = client.post(f"/api/projekte/{project['id']}/kopie", json={}).json()
    assert copy["name"] == "Lieferanten 2026 (Kopie)"
    assert copy["beschreibung"] == "Befragung der Lieferanten" and copy["ki_anweisung"] == "Eigene Anweisung"
    assert copy["gruppen"] == 2 and copy["kataloge"] == 2 and copy["interviews"] == 0

    copied = client.get(f"/api/groups?projekt_id={copy['id']}").json()
    assert [g["name"] for g in copied] == ["Einkauf", "Lager"]
    lager = copied[1]
    assert lager["id"] != group["id"]
    assert [(c["name"], c["version"]) for c in lager["questionnaires"]] == [("Leitfaden", 1), ("Leitfaden", 2)]
    questions = client.get(f"/api/questionnaires/{lager['questionnaires'][0]['id']}").json()["questions"]
    assert [(q["position"], q["text"], q["hinweis"]) for q in questions] == [(1, "Erste", "zu Erste"), (2, "Zweite", "zu Zweite")]

    # Kopie ist unabhängig: Änderungen wirken nicht aufs Original
    client.put(f"/api/questions/{questions[0]['id']}", json={"text": "Geändert"})
    original = client.get(f"/api/questionnaires/{catalog['id']}").json()["questions"]
    assert original[0]["text"] == "Erste"

    # Zweite Kopie bekommt einen freien Namen, eigener Name geht auch
    assert client.post(f"/api/projekte/{project['id']}/kopie", json={}).json()["name"] == "Lieferanten 2026 (Kopie 2)"
    named = client.post(f"/api/projekte/{project['id']}/kopie", json={"name": "Lieferanten 2027", "beschreibung": ""})
    assert named.json()["name"] == "Lieferanten 2027" and named.json()["beschreibung"] == ""
    assert client.post(f"/api/projekte/{project['id']}/kopie", json={"name": "Lieferanten 2027"}).status_code == 409


# ------------------------------------------------------------------ Löschen
def test_delete_project(client, project):
    group = new_group(client, project)
    interview = new_interview(client, new_catalog(client, group))
    assert client.delete(f"/api/projekte/{project['id']}").status_code == 409
    client.delete(f"/api/interviews/{interview['id']}")
    assert client.delete(f"/api/projekte/{project['id']}").status_code == 204
    assert client.get(f"/api/groups/{group['id']}").status_code == 404  # Gruppen und Kataloge mit gelöscht
    assert client.get(f"/api/projekte/{project['id']}").status_code == 404


def test_last_project_cannot_be_deleted(client):
    only = client.get("/api/projekte").json()[0]
    assert client.delete(f"/api/projekte/{only['id']}").status_code == 409


def test_requires_login(anon):
    assert anon.get("/api/projekte").status_code == 401


# ------------------------------------------------------------------ KI-Anweisung je Projekt
def test_evaluation_uses_project_instructions(client, project, monkeypatch):
    monkeypatch.setattr(evaluation, "list_models", lambda server, timeout=10: ["m"])
    catalog = new_catalog(client, new_group(client, project))
    interview = new_interview(client, catalog)
    client.put(f"/api/interviews/{interview['id']}", json={"gesamtnotiz": "Gut"})
    url = f"/api/interviews/{interview['id']}/bewertung"

    def run():
        seen = {}
        client.post(url)
        evaluation.process_next(lambda server, model, prompt: seen.update(server=server, prompt=prompt) or "## OK")
        return seen

    body = client.get(url).json()
    assert body["anweisung_quelle"] == "allgemein" and body["projekt_name"] == "Lieferanten 2026"
    seen = run()
    assert seen["server"].anweisung == settings_service.LLM_INSTRUCTIONS
    assert "- Projekt: Lieferanten 2026" in seen["prompt"]

    client.put(
        f"/api/projekte/{project['id']}", json={"name": project["name"], "ki_anweisung": "Bewerte als Einkäufer."}
    )
    assert client.get(url).json()["anweisung_quelle"] == "projekt"
    assert run()["server"].anweisung == "Bewerte als Einkäufer."

    # Leere Anweisung im Projekt = wieder die allgemeine (auch eine geänderte aus den Einstellungen)
    client.put(f"/api/projekte/{project['id']}", json={"name": project["name"], "ki_anweisung": "  "})
    client.put("/api/einstellungen/llm", json={"anweisung": "Allgemein neu."})
    assert run()["server"].anweisung == "Allgemein neu."


def test_exports_contain_project(client, project):
    interview = new_interview(client, new_catalog(client, new_group(client, project)))
    md = client.get(f"/api/interviews/{interview['id']}/export.md").text
    assert "- **Projekt:** Lieferanten 2026" in md
    csv = client.get(f"/api/interviews/{interview['id']}/export.csv").text
    assert ";Lieferanten 2026;Lager;Leitfaden;" in csv
