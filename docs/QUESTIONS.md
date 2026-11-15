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

## Paket 11: Audio-Aufnahme und Transkription (aus ki-prompt.md, nicht in der SPEC)

11. **Skript „importieren“:** `transcribe_interview.py` liegt als unveränderte Kopie in `backend/app/services/`,
    weil der Container nur das Repo sieht. Der Adapter setzt die Modulvariablen (`SERVER_URL`, `MODEL_NAME`,
    `API_KEY`), fängt `sys.exit` ab und leitet `print` ins Auftragsprotokoll um. Alternative wäre ein
    gemeinsames Paket für beide Projekte.
12. **Neue Tabellen** `recording` (mehrere Aufnahmen je Interview möglich, z. B. bei unterbrochener OBS-Aufnahme)
    und `setting` (Schlüssel/Wert für die Server-Konfiguration). Migration `0002`.
13. **„Ins Interview eintragen“:** Das Transkript gehört zur Aufnahme, wird im Abschluss-Bildschirm angezeigt, ist
    dort korrigierbar und steht in allen Exporten unter „Transkript“. Es wird **nicht** auf die einzelnen Fragen
    verteilt und nicht in die Gesamtnotiz kopiert. Eine Zuordnung Transkript→Frage wäre ein eigenes Paket
    (z. B. per LLM, SPEC Version 2).
14. **Abgeschlossene Interviews:** Aufnahmen und Transkripte bleiben änderbar, weil die Aufnahme meist erst nach
    dem Gespräch hochgeladen wird. Notizen bleiben schreibgeschützt.
15. **Gesprächspartner-Name** im Transkript ist ohne Angabe die interviewte Person (Feld `person`).
16. **Hintergrund-Thread statt Job-Queue:** ein Thread im App-Prozess, ein Auftrag gleichzeitig, Status in der DB.
    Reicht für einen uvicorn-Prozess; bei mehreren Workern müsste der Auftrag per DB-Sperre vergeben werden.

## Paket 12: KI-Bewertung (Auftrag aus dem Chat, SPEC Version 2 „LLM-Zusammenfassung“)

17. **Ein Ergebnis je Interview** (Tabelle `evaluation`, Migration `0003`). „Neu bewerten“ ersetzt es; schlägt ein
    neuer Lauf fehl, bleibt das vorherige Ergebnis stehen. Keine Versionshistorie.
18. **Inhalt** der Bewertung: Zusammenfassung, Kernaussagen (mit Zeitmarken), Gesamtbewertung mit Einstufung
    (sehr positiv … sehr kritisch), Abweichungen zwischen Notizen und Transkript, offene Punkte. Keine Punktzahl,
    weil der Zweck der Interviews je Gruppe verschieden ist; der Maßstab lässt sich über die Anweisung (System-Prompt)
    in den Einstellungen anpassen.
19. **Modell automatisch:** Ohne eingestelltes Modell nimmt die App das erste unter `/models` (der Server bietet genau
    eines an). Vorgabe-URL `http://localhost:8000/v1` steht im Code, damit es ohne `.env`-Eintrag läuft.
20. **Transkript wird bei Start gelesen**, nicht beim Einreihen. Läuft noch eine Transkription, weist die Oberfläche
    darauf hin, wartet aber nicht automatisch.
21. **Download** als PDF und Markdown; zusätzlich steht die Bewertung in den Interview-Exporten (MD/PDF/CSV) und damit
    auch im Backup-ZIP, jeweils mit Vermerk „KI-generiert – bitte prüfen“.
22. **Eigener Hintergrund-Thread** (gleiche `Worker`-Klasse wie die Transkription), damit eine stundenlange
    Transkription die Bewertung nicht blockiert. `TRANSCRIPTION_WORKER=0` schaltet beide ab.
23. **Markdown → PDF** mit einem kleinen eigenen Umsetzer (Überschriften, Listen, fett/kursiv), keine neue
    Abhängigkeit. Rohes HTML aus der LLM-Antwort wird immer escaped.

## Paket 13: Wiederherstellen (Auftrag aus dem Chat)

24. **Quelle:** Backup-ZIP der App (darin `interviews.db`) oder die tägliche `.db` des Dienstes `backup`. Die CSVs im
    ZIP werden nicht gelesen, sie sind nur zum Lesen ohne App gedacht.
25. **Alles oder nichts:** Es wird die ganze Datenbank ersetzt, kein Zusammenführen einzelner Interviews.
26. **Im laufenden Betrieb** über die SQLite-Backup-API in die geöffnete Datei, danach `alembic upgrade head`
    im Prozess. Kein Neustart nötig; gesperrt, solange ein Auftrag „läuft“ (kleines Zeitfenster zwischen Prüfung
    und Kopie bleibt, ein Auftrag würde dann beim Speichern seine Aufnahme nicht mehr finden oder eine falsche treffen).
27. **Rückgängig** über automatische Sicherungskopien in `<daten>/wiederherstellung/`, die letzten fünf.
28. **Audiodateien** bleiben unberührt: weder gelöscht (könnten zu einem späteren Restore passen) noch
    wiederhergestellt (nicht im Backup). Verwaiste Dateien muss man bei Bedarf von Hand löschen.
29. Navigation: Der Link „Backup“ ist jetzt die Seite „Sicherung“ mit Download, Wiederherstellen und Rückgängig.

## Paket 14: Projekte (Auftrag aus dem Chat)

30. **Zuordnung:** Gruppen haben ein Projekt (`group.project_id`, Migration `0004`). Interviews gehören über ihren
    Katalog zur Gruppe und damit zum Projekt – kein eigenes Feld, damit beides nicht auseinanderlaufen kann.
31. **Bestand:** Vorhandene Gruppen kommen bei der Migration ins „Standardprojekt“. Gruppennamen sind nur noch je
    Projekt eindeutig (sonst hätte eine Kopie andere Namen gebraucht).
32. **Kopieren** übernimmt Beschreibung, KI-Anweisung, alle Gruppen und alle Katalogversionen mit Fragen, aber keine
    Interviews, Aufnahmen oder Bewertungen. Name ohne Angabe: „<Name> (Kopie)“, dann „(Kopie 2)“ usw.
33. **Löschen** nur ohne Interviews (wie bei Gruppen und Katalogen) und nicht das letzte Projekt.
34. **Verschieben** einer Gruppe in ein anderes Projekt ist möglich (nicht ausdrücklich verlangt, aber nötig, um den
    Bestand aus dem Standardprojekt aufzuteilen); die Interviews wandern mit.
35. **KI-Anweisung je Projekt** ersetzt die allgemeine vollständig (keine Ergänzung). Leer = allgemeine Anweisung aus
    den Einstellungen. Beim Einschalten wird die allgemeine als Vorlage eingesetzt.
36. **Aktuelles Projekt** wird je Browser gemerkt (localStorage), nicht je Benutzer (es gibt nur einen Zugang).
    „Interviews“ kann per Häkchen alle Projekte zeigen.
37. **Exporte und Backup** nennen das Projekt (Zeile „Projekt“, CSV-Spalte `projekt`, Katalogordner im Backup-ZIP
    `kataloge/<projekt>/<gruppe>/`). Die CSV hat damit eine Spalte mehr.

## Paket 15: Sammelexport und KI-Analyse je Projekt (Auftrag aus dem Chat)

38. **Sammelexport** als Markdown und JSON, wahlweise „nur Transkripte“. Inhalt je Interview wie der Einzelexport
    (Markdown) bzw. strukturiert (JSON, Format `interview-leitfaden-projekt/1`). Die Projekt-Analyse ist nicht
    enthalten, sie hat einen eigenen Download.
39. **Analyse und Kurzzusammenfassung** in zwei LLM-Aufrufen: erst die Analyse über alle Unterlagen, dann die
    Kurzzusammenfassung aus der Analyse (kein zweites Mal alle Transkripte, und beide widersprechen sich nicht).
    Ein Ergebnis je Projekt, neue Analyse ersetzt es; bei Fehler bleibt das vorherige stehen.
40. **Kontextfenster** (262 144 Tokens beim jetzigen Modell, Grenze ca. 600 000 Zeichen): Kürzen in Stufen statt
    Teil-Analysen je Interview (Map-Reduce). Reicht für Projekte bis etwa 30–40 Interviews mit je einer Stunde
    Transkript, wenn die Interviews eine KI-Bewertung haben. Darüber wäre Map-Reduce ein eigenes Paket.
41. **Eigene Analyse-Anweisung** je Projekt und eine allgemeine in den Einstellungen, wie bei der Interview-Bewertung.
    Die Anweisung für die Kurzzusammenfassung ist fest.
42. **Ein Hintergrund-Thread** für alle LLM-Aufträge; Interview-Bewertungen haben Vorrang vor Projekt-Analysen.

## Paket 16: Mehrbenutzer für das Intranet (Auftrag aus dem Chat, SPEC Version 2 „Mehrbenutzer, Rollen“)

Entscheidungen des Auftraggebers: eigene Konten (kein AD/LDAP), Interviewer sehen zugeordnete Projekte und ändern
nur eigene Interviews, dürfen Projekte anlegen, Kataloge pflegen und KI-Funktionen nutzen. Kein Internet-Betrieb.
Damit ist auch die offene Frage der SPEC „Einzelnutzer oder mehrere Interviewer“ beantwortet.

43. **Übergang:** Das erste Konto `admin` entsteht beim Start aus `ADMIN_PASSWORD`, nicht in der Migration (kein
    Passwort im Migrationsverlauf). Vorhandene Interviews gehören diesem Konto. Ein Login nur mit Passwort (ohne
    Benutzername) gilt als `admin`, damit alte Skripte weiterlaufen. Danach ist `ADMIN_PASSWORD` ohne Wirkung.
44. **Projekt anlegen** macht die anlegende Person zum Mitglied, auch beim Kopieren. Projekte löschen und Mitglieder
    festlegen nur Admins. Interviewer dürfen Projekte, in denen sie Mitglied sind, umbenennen und deren
    KI-Anweisungen ändern.
45. **Nicht sichtbar = 404**, keine Berechtigung = 403. So lässt sich nicht erraten, welche Projekt-IDs es gibt.
46. **Konten löschen** nur ohne Interviews; sonst sperren. Gelöschte Konten (falls doch per DB) lassen das Interview
    stehen („Konto gelöscht“), dann darf nur noch ein Admin es ändern.
47. **Lesen der Einstellungen** (Vorgaben für Transkription, allgemeine Anweisungen) bleibt für alle erlaubt, weil
    Formulare sie als Vorgabe brauchen; API-Schlüssel werden nie ausgeliefert.
48. **Audit-Log** speichert jetzt die Benutzer-ID (ohne Fremdschlüssel, damit Löschen das Log nicht ändert).
49. **Bewusst nicht enthalten** (für Internet-Betrieb nötig): Zwei-Faktor-Anmeldung, Passwort-Vergessen per E-Mail,
    Sperre je Konto statt je IP, Passwortrichtlinien über die Mindestlänge hinaus.
