# Interview-Leitfaden-App – Entwicklungsplan

Nov 9, 2026 · @Rainer Sestig

## Ziel & Funktionsumfang

Eine selbst gehostete Web-App, die pro Personengruppe einen importierten Fragenkatalog bereitstellt und den Interviewer Frage für Frage durch das Gespräch führt – mit Notizen je Frage und Export am Ende. Das MVP ist in 3–4 Wochen Teilzeit realistisch.

**MVP (Version 1)**

- Personengruppen anlegen (z. B. „Kunden Einkauf“, „Lagerpersonal“, „Geschäftsführung“)
- Fragenliste je Gruppe per CSV/Excel/JSON importieren, Vorschau und Validierung vor dem Speichern
- Fragen nach Abschnitten gruppieren, Reihenfolge per Drag & Drop ändern, Pflicht/optional markieren
- Interview starten: Gruppe wählen, Interviewte Person + Datum erfassen
- Interview-Modus: eine Frage pro Bildschirm, Notizfeld, Status (beantwortet / übersprungen / später), Fortschrittsbalken
- Autosave jeder Notiz, Interview jederzeit unterbrechen und fortsetzen
- Abschluss mit Gesamtnotiz, Export als Markdown/PDF und CSV

**Später (Version 2+)**

- Bedingte Folgefragen („wenn Antwort X, dann Frage Y“)
- Antwort-Typen neben Freitext: Skala 1–5, Ja/Nein, Auswahl
- Zeitmessung pro Frage und Zeitbudget je Abschnitt
- Auswertung über mehrere Interviews einer Gruppe (alle Notizen zu Frage 7 nebeneinander)
- Mehrbenutzer mit Login, Rollen (Admin, Interviewer)
- Optional: Zusammenfassung der Notizen durch ein lokales LLM

## Architektur & Tech-Stack im Container

Empfehlung: ein einziger Container mit Python-Backend, das auch das gebaute Frontend ausliefert, und SQLite im gemounteten Volume – minimaler Betrieb, trotzdem sauber erweiterbar.

&#91;embedded content: Architektur · ein Container, ein Volume\]

Der Browser spricht nur mit dem Backend; alle Daten liegen im Volume und überleben Updates des Images.

| Schicht | Wahl | Begründung |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic | Schnell entwickelt, gute CSV/Excel-Bibliotheken (pandas/openpyxl) |
| Frontend | Vue 3 + Vite, Tailwind | Reaktiver Interview-Modus, Drag & Drop ohne Aufwand |
| Datenbank | SQLite (Datei im Volume) | Kein zweiter Container; Wechsel auf PostgreSQL per SQLAlchemy möglich |
| Export | Markdown nativ, PDF via WeasyPrint | Läuft komplett im Container, keine externen Dienste |
| Betrieb | Docker, docker compose | Passt auf NAS (Portainer) wie auf VPS |

Alternative mit weniger JavaScript: Server-gerendert mit HTMX statt Vue – einfacher, aber Autosave und Navigation werden etwas hakeliger.

## Datenmodell

Sechs Tabellen reichen für das MVP. Fragen werden beim Interview-Start als Kopie (Snapshot) übernommen, damit spätere Änderungen am Katalog alte Interviews nicht verfälschen.

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `group` | id, name, beschreibung | Personengruppe |
| `questionnaire` | id, group\_id, name, version, importiert\_am | Fragenkatalog einer Gruppe, versioniert |
| `question` | id, questionnaire\_id, abschnitt, position, text, hinweis, pflicht, typ | Einzelne Frage inkl. Interviewer-Hinweis |
| `interview` | id, questionnaire\_id, person, organisation, datum, status, gesamtnotiz | Ein durchgeführtes Interview |
| `answer` | id, interview\_id, question\_snapshot, notiz, status, geändert\_am | Notiz je Frage (beantwortet / übersprungen / später) |
| `audit_log` | id, entität, aktion, zeitpunkt | Nachvollziehbarkeit, optional im MVP |

## Importformat für Fragenlisten

CSV ist das Hauptformat, weil Fragen meist in Excel gepflegt werden; XLSX und JSON werden auf dasselbe interne Schema abgebildet. Nur die Spalte `frage` ist Pflicht, alles andere hat Standardwerte.

```csv
abschnitt;position;frage;hinweis;pflicht;typ
Einstieg;1;Wie sieht Ihr typischer Arbeitstag aus?;Locker beginnen;ja;text
Einkauf;2;Wie bestellen Sie heute Bauteile?;Nach Tools fragen;ja;text
Einkauf;3;Wie zufrieden sind Sie mit den Lieferzeiten?;;nein;skala
```

Regeln für den Import:

1. Trennzeichen (`;` oder `,`) und Zeichensatz automatisch erkennen – UTF-8 und Windows-1252 müssen beide funktionieren, da Excel-Exporte unter Windows oft 1252 liefern
2. Vorschau mit Fehlerliste anzeigen (leere Fragen, doppelte Positionen, unbekannter Typ), erst dann speichern
3. Wahl beim Import: neuen Katalog anlegen, als neue Version speichern oder an bestehenden anhängen
4. Eine Beispieldatei als Download in der App anbieten

## Ablauf & UI des Interview-Modus

Der Interview-Modus ist der Kern der App: groß, ablenkungsfrei, tablet- und laptoptauglich, voll per Tastatur bedienbar.

1. **Start:** Gruppe und Katalog wählen, Person, Organisation und Datum eingeben
2. **Fragebildschirm:** oben Abschnitt und Fortschritt (z. B. 7/24), groß die Frage, darunter klein der Interviewer-Hinweis, dann ein breites Notizfeld
3. **Navigation:** Weiter, Zurück, Überspringen, „Später nochmal“; seitliche Liste aller Fragen mit Status-Punkten zum direkten Springen
4. **Autosave:** Notiz wird nach 1–2 s Tipp-Pause gespeichert, Anzeige „gespeichert“ – kein Verlust bei Verbindungsabbruch
5. **Abschluss:** Übersicht offener/übersprungener Fragen, Gesamtnotiz, Interview abschließen und exportieren

Tastenkürzel: `Strg+Enter` weiter, `Strg+←` zurück, `Strg+S` überspringen.

## Phasen & Meilensteine

Fünf Phasen, jede endet mit etwas Lauffähigem; nach Phase 3 ist die App für echte Interviews nutzbar.

| Phase | Inhalt | Ergebnis | Aufwand (ca.) |
| --- | --- | --- | --- |
| 0 Grundgerüst | Repo, Docker-Setup, Backend/Frontend-Skelett, DB-Migrationen | `docker compose up` zeigt leere App | 1–2 Tage |
| 1 Kataloge | Gruppen-CRUD, CSV/XLSX-Import mit Vorschau, Fragen sortieren | Fragenlisten importiert und bearbeitbar | 3–4 Tage |
| 2 Interview-Modus | Start-Dialog, Fragebildschirm, Navigation, Autosave, Fortsetzen | Interview komplett durchführbar | 4–5 Tage |
| 3 Abschluss & Export | Übersicht, Gesamtnotiz, Export Markdown/PDF/CSV, Backup-Skript | MVP produktiv nutzbar | 2–3 Tage |
| 4 Ausbau | Login, Antwort-Typen, Folgefragen, Gruppenauswertung, LLM-Zusammenfassung | Version 2 | nach Bedarf |

Tests laufen ab Phase 1 mit: Import-Parser per Unit-Test (inkl. 1252-Dateien), Interview-Ablauf per End-to-End-Test (Playwright).

## Umsetzung mit KI-Coding-Agent (Claude Code / Codex)

Der Agent arbeitet am besten in kleinen, prüfbaren Paketen: je ein Paket pro Sitzung, mit klarem Ziel, festen Akzeptanzkriterien und Tests, die er selbst ausführt. Dieses Dokument ist die Spezifikation; im Repo liegt es als `docs/SPEC.md`.

**1. Repo vorbereiten (einmalig, vor dem ersten Prompt)**

- `docs/SPEC.md` = dieses Dokument (Funktionsumfang, Datenmodell, Importformat, UI-Ablauf)
- `AGENTS.md` (Codex) bzw. `CLAUDE.md` (Claude Code) mit den Regeln unten – beide Dateien dürfen denselben Inhalt haben
- `docs/TASKS.md` mit der Paketliste als Checkliste; der Agent hakt erledigte Pakete ab und notiert Abweichungen
- Beispieldateien in `testdata/`: je eine CSV in UTF-8 und in Windows-1252, eine XLSX, eine fehlerhafte CSV

**2. Inhalt von AGENTS.md / CLAUDE.md**

```markdown
# Interview-Leitfaden – Regeln für den Agenten
- Spezifikation: docs/SPEC.md ist verbindlich. Abweichungen nur nach Rückfrage.
- Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite; Frontend Vue 3 + Vite + TypeScript.
- Struktur: backend/app/{api,models,services,importers}, frontend/src/{views,components,stores}.
- Jede Schemaänderung = neue Alembic-Migration, nie bestehende ändern.
- Tests: pytest für Backend, Vitest für Frontend, Playwright für E2E. Vor jedem Commit: make test.
- Ein Paket aus docs/TASKS.md pro Sitzung; danach abhaken und kurz notieren, was offen ist.
- Keine neuen Abhängigkeiten ohne Begründung im Commit-Text.
- Alles muss im Container laufen: docker compose up --build muss grün starten.
```

**3. Arbeitspakete als Prompts**

Jedes Paket wird als eigener Prompt gegeben: „Setze Paket N aus docs/TASKS.md um, halte dich an docs/SPEC.md, schreibe zuerst die Tests.“

| Nr. | Paket | Akzeptanzkriterium (vom Agenten prüfbar) |
| --- | --- | --- |
| 1 | Repo-Skelett, Dockerfile (multi-stage), compose, Makefile | `docker compose up --build` startet, `/api/health` liefert 200 |
| 2 | Datenmodell + Alembic-Migration | Migration läuft auf leerer DB, Model-Tests grün |
| 3 | Gruppen- und Katalog-API (CRUD) | pytest-Tests für alle Endpunkte grün |
| 4 | Import-Parser CSV/XLSX/JSON mit Encoding-Erkennung | Alle Dateien in `testdata/` korrekt bzw. mit erwarteten Fehlern geparst |
| 5 | Import-UI mit Vorschau und Fehlerliste | E2E-Test: Datei hochladen → Vorschau → speichern |
| 6 | Katalog-Editor (Sortieren, Bearbeiten) | E2E-Test: Frage verschieben, Reihenfolge bleibt nach Reload |
| 7 | Interview-API inkl. Snapshot und Autosave | Notiz-Update idempotent, Snapshot unverändert nach Katalogänderung |
| 8 | Interview-Modus UI mit Navigation und Tastenkürzeln | E2E-Test: komplettes Interview durchklicken, Abbruch und Fortsetzen |
| 9 | Abschluss + Export Markdown/PDF/CSV | Export-Dateien gegen Referenzdateien geprüft |
| 10 | Admin-Passwort, Backup-Endpunkt, README | Ohne Login 401; Backup-ZIP enthält DB und CSVs |

**4. Arbeitsweise**

- Pakete 1–4 kann der Agent weitgehend autonom abarbeiten; ab Paket 5 nach jedem Paket kurz selbst im Browser prüfen
- Pro Paket ein Git-Branch oder Commit, damit sich Fehlversuche leicht zurückdrehen lassen
- Bei UI-Paketen eine grobe Skizze oder einen Screenshot als Referenz in den Prompt geben
- Unklarheiten nicht raten lassen: Agent soll Fragen in `docs/QUESTIONS.md` sammeln statt Annahmen zu treffen

## Deployment, Backup, Sicherheit/Datenschutz

Docker Compose mit drei Diensten: die App, ein Backup-Dienst für tägliche DB-Sicherungen und optional Caddy als HTTPS-Proxy (Profil `proxy`). Alle Einstellungen kommen aus einer `.env`; das Setup läuft auf NAS (Portainer) und VPS gleichermaßen.

**Dateistruktur im Repo-Root**

```
.
├── Dockerfile
├── docker-compose.yml        # Betrieb (App + Backup, optional Proxy)
├── docker-compose.dev.yml    # Entwicklung mit Hot-Reload
├── .env.example              # Vorlage, als .env kopieren
├── Caddyfile                 # nur für Profil "proxy"
├── backend/
├── frontend/
├── data/                     # SQLite-DB (wird erzeugt)
└── backups/                  # tägliche DB-Sicherungen (wird erzeugt)
```

**Dockerfile (multi-stage)**

```dockerfile
# Stage 1: Frontend bauen
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Laufzeit
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /build/dist ./static
RUN useradd -u 1000 app && mkdir -p /app/data && chown app /app/data
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

**docker-compose.yml**

```yaml
services:
  app:
    build: .
    image: interview-leitfaden:latest
    container_name: interview-leitfaden
    env_file: .env
    ports:
      - "${APP_PORT:-8080}:8000"
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  backup:
    image: alpine:3.20
    volumes:
      - ./data:/data:ro
      - ./backups:/backups
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache sqlite >/dev/null
        while true; do
          sqlite3 /data/interviews.db ".backup /backups/interviews-$$(date +%F).db"
          find /backups -name 'interviews-*.db' -mtime +${BACKUP_KEEP_DAYS:-14} -delete
          sleep 86400
        done
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    profiles: ["proxy"]
    environment:
      DOMAIN: ${DOMAIN}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    depends_on:
      - app
    restart: unless-stopped

volumes:
  caddy_data:
```

**Caddyfile** (automatisches HTTPS per Let's Encrypt)

```
{$DOMAIN} {
    reverse_proxy app:8000
}
```

**.env.example**

```
APP_PORT=8080
SECRET_KEY=bitte-aendern
ADMIN_PASSWORD=bitte-aendern
DATABASE_URL=sqlite:////app/data/interviews.db
BACKUP_KEEP_DAYS=14
DOMAIN=interviews.example.de
```

**docker-compose.dev.yml** (Hot-Reload für Backend und Frontend)

```yaml
services:
  app:
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes:
      - ./backend:/app
      - ./data:/app/data

  frontend:
    image: node:22-alpine
    working_dir: /app
    command: sh -c "npm ci && npm run dev -- --host 0.0.0.0"
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    environment:
      VITE_API_URL: http://localhost:8080
```

**Befehle**

| Zweck | Befehl |
| --- | --- |
| Erststart | `cp .env.example .env` → Werte setzen → `docker compose up -d --build` |
| Mit HTTPS-Proxy (VPS) | `docker compose --profile proxy up -d --build` |
| Entwicklung | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` |
| Update | `git pull && docker compose up -d --build` |
| Logs | `docker compose logs -f app` |
| Backup wiederherstellen | App stoppen, Datei aus `backups/` nach `data/interviews.db` kopieren, starten |

Hinweise zum Betrieb:

- **Rechte:** der Container läuft als UID 1000 – `data/` und `backups/` auf dem Host müssen für diese UID beschreibbar sein (`chown 1000 data backups`)
- **Portainer/NAS:** die Compose-Datei als Stack einfügen; Bind-Mounts dann auf absolute Pfade des NAS umstellen
- **Zugriff:** mit Profil `proxy` den App-Port nicht zusätzlich nach außen freigeben (Firewall) – oder Zugriff nur per VPN
- **Datenschutz:** Notizen sind personenbezogen – Löschfunktion je Interview, optionale Pseudonymisierung (Person = Kürzel), keine externen CDNs oder Tracker
- **Für den Agenten:** Paket 1 legt genau diese Dateien an; Akzeptanzkriterium ist ein grüner Healthcheck nach `docker compose up -d --build`

## Offene Entscheidungen

- [ ] Einzelnutzer oder von Anfang an mehrere Interviewer mit eigenem Login?
- [ ] Tech-Stack bestätigen: Python/FastAPI + Vue oder lieber ASP.NET Core?
- [ ] SQLite reicht – oder gleich PostgreSQL, z. B. zur Anbindung an bestehende Auswertungen?
- [ ] Werden Interviews auch offline geführt (Tablet ohne Netz)? Dann PWA mit lokalem Zwischenspeicher einplanen
- [ ] Welches Exportformat wird primär weiterverarbeitet: PDF zum Ablegen, CSV/Excel zum Auswerten oder Word?
