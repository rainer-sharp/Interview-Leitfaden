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
| Update | `scripts/update.sh` (holt den Code, sichert, baut neu, prüft die laufende Version) |
| Logs | `docker compose logs -f app` |
| Vollsicherung als ZIP | `scripts/backup.sh` oder in der App unter „Sicherung“ |
| Backup wiederherstellen | in der App unter „Sicherung“ oder `scripts/restore.sh <backup.zip \| backups/interviews-<datum>.db>` |

### Update

`scripts/update.sh` im Repo-Verzeichnis auf dem Server. Das Skript

1. holt den neuesten Stand des aktuellen Branches (`git pull --ff-only`; bricht bei lokalen Änderungen ab),
2. legt eine Vollsicherung unter `backups/` ab,
3. baut das Image neu und ersetzt den Container,
4. wartet, bis die App antwortet, und prüft, dass sie den gerade gebauten Git-Stand meldet.

Der laufende Stand steht unter `/api/health` (`version`) und unten auf der Seite „Sicherung“. Geöffnete
Browser-Tabs merken ein Update selbst (Prüfung alle 5 Minuten und beim Zurückwechseln in den Tab): Sie zeigen
oben „Neue Version … Jetzt neu laden“ und laden spätestens beim nächsten Seitenwechsel neu. Abmelden lädt die App
ebenfalls komplett neu. Optionen:
`--no-cache` (ohne Docker-Cache bauen), `--no-pull` (nur lokal neu bauen), `--no-backup`.

Wichtig: Der Server baut, was in seinem Git-Checkout liegt. Neue Funktionen kommen dort erst an, wenn sie
committet **und** gepusht sind und der Server auf dem richtigen Branch steht (`git branch`).

## Bedienung

0. **Projekt wählen** (Auswahl oben in der Navigation, verwalten unter „Projekte“). Ein Projekt fasst Gruppen mit
   ihren Katalogen und deren Interviews zusammen; Gruppen, Interviews und „Interview starten“ zeigen immer das
   aktuelle Projekt. „Kopieren“ legt ein neues Projekt mit Kopien aller Gruppen, Kataloge und Fragen an (ohne
   Interviews), z. B. für die nächste Befragungsrunde. Unter „Bearbeiten“ lässt sich je Projekt eine eigene
   Anweisung für die KI-Bewertung festlegen. Daten aus der Zeit vor den Projekten liegen im „Standardprojekt“; eine
   Gruppe lässt sich mit allen Interviews in ein anderes Projekt verschieben (Gruppe → Bearbeiten → Projekt).
   Unter Projekte → **Details**:
   - **Alle Interviews als eine Datei**: Markdown oder JSON mit Fragen, Notizen, Gesamtnotiz, KI-Bewertung und
     Transkripten aller Interviews des Projekts; wahlweise nur die Transkripte.
   - **KI-Analyse des Projekts**: Analyse über alle Interviews (Überblick, Erkenntnisse, Gemeinsamkeiten und
     Unterschiede, Bedarfe, Gesamtbewertung, Empfehlungen) plus daraus abgeleitete Kurzzusammenfassung; korrigierbar,
     Download als PDF oder Markdown. Sehr umfangreiche Projekte werden gekürzt (erst Transkripte von Interviews,
     die schon eine KI-Bewertung haben, dann übrige Transkripte); das Ergebnis vermerkt, was gekürzt wurde.
   - Eigene Anweisungen für die Bewertung einzelner Interviews und für die Projekt-Analyse.
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
  Anweisungen an das Modell (System-Prompts) für die Bewertung eines Interviews und für die Analyse eines Projekts.
  Ein Projekt kann für beides eigene Anweisungen haben. Leere Felder fallen auf
  `LLM_URL`, `LLM_MODEL`, `LLM_API_KEY` aus der `.env` und danach auf die Vorgaben zurück.
- Die Bewertung läuft im Hintergrund (typisch unter einer Minute, bei langen Transkripten länger), unabhängig von
  einer laufenden Transkription. Transkripte über 500 000 Zeichen werden gekürzt.

### Sicherung und Wiederherstellung

- **Backup:** „Sicherung“ → „Backup herunterladen“ (ZIP: Datenbank, CSV je Interview, Kataloge im Importformat)
  bzw. `scripts/backup.sh`. Zusätzlich legt der Dienst `backup` täglich `backups/interviews-<datum>.db` ab.
- **Wiederherstellen:** „Sicherung“ → Datei wählen (Backup-ZIP oder tägliche `.db`), bestätigen. Oder auf dem
  Server `scripts/restore.sh <datei>` (fragt nach, die App muss laufen). **Alle aktuellen Daten werden ersetzt.**
- Vorher wird geprüft: SQLite-Datei bzw. `interviews.db` im ZIP, Integrität, Tabellen dieser App und ein bekannter
  Datenbankstand. Ältere Backups werden danach automatisch migriert; Backups aus einer neueren App-Version werden
  abgelehnt. Während eine Transkription oder KI-Bewertung läuft, ist Wiederherstellen gesperrt.
- Der Stand vor jeder Wiederherstellung landet in `data/wiederherstellung/` (die letzten fünf) und lässt sich auf
  der Seite „Sicherung“ mit „Zurückholen“ wieder einspielen.
- Audiodateien sind nicht im Backup. Vorhandene Dateien in `data/audio/` bleiben liegen; fehlt zu einer
  wiederhergestellten Aufnahme die Datei, meldet die Seite das (das Transkript ist trotzdem da).
- Anmeldungen bleiben gültig (Passwort und Schlüssel stehen in der `.env`, nicht in der Datenbank).

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
