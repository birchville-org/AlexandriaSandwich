# Deploy — alex.local

## Target
- Host: `alex.local` (alex.local)
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
ssh <deploy-user>@alex.local
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

## Headless Typst- & Font-Deployment (Linux Worker)

Für die fehlerfreie Kompilierung der typografischen Vektor-Neueditionen (`*.typeset_edition.pdf`) ohne Tofu-Zeichen (`?`) auf Headless-Linux-Hosts gilt folgende Konfiguration:

### 1. Hermetisches Font-Vendoring (`data/fonts`)
Typst sucht Schriften standardmäßig in Betriebssystem-Verzeichnissen. Da Linux-Server die proprietären macOS-Schriften (`Devanagari MT`, `Kohinoor Devanagari`, `Baskerville`) nicht besitzen, führt das Repository kanonische Open-Source-Schriften direkt unter `data/fonts/` mit:
* `NotoSerifDevanagari-Regular.ttf` & `NotoSerifDevanagari-Bold.ttf` (Google Noto, OFL)
* `LinLibertine_R.otf`, `LinLibertine_RB.otf`, `LinLibertine_RI.otf` (Linux Libertine O)

In `scripts/build_typeset_edition.py` übergibt die Pipeline automatisch `--font-path data/fonts`.

### 2. Erforderliche Pakete im Worker-Container (`docker/worker/Dockerfile`)
* **APT:** `fonts-noto-extra` (in Ubuntu 24.04 liegen die indischen Devanāgarī-Schriften nicht im Basispaket `fonts-noto-core`, sondern zwingend in `fonts-noto-extra`).
* **PIP:** `pymupdf` (wird für Bounding-Box-Messungen, Layout-Audits und Textlayer-Extraktionen benötigt).

### 3. Docker-Compose Volume-Mounts (`deploy/docker-compose.alex.yml`)
Damit Schriften und kanonische Datenbanken (`dhatupatha_canonical.json`) dem Container zur Verfügung stehen:
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

## Web-Portal Deploy — synology.local

- **Host:** `synology.local` (synology.local)
- **SSH user:** `marco`
- **App dir:** `/volume1/docker/alexandria`
- **Compose:** `deploy/docker-compose.synology.yml`
- **Anbindung:** Traefik Reverse-Proxy + Authelia 2FA SSO (`alex.birchville.cc`)
- **Volumes:** Live-Bind-Mount (`./ui:/app`, `./scripts:/app/scripts`)

Templates & Frontend synchronisieren:
```bash
bash scripts/deploy_ui_synology.sh
```


