"""Audio-Aufnahmen, Transkriptions-Aufträge, Server-Einstellungen und der Adapter um transcribe_interview.py."""
import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import Recording
from app.services import settings as settings_service
from app.services import transcribe_interview as script
from app.services import transcription

TRANSCRIPT = """# Transkript: gespraech.mkv

- Dauer: 00:00:12
- Modus: mix
- Modell: test
- Erstellt: 2026-11-10 10:00

---

**[00:00:00] Ich:** Wie bestellen Sie heute?

**[00:00:04] A. B.:** Meistens per <Telefon> & Mail.
"""


@pytest.fixture
def interview(client):
    group_id = client.post("/api/groups", json={"name": "Lager"}).json()["id"]
    catalog = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": "Leitfaden"}).json()
    client.post(f"/api/questionnaires/{catalog['id']}/questions", json={"text": "Erste"})
    response = client.post(
        "/api/interviews", json={"questionnaire_id": catalog["id"], "person": "A. B.", "datum": "2026-11-09"}
    )
    return response.json()


def upload(client, interview, name="gespraech.mkv", content=b"\x1a\x45\xdf\xa3 audio"):
    return client.post(f"/api/interviews/{interview['id']}/aufnahmen", files={"datei": (name, content)})


@pytest.fixture
def recording(client, interview):
    response = upload(client, interview)
    assert response.status_code == 201
    return response.json()


def rec_url(recording, suffix=""):
    return f"/api/interviews/{recording['interview_id']}/aufnahmen/{recording['id']}{suffix}"


# ------------------------------------------------------------------ Hochladen
def test_upload_stores_file_next_to_database(client, recording, database):
    assert recording["dateiname"] == "gespraech.mkv" and recording["groesse"] == 10
    assert recording["transkript_status"] == "keine"
    files = list((database.parent / "audio" / str(recording["interview_id"])).iterdir())
    assert len(files) == 1 and files[0].suffix == ".mkv" and files[0].name != "gespraech.mkv"

    download = client.get(rec_url(recording, "/datei"))
    assert download.status_code == 200 and download.content == b"\x1a\x45\xdf\xa3 audio"
    assert "gespraech.mkv" in download.headers["content-disposition"]

    detail = client.get(f"/api/interviews/{recording['interview_id']}").json()
    assert [a["id"] for a in detail["aufnahmen"]] == [recording["id"]]


def test_upload_rejects_unknown_type_and_empty_file(client, interview):
    assert upload(client, interview, name="notizen.txt").status_code == 422
    assert upload(client, interview, content=b"").status_code == 422


def test_upload_size_limit(client, interview, monkeypatch, database):
    import app.api.recordings as api

    small = dataclasses.replace(api.get_settings(), max_audio_mb=0)
    monkeypatch.setattr(api, "get_settings", lambda: small)
    assert upload(client, interview).status_code == 413
    assert not any((database.parent / "audio").rglob("*.mkv"))


def test_upload_requires_login(anon, interview):
    anon.cookies.clear()
    assert anon.get(f"/api/interviews/{interview['id']}/aufnahmen").status_code == 401


def test_delete_recording_and_interview_remove_files(client, interview, database):
    first = upload(client, interview).json()
    upload(client, interview)
    audio = database.parent / "audio" / str(interview["id"])
    assert len(list(audio.iterdir())) == 2

    assert client.delete(rec_url(first)).status_code == 204
    assert len(list(audio.iterdir())) == 1
    assert client.get(rec_url(first)).status_code == 404

    assert client.delete(f"/api/interviews/{interview['id']}").status_code == 204
    assert not audio.exists()


def test_recording_of_other_interview_is_not_found(client, interview, recording):
    other = client.post(
        "/api/interviews", json={"questionnaire_id": interview["questionnaire_id"], "person": "X", "datum": "2026-11-10"}
    ).json()
    assert client.get(f"/api/interviews/{other['id']}/aufnahmen/{recording['id']}").status_code == 404


# ------------------------------------------------------------------ Aufträge
def test_transcription_job_fills_interview(client, recording):
    started = client.post(rec_url(recording, "/transkription"), json={"modus": "mix", "begriffe": "DigiKey, Nexar\nDigiKey"})
    assert started.status_code == 202
    body = started.json()
    assert body["transkript_status"] == "wartend"
    # Gesprächspartner heißt ohne Angabe wie die interviewte Person
    assert body["transkript_optionen"] == {
        "modus": "mix", "name_ich": "Ich", "name_partner": "A. B.", "begriffe": ["DigiKey", "Nexar"],
    }
    assert client.post(rec_url(recording, "/transkription"), json={}).status_code == 409

    calls = []

    def fake(src, name, server, options, log):
        calls.append((src, name, server, options))
        log("Mix: 00:00:00–00:00:12 ...")
        return TRANSCRIPT

    assert transcription.process_next(fake) is True
    assert transcription.process_next(fake) is False
    src, name, server, options = calls[0]
    assert src.is_file() and name == "gespraech.mkv"
    assert server.url == settings_service.TRANSCRIBE_URL and options.name_partner == "A. B."

    done = client.get(rec_url(recording)).json()
    assert done["transkript_status"] == "fertig" and done["transkript"] == TRANSCRIPT
    assert done["transkript_log"] == "Mix: 00:00:00–00:00:12 ..."
    assert done["transkript_start"] and done["transkript_ende"]

    interview_url = f"/api/interviews/{recording['interview_id']}"
    markdown = client.get(f"{interview_url}/export.md").text
    assert "## Transkript: gespraech.mkv" in markdown
    assert "**[00:00:04] A. B.:** Meistens per <Telefon> & Mail." in markdown
    assert "- Modell: test" not in markdown  # Kopf des Skripts entfällt im Export
    csv = client.get(f"{interview_url}/export.csv").text
    assert "Transkript;gespraech.mkv;;transkript;" in csv
    assert client.get(rec_url(recording, "/transkript.md")).text == TRANSCRIPT

    from pypdf import PdfReader
    import io
    pdf = PdfReader(io.BytesIO(client.get(f"{interview_url}/export.pdf").content))
    text = "".join(page.extract_text() for page in pdf.pages)
    assert "Transkript: gespraech.mkv" in text and "[00:00:04] A. B.: Meistens per <T" in text and "& Mail." in text


def test_transcription_error_is_stored(client, recording):
    client.post(rec_url(recording, "/transkription"), json={"modus": "tracks"})

    def failing(*_args):
        raise transcription.TranscriptionError("Server-Fehler 500: kaputt")

    transcription.process_next(failing)
    failed = client.get(rec_url(recording)).json()
    assert failed["transkript_status"] == "fehler" and failed["transkript_fehler"] == "Server-Fehler 500: kaputt"

    def crashing(*_args):
        raise KeyError("choices")

    client.post(rec_url(recording, "/transkription"), json={})
    transcription.process_next(crashing)
    assert "KeyError" in client.get(rec_url(recording)).json()["transkript_fehler"]


def test_recording_deleted_while_running(client, recording):
    client.post(rec_url(recording, "/transkription"), json={})

    def delete_meanwhile(*_args):
        client.delete(rec_url(recording))
        return TRANSCRIPT

    assert transcription.process_next(delete_meanwhile) is True
    assert client.get(f"/api/interviews/{recording['interview_id']}/aufnahmen").json() == []


def test_interrupted_jobs_are_requeued(client, recording):
    with Session(get_engine()) as db:
        db.get(Recording, recording["id"]).transkript_status = "laeuft"
        db.commit()
    assert transcription.requeue_interrupted() == 1
    assert client.get(rec_url(recording)).json()["transkript_status"] == "wartend"


def test_transcript_can_be_corrected(client, recording):
    response = client.put(rec_url(recording, "/transkript"), json={"transkript": "Korrigiert"})
    assert response.status_code == 200
    assert response.json()["transkript"] == "Korrigiert" and response.json()["transkript_status"] == "fertig"
    client.post(rec_url(recording, "/transkription"), json={})
    assert client.put(rec_url(recording, "/transkript"), json={"transkript": "x"}).status_code == 409


def test_closed_interview_still_accepts_recordings(client, interview):
    client.post(f"/api/interviews/{interview['id']}/abschliessen")
    created = upload(client, interview)
    assert created.status_code == 201
    assert client.post(rec_url(created.json(), "/transkription"), json={}).status_code == 202


# ------------------------------------------------------------------ Einstellungen
def test_settings_defaults(client):
    body = client.get("/api/einstellungen/transkription").json()
    assert body["url"] == settings_service.TRANSCRIBE_URL and body["model"] == script.MODEL_NAME
    assert body["modus"] == "mix" and body["name_ich"] == "Ich" and body["api_key_gesetzt"] is False
    assert "api_key" not in body


def test_settings_update_and_reset(client):
    url = "/api/einstellungen/transkription"
    body = client.put(url, json={"url": "http://gpu:8001/v1", "api_key": "geheim", "begriffe": "SestigSystems"}).json()
    assert body["url"] == "http://gpu:8001/v1" and body["api_key_gesetzt"] is True and body["begriffe"] == "SestigSystems"
    assert "geheim" not in json.dumps(body)

    body = client.put(url, json={"model": "anderes"}).json()
    assert body["url"] == "http://gpu:8001/v1" and body["model"] == "anderes"  # nicht übergebene Felder bleiben

    body = client.put(url, json={"url": "", "api_key": ""}).json()
    assert body["url"] == settings_service.TRANSCRIBE_URL and body["api_key_gesetzt"] is False

    assert client.put(url, json={"url": "ftp://x"}).status_code == 422
    assert client.put(url, json={"modus": "egal"}).status_code == 422


def test_job_uses_saved_server_settings(client, recording):
    client.put("/api/einstellungen/transkription", json={"url": "http://gpu:9/v1", "model": "m", "api_key": "k"})
    client.post(rec_url(recording, "/transkription"), json={})
    seen = []
    transcription.process_next(lambda src, name, server, options, log: seen.append(server) or "x")
    assert (seen[0].url, seen[0].model, seen[0].api_key) == ("http://gpu:9/v1", "m", "k")


@pytest.fixture
def fake_server():
    """Minimaler OpenAI-kompatibler /v1/models-Endpunkt."""
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            seen["auth"] = self.headers.get("Authorization")
            body = json.dumps({"data": [{"id": "modell-a"}]}).encode()
            self.send_response(200 if self.path == "/v1/models" else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1", seen
    server.shutdown()


def test_server_check(client, fake_server):
    url, seen = fake_server
    ok = client.post("/api/einstellungen/transkription/test", json={"url": url, "model": "modell-a", "api_key": "k"})
    assert ok.json() == {"ok": True, "meldung": "Server erreichbar, Modell vorhanden.", "modelle": ["modell-a"]}
    assert seen["auth"] == "Bearer k"

    missing = client.post("/api/einstellungen/transkription/test", json={"url": url, "model": "anderes"}).json()
    assert missing["ok"] is False and "anderes" in missing["meldung"] and missing["modelle"] == ["modell-a"]

    down = client.post("/api/einstellungen/transkription/test", json={"url": "http://127.0.0.1:9/v1"}).json()
    assert down["ok"] is False and "Nicht erreichbar" in down["meldung"]


# ------------------------------------------------------------------ Adapter um das Skript
SERVER = settings_service.TranscriptionSettings(
    url="http://gpu:8001/v1/", model="m", api_key="", modus="mix", name_ich="Ich", begriffe=""
)


def test_adapter_runs_script_pipeline(tmp_path, monkeypatch):
    src = tmp_path / "abc123.mkv"
    src.write_bytes(b"x")
    seen = {}

    def mode_mix(path, tmp, prompt, has_tracks, names):
        seen.update(path=path, prompt=prompt, has_tracks=has_tracks, names=names,
                    server=(script.SERVER_URL, script.MODEL_NAME, script.API_KEY))
        script.print("  Mix: 00:00:00–00:00:09 ...", file=None)  # so gibt das Skript Fortschritt aus
        return [
            {"word": "Hallo", "start": 0.0, "end": 0.5, "name": names[0]},
            {"word": "zusammen.", "start": 0.6, "end": 1.0, "name": names[0]},
            {"word": "Guten", "start": 1.5, "end": 1.8, "name": names[1]},
            {"word": "Tag", "start": 1.9, "end": 2.2, "name": names[1]},
            {"word": "!", "start": 2.2, "end": 2.3, "name": names[1]},
        ], 9.0

    monkeypatch.setattr(transcription, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(script, "audio_track_count", lambda _src: 3)
    monkeypatch.setattr(script, "mode_mix", mode_mix)
    log = []
    options = transcription.Options(modus="mix", name_ich="Rainer", name_partner="Frau Müller", begriffe=["DigiKey"])
    text = transcription.transcribe_file(src, "Interview Müller.mkv", SERVER, options, log.append)

    assert seen["path"] == src and seen["has_tracks"] is True and seen["names"] == ("Rainer", "Frau Müller")
    assert seen["prompt"].startswith(script.PROMPT_SPK) and seen["prompt"].endswith("Context terms: DigiKey.")
    assert seen["server"] == ("http://gpu:8001/v1", "m", "EMPTY")
    assert text.startswith("# Transkript: Interview Müller.mkv")
    assert "- Kontextbegriffe: DigiKey" in text
    assert "**[00:00:00] Rainer:** Hallo zusammen." in text
    assert "**[00:00:01] Frau Müller:** Guten Tag!" in text
    assert log == ["Interview Müller.mkv: 3 Audiospur(en), Modus mix", "Mix: 00:00:00–00:00:09 ..."]
    # Skript ist danach wieder im Ausgangszustand
    assert script.SERVER_URL != "http://gpu:8001/v1" and "print" not in vars(script)


def test_adapter_turns_sys_exit_into_error(tmp_path, monkeypatch):
    src = tmp_path / "a.mp3"
    src.write_bytes(b"x")
    monkeypatch.setattr(transcription, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(script, "audio_track_count", lambda _src: 1)
    saved_url = script.SERVER_URL

    with pytest.raises(transcription.TranscriptionError, match="braucht 3 Audiospuren"):
        transcription.transcribe_file(src, "a.mp3", SERVER, transcription.Options(modus="tracks"))

    def server_error(*_args, **_kw):
        script.sys.exit("Server-Fehler 503: busy")

    monkeypatch.setattr(script, "mode_mix", server_error)
    with pytest.raises(transcription.TranscriptionError, match="Server-Fehler 503"):
        transcription.transcribe_file(src, "a.mp3", SERVER, transcription.Options())
    assert script.SERVER_URL == saved_url and "print" not in vars(script)


def test_adapter_without_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr(transcription, "ffmpeg_available", lambda: False)
    with pytest.raises(transcription.TranscriptionError, match="ffmpeg"):
        transcription.transcribe_file(tmp_path / "a.wav", "a.wav", SERVER, transcription.Options())


def test_vendored_script_is_unchanged():
    """Die Kopie soll mit dem Original übereinstimmen, damit Fehlerbehebungen dort einfach übernommen werden können."""
    original = Path("/workspace/transcription/transcribe_interview.py")
    if not original.exists():
        pytest.skip("Projekt transcription nicht vorhanden")
    assert Path(script.__file__).read_bytes() == original.read_bytes()


def test_split_terms():
    assert transcription.split_terms("A, B\n# Kommentar\nA,,C ") == ["A", "B", "C"]
