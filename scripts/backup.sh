#!/bin/sh
# Vollsicherung (DB + CSVs aller Interviews + Kataloge im Importformat) als ZIP nach backups/.
# Ergänzt die tägliche DB-Sicherung des backup-Dienstes. Aufruf im Repo-Verzeichnis: scripts/backup.sh
set -eu
cd "$(dirname "$0")/.."
target="backups/voll-$(date +%Y-%m-%d-%H%M).zip"
docker compose exec -T app python -m app.services.backup - > "$target"
echo "Gesichert: $target"
