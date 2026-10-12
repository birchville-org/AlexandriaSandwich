# Workflow for New Documents & Evolutionary Engine Hardening

This document defines the standardized operational workflow when processing new historical books with **AlexandriaSandwich** and encountering novel typographic or layout anomalies.

---

## 1. The Core Paradigm

> **The pipeline matures with each book.**  
> Scripts inside `scripts/` are never duplicated or forked per job. Every edge-case fix and refinement flows directly into the central engine and automatically benefits all past and future books.

---

## 2. The 4-Stage Cycle

### Stage 1: Ingress & Baseline Run
1. Place scans in `data/input/<job>/`.
2. Optionally specify book parameters in `data/input/<job>/job.config.json`.
3. Execute standard pipeline: `./scripts/run_pipeline.sh --job <job>`.

### Stage 2: Diagnostics & Edge-Case Inspection
Inspect output artifacts in `data/output/<job>/`:
- OCR pass rates and fallback costs (`<job>.pipeline.json`).
- Textlayer alignment and drift (`<job>.sandwich.pdf`).
- Layout structure in vector reprints (`<job>.digital.pdf` / `<job>.typeset_edition.pdf`).

### Stage 3: Generalized Solution in Core Engine
Implement fixes strictly in `scripts/`:
- **Never branch on job name** (`if job == "xyz": ...`).
- Abstract structural features (e.g., column density, script/Unicode block, font scale differences).

### Stage 4: Regression Gate (Golden Master Guard)
Run fast checks against reference jobs (`alex_smoke`, `katha_06`):
- Ensure existing books suffer no quality regressions.
- Validate that the new book succeeds and joins the verified reference fleet.
