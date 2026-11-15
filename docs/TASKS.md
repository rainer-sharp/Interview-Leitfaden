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
- [x] 11 Audio-Aufnahme je Interview, Transkription über transcribe_interview.py, Server-Einstellungen (ki-prompt.md)
- [x] 12 KI-Bewertung je Interview (Zusammenfassung inkl. Transkript) per LLM, Download PDF/Markdown, LLM-Einstellungen
- [x] 13 Restore: Backup-ZIP oder tägliche .db in der App bzw. per scripts/restore.sh, mit Sicherungskopie und Rückgängig
- [x] 14 Projekte: Gruppen und Interviews je Projekt, Projekt kopieren (mit Gruppen/Katalogen), KI-Anweisung je Projekt

## Offen

- `docker compose up --build` wurde in der Entwicklungsumgebung nicht ausgeführt (dort gibt es kein Docker).
  Geprüft sind Backend, Migration, gebautes Frontend und E2E-Tests gegen denselben Code. Erster Docker-Start: bitte
  Healthcheck kontrollieren (`docker compose ps`).
- Paket 11: Echte Transkription nur gegen den Server geprüft (`/models` erreichbar, Modell vorhanden), nicht mit
  einer echten Aufnahme – in der Entwicklungsumgebung fehlt ffmpeg. Die E2E-Tests (`e2e/recordings.spec.ts`) liefen
  dort nicht, weil Chromium Systembibliotheken fehlen (`libatk-1.0`); Backend-Tests und Live-Test mit Worker grün.
  Bitte im Container eine kurze OBS-Aufnahme transkribieren.
- Paket 11: Audiodateien sind nicht im Backup-ZIP (Größe). Kein Abbrechen laufender Transkriptionen (die Anfrage an
  den Server lässt sich nicht unterbrechen); Löschen der Aufnahme verwirft das Ergebnis.
- Paket 12: Live gegen 192.168.101.94:8000 geprüft (Modell automatisch erkannt, ~1 min, PDF/MD-Download). E2E
  (`e2e/evaluation.spec.ts`) lief hier aus demselben Grund wie in Paket 11 nicht (libatk fehlt). Kein Abbrechen der
  laufenden LLM-Anfrage; „Abbrechen“ verwirft nur das Ergebnis.
- Paket 13: `scripts/restore.sh` nur ohne Docker geprüft (Python-Pfad `-` über stdin ist derselbe Code wie die CLI,
  die per Test läuft). E2E (`e2e/backup.spec.ts`) lief hier nicht (libatk fehlt). Restore gegen laufenden uvicorn
  live geprüft.
- Paket 13: `scripts/update.sh` (Update mit Sicherung und Versionsprüfung) nur mit einer docker-Attrappe getestet,
  nicht gegen echtes Docker.
- Update-Hinweis im Browser (`e2e/version.spec.ts`) nur per Vitest geprüft, E2E lief hier nicht (libatk fehlt).
- Paket 14: E2E (`e2e/projects.spec.ts`) lief hier nicht (libatk fehlt). Migration 0004 mit vorhandenen Gruppen
  sowie Downgrade geprüft. Vor dem Update auf dem Server: Backup (macht `scripts/update.sh` automatisch).
- Version 2 laut SPEC: Folgefragen, Antwort-Typen, Zeitmessung, Gruppenauswertung, Rollen. (LLM-Zusammenfassung je
  Interview: Paket 12; über mehrere Interviews einer Gruppe noch offen.)
