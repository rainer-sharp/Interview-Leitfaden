# Interview-Leitfaden – Regeln für den Agenten
- Spezifikation: docs/SPEC.md ist verbindlich. Abweichungen nur nach Rückfrage.
- Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite; Frontend Vue 3 + Vite + TypeScript.
- Struktur: backend/app/{api,models,services,importers}, frontend/src/{views,components,stores}.
- Jede Schemaänderung = neue Alembic-Migration, nie bestehende ändern.
- Tests: pytest für Backend, Vitest für Frontend, Playwright für E2E. Vor jedem Commit: make test.
- Ein Paket aus docs/TASKS.md pro Sitzung; danach abhaken und kurz notieren, was offen ist.
- Keine neuen Abhängigkeiten ohne Begründung im Commit-Text.
- Alles muss im Container laufen: docker compose up --build muss grün starten.
