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

Tastenkürzel im Interview: `Strg+Enter` weiter · `Strg+←` zurück · `Strg+S` überspringen (auf dem Mac auch mit `⌘`).

### Importformat

```csv
abschnitt;position;frage;hinweis;pflicht;typ
Einstieg;1;Wie sieht Ihr typischer Arbeitstag aus?;Locker beginnen;ja;text
```

Nur `frage` ist Pflicht. Trennzeichen `;` oder `,`, Zeichensatz UTF-8 oder Windows-1252 (Excel) werden erkannt.
`typ` ist einer von `text`, `skala`, `ja_nein`, `auswahl`. In Version 1 wird jede Antwort als Notiz erfasst.
JSON: eine Liste von Objekten mit denselben Feldern, oder `{"fragen": [...]}`.

## Datenschutz und Sicherheit

- Alle Daten liegen in `data/interviews.db`. Es gibt keine externen CDNs, Schriften oder Tracker.
- Zugang mit einem Admin-Passwort, die Sitzung liegt in einem signierten HttpOnly-Cookie (14 Tage). Ändert man
  `ADMIN_PASSWORD`, werden alle Sitzungen ungültig. Nach 10 Fehlversuchen ist die Anmeldung 15 Minuten gesperrt.
- Interviews lassen sich einzeln löschen, Notizen inklusive. Das Audit-Log speichert nur IDs und Aktionen, keine Inhalte.
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
