# Deploy — alex.local

## Target
- Host: `alex.local` (192.168.1.239)
- SSH user: `marco` (sudo + docker group)
- App dir: `/opt/alexandria`
- Data: `/data/{input,processing,output}`
- Container: `alexandria_worker` (`alexandria-worker:latest`)

## One-shot deploy

From the repo on the build host (amd64 image required for alex):

```bash
bash scripts/deploy_alex.sh
# env: AS_WORKER_HOST=alex.local AS_WORKER_USER=marco
```

What it does:
1. rsync `scripts/`, `docker/`, `deploy/`, docs/ansible to `/opt/alexandria`
2. optional `.env` (mode 600)
3. `docker save | ssh docker load` of `alexandria-worker:latest`
4. `docker compose up -d` with host binds to `/data` and scripts

## Manual smoke test

```bash
ssh marco@alex.local
docker exec -e OCR_LANG=eng alexandria_worker \
  bash /opt/alexandria/scripts/run_pipeline.sh --job smoke --limit 1 --no-mistral --lang eng
pdftotext -layout /data/output/pdf/smoke.sandwich.pdf -
```

## Notes
- Root SSH is disabled; use `marco`.
- After first `usermod -aG docker`, new login/`sg docker` may be required.
- NFS to NAS is optional (`alexandria_nfs_mount` in ansible group_vars).
- Rebuild image on hermes/dev after Dockerfile changes, then re-run deploy.

---

## Web-Portal Deploy — synology.local

- **Host:** `synology.local` (192.168.1.8)
- **SSH user:** `marco`
- **App dir:** `/volume1/docker/alexandria`
- **Compose:** `deploy/docker-compose.synology.yml`
- **Anbindung:** Traefik Reverse-Proxy + Authelia 2FA SSO (`alex.birchville.cc`)
- **Volumes:** Live-Bind-Mount (`./ui:/app`, `./scripts:/app/scripts`)

Templates & Frontend synchronisieren:
```bash
bash scripts/deploy_ui_synology.sh
```

---

## Lokale GPU-Node — nyx.local:8088

- **Host:** `nyx.local` (Port 8088)
- **Dienst:** OpenAI-kompatibler Server für `Qwen2.5-VL`
- **API-Key:** **Nicht erforderlich** (100 % lokale Inferenz, 0,00 $ Fremdkosten)
- **Healthcheck:** UI prüft automatisch `http://nyx.local:8088/v1/models` auf Verfügbarkeit.
