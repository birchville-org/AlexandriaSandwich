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
  * **AI Fallback:** Automatic switch to **Mistral OCR (`mistral-ocr-latest`)** for low confidence scores (< 85%), Fraktur typography, or degraded pages.
* 📦 **Three Core Artifacts:**
  1. **Generic TEI-P5 XML** (`<job>.tei.xml`) for long-term preservation and digital libraries.
  2. **1:1 Sandwich PDF** (`<job>.sandwich.pdf`) retaining the original scan 1:1 with an invisible text layer (PDF Mode 3).
  3. **Digital Vector PDF** (`<job>.digital.pdf`) typeset from an AST via Typst with modern typography.
* 🛠️ **Dual Correction Paths:**
  * **Path A:** hOCR text editing *prior* to PDF compilation.
  * **Path B:** Direct editing of the invisible text layer *inside* the finished PDF via QA Viewer.
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
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ Multi-Artifact Assembly & Export                                           │
 ├────────────────────────────┬───────────────────────────┬───────────────────┤
 │ 5. Sandwich PDF Assembly   │ 6. TEI-P5 XML Export      │ 7. Typst Vector   │
 │ (OCRmyPDF + img2pdf)       │ (lxml + book.json schema) │ (book.typ template)│
 └──────────┬─────────────────┴─────────────┬─────────────┴─────────────┬─────┘
            ▼                               ▼                           ▼
   <job>.sandwich.pdf                 <job>.tei.xml               <job>.digital.pdf
 (Visual scan + text layer)         (Library archive standard)  (Digital reading PDF)
```

---

## 🛠️ Scripts Directory (`scripts/`)

| Script | Type | Description |
| :--- | :--- | :--- |
| [`run_pipeline.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/run_pipeline.sh) | Bash | Master pipeline orchestrator (Preprocessing, Quality Check, Fallback, Assembly, Reporting). |
| [`preprocess.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/preprocess.sh) | Bash | Cleans raw scans using ImageMagick and unpaper (deskew, border cleaning, contrast). |
| [`quality_check.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/quality_check.py) | Python | Executes Tesseract, evaluates per-word/per-page confidence, decides pass/fallback. |
| [`mistral_ocr.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/mistral_ocr.py) | Python | Vision LLM API client for fallback OCR on damaged or degraded pages. |
| [`assemble_sandwich.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/assemble_sandwich.py) | Python | Assembles 1:1 Sandwich PDFs with invisible searchable text layer (PDF Mode 3). |
| [`consolidate_book.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/consolidate_book.py) | Python | Aggregates individual page hOCR/Markdown files into canonical `book.json`. |
| [`export_tei.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/export_tei.py) | Python | Generates archival TEI-P5 XML from `book.json`. |
| [`render_digital_pdf.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/render_digital_pdf.py) | Python | Typesets modern readable PDF using Typst 0.11+. |
| [`hocr_correct.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/hocr_correct.py) | Python | Path A interactive/batch correction tool for hOCR word boundaries. |
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
