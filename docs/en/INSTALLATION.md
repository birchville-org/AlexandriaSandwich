# Installation Guide: AlexandriaSandwich

This guide covers complete installation, system dependencies, and configuration of the AlexandriaSandwich pipeline for production and development environments.

---

## 1. Architectural Overview

The system consists of three closely coupled containers:

```text
               ┌────────────────────────────────────────────────────────┐
               │                      Host System                       │
               │   Storage: /data/{input, processing, output}           │
               │   App:     /opt/alexandria/                            │
               └───────────────────────────┬────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌───────────────────┐             ┌───────────────────┐             ┌───────────────────┐
│   alexandria_ui   │             │  alexandria_n8n   │             │ alexandria_worker │
│   Port: 8080      │ ──────────► │  Port: 5678       │ ──────────► │ CLI Harness       │
│   FastAPI / HTML5 │  (Webhook)  │  n8n Orchestrator │(docker exec)│ OCR, Typst, TEI   │
└───────────────────┘             └───────────────────┘             └───────────────────┘
         ▲                                                                   │
         └───────────────────────────────────────────────────────────────────┘
                       Generated Artifacts: TEI-P5, Sandwich PDF, Digital PDF
```

All three containers communicate over the shared Docker bridge network **`alexandria_default`**.

---

## 2. External Dependencies & Libraries

### 2.1 Worker Container (`alexandria_worker`)
Base image: `ubuntu:24.04` (Multi-Arch: AMD64 & ARM64).

| Category | Utility / Library | Version / Purpose |
| :--- | :--- | :--- |
| **Image Preprocessing** | `unpaper` | 6.1+ (Deskew, edge clearing, black border removal) |
| | `imagemagick` | 7.x / 6.x (Contrast stretching, format conversion) |
| **OCR Engines** | `tesseract-ocr` | 5.3+ (Local open-source OCR engine) |
| | `tesseract-ocr-deu` | German Antiqua / Fraktur language packs |
| | `tesseract-ocr-eng` | English language pack |
| | *(optional)* Languages | `tesseract-ocr-san` (Sanskrit), `fra`, `ita`, `lat` |
| **PDF Tools & Compression** | `poppler-utils` | `pdftoppm`, `pdfinfo`, `pdftotext` |
| | `qpdf` | Linearization and PDF structural validation |
| | `ghostscript` | PostScript and PDF rasterization |
| | `pngquant` | Lossy PNG color reduction |
| | `jbig2` / `jbig2dec` | JBIG2 monochrome compression for sandwich layers |
| **Typesetting (Digital PDF)** | `typst` | **0.11.1+** (Fast Rust-based vector typesetting engine) |
| | `fonts-linuxlibertine` | Classical book serif (Linux Libertine O) |
| | `fonts-dejavu-core` | Serif & Sans fallbacks |
| | `fonts-noto-core` | Full Unicode coverage for diacritics and special scripts |
| **Python Runtime** | `python3` (3.12+), `pip` | Execution runtime for pipeline scripts |

#### Python Packages in Worker:
- `ocrmypdf` (16.x / 17.x): Generates standards-compliant Sandwich PDFs (Text Rendering Mode 3).
- `img2pdf` (0.5+): Lossless raster image embedding into PDF wrappers.
- `mistralai` (1.x / 2.x): API client for vision-based OCR fallback when Tesseract confidence is low.
- `pikepdf` & `lxml`: Low-level manipulation of PDF objects and hOCR/XML DOM trees.

---

### 2.2 Web UI Container (`alexandria_ui`)
Base image: `python:3.12-slim`.

| Package | Version | Purpose |
| :--- | :--- | :--- |
| `fastapi` | 0.115+ | Async backend for dashboard, uploads, and REST API |
| `uvicorn[standard]` | 0.30+ | ASGI web server |
| `jinja2` | 3.1+ | HTML5 templates (QA Viewer, Dashboard, Job Detail) |
| `httpx` | 0.27+ | Async HTTP client for n8n webhook triggers |
| `python-multipart` | 0.0.9+ | Multipart file upload parsing |
| `poppler-utils` | OS package | PDF page rasterization for textlayer editor |

---

### 2.3 Orchestrator (`alexandria_n8n`)
Base image: `docker.n8n.io/n8nio/n8n:latest`.

- **Docker CLI (`/usr/bin/docker`)**: Mounted from host to trigger `docker exec` into the worker.
- **Docker Socket (`/var/run/docker.sock`)**: Container management.
- **Environment**: `NODES_EXCLUDE=[]` (mandatory to enable `ExecuteCommand` node in n8n v2).

---

## 3. Host Requirements & Storage

### 3.1 Operating System
- Tested on: **Ubuntu 22.04 / 24.04 LTS (x86_64)** and **macOS Sonoma/Sequoia (Apple Silicon / ARM64)**.
- Docker Engine >= 24.0 and Docker Compose v2.

### 3.2 Directory Creation
Create the required directory structure on the host:

```bash
sudo mkdir -p /data/input /data/processing /data/output
sudo chown -R $USER:$USER /data
mkdir -p /opt/alexandria
```

### 3.3 Rootless Docker Permissions
Ensure the deployment user belongs to the `docker` group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 4. Step-by-Step Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/marcodem/AlexandriaSandwich.git /opt/alexandria
cd /opt/alexandria
```

### Step 2: Configure Environment (`.env`)
Create `.env` (file permissions `600`):
```bash
cp .env.example .env
# Optional: customize MISTRAL_API_KEY and paths
chmod 600 .env
```

Example content:
```bash
# Mistral API Key for OCR fallback (required on alex.local, monitoring on synology.local)
MISTRAL_API_KEY=your_mistral_api_key_here

# Pipeline Defaults (deu+eng, eng+san, deu+san, deu+eng+san, san)
OCR_LANG=deu+eng
OCR_CONFIDENCE_THRESHOLD=85
DATA_DIR=./data
```

### Step 3: Docker Network
The shared bridge network **`alexandria_default`** is declared in Docker Compose and created automatically. Manual creation is optional (`docker network create alexandria_default || true`).

### Step 4: Start Worker Container
The OCR worker can be started directly using the root compose file (automatically builds the local worker image):

```bash
docker compose up -d --build ocr_worker
```

Verify Typst installation inside worker:
```bash
docker exec alexandria_worker typst --version
# Expected output: typst 0.11.1 (...)
```

### Step 5: Optional — Full Stack (UI + n8n) via Compose Profiles
Instead of copying individual compose files, use compose profiles:

```bash
# Start Web UI:
docker compose --profile ui up -d --build

# Start n8n orchestrator:
docker compose --profile n8n up -d

# Start the full stack (Worker + UI + n8n):
docker compose --profile all up -d --build
```

Import and activate pipeline workflow (if using n8n):
```bash
# 1. Import workflow
docker exec alexandria_n8n n8n import:workflow --input=/opt/alexandria/workflows/n8n_ocr_pipeline.json

# 2. Publish workflow
docker exec alexandria_n8n n8n publish:workflow --id=alexandria-pipeline

# 3. Restart container to arm webhook trigger
docker restart alexandria_n8n
```

Verify Web UI health:
```bash
curl -fsS http://localhost:8080/health
# Response: {"status":"ok","data_dir":"/data","n8n_url":"http://alexandria_n8n:5678/webhook/alexandria/ocr"}
```

---

## 5. Local Development without Docker (macOS / Linux)

### 1. Install System Dependencies
```bash
brew install tesseract tesseract-lang unpaper imagemagick poppler qpdf typst
```

### 2. Configure Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ui/requirements.txt
pip install ocrmypdf img2pdf mistralai
```

### 3. Run Pipeline Locally
```bash
./scripts/run_pipeline.sh \
  --job my_book \
  --input ./data/input \
  --processing ./data/processing \
  --output ./data/output \
  --no-mistral
```

---

## 6. End-to-End Verification (Smoke Test)

```bash
# 1. Create test input
mkdir -p /data/input/smoke_test
convert -size 800x200 xc:white -fill black -pointsize 24 -annotate +50+100 "Alexandria Pipeline Test" /data/input/smoke_test/page_01.png

# 2. Trigger pipeline via Web UI or curl
curl -X POST http://localhost:8080/jobs/smoke_test/trigger

# 3. Verify all 3 primary artifacts
ls -lh /data/output/pdf/smoke_test.sandwich.pdf
ls -lh /data/output/tei/smoke_test.tei.xml
ls -lh /data/output/pdf/smoke_test.digital.pdf
```
