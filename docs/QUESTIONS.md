# Offene Fragen und Abweichungen

Gesammelt bei der Umsetzung der Pakete 1–10. Die Punkte unter „Annahmen“ sind umgesetzt, lassen sich aber leicht ändern.

## Offene Entscheidungen aus der SPEC (unverändert offen)

- Einzelnutzer oder mehrere Interviewer mit eigenem Login? **Umgesetzt:** ein gemeinsames Admin-Passwort (Paket 10).
- Offline-Betrieb auf dem Tablet (PWA)? **Umgesetzt ist nur:** Notizen überstehen kurze Verbindungsabbrüche und
  Reloads (Puffer im localStorage). Ein Interview ganz ohne Netz zu *starten* geht nicht.
- Primäres Exportformat? Alle drei (PDF, Markdown, CSV) sind vorhanden, Word nicht.
- Tech-Stack und Datenbank: wie empfohlen (FastAPI + Vue, SQLite).

## Annahmen und kleine Abweichungen

1. **Dockerfile:** zusätzlich `libharfbuzz-subset0` und `fonts-dejavu-core`. Ohne sie bricht WeasyPrint im
   `python:3.12-slim`-Image ab bzw. rendert PDFs ohne Schrift. `useradd -m`, damit Fontconfig einen Cache anlegen kann.
2. **docker-compose.dev.yml:** `VITE_API_URL` zeigt auf `http://app:8000` statt `localhost:8080`, weil der
   Vite-Proxy im Frontend-Container läuft und das Backend dort nur unter dem Dienstnamen erreicht.
3. **Datenmodell:** `answer.position` ergänzt (Reihenfolge der Fragen im Interview, unabhängig vom Snapshot).
   `audit_log.entität` heißt `entitaet` (ASCII-Spaltenname) und enthält `typ:id`.
4. **Katalog löschen:** nur ohne Interviews (409), sonst müssten die Interviews zuerst gelöscht werden.
   Snapshots würden zwar reichen, aber die Herkunft (Gruppe, Katalog, Version) im Export ginge verloren.
5. **Neuer Katalog mit vorhandenem Namen:** wird abgelehnt mit Hinweis auf „als neue Version speichern“.
6. **Antwort-Status:** „beantwortet“ ergibt sich aus einer nicht leeren Notiz. „Übersprungen“ und „später“ bleiben beim
   Tippen erhalten, „Weiter“ mit Notiz setzt „beantwortet“.
7. **Abgeschlossene Interviews** sind schreibgeschützt (409), bis sie wieder geöffnet werden.
8. **Abschnitte** im Editor sind zusammenhängende Läufe. Taucht ein Abschnittsname an zwei Stellen auf, erscheint er
   zweimal.
9. **Login-Sperre** zählt je Client-IP. Hinter Caddy sehen alle Anfragen gleich aus (Proxy-IP), die Sperre wirkt
   dann global. Das ist gewollt: `--proxy-headers` würde gefälschte `X-Forwarded-For`-Header zulassen, solange der
   App-Port offen ist.
10. **Antwort-Typen** (Skala, Ja/Nein, Auswahl) werden importiert und angezeigt, erfasst wird in Version 1 aber
    immer eine Freitext-Notiz (laut SPEC erst Version 2).
