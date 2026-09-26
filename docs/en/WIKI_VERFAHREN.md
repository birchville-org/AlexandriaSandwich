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
│ Dev Node (Mac mini M2)                                      │
│ • Pipeline development & multi-arch container builds        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Git / Docker Registry
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Control Node (NAS)                                          │
│ • n8n workflow orchestrator                                 │
│ • Central storage:                                          │
│   ├── /data/input       (Incoming raw scans)                │
│   ├── /data/processing  (Intermediate artifacts)            │
│   └── /data/output      (Final PDFs, XML, Markdown)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ NFS Mount & Webhooks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Compute Node (Proxmox VM: alex.local)                       │
│ • alexandria_worker  (ImageMagick, unpaper, Tesseract, OCR) │
│ • alexandria_ui      (FastAPI Dashboard & Path B Editor)    │
└─────────────────────────────────────────────────────────────┘
```

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
   │      [4. AI Fallback] ──► Mistral OCR API (mistral-ocr-latest)
   │            │
   ▼            ▼
[5. Multi-Artifact Generation]
   ├── 1:1 Sandwich PDF (OCRmyPDF / img2pdf)
   ├── Generic TEI-P5 XML (export_tei.py)
   └── Typst Digital PDF (render_digital_pdf.py)
   │
   ▼
[6. QA & Correction] ────► Path A (hOCR pre-assembly) OR Path B (Post-PDF layer)
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
