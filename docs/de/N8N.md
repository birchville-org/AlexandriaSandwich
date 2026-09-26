# n8n — Workflow-Orchestrierung für AlexandriaSandwich

## 1. Architektur & Topologie (Produktion)

Die n8n-Instanz läuft auf dem Compute-Knoten `alex.local` parallel zum Container `alexandria_worker`:

```text
Webhook → n8n ( Port 5678 )
       → /opt/alexandria/scripts/n8n_run_job.sh
       → docker exec alexandria_worker run_pipeline.sh
```

- **Trigger:** Webhook-Anfragen werden von n8n entgegengenommen und validiert.
- **Ausführung:** Über den Host-Docker-Socket startet n8n das Verarbeitungs-Skript direkt im isolierten `alexandria_worker`-Container.
- **Rückmeldung:** Nach Abschluss des Jobs liefert der Webhook den JSON-Verarbeitungsbericht mit Konfidenzwerten und Artefaktpfaden synchron zurück.

---

## 2. Bereitstellung (Deployment)

Das Deployment auf `alex.local` erfolgt vollautomatisiert per Skript:

```bash
bash scripts/deploy_n8n_alex.sh
```

Weboberfläche: [http://alex.local:5678/](http://alex.local:5678/)

### Ersteinrichtung
1. Weboberfläche öffnen und Benutzerkonto anlegen (Owner Account).
2. Workflow importieren: `workflows/n8n_ocr_pipeline.json` (liegt auf dem Host unter `/opt/alexandria/workflows/`).
3. Workflow oben rechts auf **Active** schalten.
4. Der Produktions-Webhook ist danach erreichbar unter: `POST http://alex.local:5678/webhook/alexandria/ocr`

---

## 3. Webhook-Schnittstelle

### Parameter (JSON-Body)

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

| Parameter | Typ | Standard | Beschreibung |
|---|---|---|---|
| `job` | String | *Pflicht* | Eindeutiger Name des Buch-Jobs (Verzeichnis unter `/data/input/<job>/`) |
| `pull` | Boolean | `false` | Vor der Ausführung Scans via rsync vom NAS abholen |
| `push` | Boolean | `false` | Nach Fertigstellung Ergebnisse zum NAS synchronisieren |
| `lang` | String | `deu+eng` | Tesseract-Sprachmodelle für lokale OCR |
| `threshold` | Integer | `85` | Qualitäts-Schwellenwert für das Quality Gate (in %) |
| `limit` | Integer | `0` | Maximale Seitenanzahl (`0` = alle Seiten verarbeiten) |
| `no_mistral` | Boolean | `false` | KI-Fallback erzwingend deaktivieren |

### Testaufruf (Smoke Test)

```bash
curl -sS -X POST http://alex.local:5678/webhook/alexandria/ocr \
  -H 'content-type: application/json' \
  -d '{"job":"n8n_smoke","lang":"eng","limit":1,"no_mistral":true}'
```

---

## 4. Relevante Dateien

| Pfad | Funktion |
|---|---|
| `deploy/docker-compose.n8n.yml` | Container-Definition (Docker-Socket & CLI-Einbindung) |
| `scripts/n8n_run_job.sh` | Brückenskript zwischen Webhook und `docker exec` |
| `scripts/deploy_n8n_alex.sh` | Automatisiertes Deployment auf `alex.local` |
| `workflows/n8n_ocr_pipeline.json` | Importierbarer n8n-Workflow |

---

## 5. Betrieb & Diagnose

Die n8n-Instanz wird über `docker compose` verwaltet. Im Regelbetrieb sind keine manuellen Eingriffe erforderlich.

### Container-Status & Logs

```bash
# Status der n8n-Instanz auf alex.local prüfen
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml ps"

# Live-Logs der Pipeline einsehen
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml logs -f n8n"
```

### Neustart der Instanz

```bash
ssh marco@alex.local "docker compose -f /opt/alexandria/deploy/docker-compose.n8n.yml restart n8n"
```
