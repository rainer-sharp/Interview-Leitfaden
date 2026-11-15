# Interview-Leitfaden – Bedienungsanleitung

Der Interview-Leitfaden führt Sie Frage für Frage durch ein Gespräch, speichert Ihre Notizen automatisch und
erstellt am Ende Exporte, Transkripte und – auf Wunsch – eine Auswertung durch eine KI.

Diese Anleitung beschreibt die Bedienung im Browser. Wie das Programm auf einem Server eingerichtet wird, steht in
der [Installationsanleitung](INSTALLATION.md).

**Inhalt**

1. [Grundbegriffe](#1-grundbegriffe)
2. [Anmelden und Aufbau der Oberfläche](#2-anmelden-und-aufbau-der-oberfläche)
3. [Projekte](#3-projekte)
4. [Personengruppen](#4-personengruppen)
5. [Fragenkataloge importieren](#5-fragenkataloge-importieren)
6. [Fragenkataloge bearbeiten](#6-fragenkataloge-bearbeiten)
7. [Ein Interview führen](#7-ein-interview-führen)
8. [Abschluss und Export eines Interviews](#8-abschluss-und-export-eines-interviews)
9. [Aufnahme und Transkript](#9-aufnahme-und-transkript)
10. [KI-Bewertung eines Interviews](#10-ki-bewertung-eines-interviews)
11. [Auswertung eines ganzen Projekts](#11-auswertung-eines-ganzen-projekts)
12. [Interviews verwalten](#12-interviews-verwalten)
13. [Einstellungen](#13-einstellungen)
14. [Sicherung und Wiederherstellung](#14-sicherung-und-wiederherstellung)
15. [Datenschutz im Alltag](#15-datenschutz-im-alltag)
16. [Häufige Fragen](#16-häufige-fragen)

---

## 1. Grundbegriffe

Die Inhalte sind in vier Ebenen geordnet:

```
Projekt               z. B. „Lieferantenbefragung 2026“
└── Personengruppe    z. B. „Einkauf“, „Lager“, „Geschäftsführung“
    └── Fragenkatalog z. B. „Leitfaden Einkauf“, Version 1, 2, …
        └── Interview z. B. „Frau Meier, Muster GmbH, 12.11.2026“
```

| Begriff | Bedeutung |
| --- | --- |
| **Projekt** | Klammer um eine Befragung. Enthält Gruppen und damit alle Interviews dieser Befragung. Kann für eine neue Runde kopiert werden. |
| **Personengruppe** | Eine Zielgruppe von Befragten. Jede Gruppe hat eigene Fragenkataloge. |
| **Fragenkatalog** | Die Liste der Fragen, gegliedert in Abschnitte. Ändert sich ein Katalog grundlegend, legt man eine neue **Version** an; bereits geführte Interviews behalten ihre Fragen. |
| **Interview** | Ein geführtes Gespräch mit einer Person: Notizen zu jeder Frage, Gesamtnotiz, optional Audio-Aufnahme, Transkript und KI-Bewertung. |
| **Transkript** | Die automatisch erstellte Abschrift einer Audio-Aufnahme, mit Zeitmarken und Sprechern. |
| **KI-Bewertung** | Eine von einem Sprachmodell erstellte Zusammenfassung und Einschätzung eines einzelnen Interviews. |
| **KI-Analyse** | Die Auswertung über alle Interviews eines Projekts, mit Kurzzusammenfassung. |

## 2. Anmelden und Aufbau der Oberfläche

Rufen Sie die Adresse auf, die Sie von Ihrer Administration erhalten haben (z. B. `http://192.168.1.50:8080`), und
geben Sie das Passwort ein. Die Anmeldung bleibt auf diesem Gerät 14 Tage gültig.

Oben auf jeder Seite steht die **Navigation**:

| Element | Funktion |
| --- | --- |
| **Interview-Leitfaden** | Zur Startseite (Personengruppen). |
| **Projektauswahl** (Auswahlfeld) | Wählt das *aktuelle Projekt*. Gruppen, Interviews und „Neues Interview“ beziehen sich immer darauf. Das Gerät merkt sich die Auswahl. |
| **Projekte** | Projekte anlegen, kopieren, auswerten. |
| **Gruppen** | Die Personengruppen des aktuellen Projekts. |
| **Interviews** | Liste der Interviews des aktuellen Projekts. |
| **Einstellungen** | Server für Transkription und KI. |
| **Sicherung** | Backup herunterladen und wiederherstellen. |
| **Neues Interview** | Startet ein Interview. |
| **Abmelden** | Meldet ab und lädt die Seite neu. |

Erscheint oben ein **gelber Balken** „Eine neue Version der App ist installiert“, klicken Sie auf **Jetzt neu
laden**. Ihre gespeicherten Notizen bleiben erhalten.

## 3. Projekte

Seite **Projekte** in der Navigation.

### Projekt anlegen

Unten im Feld **Neues Projekt** einen Namen eintragen, optional eine Beschreibung, dann **Anlegen**. Das neue
Projekt wird sofort zum aktuellen Projekt, und Sie landen bei dessen (noch leeren) Gruppen.

Alles, was vor Einführung der Projekte angelegt wurde, liegt im **Standardprojekt**.

### Knöpfe in der Projektliste

| Knopf | Wirkung |
| --- | --- |
| **Öffnen** | Macht das Projekt zum aktuellen Projekt und zeigt seine Gruppen. |
| **Details** | Öffnet die Projektseite: Sammelexport, KI-Analyse, Name, Beschreibung und KI-Anweisungen (Abschnitt 11). |
| **Kopieren** | Legt ein neues Projekt mit Kopien **aller Gruppen, Fragenkataloge (alle Versionen) und Fragen** an. **Interviews werden nicht kopiert.** Ideal für eine Folgebefragung mit denselben Fragen. Name vorschlagen lassen oder eigenen eingeben, dann **Kopie anlegen**. |
| **Löschen** | Nur sichtbar, wenn das Projekt keine Interviews hat und nicht das letzte ist. Löscht das Projekt mit allen Gruppen und Katalogen. |

### Gruppe in ein anderes Projekt verschieben

Gruppe öffnen → **Bearbeiten** → im Feld **Projekt** das Zielprojekt wählen → **Speichern**. Die Gruppe wandert mit
allen Katalogen **und Interviews** in das andere Projekt. So lassen sich die Inhalte des Standardprojekts aufteilen.

## 4. Personengruppen

Seite **Gruppen** (Startseite). Angezeigt werden die Gruppen des aktuellen Projekts.

- **Gruppe anlegen:** unten **Neue Gruppe** und optional **Beschreibung** ausfüllen, **Anlegen**. Ein Gruppenname
  darf in einem Projekt nur einmal vorkommen.
- **Gruppe öffnen:** auf die Kachel klicken. Dort sehen Sie die **Fragenkataloge** der Gruppe mit Version, Anzahl
  Fragen und Interviews.
- **Bearbeiten:** Name, Beschreibung und Projekt ändern.
- **Löschen:** nur möglich, solange die Gruppe keine Interviews hat.

In der Gruppe gibt es zwei Wege zu einem Katalog:

- **Fragenliste importieren** – aus einer Datei (Abschnitt 5),
- **Leeren Katalog anlegen** – Namen eingeben, **Anlegen**, Fragen dann von Hand eintragen (Abschnitt 6).

## 5. Fragenkataloge importieren

In der Gruppe auf **Fragenliste importieren** klicken.

### Die Datei vorbereiten

Am einfachsten in Excel oder einer Tabellenkalkulation. Die erste Zeile enthält die Spaltennamen:

| abschnitt | position | frage | hinweis | pflicht | typ |
| --- | --- | --- | --- | --- | --- |
| Einstieg | 1 | Wie sieht Ihr typischer Arbeitstag aus? | Locker beginnen | ja | text |
| Einkauf | 2 | Wie bestellen Sie heute Bauteile? | | ja | text |
| Einkauf | 3 | Wie zufrieden sind Sie mit den Lieferzeiten? | Skala 1–5 | nein | skala |

| Spalte | Pflicht? | Inhalt |
| --- | --- | --- |
| `frage` | **ja** | Der Fragetext. |
| `abschnitt` | nein | Überschrift, unter der die Frage steht (Standard „Allgemein“). |
| `position` | nein | Reihenfolge. Ohne Angabe gilt die Zeilenreihenfolge. |
| `hinweis` | nein | Hinweis für den Interviewer, wird unter der Frage angezeigt. |
| `pflicht` | nein | `ja`/`nein` – Pflichtfragen sind markiert und werden beim Abschluss angemahnt. |
| `typ` | nein | `text`, `skala`, `ja_nein` oder `auswahl`. Wird angezeigt; erfasst wird derzeit immer eine Freitext-Notiz. |

Erlaubte Formate: **CSV** (Trennzeichen Semikolon oder Komma, Zeichensatz UTF-8 oder Windows/Excel), **XLSX** (Excel)
oder **JSON**. Eine fertige Vorlage erhalten Sie über **Beispieldatei herunterladen**.

### Importieren

1. Bei **Datei (CSV, XLSX oder JSON)** die Datei auswählen.
2. Die **Vorschau** zeigt alle erkannten Fragen sowie Zeichensatz und Trennzeichen. Fehler werden mit Zeilennummer
   gelistet, z. B. eine fehlende Frage. Korrigieren Sie die Datei und wählen Sie sie erneut aus.
3. Unter **Speichern als** wählen:
   - **Neuer Katalog** – mit **Name des Katalogs**,
   - **Neue Version eines bestehenden Katalogs** – z. B. wenn sich Fragen geändert haben; alte Interviews behalten
     ihre Fragen,
   - **An bestehenden Katalog anhängen** – die Fragen kommen ans Ende.
4. Auf **… Fragen speichern** klicken. Erst jetzt wird gespeichert.

## 6. Fragenkataloge bearbeiten

In der Gruppe auf den Namen eines Katalogs klicken.

| Aktion | So geht's |
| --- | --- |
| Frage verschieben | Am Griff **⠿** ziehen oder mit **↑**/**↓** – auch in einen anderen Abschnitt. |
| Abschnitt verschieben | Pfeile neben dem Abschnittsnamen. |
| Abschnitt umbenennen | **umbenennen** neben dem Abschnittsnamen. |
| Frage ändern | **Bearbeiten** an der Frage: Text, Abschnitt, Hinweis für den Interviewer, Pflichtfrage, Typ. **Speichern**. |
| Frage hinzufügen | **Frage hinzufügen** unten. |
| Frage löschen | **Löschen** an der Frage. |
| Katalog umbenennen | **Umbenennen** oben. |

> Änderungen an einem Katalog wirken nur auf **neue** Interviews. Jedes Interview speichert beim Start eine Kopie
> seiner Fragen, damit Notizen und Fragen immer zusammenpassen.

## 7. Ein Interview führen

### Starten

Oben auf **Neues Interview** (oder in der Gruppe beim Katalog auf **Interview starten**):

| Feld | Hinweis |
| --- | --- |
| **Personengruppe** | Nur Gruppen des aktuellen Projekts mit mindestens einem Katalog mit Fragen. |
| **Fragenkatalog** | Vorgeschlagen wird die neueste Version. |
| **Interviewte Person** | Name oder – für pseudonyme Notizen – ein Kürzel. |
| **Organisation (optional)** | Firma, Abteilung o. Ä. |
| **Datum** | Vorbelegt mit heute. |

**Interview starten** öffnet den Interview-Modus.

### Der Interview-Bildschirm

- **Kopfzeile:** **⏸ Pause**, Person und Katalog, der Speicherstatus und ein Fortschrittsbalken.
- **Links** (auf schmalen Bildschirmen über **Fragenliste**): alle Fragen nach Abschnitten, mit farbigem Punkt für
  den Status. Pflichtfragen tragen ein `*`. Ein Klick springt zur Frage. Ganz unten **✓ Abschluss**.
- **Mitte:** Abschnitt, Fragennummer (z. B. 3/12), die **Frage**, ggf. **Pflicht** und der **Hinweis für den
  Interviewer**, darunter das große **Notizfeld**.

### Notizen und Speichern

Schreiben Sie einfach ins Notizfeld. Die Notiz wird gut eine Sekunde nach der letzten Eingabe **automatisch
gespeichert**. Oben steht dann **gespeichert**.

Bricht das Netz ab, steht dort **offline – wird lokal gehalten und erneut gesendet**. Schreiben Sie ruhig weiter:
Die Notizen bleiben im Browser und werden nachgeschickt, sobald die Verbindung wieder da ist. Schließen Sie das
Browserfenster in diesem Zustand nicht.

### Status einer Frage

| Status | Wie er entsteht |
| --- | --- |
| **offen** | Noch nicht bearbeitet. |
| **beantwortet** | Sobald die Notiz nicht leer ist. |
| **übersprungen** | Knopf **Überspringen**. |
| **später nochmal** | Knopf **Später nochmal** – zum Merken für Rückfragen am Ende. |

### Knöpfe und Tastenkürzel

| Knopf | Tastenkürzel | Wirkung |
| --- | --- | --- |
| **← Zurück** | `Strg+←` | Vorige Frage. |
| **Überspringen** | `Strg+S` | Frage als übersprungen markieren, weiter. |
| **Später nochmal** | – | Frage zum Wiedervorlegen markieren, weiter. |
| **Weiter →** / **Zum Abschluss →** | `Strg+Enter` | Nächste Frage bzw. Abschluss-Seite. |

Auf dem Mac gelten die Kürzel auch mit `⌘` statt `Strg`.

### Unterbrechen und fortsetzen

**⏸ Pause** führt zur Interview-Liste; alles ist gespeichert. Dort setzt **Fortsetzen** das Interview bei der
ersten offenen Frage fort.

## 8. Abschluss und Export eines Interviews

Über **✓ Abschluss** (links) oder nach der letzten Frage gelangen Sie zur Abschluss-Seite.

1. **Noch nicht beantwortet:** Liste aller offenen, übersprungenen und zurückgestellten Fragen. Fehlende
   Pflichtfragen werden hervorgehoben. Ein Klick springt zur Frage.
2. **Gesamtnotiz:** Gesamteindruck, wichtigste Erkenntnisse, nächste Schritte.
3. **Exportieren:** **PDF** (zum Ablegen und Drucken), **Markdown** (Text zum Weiterverarbeiten) oder
   **CSV (Excel)** (eine Zeile pro Frage, öffnet sich in deutschem Excel direkt richtig). Exporte enthalten auch
   Transkripte und KI-Bewertung, sofern vorhanden.
4. **Interview abschließen:** Danach sind Notizen schreibgeschützt. **Wieder öffnen und bearbeiten** hebt das auf.

Aufnahmen, Transkripte und KI-Bewertung bleiben auch bei abgeschlossenen Interviews änderbar, weil sie meist erst
nach dem Gespräch entstehen.

## 9. Aufnahme und Transkript

Bereich **Aufnahme und Transkript** auf der Abschluss-Seite. Voraussetzung ist ein eingerichteter
Transkriptions-Server (Abschnitt 13).

### Aufnahme hochladen

Bei **Aufnahme hochladen** eine Datei wählen. Geeignet sind:

- **OBS-Aufnahmen (.mkv)** mit drei Tonspuren: Mix, eigene Stimme (Spur 2), Gesprächspartner (Spur 3) – das beste
  Ergebnis, weil die Sprecher sauber getrennt sind,
- normale Audio- oder Videodateien: `.wav`, `.mp3`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.flac`, `.webm`, `.mp4`,
  `.mov`.

Ein Balken zeigt den Upload-Fortschritt. Mehrere Aufnahmen pro Interview sind möglich (z. B. wenn die Aufnahme
unterbrochen wurde).

### Transkribieren

1. Bei der Aufnahme auf **Transkribieren** klicken.
2. Einstellungen prüfen:
   - **Modus:** *Mix-Spur mit Sprechererkennung* (Standard, auch für einfache Audiodateien) oder *Spuren 2 und 3
     getrennt* (nur bei OBS-Aufnahmen mit 3 Spuren, sehr genaue Sprecherzuordnung).
   - **Name Interviewer** und **Name Gesprächspartner** – so erscheinen die Sprecher im Transkript.
   - **Kontextbegriffe** – Firmennamen, Produkte, Fachbegriffe, damit sie richtig geschrieben werden.
3. **Transkription starten.**

Die Transkription läuft auf dem Server weiter, **die Seite darf geschlossen werden**. Lange Aufnahmen brauchen
einige Minuten; ein Protokoll zeigt den Fortschritt. Es wird immer eine Aufnahme nach der anderen bearbeitet.

### Transkript nutzen

Das fertige Transkript erscheint unter der Aufnahme als Dialog mit Zeitmarken, z. B.
`**[00:01:14] Frau Meier:** Ich weiß nie, wann die Teile kommen.`

- Falsch erkannte Namen oder Wörter direkt im Feld korrigieren, dann **Korrekturen speichern**.
- **Transkript (Markdown)** lädt es einzeln herunter; **Audio** lädt die Originaldatei.
- **Neu transkribieren** startet erneut, z. B. mit anderen Kontextbegriffen.
- **Löschen** entfernt Aufnahme **und** Transkript.

## 10. KI-Bewertung eines Interviews

Bereich **KI-Bewertung** auf der Abschluss-Seite. Voraussetzung ist ein eingerichteter KI-Server.

1. Unter dem Status steht, was einfließt (Notizen, Gesamtnotiz, Transkript) und welche **Anweisung** gilt – die
   allgemeine oder die eigene des Projekts.
2. **Interview bewerten** klicken. Die Bewertung dauert meist unter einer Minute; die Seite darf geschlossen werden.
3. Das Ergebnis enthält: **Zusammenfassung**, **Kernaussagen** (mit Zeitmarken), **Gesamtbewertung** mit Einstufung
   von *sehr positiv* bis *sehr kritisch*, **Abweichungen und Lücken** (z. B. Widersprüche zwischen Notiz und
   Transkript) sowie **Offene Punkte und nächste Schritte**.
4. Text bei Bedarf korrigieren → **Korrekturen speichern**.
5. Herunterladen als **Bewertung (PDF)** oder **Bewertung (Markdown)**. Die Bewertung steht außerdem in allen
   Exporten des Interviews.

**Neu bewerten** erstellt eine neue Bewertung (z. B. nachdem das Transkript fertig ist). Schlägt das fehl, bleibt die
vorige erhalten. **Verwerfen** löscht sie.

> **Bitte immer prüfen.** Die Bewertung ist ein Vorschlag eines Sprachmodells. Sie kann Aussagen falsch zuordnen
> oder zu weit deuten. Im PDF steht deshalb der Vermerk „KI-generiert – bitte prüfen“.

## 11. Auswertung eines ganzen Projekts

**Projekte** → beim Projekt **Details**. Die Seite hat drei Bereiche.

### Alle Interviews als eine Datei

Fasst alle Interviews des Projekts in **einer** Datei zusammen – je Interview Fragen mit Notizen, Gesamtnotiz,
KI-Bewertung und Transkripte:

- **Markdown** – zum Lesen und Weitergeben, mit Inhaltsverzeichnis.
- **JSON** – strukturierte Daten zur Weiterverarbeitung, z. B. in anderen Programmen oder KI-Werkzeugen.
- Häkchen **Nur Transkripte** – die Datei enthält dann je Interview nur Kopfdaten und Transkripte.

### KI-Analyse des Projekts

1. Vor dem Start steht dort, wie viele Interviews einfließen, wie viele davon ein Transkript und wie viele eine
   KI-Bewertung haben.
2. **Projekt analysieren** klicken. Der Fortschritt wird angezeigt (Schritt 1: Analyse, Schritt 2:
   Kurzzusammenfassung). Bei vielen Interviews dauert das einige Minuten; die Seite darf geschlossen werden.
3. Ergebnis:
   - **Kurzzusammenfassung** für Entscheider: ein einleitender Absatz, 5–8 Kernpunkte, ein Satz zur
     Gesamteinschätzung.
   - **Ausführliche Analyse** (aufklappen): Überblick, Zentrale Erkenntnisse, Gemeinsamkeiten und Unterschiede,
     Bedarfe/Probleme/Chancen, Auffälligkeiten und Lücken, Gesamtbewertung, Empfehlungen und nächste Schritte.
4. Beide Texte lassen sich korrigieren → **Korrekturen speichern**.
5. Herunterladen als **Analyse (PDF)** oder **Analyse (Markdown)** – Kurzzusammenfassung vorn, Analyse dahinter.

**Tipps für gute Ergebnisse**

- Lassen Sie die einzelnen Interviews **vorher bewerten** (Abschnitt 10). Die Analyse nutzt diese Bewertungen.
  Bei sehr großen Projekten kann sie dann auf die langen Transkripte bewerteter Interviews verzichten.
- Bei sehr umfangreichen Projekten (viele Stunden Transkript) kürzt das Programm automatisch. Was gekürzt wurde,
  steht beim Ergebnis (z. B. „Transkripte nur bei Interviews ohne KI-Bewertung“).
- Eine neue Analyse ersetzt die alte. Laden Sie wichtige Stände vorher als PDF herunter.

### Projekt bearbeiten und KI-Anweisungen

Name und Beschreibung ändern Sie hier ebenfalls. Darunter folgen zwei **KI-Anweisungen**. Eine Anweisung (auch
„System-Prompt“) sagt dem Sprachmodell, wie es bewerten soll: welche Abschnitte, welcher Maßstab, welche
Schwerpunkte.

- **Anweisung für die KI-Bewertung einzelner Interviews**
- **Anweisung für die KI-Analyse des Projekts**

Ohne Häkchen gilt jeweils die **allgemeine Anweisung** aus den Einstellungen; mit **Allgemeine Anweisung ansehen**
können Sie sie lesen. Setzen Sie das Häkchen **Eigene Anweisung …**, wird die allgemeine als Vorlage eingesetzt und
Sie passen sie an, z. B.:

- „Bewerte aus Sicht des Einkaufs; Schwerpunkt Lieferzeiten und Preise.“
- „Ergänze einen Abschnitt ## Zitate mit den drei aussagekräftigsten wörtlichen Zitaten.“
- „Verwende eine Skala von 1 (sehr kritisch) bis 5 (sehr positiv).“

Behalten Sie dabei die Bitte bei, nichts zu erfinden und nur mit dem Ergebnis zu antworten. **Speichern** nicht
vergessen. Die Anweisungen gelten ab der nächsten Bewertung bzw. Analyse; beim Kopieren eines Projekts werden sie
mitkopiert.

## 12. Interviews verwalten

Seite **Interviews**: alle Interviews des aktuellen Projekts, neueste zuerst, mit Status (*läuft* /
*abgeschlossen*) und Anzahl bearbeiteter Fragen.

- **Fortsetzen** bzw. **Ansehen** öffnet das Interview.
- **Löschen** entfernt das Interview endgültig – mit Notizen, Aufnahmen, Transkripten und KI-Bewertung. Es folgt
  eine Sicherheitsabfrage.
- Häkchen **Interviews aller Projekte zeigen** – Liste über alle Projekte hinweg.

## 13. Einstellungen

Seite **Einstellungen**. Meist richtet die Administration das einmalig ein.

### Transkriptions-Server

- **Server-URL**, **Modell**, **API-Schlüssel** (nur falls verlangt).
- **Verbindung testen** prüft, ob der Server erreichbar ist und das Modell anbietet.
- **Vorgaben für neue Transkriptionen:** Modus, **Name Interviewer** (z. B. Ihr Name) und **Kontextbegriffe**, die
  bei jeder Transkription vorausgefüllt werden.

### LLM-Server für die KI-Bewertung

- **Server-URL**, **Modell** (leer = automatisch das Modell des Servers), **API-Schlüssel**.
- **Verbindung testen** zeigt, welches Modell verwendet wird.
- **Anweisung für die Interview-Bewertung** und **Anweisung für die Projekt-Analyse** – die allgemeinen Anweisungen
  für alle Projekte ohne eigene. **Vorgabe wiederherstellen** setzt sie auf den Auslieferungszustand zurück.

**Speichern** gilt jeweils für den Bereich, in dem der Knopf steht.

## 14. Sicherung und Wiederherstellung

Seite **Sicherung**.

### Backup herunterladen

**Backup herunterladen** erzeugt eine ZIP-Datei mit allen Daten: der Datenbank, jedem Interview als CSV-Datei und
allen Fragenkatalogen im Importformat. Bewahren Sie sie an einem sicheren Ort auf – sie enthält personenbezogene
Daten. **Audiodateien sind nicht enthalten**, Transkripte schon.

Zusätzlich sichert der Server die Datenbank täglich automatisch.

### Backup wiederherstellen

1. Bei **Backup-Datei (.zip oder .db)** die Datei wählen – ein heruntergeladenes Backup-ZIP oder eine tägliche
   Sicherung (`interviews-<datum>.db`) von der Administration.
2. Häkchen setzen: „Ja, alle aktuellen Daten durch … ersetzen.“
3. **Wiederherstellen.**

**Achtung: Alle aktuellen Daten werden durch das Backup ersetzt.** Das Programm prüft die Datei vorher und lehnt
beschädigte oder fremde Dateien ab. Anschließend zeigt es, wie viele Gruppen, Kataloge, Interviews und Aufnahmen
wiederhergestellt wurden, und ob Audiodateien fehlen. Klicken Sie danach auf **Zur Übersicht**.

Während eine Transkription oder KI-Auswertung läuft, ist Wiederherstellen gesperrt – kurz warten.

### Rückgängig machen

Vor jeder Wiederherstellung hebt das Programm den bisherigen Stand auf. Unter **Stände vor früheren
Wiederherstellungen** (die letzten fünf) holt **Zurückholen** einen solchen Stand zurück.

Ganz unten auf der Seite steht der **Programmstand** (Versionskennung).

## 15. Datenschutz im Alltag

- Interviews enthalten personenbezogene Daten. Verwenden Sie bei Bedarf **Kürzel** statt Namen.
- **Exporte und Backups** sind ebenso schutzbedürftig wie die App selbst. Nicht unverschlüsselt per E-Mail
  verschicken; nicht mehr benötigte Dateien löschen.
- Aufnahmen und Texte gehen **nur** an die in den Einstellungen eingetragenen Server – und nur, wenn Sie
  **Transkribieren**, **Interview bewerten** oder **Projekt analysieren** klicken.
- Informieren Sie die Befragten vor einer Aufnahme und holen Sie ihr Einverständnis ein.
- Interviews, die nicht mehr gebraucht werden, unter **Interviews** löschen. Das entfernt auch Aufnahmen,
  Transkripte und Bewertungen. Ältere Backups enthalten sie aber weiterhin.
- Am gemeinsam genutzten Gerät **Abmelden** nicht vergessen.

## 16. Häufige Fragen

**Ich sehe meine Gruppen oder Interviews nicht mehr.**
Prüfen Sie oben die **Projektauswahl** – angezeigt wird immer nur das aktuelle Projekt. Unter **Interviews** zeigt
das Häkchen **Interviews aller Projekte zeigen** alles.

**Bei „Neues Interview“ fehlt meine Gruppe.**
Die Gruppe gehört zu einem anderen Projekt, oder ihr Katalog hat noch keine Fragen.

**Ich kann eine Notiz nicht ändern.**
Das Interview ist abgeschlossen. Auf der Abschluss-Seite **Wieder öffnen und bearbeiten** klicken.

**Oben steht „offline – wird lokal gehalten …“.**
Die Verbindung zum Server ist unterbrochen. Weiterschreiben ist möglich; das Fenster nicht schließen, bis wieder
**gespeichert** erscheint.

**Die Transkription meldet einen Fehler.**
Die Fehlermeldung steht rot unter der Aufnahme, das **Protokoll** lässt sich aufklappen. Häufige Ursachen: der
Transkriptions-Server ist nicht erreichbar (Einstellungen → Verbindung testen), die Datei enthält keine Tonspur oder
der Modus *Spuren getrennt* wurde bei einer Datei ohne drei Spuren gewählt.

**Die KI-Bewertung meldet „LLM-Server nicht erreichbar“.**
Einstellungen → LLM-Server → **Verbindung testen**. Bleibt es dabei, die Administration informieren.

**Die KI-Bewertung enthält einen Fehler.**
Im Textfeld korrigieren und **Korrekturen speichern** – die korrigierte Fassung gilt dann auch für PDF und Exporte
und wird als „von Hand überarbeitet“ vermerkt. Oder die Anweisung des Projekts schärfen und **Neu bewerten**.

**Nach einem Update fehlen neue Funktionen.**
Auf den gelben Balken **Jetzt neu laden** klicken oder **Strg+Shift+R** drücken.

**Wie bekomme ich alle Interviews für eine Auswertung in Excel?**
Jedes Interview hat den Export **CSV (Excel)**. Für alle Interviews auf einmal: **Sicherung → Backup herunterladen**;
im ZIP liegt `alle-interviews.csv`.
