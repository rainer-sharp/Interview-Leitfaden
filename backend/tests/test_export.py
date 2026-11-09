"""Exporte gegen Referenzdateien in testdata/referenz. Neu erzeugen: REGENERATE=1 pytest tests/test_export.py"""
import io
import os

import pytest
from pypdf import PdfReader

REGENERATE = os.environ.get("REGENERATE") == "1"


@pytest.fixture
def interview(client):
    group_id = client.post("/api/groups", json={"name": "Kunden Einkauf"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "Leitfaden"}).json()
    url = f"/api/questionnaires/{catalog['id']}/questions"
    client.post(url, json={"text": "Wie sieht Ihr typischer Arbeitstag aus?", "abschnitt": "Einstieg", "pflicht": True})
    client.post(url, json={"text": "Wie bestellen Sie heute Bauteile?", "abschnitt": "Einkauf", "pflicht": True})
    client.post(url, json={"text": "Wie zufrieden sind Sie mit den Lieferzeiten?", "abschnitt": "Einkauf", "typ": "skala"})
    client.post(url, json={"text": "Was würden Sie sofort ändern?", "abschnitt": "Abschluss"})
    created = client.post(
        "/api/interviews",
        json={"questionnaire_id": catalog["id"], "person": "Jürgen Müller", "organisation": "Muster & Söhne GmbH",
              "datum": "2026-11-09"},
    ).json()
    answers = [a["id"] for a in created["answers"]]
    base = f"/api/interviews/{created['id']}"
    client.put(f"{base}/answers/{answers[0]}", json={"notiz": "Beginnt um 7 Uhr.\nZuerst Wareneingang, dann Mails."})
    client.put(f"{base}/answers/{answers[1]}", json={"notiz": "=Telefon; manchmal \"Fax\""})
    client.put(f"{base}/answers/{answers[2]}", json={"status": "uebersprungen"})
    client.put(base, json={"gesamtnotiz": "Lieferzeiten sind das Hauptthema."})
    client.post(f"{base}/abschliessen")
    return created["id"]


def check_reference(testdata, name: str, actual: bytes) -> None:
    path = testdata / "referenz" / name
    if REGENERATE:
        path.write_bytes(actual)
    assert actual == path.read_bytes()


def test_markdown_matches_reference(client, testdata, interview):
    response = client.get(f"/api/interviews/{interview}/export.md")
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert 'filename="interview-1-2026-11-09-jurgen-muller.md"' in response.headers["content-disposition"]
    check_reference(testdata, "interview.md", response.content)


def test_csv_matches_reference(client, testdata, interview):
    response = client.get(f"/api/interviews/{interview}/export.csv")
    assert response.content.startswith("﻿".encode())
    check_reference(testdata, "interview.csv", response.content)


def test_pdf_contains_all_content(client, interview):
    response = client.get(f"/api/interviews/{interview}/export.pdf")
    assert response.headers["content-type"] == "application/pdf"
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
    for expected in (
        "Interview: Jürgen Müller", "Muster & Söhne GmbH", "09.11.2026", "Wie bestellen Sie heute Bauteile?",
        "Zuerst Wareneingang", "Status: übersprungen", "(keine Notiz)", "Lieferzeiten sind das Hauptthema.",
    ):
        assert expected in text


def test_markup_in_notes_is_escaped(client, interview):
    from sqlalchemy.orm import Session

    from app.db import get_engine
    from app.models import Interview
    from app.services.export import to_html

    answer_id = client.get(f"/api/interviews/{interview}").json()["answers"][3]["id"]
    client.post(f"/api/interviews/{interview}/wiederoeffnen")
    client.put(f"/api/interviews/{interview}/answers/{answer_id}", json={"notiz": '<img src="http://example.invalid/x">'})
    with Session(get_engine()) as db:
        rendered = to_html(db.get(Interview, interview))
    assert "<img" not in rendered and "&lt;img src=&quot;http://example.invalid/x&quot;&gt;" in rendered
    assert client.get(f"/api/interviews/{interview}/export.pdf").status_code == 200


def test_unknown_format_and_missing_interview(client, interview):
    assert client.get(f"/api/interviews/{interview}/export.docx").status_code == 404
    assert client.get("/api/interviews/999/export.md").status_code == 404
