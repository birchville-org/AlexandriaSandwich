#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${AS_WORKER_HOST:-alex.local}"
USER="${AS_WORKER_USER:-marco}"
REMOTE="${USER}@${HOST}"
APP="/opt/alexandria"
log(){ printf '%s\n' "$*" >&2; }

log "1) rsync assets"
rsync -az "$ROOT/deploy/docker-compose.n8n.yml" "$REMOTE:$APP/docker-compose.n8n.yml"
rsync -az "$ROOT/workflows/" "$REMOTE:$APP/workflows/"
rsync -az "$ROOT/scripts/n8n_run_job.sh" "$ROOT/scripts/run_pipeline.sh" "$ROOT/scripts/preprocess.sh" \
  "$ROOT/scripts/quality_check.py" "$ROOT/scripts/assemble_sandwich.py" "$ROOT/scripts/mistral_ocr.py" \
  "$ROOT/scripts/hocr_correct.py" "$ROOT/scripts/pdf_text_correct.py" "$ROOT/scripts/sync_storage.sh" \
  "$REMOTE:$APP/scripts/"
ssh "$REMOTE" "chmod +x $APP/scripts/*.sh $APP/scripts/*.py 2>/dev/null || true; mkdir -p $APP/n8n-data"

log "2) patch docker binary path + compose up"
ssh "$REMOTE" 'set -e
APP=/opt/alexandria
DOCKER_BIN=$(command -v docker)
python3 - <<PY
from pathlib import Path
p = Path("/opt/alexandria/docker-compose.n8n.yml")
t = p.read_text()
import re, shutil
db = shutil.which("docker")
t = re.sub(r"- [^:\n]+:/usr/bin/docker:ro", f"- {db}:/usr/bin/docker:ro", t)
p.write_text(t)
print("compose docker bind ->", db)
PY
cd "$APP"
docker compose -f docker-compose.n8n.yml pull
docker compose -f docker-compose.n8n.yml up -d
docker ps --filter name=alexandria_n8n --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo -n "docker-in-n8n: "; docker exec alexandria_n8n docker version --format "{{.Client.Version}}"
echo
docker exec alexandria_n8n docker ps --filter name=alexandria_worker --format "{{.Names}} {{.Status}}"
# bridge script smoke (no full OCR if empty) 
docker exec alexandria_n8n bash -lc "test -x /opt/alexandria/scripts/n8n_run_job.sh && echo bridge_ok"
'

log "3) wait for UI http://${HOST}:5678/"
for i in $(seq 1 40); do
  code=$(curl -sS -m 2 -o /dev/null -w "%{http_code}" "http://${HOST}:5678/" || true)
  if [[ "$code" =~ ^(200|302|401|403)$ ]]; then
    log "n8n HTTP $code"
    log "Open http://${HOST}:5678/ → create owner → Import workflows/n8n_ocr_pipeline.json → Activate"
    log "Webhook: POST http://${HOST}:5678/webhook/alexandria/ocr"
    exit 0
  fi
  sleep 2
done
log "timed out waiting for UI; docker logs:"
ssh "$REMOTE" "docker logs --tail 40 alexandria_n8n" || true
exit 1
