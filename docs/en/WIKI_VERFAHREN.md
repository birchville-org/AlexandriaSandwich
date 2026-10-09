# Pipeline Architecture: AlexandriaSandwich

## 1. Objective & Core Concept

**AlexandriaSandwich** automates high-quality digitization of books and archival documents into long-term archival formats and modern digital representations.

A Sandwich PDF consists of two precisely registered layers:
1. **Visual Image Layer (top):** The original cleaned scan image is preserved 1:1 down to the pixel. No destructive typesetting or visual replacement occurs.
2. **Invisible Text Layer (bottom):** An invisible vector text layer (`GlyphLessFont`) with bounding boxes that enables full-text search, selection, and copy-paste.

The pipeline follows a **Local-First approach with AI Fallback**: regular scans are processed locally and cost-effectively; cloud-based AI is engaged only when local OCR confidence degrades.

---

## 2. System Architecture & Topology

```text
┌─────────────────────────────────────────────────────────────┐
│ Dev Node (Mac mini M2: hermes.local)                        │
│ • Pipeline development & multi-arch container builds        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Git / Rsync
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage & Web Portal (Synology NAS: synology.local)          │
│ • alexandria_ui      (FastAPI Dashboard, Textlayer Editor)  │
│ • Traefik Reverse-Proxy + Authelia 2FA SSO (alex.birchville)│
│ • Central NFS storage:                                       │
│   ├── /data/input       (Incoming raw scans)                │
│   ├── /data/processing  (Intermediate artifacts)            │
│   └── /data/output      (Final PDFs, XML, Markdown)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ NFS Mount & Webhooks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Compute Node (Proxmox VM: alex.local)                       │
│ • alexandria_worker  (ImageMagick, unpaper, Tesseract, OCR) │
│ • alexandria_n8n     (Workflow orchestration & webhooks)    │
└─────────────────────────────────────────────────────────────┘
```

### Roles & API Key Distribution

| Host | Services | Mistral API Key? | Role & Rationale |
| :--- | :--- | :---: | :--- |
| **`alex.local`** | `alexandria_worker`, `n8n` | **Yes (Required)** | Executes OCR pipeline & Cloud API calls (`MISTRAL_API_KEY` in `/opt/alexandria/.env`). |
| **`synology.local`** | `alexandria_ui`, Traefik, Authelia | **Yes (Monitoring)** | Health checks against `api.mistral.ai` & displays cost metrics. |

---

## 3. Pipeline Execution Stages

```text
[Raw Scan] 
   │
   ▼
[1. Preprocessing] ──────► Deskew & edge cleanup (ImageMagick + unpaper)
   │
   ▼
[2. Local OCR] ────────► Tesseract produces hOCR with word coordinates & confidence
   │
   ▼
[3. Quality Gate] ──────► quality_check.py: Average confidence >= 85%?
   │            │
   │ (Yes)      │ (No)
   │            ▼
   │      [4. AI Fallback] ──► Mistral Document AI (mistral-ocr-latest)
   │            │
   ▼            ▼
[5. Multi-Artifact Generation]
   ├── 1:1 Sandwich PDF (OCRmyPDF / img2pdf)
   ├── Generic TEI-P5 XML (export_tei.py)
   └── Typst Digital PDF (render_digital_pdf.py)
   │
   ▼
[6. QA & Correction] ────► Pre-Assembly (hOCR) OR Post-Assembly (Textlayer / .aligned.pdf)
```

---

## 4. The Three Primary Artifacts

1. **Generic TEI-P5 XML (`<job>.tei.xml`):**
   * Validated against the Text Encoding Initiative P5 standard schema.
   * Semantic structure with document metadata, facsimile page links, surface coordinates, zones, paragraphs, and line breaks.

2. **1:1 Sandwich PDF (`<job>.sandwich.pdf`):**
   * Retains the authentic historical scan image with zero visual distortion.
   * Inconspicuous vector glyph layer for search and clipboard operations.

3. **Digital Vector PDF (`<job>.digital.pdf`):**
   * Built from an Abstract Syntax Tree (`book.json` / `book.md`) via Typst 0.11+.
   * Clean typography, selectable vector fonts (Linux Libertine, DejaVu, Noto), optimized for reading and printing.

---

## Reference Projects & Case Studies

* **[Pāṇini's Grammar (Otto von Böhtlingk, 1887)](case-study.md):**
  Complete scholarly digitization, multi-script OCR, canonical alignment, TEI-P5 modeling, and [OCR engine benchmark (Mistral vs. local Qwen2.5-VL)](case-study.md#step-21-local-vlm-alternative-model-benchmark-mistral-ocr-vs-qwen25-vl) across 3,997 Sūtras on 478 book pages.

