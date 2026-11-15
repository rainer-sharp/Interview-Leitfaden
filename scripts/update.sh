#!/bin/sh
# Bringt eine laufende Installation auf den neuesten Stand:
#   Code holen (git pull) → Vollsicherung → Image neu bauen → Container ersetzen → auf „healthy“ warten
#   → prüfen, dass der Container wirklich den neuen Stand ausführt.
# Aufruf im Repo-Verzeichnis auf dem Server:
#   scripts/update.sh               normal
#   scripts/update.sh --no-cache    Image komplett ohne Docker-Cache bauen (wenn etwas „hängen“ bleibt)
#   scripts/update.sh --no-pull     nur den lokalen Stand neu bauen (ohne git pull)
#   scripts/update.sh --no-backup   ohne Sicherung vorher
set -eu
cd "$(dirname "$0")/.."

no_cache="" pull=1 backup=1
for arg in "$@"; do
  case "$arg" in
    --no-cache) no_cache="--no-cache" ;;
    --no-pull) pull=0 ;;
    --no-backup) backup=0 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unbekannte Option: $arg (siehe --help)" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nFEHLER: %s\n' "$*" >&2; exit 1; }

[ -f .env ] || fail ".env fehlt (cp .env.example .env und Werte eintragen)."
command -v git >/dev/null || fail "git ist nicht installiert."
docker compose version >/dev/null 2>&1 || fail "docker compose ist nicht verfügbar."

# ------------------------------------------------------------------ Code
branch=$(git rev-parse --abbrev-ref HEAD)
before=$(git rev-parse --short HEAD)
if [ "$pull" = 1 ]; then
  step "Code holen (Branch $branch, aktuell $before)"
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    git status --short --untracked-files=no
    fail "Lokale Änderungen im Repo. Bitte committen oder mit 'git stash' beiseitelegen, dann erneut starten."
  fi
  echo "Quelle: $(git remote get-url origin 2>/dev/null || echo 'kein origin')"
  git fetch --prune --tags
  upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) \
    || fail "Branch $branch hat keinen Upstream (git branch -u origin/$branch)."
  if [ "$(git rev-parse HEAD)" = "$(git rev-parse "$upstream")" ]; then
    echo "Bereits auf dem Stand von $upstream."
  fi
  git merge --ff-only "$upstream" || fail "Kein Fast-Forward möglich (lokale Commits?). Bitte von Hand zusammenführen."
fi
after=$(git rev-parse --short HEAD)
git log -1 --format='Stand: %h %s (%cd)' --date=format:'%d.%m.%Y %H:%M'
if [ "$branch" != "main" ]; then
  echo "Hinweis: Branch ist $branch, nicht main."
fi
if [ "$before" != "$after" ]; then
  echo "Neu seit $before:"
  git log --oneline "$before..$after" | sed 's/^/  /'
fi
# Version: Release-Tag (v1.0.0), nach weiteren Commits v1.0.0-3-g<commit>, ohne Tag nur der Commit.
version=$(git describe --tags --always 2>/dev/null || echo "$after")
[ -z "$(git status --porcelain --untracked-files=no)" ] || version="$version-geaendert"

# ------------------------------------------------------------------ Sicherung
if [ "$backup" = 1 ] && [ -n "$(docker compose ps -q --status running app 2>/dev/null)" ]; then
  step "Vollsicherung vor dem Update"
  mkdir -p backups
  scripts/backup.sh
fi

# ------------------------------------------------------------------ Bauen und starten
step "Image bauen (Version $version)"
export GIT_COMMIT="$version"
docker compose build --pull $no_cache app

step "Container ersetzen"
docker compose up -d --force-recreate --remove-orphans

step "Warten, bis die App antwortet"
health=""
i=0
while [ $i -lt 60 ]; do
  health=$(docker compose exec -T app curl -fsS http://localhost:8000/api/health 2>/dev/null || true)
  [ -n "$health" ] && break
  i=$((i + 1))
  sleep 2
done
if [ -z "$health" ]; then
  docker compose logs --tail 40 app
  fail "Die App antwortet nach 2 Minuten nicht. Logs siehe oben (häufig: Migration fehlgeschlagen, .env unvollständig)."
fi

running=$(printf '%s' "$health" | sed -n 's/.*"version" *: *"\([^"]*\)".*/\1/p')
echo "Läuft: Version ${running:-unbekannt}"
if [ "$running" != "$version" ]; then
  fail "Der Container meldet ${running:-keine Version}, erwartet war $version. Mit --no-cache erneut versuchen."
fi

# Alte, nicht mehr verwendete Images der vorherigen Builds aufräumen
docker image prune -f >/dev/null 2>&1 || true

step "Fertig: Version $version läuft. Im Browser einmal neu laden (Strg+F5)."
