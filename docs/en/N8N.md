# n8n — Workflow Orchestration for AlexandriaSandwich

## 1. Production Architecture & Layout

The n8n instance runs on compute node `alex.local` alongside the `alexandria_worker` container:

```text
Webhook → n8n ( Port 5678 )
       → /opt/alexandria/scripts/n8n_run_job.sh
       → docker exec alexandria_worker run_pipeline.sh
```

- **Trigger:** Webhook requests are received and validated by n8n.
- **Execution:** Via the host Docker socket, n8n invokes the job runner directly inside the isolated `alexandria_worker` container.
- **Response:** Upon completion, the webhook synchronously returns the structured JSON execution report containing confidence scores and artifact paths.

---

## 2. Deployment

Deployment to `alex.local` is fully automated via script:

```bash
bash scripts/deploy_n8n_alex.sh
```

Web UI: [http://alex.local:5678/](http://alex.local:5678/)

### Initial Setup
1. Open the web UI and create the owner account.
2. Import the workflow: `workflows/n8n_ocr_pipeline.json` (also available on host at `/opt/alexandria/workflows/`).
3. Toggle the workflow to **Active**.
4. The production webhook is then live at: `POST http://alex.local:5678/webhook/alexandria/ocr`

---

## 3. Webhook Interface

### Parameters (JSON Body)

```json
{
  "job": "book-001",
  "pull": false,
  "push": false,
  "lang": "deu+eng",
  "threshold": 85,
  "limit": 0,
  "no_mistral": false
}
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `job` | String | *Required* | Unique name of the book job (directory in `/data/input/<job>/`) |
| `pull` | Boolean | `false` | Pull scans from NAS via rsync before processing |
| `push` | Boolean | `false` | Synchronize generated artifacts back to NAS upon completion |
| `lang` | String | `deu+eng` | Tesseract language models for local OCR |
| `threshold` | Integer | `85` | Quality Gate threshold score (in %) |
| `limit` | Integer | `0` | Page processing limit (`0` = process all pages) |
| `no_mistral` | Boolean | `false` | Explicitly disable cloud AI fallback |

### Smoke Test Call

```bash
curl -sS -X POST http://alex.local:5678/webhook/alexandria/ocr \
  -H 'content-type: application/json' \
  -d '{"job":"n8n_smoke","lang":"eng","limit":1,"no_mistral":true}'
```

---

## 4. Key Files

| Path | Purpose |
|---|---|
| `deploy/docker-compose.n8n.yml` | Container definition (Docker socket and CLI bindings) |
| `scripts/n8n_run_job.sh` | Bridge script connecting webhook to `docker exec` |
| `scripts/deploy_n8n_alex.sh` | Automated deployment script for `alex.local` |
| `workflows/n8n_ocr_pipeline.json` | Importable production workflow definition |

---

## 5. Operations & Diagnostics

The n8n instance is managed via `docker compose`. In routine operations, no manual intervention is required.

### Container Status & Logs

```bash
# Check service status on alex.local
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml ps"

# Stream live pipeline logs
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml logs -f n8n"
```

### Restart Service

```bash
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml restart n8n"
```
