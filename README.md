# Interview-Leitfaden

Selbst gehostete Web-App, die Interviewer Frage für Frage durch ein Gespräch führt. Pro Personengruppe gibt es
importierte Fragenkataloge, je Frage eine Notiz mit Autosave und am Ende einen Export als PDF, Markdown oder CSV.

Die Spezifikation steht in [docs/SPEC.md](docs/SPEC.md), der Umsetzungsstand in [docs/TASKS.md](docs/TASKS.md).

## Start

```sh
cp .env.example .env              # SECRET_KEY und ADMIN_PASSWORD unbedingt ändern
mkdir -p data backups && sudo chown 1000 data backups
docker compose up -d --build
```

Danach ist die App unter `http://<host>:8080` erreichbar (Port über `APP_PORT`). Ohne eigene Werte für `SECRET_KEY`
und `ADMIN_PASSWORD` startet sie bewusst nicht. Einen guten Schlüssel erzeugt z. B. `openssl rand -hex 32`.

| Zweck | Befehl |
| --- | --- |
| Mit HTTPS-Proxy (VPS, `DOMAIN` in `.env`) | `docker compose --profile proxy up -d --build` |
| Entwicklung mit Hot-Reload | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` → Frontend auf Port 5173 |
| Update | `git pull && docker compose up -d --build` |
| Logs | `docker compose logs -f app` |
| Vollsicherung als ZIP | `scripts/backup.sh` oder in der App oben auf „Backup“ |
| Backup wiederherstellen | App stoppen, `backups/interviews-<datum>.db` nach `data/interviews.db` kopieren, starten |

## Bedienung

1. **Gruppe anlegen**, z. B. „Lagerpersonal“.
2. **Fragenliste importieren** (CSV, XLSX oder JSON). Die Vorschau zeigt Zeichensatz, Trennzeichen und Fehler mit
   Zeilennummer, gespeichert wird erst danach: als neuer Katalog, als neue Version oder angehängt. Eine Beispieldatei
   gibt es auf der Import-Seite.
3. **Katalog bearbeiten**: Fragen per Drag & Drop (Griff ⠿) oder mit ↑/↓ verschieben, auch über Abschnittsgrenzen,
   und Abschnitte umbenennen oder umsortieren.
4. **Interview starten**: Katalog wählen, Person (ein Kürzel genügt zur Pseudonymisierung), Organisation, Datum.
5. **Interview-Modus**: eine Frage pro Bildschirm, Notizen werden 1,2 s nach der letzten Eingabe gespeichert.
   Ohne Netz bleiben sie im Browser und werden später nachgesendet. „Pause“ unterbricht, „Fortsetzen“ springt zur
   ersten offenen Frage.
6. **Abschluss**: Übersicht offener Fragen, Gesamtnotiz, abschließen, exportieren. Abgeschlossene Interviews sind
   schreibgeschützt, bis man sie wieder öffnet.

7. **Aufnahme und Transkript** (im Abschluss-Bildschirm, auch bei abgeschlossenen Interviews): Audiodatei
   hochladen (OBS-`.mkv` mit den Spuren Mix/Ich/Partner oder `.wav`, `.mp3`, `.m4a`, `.webm` …), „Transkribieren“
   wählen, Modus, Namen und Kontextbegriffe prüfen und starten. Die App schickt die Aufnahme im Hintergrund an den
   Transkriptions-Server; der Fortschritt erscheint im Protokoll, die Seite darf dabei geschlossen werden. Das
   fertige Transkript (Dialog mit Zeitstempeln) steht unter der Aufnahme, lässt sich korrigieren und ist Teil der
   Exporte (Markdown, PDF, CSV).
8. **KI-Bewertung** (im Abschluss-Bildschirm unter dem Transkript): „Interview bewerten“ schickt Fragen, Notizen,
   Gesamtnotiz und – falls vorhanden – die Transkripte an ein LLM. Ergebnis: Zusammenfassung, Kernaussagen,
   Gesamtbewertung mit Einstufung, Abweichungen/Lücken, offene Punkte. Es lässt sich korrigieren, als PDF oder
   Markdown herunterladen und steht zusätzlich in den Interview-Exporten unter „KI-Bewertung“.

Tastenkürzel im Interview: `Strg+Enter` weiter · `Strg+←` zurück · `Strg+S` überspringen (auf dem Mac auch mit `⌘`).

### Importformat

```csv
abschnitt;position;frage;hinweis;pflicht;typ
Einstieg;1;Wie sieht Ihr typischer Arbeitstag aus?;Locker beginnen;ja;text
```

Nur `frage` ist Pflicht. Trennzeichen `;` oder `,`, Zeichensatz UTF-8 oder Windows-1252 (Excel) werden erkannt.
`typ` ist einer von `text`, `skala`, `ja_nein`, `auswahl`. In Version 1 wird jede Antwort als Notiz erfasst.
JSON: eine Liste von Objekten mit denselben Feldern, oder `{"fragen": [...]}`.

### Transkriptions-Server

Transkribiert wird mit `backend/app/services/transcribe_interview.py`, einer unveränderten Kopie aus dem Projekt
`transcription` (Nemotron-3.5-Transcribe über einen OpenAI-kompatiblen vLLM-Endpunkt). Der Adapter
`backend/app/services/transcription.py` importiert das Skript als Modul, setzt Server, Modell und Schlüssel und
liest dessen Markdown-Ausgabe. Änderungen am Skript im Projekt `transcription` vornehmen und die Datei danach
hierher kopieren (`test_vendored_script_is_unchanged` meldet Abweichungen, wenn beide Projekte nebeneinander liegen).

- **Einstellungen** (oben in der Navigation): Server-URL, Modell, API-Schlüssel, „Verbindung testen“ (fragt
  `/models` ab) sowie Vorgaben für Modus, Interviewer-Name und Kontextbegriffe. Gespeichert in der Datenbank; leere
  Felder fallen auf `TRANSCRIBE_URL`, `TRANSCRIBE_MODEL`, `TRANSCRIBE_API_KEY` aus der `.env` und danach auf die
  Werte im Skript zurück.
- Es läuft immer nur eine Transkription gleichzeitig, weitere warten. Nach einem Neustart der App werden
  unterbrochene Aufträge wiederholt.
- Der Container braucht Netzzugriff auf den Server (LAN). `ffmpeg` ist im Image enthalten.

### LLM-Server (KI-Bewertung)

- Vorgabe: `http://192.168.101.94:8000/v1` (vLLM). Ohne eingestelltes Modell nimmt die App das erste Modell, das der
  Server unter `/models` anbietet (derzeit `nvidia/Qwen3.8-Flash-Next-FP4-Local`), ein Modellwechsel auf dem Server
  braucht also keine Änderung in der App.
- **Einstellungen** → „LLM-Server für die KI-Bewertung“: URL, Modell, API-Schlüssel, „Verbindung testen“ und die
  Anweisung an das Modell (System-Prompt; legt Aufbau und Maßstab der Bewertung fest). Leere Felder fallen auf
  `LLM_URL`, `LLM_MODEL`, `LLM_API_KEY` aus der `.env` und danach auf die Vorgaben zurück.
- Die Bewertung läuft im Hintergrund (typisch unter einer Minute, bei langen Transkripten länger), unabhängig von
  einer laufenden Transkription. Transkripte über 500 000 Zeichen werden gekürzt.

## Datenschutz und Sicherheit

- Alle Daten liegen in `data/interviews.db`, Audio-Aufnahmen in `data/audio/<interview-id>/`. Es gibt keine
  externen CDNs, Schriften oder Tracker. Aufnahmen gehen zur Transkription nur an den eingestellten Server, Notizen und
  Transkripte für die KI-Bewertung nur an den eingestellten LLM-Server – und nur, wenn jemand „Interview bewerten“
  wählt.
- Das Backup-ZIP und die tägliche DB-Sicherung enthalten die Transkripte, **nicht** die Audiodateien. Wer diese
  sichern will, muss `data/audio/` zusätzlich sichern.
- Zugang mit einem Admin-Passwort, die Sitzung liegt in einem signierten HttpOnly-Cookie (14 Tage). Ändert man
  `ADMIN_PASSWORD`, werden alle Sitzungen ungültig. Nach 10 Fehlversuchen ist die Anmeldung 15 Minuten gesperrt.
- Interviews lassen sich einzeln löschen, Notizen, Aufnahmen, Transkripte und KI-Bewertung inklusive. Das Audit-Log speichert nur IDs und Aktionen, keine Inhalte.
- Hinter dem Proxy (Profil `proxy`) den App-Port nicht zusätzlich nach außen öffnen.

## Entwicklung ohne Docker

Voraussetzungen: Python 3.12, Node 22+.

```sh
make setup     # .venv, npm ci, Playwright-Browser
make test      # pytest, Vitest, Playwright-E2E (baut das Frontend und startet einen Testserver)
```

Struktur: `backend/app/{api,models,services,importers}`, `frontend/src/{views,components,stores}`, Testdateien in
`testdata/`, Export-Referenzdateien in `testdata/referenz/` (neu erzeugen mit `REGENERATE=1 pytest tests/test_export.py`).
Schemaänderungen immer als neue Alembic-Migration in `backend/alembic/versions/`.
