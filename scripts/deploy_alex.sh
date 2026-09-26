#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${AS_WORKER_HOST:-alex.local}"
USER="${AS_WORKER_USER:-marco}"
REMOTE="${USER}@${HOST}"
REMOTE_APP="/opt/alexandria"
IMAGE="${IMAGE:-alexandria-worker:latest}"
log(){ printf '%s\n' "$*" >&2; }
log "1) rsync code"
rsync -az --delete \
  --exclude '.git/' \
  --exclude 'data/input/' \
  --exclude 'data/processing/' \
  --exclude 'data/output/' \
  --exclude '__pycache__/' \
  --exclude '.env' \
  "$ROOT/scripts" "$ROOT/docker" "$ROOT/deploy" "$ROOT/docs" \
  "$ROOT/templates" "$ROOT/ansible" "$ROOT/README.md" \
  "$REMOTE:${REMOTE_APP}/"
ssh "$REMOTE" "cp -f ${REMOTE_APP}/deploy/docker-compose.alex.yml ${REMOTE_APP}/docker-compose.yml && mkdir -p ${REMOTE_APP}/scripts"
# scripts is nested after rsync of scripts dir: /opt/alexandria/scripts
if [[ -f "$ROOT/.env" ]]; then
  log "2) .env"
  rsync -az "$ROOT/.env" "$REMOTE:${REMOTE_APP}/.env"
  ssh "$REMOTE" "chmod 600 ${REMOTE_APP}/.env"
fi
log "3) data dirs"
ssh "$REMOTE" "mkdir -p /data/input /data/processing /data/output"
log "4) build worker on alex.local"
ssh "$REMOTE" "docker build -t ${IMAGE} ${REMOTE_APP}/docker/worker"
log "5) compose up"
ssh "$REMOTE" "cd ${REMOTE_APP} && docker compose up -d"
ssh "$REMOTE" "docker ps --filter name=alexandria_worker --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
log DONE
