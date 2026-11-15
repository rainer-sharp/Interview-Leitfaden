# Interview-Leitfaden – Installationsanleitung

Diese Anleitung führt Schritt für Schritt durch die Installation auf einem eigenen Server. Vorkenntnisse in
Programmierung sind nicht nötig. Sie sollten aber ein Terminal öffnen und Befehle eintippen (oder hineinkopieren)
können. Jeder Befehl ist erklärt.

**Inhalt**

1. [Was wird installiert?](#1-was-wird-installiert)
2. [Voraussetzungen](#2-voraussetzungen)
3. [Docker installieren](#3-docker-installieren)
4. [Programm herunterladen](#4-programm-herunterladen)
5. [Grundeinstellungen festlegen (.env)](#5-grundeinstellungen-festlegen-env)
6. [Programm starten](#6-programm-starten)
7. [Erste Anmeldung und Prüfung](#7-erste-anmeldung-und-prüfung)
8. [Transkription und KI einrichten](#8-transkription-und-ki-einrichten)
9. [Zugriff aus dem Internet mit HTTPS (optional)](#9-zugriff-aus-dem-internet-mit-https-optional)
10. [Datensicherung](#10-datensicherung)
11. [Updates einspielen](#11-updates-einspielen)
12. [Tägliche Handgriffe](#12-tägliche-handgriffe)
13. [Probleme lösen](#13-probleme-lösen)
14. [Deinstallieren](#14-deinstallieren)

---

## 1. Was wird installiert?

Der Interview-Leitfaden ist eine **Web-Anwendung**: Sie läuft auf einem Rechner im Netzwerk (dem *Server*) und wird
von beliebigen Geräten aus im **Browser** bedient – PC, Laptop oder Tablet. Auf den Arbeitsplätzen muss nichts
installiert werden.

Auf dem Server läuft das Programm in **Docker**. Docker ist eine Art „Paketbox“: Alles, was das Programm braucht
(Python, Bibliotheken, PDF-Erzeugung, Audio-Werkzeuge), steckt fertig darin. Sie installieren nur Docker selbst.

Alle Daten (Datenbank, Audio-Aufnahmen) liegen auf dem Server im Ordner `data/` des Programmverzeichnisses. Sie
verlassen den Server nur, wenn Sie Transkription oder KI-Bewertung nutzen – und dann nur zu den Servern, die Sie
selbst einstellen (siehe Abschnitt 8).

## 2. Voraussetzungen

| Was | Empfehlung |
| --- | --- |
| Server | Ein Linux-Rechner, der dauerhaft läuft: z. B. ein kleiner PC, eine virtuelle Maschine, ein NAS mit Docker-Unterstützung oder ein gemieteter Server (VPS). Empfohlen: Ubuntu 22.04/24.04 oder Debian 12. |
| Leistung | 2 CPU-Kerne, 2 GB Arbeitsspeicher. Die Transkription und KI laufen auf eigenen Servern, nicht hier. |
| Speicherplatz | 5 GB für Programm und Datenbank. Wer Audio-Aufnahmen hochlädt: zusätzlich pro Stunde Aufnahme etwa 100–700 MB. |
| Netzwerk | Der Server muss für die Arbeitsplätze erreichbar sein (gleiches Netz oder Internet). Für Transkription und KI muss er die entsprechenden Server erreichen. |
| Zugang | Ein Benutzerkonto auf dem Server mit Administratorrechten (`sudo`). |
| Programmcode | Zugang zum Git-Repository des Interview-Leitfadens (Adresse und Zugangsdaten bekommen Sie vom Betreuer des Projekts) oder eine ZIP-Datei des Programms. |

> **Windows oder Mac?** Zum Ausprobieren geht auch *Docker Desktop*. Die Hilfsskripte für Update, Sicherung und
> Wiederherstellung (`scripts/*.sh`) sind aber für Linux geschrieben. Für den Dauerbetrieb empfehlen wir einen
> Linux-Server.

**Terminal öffnen:** Melden Sie sich am Server an – direkt oder von Ihrem PC aus per SSH, z. B. unter Windows in der
Eingabeaufforderung mit `ssh benutzer@servername`. Alle folgenden Befehle tippen Sie dort ein und bestätigen mit
Enter.

## 3. Docker installieren

Prüfen Sie zuerst, ob Docker schon vorhanden ist:

```sh
docker --version
docker compose version
```

Erscheinen bei beiden Befehlen Versionsnummern (Docker 24 oder neuer, Compose 2.20 oder neuer), springen Sie zu
Abschnitt 4.

Sonst installieren Sie Docker mit dem offiziellen Installationsskript (Ubuntu/Debian):

```sh
sudo apt update
sudo apt install -y curl git
curl -fsSL https://get.docker.com | sudo sh
```

Damit Sie Docker ohne `sudo` benutzen können, nehmen Sie Ihr Benutzerkonto in die Gruppe `docker` auf und melden
sich danach **einmal ab und wieder an**:

```sh
sudo usermod -aG docker $USER
```

Kontrolle nach dem erneuten Anmelden:

```sh
docker run --rm hello-world
```

Erscheint „Hello from Docker!“, ist Docker bereit.

> **NAS (Synology, QNAP …):** Installieren Sie dort das Docker- bzw. „Container Manager“-Paket aus dem Paketzentrum
> und aktivieren Sie den SSH-Zugang. Die weiteren Schritte sind gleich.

## 4. Programm herunterladen

Legen Sie fest, wo das Programm liegen soll, z. B. im Heimatverzeichnis unter `interview`.

**Mit Git (empfohlen, weil Updates dann ein einziger Befehl sind):**

```sh
cd ~
git clone <ADRESSE-DES-REPOSITORYS> interview
cd interview
```

`<ADRESSE-DES-REPOSITORYS>` ersetzen Sie durch die Adresse, die Sie erhalten haben. Fragt Git nach Zugangsdaten
oder meldet „Host key verification failed“, wenden Sie sich an den Betreuer: Für SSH-Adressen muss auf dem Server
ein Schlüssel hinterlegt sein.

**Mit ZIP-Datei:** Kopieren Sie die ZIP-Datei auf den Server, entpacken Sie sie (`unzip interview.zip`) und wechseln
Sie in den entpackten Ordner (`cd interview`). Updates müssen Sie dann später ebenfalls von Hand einspielen.

Alle weiteren Befehle führen Sie **in diesem Ordner** aus. Mit `pwd` sehen Sie, wo Sie gerade sind; mit `ls` sollten
Sie unter anderem `docker-compose.yml`, `README.md` und den Ordner `scripts` sehen.

## 5. Grundeinstellungen festlegen (.env)

Die Grundeinstellungen stehen in einer Datei namens `.env`. Legen Sie sie aus der Vorlage an:

```sh
cp .env.example .env
```

Erzeugen Sie dann einen zufälligen Geheimschlüssel – er schützt die Anmeldung:

```sh
openssl rand -hex 32
```

Kopieren Sie die ausgegebene lange Zeichenkette. Öffnen Sie jetzt die Datei zum Bearbeiten:

```sh
nano .env
```

Ändern Sie mindestens diese Zeilen:

| Zeile | Bedeutung | Beispiel |
| --- | --- | --- |
| `SECRET_KEY=` | Der eben erzeugte Geheimschlüssel. Nie weitergeben. | `SECRET_KEY=3f9c…a71b` |
| `ADMIN_PASSWORD=` | Das Passwort für die Anmeldung in der App. Mindestens 12 Zeichen, nicht anderweitig verwenden. | `ADMIN_PASSWORD=Sommer-Regen-Kaffee-42` |
| `APP_PORT=` | Der Port, unter dem die App im Netzwerk erreichbar ist. 8080 ist üblich; ist er belegt, nehmen Sie z. B. 8180. | `APP_PORT=8080` |

Die übrigen Zeilen können Sie zunächst so lassen:

| Zeile | Bedeutung |
| --- | --- |
| `DATABASE_URL` | Ort der Datenbank im Container. Nicht ändern. |
| `BACKUP_KEEP_DAYS` | Wie viele Tage die automatischen täglichen Sicherungen aufbewahrt werden (Standard 14). |
| `DOMAIN` | Nur für den Zugriff aus dem Internet mit HTTPS (Abschnitt 9). |
| `TRANSCRIBE_URL`, `TRANSCRIBE_MODEL`, `TRANSCRIBE_API_KEY` | Vorgaben für den Transkriptions-Server. Lassen sich bequemer in der App einstellen (Abschnitt 8). |
| `MAX_AUDIO_MB` | Größte erlaubte Audiodatei in MB (Standard 4096 = 4 GB). |
| `LLM_URL`, `LLM_MODEL`, `LLM_API_KEY` | Vorgaben für den KI-Server. Ebenfalls in der App einstellbar. |

Speichern in `nano`: **Strg+O**, Enter, dann beenden mit **Strg+X**.

> **Wichtig:** Solange `SECRET_KEY` oder `ADMIN_PASSWORD` noch `bitte-aendern` lauten, startet das Programm
> absichtlich nicht. So kann es nicht versehentlich mit einem bekannten Passwort laufen.

Legen Sie zum Schluss die Ordner für Daten und Sicherungen an und geben Sie sie dem Programm frei (das Programm läuft
im Container mit der Benutzernummer 1000):

```sh
mkdir -p data backups
sudo chown 1000 data backups
```

## 6. Programm starten

```sh
docker compose up -d --build
```

Was passiert: Docker lädt die Grundbausteine aus dem Internet, baut daraus das Programm (beim ersten Mal 3–10
Minuten, je nach Leitung und Rechner) und startet es im Hintergrund. `-d` bedeutet „im Hintergrund“, `--build`
„vorher bauen“.

Prüfen Sie danach den Zustand:

```sh
docker compose ps
```

Sie sollten zwei Dienste sehen:

- `interview-leitfaden` (das Programm) – nach etwa einer halben Minute mit dem Zusatz **(healthy)**,
- einen Eintrag mit `backup` im Namen, z. B. `interview-backup-1` (die tägliche Sicherung).

Das Programm startet nach einem Neustart des Servers automatisch wieder.

## 7. Erste Anmeldung und Prüfung

1. Ermitteln Sie die Adresse des Servers im Netzwerk, z. B. mit `hostname -I` (die erste Zahlenfolge, etwa
   `192.168.1.50`).
2. Öffnen Sie an einem Arbeitsplatz den Browser und rufen Sie auf:
   `http://192.168.1.50:8080` (Ihre Adresse und Ihr `APP_PORT`).
3. Melden Sie sich mit dem `ADMIN_PASSWORD` aus der `.env` an.
4. Sie sehen die Seite **Personengruppen** mit dem Projekt **Standardprojekt** oben in der Auswahl. Die
   Installation ist damit abgeschlossen.
5. Unten auf der Seite **Sicherung** steht der **Programmstand** (eine kurze Kennung wie `633a3fb`). Diese Angabe
   hilft bei Rückfragen.

Geben Sie den Kolleginnen und Kollegen die Adresse und das Passwort weiter. Es gibt einen gemeinsamen Zugang; die
Anmeldung bleibt 14 Tage gültig. Nach 10 falschen Passworteingaben ist die Anmeldung für 15 Minuten gesperrt.

**Passwort ändern:** Neues `ADMIN_PASSWORD` in die `.env` eintragen und `docker compose up -d` ausführen. Alle
bisherigen Anmeldungen werden dabei ungültig.

## 8. Transkription und KI einrichten

Beides ist optional. Ohne diese Server funktioniert das Programm vollständig – nur die Knöpfe „Transkribieren“,
„Interview bewerten“ und „Projekt analysieren“ melden dann einen Fehler.

Benötigt werden zwei Server im Netzwerk, die eine **OpenAI-kompatible Schnittstelle** anbieten (z. B. *vLLM*):

- ein **Transkriptions-Server** (Sprache → Text), z. B. `http://192.168.101.95:8001/v1`,
- ein **KI-Server** (Sprachmodell für Bewertung und Analyse), z. B. `http://192.168.101.94:8000/v1`.

Einrichtung in der App:

1. Oben auf **Einstellungen** klicken.
2. Bereich **Transkriptions-Server**: Server-URL und Modell eintragen, API-Schlüssel nur, wenn der Server einen
   verlangt. Auf **Verbindung testen** klicken – es erscheint „Server erreichbar, Modell vorhanden.“ Darunter die
   Vorgaben für neue Transkriptionen (Modus, Name des Interviewers, Kontextbegriffe). **Speichern**.
3. Bereich **LLM-Server für die KI-Bewertung**: Server-URL eintragen. Das Feld *Modell* dürfen Sie leer lassen –
   dann nimmt das Programm automatisch das Modell, das der Server anbietet. **Verbindung testen** zeigt, welches
   Modell verwendet wird. **Speichern**.

Prüfen Sie, dass der Server die beiden Rechner erreicht. Schlägt **Verbindung testen** mit „Nicht erreichbar“ fehl,
liegt es meist an einer Firewall oder einer falschen Adresse.

Das Programm enthält bereits alles für die Audio-Verarbeitung (ffmpeg). Hinweise zur Bedienung finden Sie in der
[Bedienungsanleitung](BEDIENUNGSANLEITUNG.md).

## 9. Zugriff aus dem Internet mit HTTPS (optional)

Soll die App aus dem Internet erreichbar sein (z. B. auf einem gemieteten Server), muss die Verbindung verschlüsselt
sein. Dafür ist ein Webserver (*Caddy*) eingebaut, der automatisch ein kostenloses Zertifikat besorgt.

Voraussetzungen:

- ein Domainname (z. B. `interviews.ihre-firma.de`), dessen DNS-Eintrag auf die öffentliche Adresse des Servers zeigt,
- die Ports 80 und 443 sind am Server bzw. Router freigegeben.

Schritte:

1. In der `.env` die Zeile `DOMAIN=` auf Ihren Domainnamen setzen.
2. Starten mit:

   ```sh
   docker compose --profile proxy up -d --build
   ```

3. Nach ein bis zwei Minuten ist die App unter `https://interviews.ihre-firma.de` erreichbar.

Sorgen Sie in diesem Fall dafür, dass der unverschlüsselte `APP_PORT` (z. B. 8080) **nicht** von außen
erreichbar ist. Am einfachsten binden Sie ihn nur an den Server selbst – in der `.env`:

```sh
APP_PORT=127.0.0.1:8080
```

und danach erneut `docker compose --profile proxy up -d`. Eine Firewall wie `ufw` allein genügt **nicht**: Docker
öffnet seine Ports an ihr vorbei.

> Die Interviews enthalten personenbezogene Daten. Klären Sie vor einem Internet-Betrieb den Datenschutz
> (Auftragsverarbeitung beim Hoster, Löschfristen, Information der Befragten).

## 10. Datensicherung

Es gibt drei Arten der Sicherung:

| Art | Wann | Wo | Inhalt |
| --- | --- | --- | --- |
| **Automatisch täglich** | Jeden Tag, ohne Zutun | `backups/interviews-<datum>.db` | Die komplette Datenbank. Aufbewahrt `BACKUP_KEEP_DAYS` Tage. |
| **Vollsicherung per Klick** | Wann Sie wollen | In der App: **Sicherung → Backup herunterladen** (landet im Download-Ordner Ihres PCs) | ZIP mit Datenbank, jedem Interview als CSV und den Fragenkatalogen im Importformat. |
| **Vollsicherung per Befehl** | Wann Sie wollen, z. B. vor Änderungen | `scripts/backup.sh` → `backups/voll-<datum>.zip` | Wie oben. |

**Nicht enthalten sind die Audiodateien** (sie wären zu groß). Die Transkripte sind enthalten. Wer die Aufnahmen
aufbewahren muss, sichert zusätzlich den Ordner `data/audio/`.

**Empfehlung:** Kopieren Sie den Ordner `backups/` regelmäßig auf ein anderes Gerät (NAS, externe Festplatte,
Cloud-Speicher mit Verschlüsselung). Eine Sicherung auf demselben Server schützt nicht vor einem Festplattenschaden.

**Wiederherstellen** geht bequem in der App (**Sicherung → Backup wiederherstellen**, siehe
[Bedienungsanleitung](BEDIENUNGSANLEITUNG.md#14-sicherung-und-wiederherstellung)) oder auf dem Server:

```sh
scripts/restore.sh backups/interviews-2026-11-14.db
```

Das Skript fragt vorher nach. **Alle aktuellen Daten werden durch das Backup ersetzt.** Der Stand davor wird
automatisch unter `data/wiederherstellung/` aufgehoben und lässt sich in der App zurückholen.

## 11. Updates einspielen

Neue Versionen spielen Sie mit einem Befehl ein (nur bei Installation über Git):

```sh
cd ~/interview
scripts/update.sh
```

Das Skript

1. holt die neueste Version,
2. legt vorher eine Vollsicherung unter `backups/` an,
3. baut das Programm neu und startet es,
4. prüft, dass wirklich die neue Version läuft, und meldet am Ende „Fertig: Version … läuft“.

Die Datenbank wird beim Start automatisch auf den neuen Stand gebracht. Geöffnete Browserfenster zeigen danach
einen gelben Hinweis „Eine neue Version der App ist installiert“ – ein Klick auf **Jetzt neu laden** genügt.

Meldet das Skript „Lokale Änderungen im Repo“, wurde im Programmordner etwas verändert. Wenden Sie sich an den
Betreuer, statt die Änderungen zu löschen.

Bei Installation per ZIP: neue ZIP-Datei in einen neuen Ordner entpacken, `.env`, `data/` und `backups/` aus dem
alten Ordner hineinkopieren, im alten Ordner `docker compose down` und im neuen `docker compose up -d --build`.

## 12. Tägliche Handgriffe

| Aufgabe | Befehl (im Programmordner) |
| --- | --- |
| Zustand prüfen | `docker compose ps` |
| Protokoll ansehen (Fehlersuche) | `docker compose logs --tail 100 app` (laufend mitlesen: `-f`, beenden mit Strg+C) |
| Programm anhalten | `docker compose stop` |
| Programm wieder starten | `docker compose start` |
| Neu starten | `docker compose restart app` |
| Laufende Version | `curl -s http://localhost:8080/api/health` (Port anpassen) |
| Belegter Speicherplatz | `du -sh data backups` |

## 13. Probleme lösen

**Die Seite lässt sich im Browser nicht öffnen.**

- `docker compose ps` – läuft `interview-leitfaden` und steht dort `(healthy)`?
- Stimmt der Port in der Adresse mit `APP_PORT` überein?
- Blockiert eine Firewall den Port? Test auf dem Server: `curl -s http://localhost:8080/api/health` – kommt
  `{"status":"ok",…}` zurück, läuft das Programm, und es liegt am Netzwerk.

**Der Dienst startet nicht oder startet immer wieder neu.** Sehen Sie ins Protokoll:

```sh
docker compose logs --tail 50 app
```

| Meldung im Protokoll | Ursache und Lösung |
| --- | --- |
| `SECRET_KEY ist nicht gesetzt` / `ADMIN_PASSWORD ist nicht gesetzt` | In der `.env` steht noch `bitte-aendern` oder nichts. Abschnitt 5. |
| `unable to open database file` / `Permission denied` | Der Ordner `data` gehört nicht dem Programm: `sudo chown -R 1000 data backups`, dann `docker compose up -d`. |
| `port is already allocated` (beim Starten) | Der Port wird schon benutzt. Anderen `APP_PORT` in die `.env` eintragen. |

**Nach einem Update sehe ich die neuen Funktionen nicht.** Im Browser **Strg+Shift+R** drücken (Mac:
**Cmd+Shift+R**). Unten auf der Seite **Sicherung** muss der neue Programmstand stehen.

**„Verbindung testen“ meldet „Nicht erreichbar“.** Adresse prüfen (mit `http://` und `/v1` am Ende) und vom Server
aus testen: `curl -s http://192.168.101.94:8000/v1/models`. Antwortet das nicht, ist der KI- bzw.
Transkriptions-Server aus oder eine Firewall dazwischen.

**Der Speicher läuft voll.** Meist sind es Audiodateien (`du -sh data/audio`). Löschen Sie nicht mehr benötigte
Aufnahmen in der App (die Transkripte bleiben dabei nicht erhalten – vorher exportieren). Alte Programmversionen
räumt `docker image prune` auf.

**Passwort vergessen.** Steht in der `.env` auf dem Server (`grep ADMIN_PASSWORD .env`).

## 14. Deinstallieren

```sh
cd ~/interview
docker compose down
```

Damit ist das Programm beendet. Die Daten liegen weiterhin in `data/` und `backups/`. Erst wenn Sie sicher sind,
dass Sie nichts mehr brauchen (vorher eine Sicherung an einen anderen Ort kopieren!), löschen Sie den Ordner:

```sh
cd ~ && sudo rm -rf interview
docker image rm interview-leitfaden:latest
```
