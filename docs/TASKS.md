# Arbeitspakete

Akzeptanzkriterien stehen in docs/SPEC.md („Arbeitspakete als Prompts“). Abweichungen: docs/QUESTIONS.md.

- [x] 1 Repo-Skelett, Dockerfile (multi-stage), compose, Makefile
- [x] 2 Datenmodell + Alembic-Migration
- [x] 3 Gruppen- und Katalog-API (CRUD)
- [x] 4 Import-Parser CSV/XLSX/JSON mit Encoding-Erkennung
- [x] 5 Import-UI mit Vorschau und Fehlerliste
- [x] 6 Katalog-Editor (Sortieren, Bearbeiten)
- [x] 7 Interview-API inkl. Snapshot und Autosave
- [x] 8 Interview-Modus UI mit Navigation und Tastenkürzeln
- [x] 9 Abschluss + Export Markdown/PDF/CSV
- [x] 10 Admin-Passwort, Backup-Endpunkt, README

## Offen

- `docker compose up --build` wurde in der Entwicklungsumgebung nicht ausgeführt (dort gibt es kein Docker).
  Geprüft sind Backend, Migration, gebautes Frontend und E2E-Tests gegen denselben Code. Erster Docker-Start: bitte
  Healthcheck kontrollieren (`docker compose ps`).
- Version 2 laut SPEC: Folgefragen, Antwort-Typen, Zeitmessung, Gruppenauswertung, Rollen, LLM-Zusammenfassung.
