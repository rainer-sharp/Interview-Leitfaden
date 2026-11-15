"""Sammelexport aller Interviews eines Projekts (Markdown/JSON) und KI-Analyse mit Kurzzusammenfassung."""
import io
import json

import pytest
from pypdf import PdfReader

from app.services import evaluation
from app.services import project_analysis
from app.services import settings as settings_service

TRANSCRIPT = "**[00:00:05] Anna:** Wir bestellen noch per Fax."
ANALYSIS = "## Überblick\n\nZwei Interviews.\n\n## Zentrale Erkenntnisse\n\n- Fax ist verbreitet"
SHORT = "Beide Befragten nutzen Fax.\n\n- Kernpunkt eins"


@pytest.fixture
def project(client):
    project = client.post("/api/projekte", json={"name": "Lieferanten", "beschreibung": "Runde 1"}).json()
    group = client.post("/api/groups", json={"name": "Einkauf", "projekt_id": project["id"]}).json()
    catalog = client.post(f"/api/groups/{group['id']}/questionnaires", json={"name": "Leitfaden"}).json()
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Wie bestellen Sie?"})
    for person, datum, note in (("Bernd", "2026-11-12", "Telefon"), ("Anna", "2026-11-10", "Fax")):
        interview = client.post(
            "/api/interviews",
            json={"questionnaire_id": catalog["id"], "person": person, "organisation": "Muster", "datum": datum},
        ).json()
        client.put(f"/api/interviews/{interview['id']}/answers/{interview['answers'][0]['id']}", json={"notiz": note})
        project.setdefault("interviews_by_person", {})[person] = interview
    anna = project["interviews_by_person"]["Anna"]
    recording = client.post(f"/api/interviews/{anna['id']}/aufnahmen", files={"datei": ("anna.mkv", b"x")}).json()
    client.put(f"/api/interviews/{anna['id']}/aufnahmen/{recording['id']}/transkript", json={"transkript": TRANSCRIPT})
    # Ein Interview in einem anderen Projekt darf nirgends auftauchen
    other = client.post("/api/groups", json={"name": "Fremd"}).json()
    other_catalog = client.post(f"/api/groups/{other['id']}/questionnaires", json={"name": "K"}).json()
    client.post(f"/api/questionnaires/{other_catalog['id']}/questions", json={"text": "F"})
    client.post("/api/interviews", json={"questionnaire_id": other_catalog["id"], "person": "Fremder", "datum": "2026-11-11"})
    return project


def url(project, suffix=""):
    return f"/api/projekte/{project['id']}{suffix}"


@pytest.fixture
def auto_model(monkeypatch):
    monkeypatch.setattr(evaluation, "list_models", lambda server, timeout=10: ["modell-a"])


def run(answers=(ANALYSIS, SHORT), calls=None):
    replies = iter(answers)

    def generator(server, model, prompt):
        if calls is not None:
            calls.append({"anweisung": server.anweisung, "model": model, "prompt": prompt})
        return next(replies)

    return project_analysis.process_next(generator)


# ------------------------------------------------------------------ Sammelexport
def test_markdown_bundle(client, project):
    response = client.get(url(project, "/export.md"))
    assert response.status_code == 200
    assert "interviews.md" in response.headers["content-disposition"]
    text = response.text
    assert text.startswith("# Projekt: Lieferanten\n\nRunde 1")
    assert "- **Interviews:** 2 (davon 1 mit Transkript)" in text
    # nach Datum sortiert, nummeriert, Interview-Überschriften eine Ebene tiefer
    assert text.index("## 1. Interview: Anna") < text.index("## 2. Interview: Bernd")
    assert "### Transkript: anna.mkv" in text and "Wir bestellen noch per Fax." in text
    assert "#### 1. Wie bestellen Sie?" in text and "Fremder" not in text


def test_markdown_only_transcripts(client, project):
    text = client.get(url(project, "/export.md?nur_transkripte=true")).text
    assert "- **Inhalt:** nur Transkripte" in text
    assert "Wir bestellen noch per Fax." in text and "_(kein Transkript)_" in text
    assert "Wie bestellen Sie?" not in text


def test_json_bundle(client, project, auto_model):
    anna = project["interviews_by_person"]["Anna"]
    client.post(f"/api/interviews/{anna['id']}/bewertung")
    evaluation.process_next(lambda *_: "## Zusammenfassung\n\nFax")
    data = json.loads(client.get(url(project, "/export.json")).text)
    assert data["format"] == "interview-leitfaden-projekt/1" and data["inhalt"] == "vollstaendig"
    assert data["projekt"]["name"] == "Lieferanten" and data["projekt"]["gruppen"] == ["Einkauf"]
    assert [i["person"] for i in data["interviews"]] == ["Anna", "Bernd"]
    first = data["interviews"][0]
    assert first["antworten"][0] == {
        "position": 1, "abschnitt": "Allgemein", "frage": "Wie bestellen Sie?", "hinweis": "", "pflicht": False,
        "status": "beantwortet", "notiz": "Fax",
    }
    assert first["transkripte"][0]["text"] == TRANSCRIPT and first["ki_bewertung"]["modell"] == "modell-a"
    assert data["interviews"][1]["ki_bewertung"] is None

    short = json.loads(client.get(url(project, "/export.json?nur_transkripte=true")).text)
    assert short["inhalt"] == "transkripte" and "antworten" not in short["interviews"][0]
    assert client.get(url(project, "/export.docx")).status_code == 404


def test_empty_project_exports(client):
    empty = client.post("/api/projekte", json={"name": "Leer"}).json()
    assert "_(keine Interviews)_" in client.get(f"/api/projekte/{empty['id']}/export.md").text
    assert json.loads(client.get(f"/api/projekte/{empty['id']}/export.json").text)["interviews"] == []
    assert client.post(f"/api/projekte/{empty['id']}/analyse").status_code == 422


# ------------------------------------------------------------------ KI-Analyse
def test_analysis_job(client, project, auto_model):
    before = client.get(url(project, "/analyse")).json()
    assert before["status"] == "keine" and before["interviews_jetzt"] == 2
    assert before["mit_transkript"] == 1 and before["mit_bewertung"] == 0 and before["anweisung_quelle"] == "allgemein"

    assert client.post(url(project, "/analyse")).status_code == 202
    assert client.post(url(project, "/analyse")).status_code == 409
    calls = []
    assert run(calls=calls) is True
    assert run() is False  # nichts mehr wartend

    analysis_call, short_call = calls
    assert analysis_call["anweisung"] == settings_service.LLM_ANALYSIS_INSTRUCTIONS
    assert "# Projekt: Lieferanten" in analysis_call["prompt"] and "## Interview 1: Anna" in analysis_call["prompt"]
    assert TRANSCRIPT in analysis_call["prompt"] and "Fremder" not in analysis_call["prompt"]
    assert short_call["anweisung"] == settings_service.LLM_SHORT_INSTRUCTIONS and ANALYSIS in short_call["prompt"]

    body = client.get(url(project, "/analyse")).json()
    assert body["status"] == "fertig" and body["analyse"] == ANALYSIS and body["kurzfassung"] == SHORT
    assert body["interviews"] == 2 and body["umfang"] == "vollständig" and body["modell"] == "modell-a"


def test_project_instructions_and_settings(client, project, auto_model):
    client.put(url(project), json={"name": "Lieferanten", "ki_analyse_anweisung": "Analysiere als Einkäufer."})
    assert client.get(url(project, "/analyse")).json()["anweisung_quelle"] == "projekt"
    client.post(url(project, "/analyse"))
    calls = []
    run(calls=calls)
    assert calls[0]["anweisung"] == "Analysiere als Einkäufer."

    # Ein PUT ohne das Feld lässt die Analyse-Anweisung stehen; leer = allgemeine aus den Einstellungen
    assert client.put(url(project), json={"name": "Lieferanten"}).json()["ki_analyse_anweisung"] == "Analysiere als Einkäufer."
    client.put(url(project), json={"name": "Lieferanten", "ki_analyse_anweisung": ""})
    llm = client.put("/api/einstellungen/llm", json={"analyse_anweisung": "Allgemein."}).json()
    assert llm["analyse_anweisung"] == "Allgemein." and llm["analyse_anweisung_angepasst"] is True
    client.post(url(project, "/analyse"))
    calls = []
    run(calls=calls)
    assert calls[0]["anweisung"] == "Allgemein."

    # Kopie übernimmt die Anweisung, aber nicht die Analyse
    client.put(url(project), json={"name": "Lieferanten", "ki_analyse_anweisung": "Eigen."})
    copy = client.post(url(project, "/kopie"), json={}).json()
    assert copy["ki_analyse_anweisung"] == "Eigen."
    assert client.get(f"/api/projekte/{copy['id']}/analyse").json()["status"] == "keine"


def test_error_keeps_previous_result(client, project, auto_model):
    client.post(url(project, "/analyse"))
    run()

    def failing(*_):
        raise evaluation.EvaluationError("LLM-Server nicht erreichbar")

    client.post(url(project, "/analyse"))
    project_analysis.process_next(failing)
    body = client.get(url(project, "/analyse")).json()
    assert body["status"] == "fehler" and "nicht erreichbar" in body["fehler"] and body["analyse"] == ANALYSIS


def test_edit_delete_and_downloads(client, project, auto_model):
    assert client.put(url(project, "/analyse"), json={"kurzfassung": "x"}).status_code == 404
    assert client.get(url(project, "/analyse.md")).status_code == 404
    client.post(url(project, "/analyse"))
    run()
    edited = client.put(url(project, "/analyse"), json={"kurzfassung": "Korrigiert.\n\n- Punkt"}).json()
    assert edited["bearbeitet"] is True and edited["analyse"] == ANALYSIS

    md = client.get(url(project, "/analyse.md"))
    assert "analyse.md" in md.headers["content-disposition"]
    assert md.text.startswith("# KI-Analyse: Projekt Lieferanten")
    assert "## Kurzzusammenfassung\n\nKorrigiert." in md.text and "### Überblick" in md.text
    assert "2 Interviews" in md.text and "von Hand überarbeitet" in md.text

    pdf = client.get(url(project, "/analyse.pdf"))
    assert pdf.content.startswith(b"%PDF")
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Kurzzusammenfassung" in text and "Zentrale Erkenntnisse" in text

    assert client.delete(url(project, "/analyse")).status_code == 204
    assert client.get(url(project, "/analyse")).json()["status"] == "keine"


def test_delete_while_running_discards(client, project, auto_model):
    client.post(url(project, "/analyse"))

    def generator(*_):
        client.delete(url(project, "/analyse"))
        return "x"

    project_analysis.process_next(generator)
    assert client.get(url(project, "/analyse")).json()["status"] == "keine"


def test_shared_worker_runs_interviews_first(monkeypatch):
    from app.services import project_analysis as pa

    order = []
    monkeypatch.setattr(evaluation, "process_next", lambda: order.append("interview") or len(order) < 2)
    monkeypatch.setattr(pa, "process_next", lambda: order.append("projekt") or False)
    assert evaluation._process_any() is True and order == ["interview"]
    assert evaluation._process_any() is False and order == ["interview", "interview", "projekt"]


# ------------------------------------------------------------------ Kürzen bei großen Projekten
def test_build_prompt_reduces_in_steps(client, project, auto_model):
    from sqlalchemy.orm import Session

    from app.db import get_engine
    from app.models import Project
    from app.services import project_export

    anna, bernd = project["interviews_by_person"]["Anna"], project["interviews_by_person"]["Bernd"]
    long_text = "**[00:00:01] Anna:** " + "Lieferzeit " * 2999 + "Ende"  # ca. 33 000 Zeichen
    for interview in (anna, bernd):
        rec = client.post(f"/api/interviews/{interview['id']}/aufnahmen", files={"datei": ("g.mkv", b"x")}).json()
        client.put(f"/api/interviews/{interview['id']}/aufnahmen/{rec['id']}/transkript", json={"transkript": long_text})
    client.post(f"/api/interviews/{anna['id']}/bewertung")
    evaluation.process_next(lambda *_: "## Zusammenfassung\n\nAnna bewertet")

    with Session(get_engine()) as db:
        model = db.get(Project, project["id"])
        interviews = project_export.interviews_of(db, model)

        def build(limit):
            return project_analysis.build_prompt(model, interviews, limit=limit)

        full, scope = build(10**6)
        assert scope == "vollständig" and full.count("Lieferzeit Lieferzeit") > 2

        # Stufe 2: Annas Transkripte fallen weg (sie hat eine KI-Bewertung), Bernds bleibt ganz
        prompt, scope = build(len(full) - 1000)
        assert scope == "Transkripte nur bei Interviews ohne KI-Bewertung" and "Anna bewertet" in prompt
        assert prompt.count(long_text) == 1

        # Stufe 3: auch Bernds Transkript wird gekürzt
        prompt, scope = build(len(full) // 2)
        assert scope.startswith("Transkripte gekürzt") and long_text not in prompt and len(prompt) <= len(full) // 2

        # Stufe 4 und Notbremse
        prompt, scope = build(2500)
        assert scope in ("ohne Transkripte (zu umfangreich)", "stark gekürzt (zu umfangreich)") and len(prompt) < 2600
