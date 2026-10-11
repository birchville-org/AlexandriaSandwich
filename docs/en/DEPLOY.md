# Deploy — alex.local

## Target
- Host: `alex.local`
- SSH user: `<deploy-user>` (sudo + docker group)
- App dir: `/opt/alexandria`
- Data: `/data/{input,processing,output}`
- Container: `alexandria_worker` (`alexandria-worker:latest`)

## One-shot deploy

From the repo on the build host (amd64 image required for alex):

```bash
bash scripts/deploy_alex.sh
# env: AS_WORKER_HOST=alex.local AS_WORKER_USER=<deploy-user>
```

What it does:
1. rsync `scripts/`, `docker/`, `deploy/`, docs/ansible to `/opt/alexandria`
2. optional `.env` (mode 600)
3. `docker save | ssh docker load` of `alexandria-worker:latest`
4. `docker compose up -d` with host binds to `/data` and scripts

## Manual smoke test

```bash
ssh <deploy-user>@alex.local
docker exec -e OCR_LANG=eng alexandria_worker \
  bash /opt/alexandria/scripts/run_pipeline.sh --job smoke --limit 1 --no-mistral --lang eng
pdftotext -layout /data/output/pdf/smoke.sandwich.pdf -
```

## Notes
- Root SSH is disabled; use a non-root user with sudo privileges.
- After first `usermod -aG docker`, new login/`sg docker` may be required.
- NFS to NAS is optional (`alexandria_nfs_mount` in ansible group_vars).
- Rebuild image on hermes/dev after Dockerfile changes, then re-run deploy.

---

## Headless Typst & Font Deployment (Linux Worker)

To guarantee flawless compilation of typographical vector editions (`*.typeset_edition.pdf`) without tofu question marks (`?`) on headless Linux hosts, enforce the following configuration:

### 1. Hermetic Font Vendoring (`data/fonts`)
Typst resolves fonts against host operating system directories by default. Because headless Linux servers lack macOS-proprietary fonts (`Devanagari MT`, `Kohinoor Devanagari`, `Baskerville`), the repository vendors open-source master fonts directly in `data/fonts/`:
* `NotoSerifDevanagari-Regular.ttf` & `NotoSerifDevanagari-Bold.ttf` (Google Noto, OFL)
* `LinLibertine_R.otf`, `LinLibertine_RB.otf`, `LinLibertine_RI.otf` (Linux Libertine O)

In `scripts/build_typeset_edition.py`, the pipeline automatically appends `--font-path data/fonts`.

### 2. Mandatory Packages in Worker Container (`docker/worker/Dockerfile`)
* **APT:** `fonts-noto-extra` (in Ubuntu 24.04, Indic Devanagari fonts reside exclusively in `fonts-noto-extra`, not in `fonts-noto-core`).
* **PIP:** `pymupdf` (required for bounding-box analysis, automated layout audits, and text layer extraction).

### 3. Docker-Compose Volume Mounts (`deploy/docker-compose.alex.yml`)
To make fonts and canonical databases (`dhatupatha_canonical.json`) accessible to the container:
```yaml
volumes:
  - /data/input:/data/input
  - /data/processing:/data/processing
  - /data/output:/data/output
  - /opt/alexandria/scripts:/opt/alexandria/scripts:ro
  - /opt/alexandria/templates:/opt/alexandria/templates:ro
  - /opt/alexandria/data:/opt/alexandria/data:ro
```

---

## Web Portal Deploy — synology.local

- **Host:** `synology.local`
- **SSH user:** `<nas-user>`
- **App dir:** `/volume1/docker/alexandria`
- **Compose:** `deploy/docker-compose.synology.yml`
- **Routing:** Traefik Reverse Proxy + Authelia 2FA SSO (`alex.birchville.cc`)
- **Volumes:** Live bind mounts (`./ui:/app`, `./scripts:/app/scripts`)

Sync templates and UI code:
```bash
bash scripts/deploy_ui_synology.sh
```


