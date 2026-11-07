# ROADMAP - AlexandriaSandwich GSD Phase Plan

## Progress Table

| Phase | Description | Plans Completed | Total Plans | Status |
|-------|-------------|:---------------:|:-----------:|--------|
| **1** | Local OCR Worker & Fallback API | 4 | 4 | Complete |
| **2** | Pre-processing & Workflow-Integration | 3 | 3 | Complete |
| **3** | Assembly & Double Correction Paths (A/B) | 4 | 4 | Complete |
| **4** | Web UI & Visual Verification (M2) | 2 | 2 | Complete |
| **5** | Multi-Format Digital Outputs (TEI-P5 & Clean Text PDF) (M3) | 4 | 4 | Complete |
| **6** | Evolutionäre Engine-Härtung & Job-Zentriertes Layout (M4) | 3 | 3 | Complete |
| **7** | Interaktive Stufen-Pipeline & Checkpoint-Orchestrierung (M5) | 0 | 3 | In Planning |

---

<details>
<summary><b>Phase 1: Local OCR Worker & Fallback API</b> Complete</summary>

**Goal:** Establish a verified Docker environment carrying all heavy OCR libraries alongside a working CLI harness for Tesseract and Mistral OCR fallback.

- [x] **Plan 01-01:** Initialize GSD Planning Structure
- [x] **Plan 01-02:** Local multi-arch Docker build verification (ARM64 & AMD64)
- [x] **Plan 01-03:** Implement quality_check.py to calculate Tesseract hOCR confidence
- [x] **Plan 01-04:** Implement mistral_ocr.py using mistralai client with error handling
</details>

<details>
<summary><b>Phase 2: Pre-processing & Workflow-Integration</b> Complete</summary>

**Goal:** Headless preprocess (ImageMagick + unpaper), storage sync/NFS, and n8n orchestration.

- [x] **Plan 02-01:** Headless preprocess (scripts/preprocess.sh) via ImageMagick deskew + unpaper
- [x] **Plan 02-02:** Establish NFS/Storage-Sync scripts for NAS and Compute Nodes
- [x] **Plan 02-03:** Build n8n webhook routes in workflows/n8n_ocr_pipeline.json
</details>

<details>
<summary><b>Phase 3: Assembly & Double Correction Paths (A/B)</b> Complete</summary>

**Goal:** Assemble raw OCR files and images into Sandwich PDFs, supporting both Phase pre-PDF (hOCR modification) and post-PDF correcting.

- [x] **Plan 03-01:** Implement scripts/assemble_sandwich.py using OCRmyPDF/img2pdf
- [x] **Plan 03-02:** Code correction pipeline Path A (Pre-PDF hOCR JSON/XML patching)
- [x] **Plan 03-03:** Code correction pipeline Path B (Post-PDF text-layer replace via pdf_text_correct.py)
- [x] **Plan 03-04:** Complete End-to-End System Integration test run (e2e_m1 PASS)
</details>

<details>
<summary><b>Phase 4: Web UI & Visual Verification (M2)</b> Complete</summary>

**Goal:** Web interface showing the OCR workflow with input/output document management.

- [x] **Plan 04-01:** FastAPI Web UI — dashboard, upload, job detail, download, n8n trigger
- [x] **Plan 04-02:** Path B visual editor — inline PDF text-layer correction UI
</details>

<details>
<summary><b>Phase 5: Multi-Format Digital Outputs: TEI-P5 & Clean Text PDF (M3)</b> Complete</summary>

**Goal:** Transform extracted OCR data into standardized academic TEI-P5 XML and publication-grade Typst vector-text PDF (`<job>.digital.pdf`), complementing the 1:1 Sandwich PDF.

- [x] **Plan 05-01:** Text Consolidation, Metadata & Book Structuring (`scripts/consolidate_book.py`)
- [x] **Plan 05-02:** Generic TEI-P5 XML Exporter (`scripts/export_tei.py`)
- [x] **Plan 05-03:** Typst Typesetting Engine Integration & CLI Renderer (`scripts/render_digital_pdf.py`)
- [x] **Plan 05-04:** Web UI & Pipeline Automation Integration (`ui/main.py`, `scripts/run_pipeline.sh`, n8n)
</details>

<details open>
<summary><b>Phase 6: Evolutionäre Engine-Härtung & Job-Zentriertes Layout (M4)</b> Complete</summary>

**Goal:** Vollständige Umstellung der Pipeline-Ausgabe auf job-zentrierte Verzeichnisse (`data/output/<job>/`), deklarative Job-Profile (`job.config.json`) und Aufbau einer automatisierten Regressions-Testsuite (Golden Master Guard).

- [x] **Plan 06-01:** Umstellung von `run_pipeline.sh`, Hilfsskripten und `ui/main.py` auf das job-zentrierte Layout (`data/output/<job>/`) mit nahtloser Rückwärtskompatibilität
- [x] **Plan 06-02:** Deklarative Job-Profile (`job.config.json`) zur Trennung buchspezifischer Metadaten/Parameter von der Engine
- [x] **Plan 06-03:** Automatisierte Golden-Master-Regressionssuite über Standard-Referenzjobs (`test_golden_regression.sh`)
</details>

<details open>
<summary><b>Phase 7: Interaktive Stufen-Pipeline & Checkpoint-Orchestrierung (M5)</b> In Planning</summary>

**Goal:** Optionale Aufteilung der AlexandriaSandwich-Pipeline in interaktive Einzelschritte via n8n (`Wait`-Nodes) und Web-UI-Inspektion, inklusive parametergesteuerter Wiederholung einzelner Stufen ohne Datenverlust.

- [ ] **Plan 07-01:** Stage-Modularisierung des Pipeline-Harness (`run_pipeline.sh --stage <preprocess|ocr|consolidate|export|assembly>` und `data/processing/<job>/stage_*/` Checkpointing)
- [ ] **Plan 07-02:** n8n Workflow-Erweiterung mit `Wait`-Nodes, Callback-Webhooks und bedingten Re-entrant-Schleifen (`Switch`/`IF`) für Parameter-Korrekturen
- [ ] **Plan 07-03:** Web-UI-Integration im Service-Portal (`/jobs/{job}/stages`): Visuelle Inspektion von Zwischenartefakten, Freigabe-Buttons und dynamische Parameteranpassung für Re-Runs
</details>

## Backlog

### Follow-ups (999.x)
- [ ] **999.1:** Integrate Graphify for code structure, architectural verification and document indexing
- [x] **999.2:** Develop Vue/PWA Frontend for visual verification (Path B editor) — absorbed into M2 Phase 4

- [ ] **999.3:** Packaging AlexandriaSandwich as an installable Python library (`alexandria-core`) via `pyproject.toml`: enable downstream edition satellites (such as `boethlingk`) to import `alexandria.typeset` (`AdaptiveTypesetSolver`, `verify_page_parity`, `postprocess_pdf_metadata`) as a clean dependency instead of maintaining duplicate scripts.
