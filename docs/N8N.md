# n8n — AlexandriaSandwich OCR Pipeline

## Layout (production)

n8n runs **on `alex.local`** beside `alexandria_worker`:

```text
Webhook → n8n ( :5678 )
       → /opt/alexandria/scripts/n8n_run_job.sh
       → docker exec alexandria_worker run_pipeline.sh
```

## Deploy

```bash
bash scripts/deploy_n8n_alex.sh
```

UI: http://alex.local:5678/

### First-time setup
1. Open UI, create owner account.
2. **Import** `workflows/n8n_ocr_pipeline.json` (also on host: `/opt/alexandria/workflows/`).
3. Toggle workflow **Active**.
4. Production webhook: `POST http://alex.local:5678/webhook/alexandria/ocr`

## Webhook body

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

```bash
curl -sS -X POST http://alex.local:5678/webhook/alexandria/ocr \
  -H 'content-type: application/json' \
  -d '{"job":"n8n_smoke","lang":"eng","limit":1,"no_mistral":true}'
```

## Files
| Path | Role |
|------|------|
| `deploy/docker-compose.n8n.yml` | n8n compose (docker.sock + docker CLI) |
| `scripts/n8n_run_job.sh` | webhook → docker exec bridge |
| `scripts/deploy_n8n_alex.sh` | ship + start on alex.local |
| `workflows/n8n_ocr_pipeline.json` | importable flow |

## Troubleshooting
- **docker not found in n8n**: re-run deploy (binds host `/usr/bin/docker`)
- **permission denied socket**: compose uses `user: root` for n8n container
- **404 webhook**: workflow must be Active; use `/webhook/` not `/webhook-test/`
