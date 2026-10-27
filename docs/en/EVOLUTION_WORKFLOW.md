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

---

## 3. The Triage & Economic Model: Core Pipeline vs. Edition Satellites

Not every historical work can or should be processed fully automatically down to a publishable critical edition. Attempting to embed bespoke parsers for singular monumental works (e.g., Böhtlingk's 3,997 Pāṇini sūtras, Vedic metric analysis, or multi-volume nested dictionary schemas) into the central engine leads directly to the **monolith trap**: the pipeline becomes overburdened, fragile, and unmaintainable.

For the production service on **`alex.birchville.org`**, an economically optimized **triage funnel** is enforced:

```text
               User submits scan / IIIF manifest
                                 │
                                 ▼
                     [ Automated Core Pipeline ]
                     Scan -> Masking -> OCR ->
                     1:1 Sandwich PDF + Raw Text
                                 │
                                 ▼
                   Output meets expectations?
                     ├── YES: Completed (80–90% of standard books)
                     └── NO: Submit case for review
                                 │
                                 ▼
                     [ Philological Triage ]
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
    Path A: Generic Engine Bug              Path B: Genuine Special Case
    (e.g., column splitting, margin         (Canonical monumental edition:
     color, broken ligature rules)           Pāṇini, dictionaries, metrics)
             │                                       │
             ▼                                       ▼
      Improvement of                          Spin-off as
      CORE PIPELINE                           EDITION SATELLITE
      (AlexandriaSandwich)                    (Dedicated repo, e.g., boethlingk)
             │                                       │
             ▼                                       ▼
      All future books benefit                Focused manual curation,
      automatically                           QA viewer & TEI-P5 modeling
```

### Economic Rationale

1. **Near-zero marginal cost for standard cases:** 80–90% of all monographs and historical prints run end-to-end without human intervention.
2. **Preventing misallocation of engineering effort (*YAGNI*):** No speculative parsers are built for theoretical edge cases. Specialized logic is written only when a real, high-value work demands it.
3. **Maximum leverage for core fixes (Path A):** Generic layout improvements are solved once in `AlexandriaSandwich/scripts/` and immediately scale across all future jobs.
4. **Scholarly curation as satellite projects (Path B):** Complex monumental works receive their own Git repository (such as [`boethlingk`](https://github.com/birchville-org/boethlingk)), consuming AlexandriaSandwich artifacts as their digital primary layer while maintaining their domain logic, ground truth, and 1:1 facsimile typesetting independently.

### Service-Level Declaration for `alex.birchville.org`

The web interface communicates this boundary transparently:
* **Standard Processing:** Fully automated generation of searchable 1:1 sandwich PDFs and TEI texts for historical print works in standard Latin and Indic scripts.
* **Complex Special Cases:** For demanding monumental works (multilingual philological typeset, multi-column dictionaries with deep lemma trees, metrical Sanskrit verse), generic automation is naturally insufficient.
* **Feedback Loop:** If results do not meet expectations, the case is submitted along with the original scan for review. We determine whether the core pipeline heuristics can be broadened (Path A) or whether the book should be inaugurated as a curated Birchville edition satellite (Path B).

