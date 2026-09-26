#!/usr/bin/env bash
# Deploy AlexandriaSandwich UI to alex.local
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="marco@alex.local"
APP="/opt/alexandria"

echo "1) rsync UI + scripts"
rsync -az "$ROOT/ui/" "$REMOTE:$APP/ui/"
rsync -az "$ROOT/scripts/" "$REMOTE:$APP/scripts/"
rsync -az "$ROOT/deploy/docker-compose.ui.yml" "$REMOTE:$APP/deploy/"

echo "2) build + start on alex.local (context = project root for scripts/ access)"
ssh "$REMOTE" "cd $APP && docker compose -f deploy/docker-compose.ui.yml up -d --build"

echo "3) verify"
sleep 3
ssh "$REMOTE" "docker ps --filter name=alexandria_ui --format '{{.Names}} {{.Status}}'"
echo "UI: http://alex.local:8080/"
