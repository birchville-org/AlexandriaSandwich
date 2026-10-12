status: complete
milestone: 4
milestone_name: "Evolutionäre Engine-Härtung & Job-Zentriertes Layout (M4)"
completed_phases: 6
completed_plans: 20
total_plans: 20
percent: 100.0
current_focus: "Milestone 4 abgeschlossen; Bereit für Backlog / nächste Buchkorpora"
last_updated: "2026-10-12"
recent_activity:
  - "2026-10-12 | COMPLETE | Plan 06-03: Automatisierte Golden-Master-Regressionssuite (scripts/test_golden_regression.sh)"
  - "2026-10-12 | COMPLETE | Plan 06-02: Deklarative Dokument-Profile (job.config.json & schemas/job.config.schema.json)"
  - "2026-10-12 | COMPLETE | Plan 06-01: Pipeline, Tools & UI auf job-zentriertes Layout (data/output/<job>/) umgestellt"
  - "2026-10-12 | COMPLETE | Bestandsdatenbereinigung in data/input/<job>/ und data/output/<job>/"
  - "2026-10-12 | ARCHITECTURE | Architekturprinzip der Evolutionären Maschinerie in ARCHITECTURE.md verankert"
  - "2026-09-26 | COMPLETE | Plan 05-04 Web UI & Pipeline Automation Integration tested & verified"
  - "2026-09-26 | COMPLETE | Plan 05-03 Typst Typesetting Engine (scripts/render_digital_pdf.py & templates/book.typ) tested & verified"
  - "2026-09-26 | COMPLETE | Plan 05-02 Generic TEI-P5 XML Exporter (scripts/export_tei.py) tested & verified"
  - "2026-09-26 | COMPLETE | Plan 05-01 Text Consolidation (scripts/consolidate_book.py) tested & verified"
  - "2026-09-26 | PLAN | Structured Phase 5 into 4 plans covering TEI-P5 XML & Typst Digital PDF"
  - "2026-07-21 | COMPLETE | Plan 04-02 Path B Editor — /edit, /preview, /correct live on alex.local"
  - "2026-07-21 | COMPLETE | Plan 04-01 Web UI dashboard"
  - "2026-07-20 | COMPLETE | M1 E2E + all plans (11/11)"
---

# Project State: AlexandriaSandwich

## Production
- **alex.local** workers:
  - `alexandria_worker` — OCR pipeline (Tesseract + Mistral fallback)
  - `alexandria_n8n` — n8n webhook orchestration (port 5678)
  - `alexandria_ui` — Web UI + Path B Editor (port 8080)
- SSH: `<deploy-user>@alex.local`
- Compose: `/opt/alexandria/docker-compose*.yml`
- Data: `/data/{input,processing,output}`
- Smoke: `alex_smoke` conf~94%, searchable PDF OK

## Milestones
- **M1 (Core OCR & Sandwich Assembly):** 11/11 plans — DONE
- **M2 (Web UI & Path B Editor):** 2/2 plans — DONE
- **M3 (Multi-Format Digital Outputs):** 4/4 plans — DONE
  - Plan 05-01: Text-Konsolidierung & Buchstrukturierung (`scripts/consolidate_book.py`) — DONE
  - Plan 05-02: Generischer TEI-P5 XML Exporter (`scripts/export_tei.py`) — DONE
  - Plan 05-03: Typst Typesetting Engine & CLI-Renderer (`scripts/render_digital_pdf.py`) — DONE
  - Plan 05-04: Web UI Integration & End-to-End Pipeline — DONE
- **M4 (Evolutionary Engine & Job-Centric Layout):** 3/3 plans — DONE
  - Plan 06-01: Pipeline & UI auf job-zentriertes Layout (`data/output/<job>/`) umstellen — DONE
  - Plan 06-02: Deklarative Dokument-Profile (`job.config.json`) — DONE
  - Plan 06-03: Golden-Master Regressions-Gate (`test_golden_regression.sh`) — DONE

## Next (Backlog)
- 999.1: Graphify integration
- n8n webhook import (docs/N8N.md)
- NAS NFS mounts

