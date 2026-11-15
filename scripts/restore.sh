#!/bin/sh
# Backup wiederherstellen: Backup-ZIP (scripts/backup.sh bzw. „Backup“ in der App) oder tägliche
# DB-Sicherung (backups/interviews-<datum>.db). ERSETZT ALLE DATEN; der vorherige Stand wird vorher nach
# data/wiederherstellung/ kopiert. Die App muss laufen. Aufruf im Repo-Verzeichnis: scripts/restore.sh <datei>
set -eu
cd "$(dirname "$0")/.."
if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Aufruf: scripts/restore.sh <backup.zip | interviews-<datum>.db>" >&2
  exit 1
fi
printf 'Alle Daten der App durch „%s“ ersetzen? [ja/nein] ' "$1"
read -r answer
[ "$answer" = "ja" ] || { echo "Abgebrochen."; exit 1; }
docker compose exec -T app python -m app.services.restore - < "$1"
