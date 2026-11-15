"""KI-Bewertung: Auftrag, Prompt, Ergebnis, Downloads, Export und LLM-Einstellungen."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pypdf import PdfReader

from app.services import evaluation
from app.services import export
from app.services import settings as settings_service

ANSWER = """## Zusammenfassung

A. B. bestellt **meistens per Telefon**.

## Kernaussagen

- Telefon ist Standard
- Mail <script>x</script> für Angebote

## Gesamtbewertung

1. neutral
"""


@pytest.fixture
def interview(client):
    group_id = client.post("/api/groups", json={"name": "Lager"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "Leitfaden"}).json()
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Wie bestellen Sie?", "pflicht": True})
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Was stört?"})
    data = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": "A. B.", "datum": "2026-11-09"}
    ).json()
    client.put(f"/api/interviews/{data['id']}/answers/{data['answers'][0]['id']}", json={"notiz": "Telefon"})
    client.put(f"/api/interviews/{data['id']}", json={"gesamtnotiz": "Offen für Neues"})
    return data


def url(interview, suffix=""):
    return f"/api/interviews/{interview['id']}/bewertung{suffix}"


def run(answer=ANSWER, seen=None):
    def generator(server, model, prompt):
        if seen is not None:
            seen.update(server=server, model=model, prompt=prompt)
        return answer

    return evaluation.process_next(generator)


@pytest.fixture
def auto_model(monkeypatch):
    monkeypatch.setattr(evaluation, "list_models", lambda server, timeout=10: ["modell-a"])


# ------------------------------------------------------------------ Auftrag
def test_without_evaluation(client, interview):
    body = client.get(url(interview)).json()
    assert body["status"] == "keine" and body["hat_transkript"] is False
    assert client.get(url(interview, ".md")).status_code == 404


def test_evaluation_job(client, interview, auto_model):
    started = client.post(url(interview))
    assert started.status_code == 202 and started.json()["status"] == "wartend"
    assert client.post(url(interview)).status_code == 409

    seen = {}
    assert run(seen=seen) is True
    assert run() is False
    assert seen["model"] == "modell-a"  # ohne Einstellung: erstes Modell des Servers
    assert "Wie bestellen Sie? (Pflichtfrage)" in seen["prompt"] and "Notiz: Telefon" in seen["prompt"]
    assert "Status: offen" in seen["prompt"] and "Offen für Neues" in seen["prompt"]
    assert "kein Transkript" in seen["prompt"]
    assert seen["server"].url == settings_service.LLM_URL

    body = client.get(url(interview)).json()
    assert body["status"] == "fertig" and body["text"] == ANSWER
    assert body["modell"] == "modell-a" and body["mit_transkript"] is False and body["fertig_am"]


def test_nothing_to_evaluate(client):
    group_id = client.post("/api/groups", json={"name": "Leer"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "K"}).json()
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "F"})
    data = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": "X", "datum": "2026-11-09"}
    ).json()
    assert client.post(url(data)).status_code == 422


def test_transcript_goes_into_prompt(client, interview, auto_model):
    recording = client.post(
        f"/api/interviews/{interview['id']}/aufnahmen", files={"datei": ("g.mkv", b"audio")}
    ).json()
    client.put(
        f"/api/interviews/{interview['id']}/aufnahmen/{recording['id']}/transkript",
        json={"transkript": "**[00:00:01] A. B.:** Wir faxen noch."},
    )
    assert client.get(url(interview)).json()["hat_transkript"] is True
    client.post(url(interview))
    seen = {}
    run(seen=seen)
    assert "# Transkript der Aufnahme g.mkv" in seen["prompt"] and "Wir faxen noch." in seen["prompt"]
    assert client.get(url(interview)).json()["mit_transkript"] is True


def test_long_transcript_is_cut(client, interview, monkeypatch):
    monkeypatch.setattr(evaluation, "MAX_TRANSCRIPT_CHARS", 50)
    recording = client.post(
        f"/api/interviews/{interview['id']}/aufnahmen", files={"datei": ("g.mkv", b"audio")}
    ).json()
    client.put(
        f"/api/interviews/{interview['id']}/aufnahmen/{recording['id']}/transkript", json={"transkript": "x" * 200}
    )
    from app.db import get_engine
    from sqlalchemy.orm import Session
    from app.models import Interview

    with Session(get_engine()) as db:
        prompt, with_transcript = evaluation.build_prompt(db.get(Interview, interview["id"]))
    assert with_transcript and "x" * 50 in prompt and "x" * 51 not in prompt and "gekürzt" in prompt


def test_error_keeps_previous_result(client, interview, auto_model):
    client.post(url(interview))
    run()

    def failing(server, model, prompt):
        raise evaluation.EvaluationError("LLM-Server nicht erreichbar")

    client.post(url(interview))
    evaluation.process_next(failing)
    body = client.get(url(interview)).json()
    assert body["status"] == "fehler" and "nicht erreichbar" in body["fehler"]
    assert body["text"] == ANSWER and body["modell"] == "modell-a"


def test_unexpected_error_is_stored(client, interview, auto_model):
    client.post(url(interview))
    evaluation.process_next(lambda *_: 1 / 0)
    assert "ZeroDivisionError" in client.get(url(interview)).json()["fehler"]


def test_delete_while_running_discards_result(client, interview, auto_model):
    client.post(url(interview))

    def generator(server, model, prompt):
        assert client.delete(url(interview)).status_code == 204
        return ANSWER

    evaluation.process_next(generator)
    assert client.get(url(interview)).json()["status"] == "keine"


def test_interrupted_jobs_are_requeued(client, interview):
    client.post(url(interview))
    from app.db import get_engine
    from sqlalchemy.orm import Session
    from app.models import Evaluation

    with Session(get_engine()) as db:
        db.query(Evaluation).update({"status": "laeuft"})
        db.commit()
    assert evaluation.requeue_interrupted() == 1
    assert client.get(url(interview)).json()["status"] == "wartend"


def test_correction_marks_as_edited(client, interview, auto_model):
    assert client.put(url(interview), json={"text": "x"}).status_code == 404
    client.post(url(interview))
    run()
    body = client.put(url(interview), json={"text": "## Zusammenfassung\n\nKorrigiert"}).json()
    assert body["bearbeitet"] is True and "Korrigiert" in body["text"]
    assert "von Hand überarbeitet" in client.get(url(interview, ".md")).text


def test_closed_interview_can_be_evaluated(client, interview, auto_model):
    client.post(f"/api/interviews/{interview['id']}/abschliessen")
    assert client.post(url(interview)).status_code == 202


def test_deleting_interview_removes_evaluation(client, interview, auto_model):
    client.post(url(interview))
    run()
    assert client.delete(f"/api/interviews/{interview['id']}").status_code == 204
    assert client.get(url(interview)).status_code == 404


def test_requires_login(anon, interview):
    assert anon.post("/api/auth/logout").status_code in (200, 204)
    assert anon.get(url(interview)).status_code == 401


# ------------------------------------------------------------------ Downloads und Export
def test_downloads(client, interview, auto_model):
    client.post(url(interview))
    run()
    md = client.get(url(interview, ".md"))
    assert md.status_code == 200
    assert "bewertung.md" in md.headers["content-disposition"]
    assert md.text.startswith("# KI-Bewertung: Interview mit A. B.")
    assert "KI-generiert" in md.text and "## Zusammenfassung" in md.text

    pdf = client.get(url(interview, ".pdf"))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    text = "".join(page.extract_text() for page in PdfReader(__import__("io").BytesIO(pdf.content)).pages)
    assert "Zusammenfassung" in text and "meistens per Telefon" in text and "<script>" in text
    assert client.get(url(interview, ".docx")).status_code == 404


def test_interview_exports_contain_evaluation(client, interview, auto_model):
    client.post(url(interview))
    run()
    md = client.get(f"/api/interviews/{interview['id']}/export.md").text
    assert "## KI-Bewertung" in md and "### Zusammenfassung" in md
    assert md.index("## Gesamtnotiz") < md.index("## KI-Bewertung")
    csv = client.get(f"/api/interviews/{interview['id']}/export.csv").text
    assert ";KI-Bewertung;modell-a;;ki-bewertung;" in csv
    pdf = client.get(f"/api/interviews/{interview['id']}/export.pdf").content
    text = "".join(page.extract_text() for page in PdfReader(__import__("io").BytesIO(pdf)).pages)
    assert "KI-Bewertung" in text and "für Angebote" in text


def test_markdown_html_escapes_and_formats():
    out = export.markdown_html(ANSWER + "\n---\nText mit *kursiv* und `code`\n  zweite Zeile\n")
    assert "<h2>Zusammenfassung</h2>" in out
    assert "<b>meistens per Telefon</b>" in out
    assert "<ul><li>Telefon ist Standard</li><li>Mail &lt;script&gt;x&lt;/script&gt; für Angebote</li></ul>" in out
    assert "<ol><li>neutral</li></ol>" in out
    assert "<i>kursiv</i>" in out and "<code>code</code>" in out and "<br>" in out


# ------------------------------------------------------------------ LLM-Server
def test_clean_answer():
    assert evaluation.clean_answer("<think>hmm</think>\n\n## A") == "## A"
    assert evaluation.clean_answer("noch gedacht</think>## A") == "## A"
    assert evaluation.clean_answer("```markdown\n## A\n```") == "## A"


@pytest.fixture
def fake_llm():
    """OpenAI-kompatibler Server mit /models und /chat/completions."""
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            seen["auth"] = self.headers.get("Authorization")
            self._send(200, {"data": [{"id": "llm-1"}, {"id": "llm-2"}]})

        def do_POST(self):  # noqa: N802
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            content = seen.get("reply", "<think>x</think>## Zusammenfassung\n\nOK")
            self._send(200, {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]})

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1", seen
    server.shutdown()


def test_job_against_server(client, interview, fake_llm):
    base, seen = fake_llm
    client.put("/api/einstellungen/llm", json={"url": base, "api_key": "k", "anweisung": "Sei knapp."})
    client.post(url(interview))
    assert evaluation.process_next() is True
    body = client.get(url(interview)).json()
    assert body["status"] == "fertig" and body["text"] == "## Zusammenfassung\n\nOK" and body["modell"] == "llm-1"
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "llm-1"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "Sei knapp."}
    assert "A. B." in seen["body"]["messages"][1]["content"]

    seen["reply"] = ""
    client.post(url(interview))
    evaluation.process_next()
    assert "leere Antwort" in client.get(url(interview)).json()["fehler"]


def test_llm_settings(client, fake_llm):
    base, _seen = fake_llm
    defaults = client.get("/api/einstellungen/llm").json()
    assert defaults["url"] == "http://localhost:8000/v1" and defaults["model"] == ""
    assert defaults["anweisung_angepasst"] is False and "## Gesamtbewertung" in defaults["anweisung"]

    changed = client.put("/api/einstellungen/llm", json={"url": base, "model": "llm-2", "anweisung": "Kurz."}).json()
    assert changed["model"] == "llm-2" and changed["anweisung_angepasst"] is True and changed["api_key_gesetzt"] is False
    # Die unveränderte Vorgabe wird nicht gespeichert, ein leeres Feld setzt zurück
    reset = client.put("/api/einstellungen/llm", json={"model": "", "anweisung": settings_service.LLM_INSTRUCTIONS})
    assert reset.json()["model"] == "" and reset.json()["anweisung_angepasst"] is False
    assert client.put("/api/einstellungen/llm", json={"url": "ftp://x"}).status_code == 422

    auto = client.post("/api/einstellungen/llm/test", json={"url": base, "model": ""}).json()
    assert auto["ok"] is True and auto["modell"] == "llm-1" and auto["modelle"] == ["llm-1", "llm-2"]
    missing = client.post("/api/einstellungen/llm/test", json={"url": base, "model": "fehlt"}).json()
    assert missing["ok"] is False and "fehlt" in missing["meldung"]
    down = client.post("/api/einstellungen/llm/test", json={"url": "http://127.0.0.1:9/v1"}).json()
    assert down["ok"] is False and "nicht erreichbar" in down["meldung"]
