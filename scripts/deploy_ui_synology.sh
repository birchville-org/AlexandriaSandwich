#!/usr/bin/env bash
# Deploy AlexandriaSandwich UI to synology.local
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${AS_SYNOLOGY_HOST:-marco@synology.local}"
APP="/volume1/docker/alexandria"

echo "1) Sync templates, static & main.py to synology.local ($APP/ui/)"
tar -C "$ROOT/ui" -cf - templates/ static/ main.py | ssh "$REMOTE" "tar -C $APP/ui -xf -"

echo "2) Sync scripts to synology.local ($APP/scripts/)"
tar -C "$ROOT" -cf - scripts/ | ssh "$REMOTE" "tar -C $APP -xf -"

echo "UI updated successfully on synology.local (bind-mount live update)."
