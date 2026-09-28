# 📚 AlexandriaSandwich

> **Automated book digitization with hybrid OCR (Tesseract + Mistral AI), GSD pipeline & 1:1 sandwich PDF output.**

![Build Status](https://img.shields.io/badge/docker-multi--arch-blue)
![Release](https://img.shields.io/badge/release-v1.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12-yellow)

**AlexandriaSandwich** is a containerized pipeline designed for archiving and digitizing historical and modern books. It converts raw scans into precise **1:1 sandwich PDFs** (visual scan preserved with an exact invisible searchable text layer underneath), generic **TEI-P5 XML** for long-term preservation, and newly typeset **digital vector PDFs** via Typst.

---

## 🚀 Quickstart (CLI in 3 Steps)

Prerequisite: [Docker Engine](https://docs.docker.com/engine/install/) with Docker Compose v2.

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/birchville-org/AlexandriaSandwich.git
cd AlexandriaSandwich
cp .env.example .env
```

### 2. Start OCR Worker
```bash
docker compose up -d ocr_worker
```

### 3. Run Sample Book Pipeline
The repository includes synthetic sample pages in `examples/sample_book`:
```bash
docker exec alexandria_worker /opt/alexandria/scripts/run_pipeline.sh \
  --job sample_book \
  --input /opt/alexandria/examples/sample_book \
  --no-mistral
```

**Results:** All generated artifacts are immediately accessible on your host in `./data/output/`:
* 📄 **1:1 Sandwich PDF:** `./data/output/pdf/sample_book.sandwich.pdf`
* 🏛️ **TEI-P5 XML:** `./data/output/tei/sample_book.tei.xml`
* 📖 **Digital Vector PDF:** `./data/output/pdf/sample_book.digital.pdf`
* 📊 **Full Pipeline Report:** `./data/output/reports/sample_book.pipeline.json`

> **Need the Web UI & n8n?** Launch the complete stack with:
> ```bash
> docker compose --profile all up -d
> ```
> * **QA Viewer & Dashboard:** [http://localhost:8080/](http://localhost:8080/)
> * **n8n Orchestrator:** [http://localhost:5678/](http://localhost:5678/)

---

## ✨ Key Features

* 🪓 **Headless Pre-Processing:** Automatic deskewing and edge cleaning for yellowed pages via **ImageMagick + unpaper** (`scripts/preprocess.sh`).
* 🤖 **Hybrid Quality Loop:**
  * **Local & Fast:** First-pass OCR using Tesseract on the compute node.
  * **AI Fallback:** Automatic switch to **Mistral OCR (`mistral-ocr-latest`)** for low confidence scores (< 85%), Fraktur typ* 📝 **Multi-Format Export (Full Target Format Matrix):**
  1. **1:1 Sandwich PDF (Path A & Path B):** Visual facsimile with an invisible text layer (`<job>.sandwich.pdf`) and semantically aligned text layer via Mistral OCR eliminating noise artifacts (`<job>.pathb.pdf`).
  2. **Reflowable EPUB 3 eBook:** For mobile devices and e-readers (`<job>.epub`) with 102+ chapters and embedded Unicode fonts (*Noto Serif Devanagari* + *Linux Libertine O*).
  3. **Digital Vector PDF:** Typeset from clean AST via Typst with modern typography (`<job>.digital.pdf`).
  4. **TEI-P5 XML:** Archival standard XML (`<job>.tei.xml`) for library catalogs and digital humanities.
  5. **Semantic AST & Markdown:** Canonical `book.json` (Single Source of Truth with token bounding boxes) and clean `book.md` for AI text processing.
  *(See detailed specification: [Target Formats & Dual Layout](TARGET_FORMATS.md))*
* 🛠️ **Dual Correction Paths:**
  * **Path A:** hOCR text editing *prior* to PDF compilation.
  * **Path B:** Direct token-level editing and alignment of the invisible text layer *inside* the finished PDF via pikepdf & QA Viewer.
* 🐳 **Multi-Architecture Support:** Built for `linux/amd64` (Intel/AMD servers & VMs) and `linux/arm64` (Apple Silicon M-series).

---

## 🔄 Pipeline Stages

```text
Raw Scans (PNG / TIFF / JPEG)
         │
         ▼
 ┌──────────────────────┐
 │ 1. Preprocessing     │ ──► ImageMagick & unpaper (Deskew, edge clearing, despeckle)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 2. Tesseract OCR     │ ──► Local OCR Engine (hOCR bounding boxes & confidence)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 3. Quality Gate      │ ── Confidence < 85%? ──► ┌───────────────────────────┐
 └──────────┬───────────┘                          │ 4. Mistral OCR Fallback   │
            │ Pass (>= 85%)                        │ (Vision LLM extraction)   │
            │                                      └─────────────┬─────────────┘
            ├────────────────────────────────────────────────────┘
            │
            ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Multi-Artifact Assembly & Target Exports                                               │
 ├────────────────────────────┬───────────────────────────┬───────────────┬───────────────┤
 │ 5. Sandwich PDF Assembly   │ 6. TEI-P5 XML Export      │ 7. Typst Satz │ 8. EPUB 3     │
 │ (OCRmyPDF + Path B Align)  │ (lxml + book.json schema) │ (book.typ)    │ (Font Inlined)│
 └──────────┬─────────────────┴─────────────┬─────────────┴───────┬───────┴───────┬───────┘
            ▼                               ▼                     ▼               ▼
   <job>.sandwich / pathb.pdf        <job>.tei.xml          <job>.digital.pdf <job>.epub
 (Facsimile + aligned layer)      (Academic Standard)    (Vector Typeset)  (Mobile eBook)
```

---

## 🛠️ Scripts Directory (`scripts/`)

| Script | Type | Description |
| :--- | :--- | :--- |
| [`run_pipeline.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/run_pipeline.sh) | Bash | Master pipeline orchestrator (Preprocessing, Quality Check, Fallback, Assembly, Multi-Format Exports). |
| [`align_mistral_pdf.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/align_mistral_pdf.py) | Python | Path B: Injects Mistral OCR corrections directly into PDF text streams matching Tesseract geometry. |
| [`export_epub.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/export_epub.py) | Python | Compiles standard EPUB 3 eBooks with semantic XHTML and embedded Unicode fonts. |
| [`render_digital_pdf.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/render_digital_pdf.py) | Python | Typesets publication-grade digital vector PDF using Typst 0.11+. |
| [`export_tei.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/export_tei.py) | Python | Generates archival TEI-P5 XML from `book.json`. |
| [`consolidate_book.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/consolidate_book.py) | Python | Aggregates individual page hOCR/Markdown files into canonical `book.json` and `book.md`. |
| [`mistral_ocr.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/mistral_ocr.py) | Python | Vision LLM API client supporting concurrent batch processing with exponential retry backoff. |
| [`assemble_sandwich.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/assemble_sandwich.py) | Python | Assembles 1:1 Sandwich PDFs with invisible searchable text layer (PDF Mode 3). |
| [`quality_check.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/quality_check.py) | Python | Executes Tesseract, evaluates per-word/per-page confidence, decides pass/fallback. |
| [`preprocess.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/preprocess.sh) | Bash | Cleans raw scans using ImageMagick and unpaper (deskew, border cleaning, contrast). |
| [`hocr_correct.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/hocr_correct.py) | Python | Path A interactive/batch correction tool for hOCR word boundaries. |
| [`pdf_text_correct.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/pdf_text_correct.py) | Python | Low-level stream replacement engine for post-processing PDF text layers (Path B). |
| [`sync_storage.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/sync_storage.sh) | Bash | Storage synchronization utility for network shares (NFS/SMB). |

---

## 🏛️ System Architecture & Reference Deployment

The pipeline runs out-of-the-box on any local workstation with Docker (`localhost`). In multi-node production setups, tasks can be distributed across nodes:

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Control Node / NAS                                          │
 │                                                             │
 │  • n8n Workflow Orchestrator (Docker Container)             │
 │  • Central Storage (NFS/SMB Share for Scans & Artifacts)    │
 └──────────────────────────────┬──────────────────────────────┘
                                │ NFS Mount & REST / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Compute Node (e.g. Proxmox VM "alex" - 16 GB RAM / 4 vCPUs) │
 │                                                             │
 │  • Docker OCR Worker Container (`alexandria_worker`)        │
 │    ├── ImageMagick + unpaper (Deskew & Cleanup)             │
 │    ├── Tesseract OCR (Primary local engine, hOCR export)    │
 │    ├── Mistral OCR Client (API fallback & layout analysis)  │
 │    └── OCRmyPDF / Typst 0.11+ / TEI Exporter                │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📖 Documentation & Links

* 🇬🇧 **Installation Guide:** [`INSTALLATION.md`](INSTALLATION.md)
* 🛠️ **Correction Paths (Path A vs Path B):** [`CORRECTION_PATHS.md`](CORRECTION_PATHS.md)
* ⚡ **n8n Operations & Setup:** [`N8N.md`](N8N.md)
* 🗄️ **Storage Architecture:** [`STORAGE.md`](STORAGE.md)
