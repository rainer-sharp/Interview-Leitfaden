import pytest

from app.db import get_engine
from sqlalchemy.orm import Session

from app.models import AuditLog


@pytest.fixture
def catalog_id(client):
    group_id = client.post("/api/groups", json={"name": "Lager"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "Leitfaden"}).json()
    url = f"/api/questionnaires/{catalog['id']}/questions"
    client.post(url, json={"text": "Erste", "abschnitt": "A", "pflicht": True, "hinweis": "h"})
    client.post(url, json={"text": "Zweite", "abschnitt": "B"})
    return catalog["id"]


@pytest.fixture
def interview(client, catalog_id):
    response = client.post(
        "/api/interviews",
        json={"questionnaire_id": catalog_id, "person": "A. B.", "organisation": "Firma", "datum": "2026-11-09"},
    )
    assert response.status_code == 201
    return response.json()


def answer_url(interview, index=0):
    return f"/api/interviews/{interview['id']}/answers/{interview['answers'][index]['id']}"


def test_start_copies_questions_as_snapshot(interview):
    assert interview["status"] == "laufend" and interview["fragen"] == 2 and interview["bearbeitet"] == 0
    first = interview["answers"][0]
    assert first["status"] == "offen" and first["notiz"] == ""
    assert first["question_snapshot"]["text"] == "Erste"
    assert first["question_snapshot"]["pflicht"] is True
    assert first["question_snapshot"]["position"] == 1


def test_snapshot_unchanged_after_catalog_changes(client, catalog_id, interview):
    questions = client.get(f"/api/questionnaires/{catalog_id}").json()["questions"]
    client.put(f"/api/questions/{questions[0]['id']}", json={"text": "Geändert", "abschnitt": "Neu"})
    client.delete(f"/api/questions/{questions[1]['id']}")
    client.post(f"/api/questionnaires/{catalog_id}/questions", json={"text": "Dazu"})

    reloaded = client.get(f"/api/interviews/{interview['id']}").json()
    assert reloaded["answers"] == interview["answers"]
    assert [a["question_snapshot"]["text"] for a in reloaded["answers"]] == ["Erste", "Zweite"]


def test_note_update_is_idempotent(client, interview):
    url = answer_url(interview)
    first = client.put(url, json={"notiz": "Text"}).json()
    second = client.put(url, json={"notiz": "Text"}).json()
    assert first == second
    assert first["status"] == "beantwortet"
    assert client.get(f"/api/interviews/{interview['id']}").json()["answers"][0]["notiz"] == "Text"


def test_status_follows_note_only_without_explicit_choice(client, interview):
    url = answer_url(interview)
    assert client.put(url, json={"notiz": "   "}).json()["status"] == "offen"
    assert client.put(url, json={"notiz": "Text"}).json()["status"] == "beantwortet"
    assert client.put(url, json={"notiz": ""}).json()["status"] == "offen"

    assert client.put(url, json={"status": "spaeter"}).json()["status"] == "spaeter"
    assert client.put(url, json={"notiz": "Merker"}).json()["status"] == "spaeter"
    assert client.put(url, json={"status": "uebersprungen"}).json()["notiz"] == "Merker"
    assert client.put(url, json={"notiz": "x", "status": "beantwortet"}).json()["status"] == "beantwortet"
    assert client.put(url, json={"status": "falsch"}).status_code == 422


def test_answer_must_belong_to_interview(client, catalog_id, interview):
    other = client.post(
        "/api/interviews", json={"questionnaire_id": catalog_id, "person": "C", "datum": "2026-11-09"}
    ).json()
    url = f"/api/interviews/{other['id']}/answers/{interview['answers'][0]['id']}"
    assert client.put(url, json={"notiz": "x"}).status_code == 404


def test_resume_returns_saved_state(client, interview):
    client.put(answer_url(interview, 1), json={"notiz": "Stand"})
    reloaded = client.get(f"/api/interviews/{interview['id']}").json()
    assert reloaded["bearbeitet"] == 1 and reloaded["answers"][1]["notiz"] == "Stand"


def test_finish_locks_until_reopened(client, interview):
    base = f"/api/interviews/{interview['id']}"
    assert client.put(base, json={"gesamtnotiz": "Fazit"}).json()["gesamtnotiz"] == "Fazit"
    assert client.post(f"{base}/abschliessen").json()["status"] == "abgeschlossen"
    assert client.post(f"{base}/abschliessen").status_code == 200

    assert client.put(answer_url(interview), json={"notiz": "x"}).status_code == 409
    assert client.put(base, json={"gesamtnotiz": "y"}).status_code == 409

    assert client.post(f"{base}/wiederoeffnen").json()["status"] == "laufend"
    assert client.put(answer_url(interview), json={"notiz": "x"}).status_code == 200


def test_update_interview_metadata_keeps_rest(client, interview):
    base = f"/api/interviews/{interview['id']}"
    body = client.put(base, json={"person": "Neu"}).json()
    assert (body["person"], body["organisation"], body["datum"]) == ("Neu", "Firma", "2026-11-09")
    assert client.put(base, json={"person": " "}).status_code == 422


def test_delete_interview_frees_catalog(client, catalog_id, interview):
    assert client.delete(f"/api/questionnaires/{catalog_id}").status_code == 409
    group_id = client.get(f"/api/questionnaires/{catalog_id}").json()["group_id"]
    assert client.delete(f"/api/groups/{group_id}").status_code == 409

    assert client.delete(f"/api/interviews/{interview['id']}").status_code == 204
    assert client.get(f"/api/interviews/{interview['id']}").status_code == 404
    assert client.delete(f"/api/questionnaires/{catalog_id}").status_code == 204


def test_empty_catalog_cannot_start(client):
    group_id = client.post("/api/groups", json={"name": "Leer"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "K"}).json()
    response = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": "A", "datum": "2026-11-09"}
    )
    assert response.status_code == 422


def test_list_is_newest_first(client, catalog_id):
    for person, datum in (("Alt", "2026-01-01"), ("Neu", "2026-06-01")):
        client.post("/api/interviews", json={"questionnaire_id": catalog_id, "person": person, "datum": datum})
    listed = client.get("/api/interviews").json()
    assert [i["person"] for i in listed] == ["Neu", "Alt"]
    assert listed[0]["group_name"] == "Lager" and listed[0]["questionnaire_name"] == "Leitfaden"


def test_audit_log_has_no_personal_data(client, interview):
    with Session(get_engine()) as db:
        entries = [(e.entitaet, e.aktion) for e in db.query(AuditLog).all()]
    assert (f"interview:{interview['id']}", "gestartet") in entries
    assert not any("A. B." in entity for entity, _ in entries)
