# Installationsanleitung: AlexandriaSandwich

Diese Anleitung beschreibt die vollständige Installation, Systemabhängigkeiten und Konfiguration der AlexandriaSandwich-Pipeline für Produktions- und Entwicklungsumgebungen.

---

## 1. Architekturübersicht

Das System besteht aus drei eng gekoppelten Schichten:

```text
               ┌────────────────────────────────────────────────────────┐
               │                     Host-System                        │
               │   Storage: /data/{input, processing, output}           │
               │   App:     /opt/alexandria/                            │
               └───────────────────────────┬────────────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌───────────────────┐             ┌───────────────────┐             ┌───────────────────┐
│   alexandria_ui   │             │  alexandria_n8n   │             │ alexandria_worker │
│   Port: 8080      │ ──────────► │  Port: 5678       │ ──────────► │ CLI-Harness       │
│   FastAPI / HTML5 │  (Webhook)  │  n8n Orchestrator │(docker exec)│ OCR, Typst, TEI   │
└───────────────────┘             └───────────────────┘             └───────────────────┘
         ▲                                                                   │
         └───────────────────────────────────────────────────────────────────┘
                       Erzeugte Artefakte: TEI-P5, Sandwich-PDF, Neusatz-PDF
```

Alle drei Container kommunizieren über das gemeinsame Docker-Netzwerk **`alexandria_default`**.

---

## 2. Externe Abhängigkeiten & Systembibliotheken

### 2.1 Worker-Container (`alexandria_worker`)
Basis: `ubuntu:24.04` (Multi-Arch: AMD64 & ARM64).

| Kategorie | Programm / Bibliothek | Mindestversion / Zweck |
| :--- | :--- | :--- |
| **Bildvorverarbeitung** | `unpaper` | 6.1+ (Entzerrung, Randbereinigung, Entflecken) |
| | `imagemagick` | 7.x / 6.x (Deskew, Kontrastspreizung, Konvertierung) |
| **OCR Engines** | `tesseract-ocr` | 5.3+ (Lokale Open-Source-Texterkennung) |
| | `tesseract-ocr-deu` | Deutsche Fraktur-/Antiqua-Traineddata |
| | `tesseract-ocr-eng` | Englische Sprachmodelle |
| | *(optional)* Sprachdaten | `tesseract-ocr-san` (Sanskrit), `fra`, `ita`, `lat` |
| **PDF-Tools & Kompression** | `poppler-utils` | `pdftoppm`, `pdfinfo`, `pdftotext` |
| | `qpdf` | Linearisierung und PDF-Strukturprüfung |
| | `ghostscript` | PostScript/PDF-Rasterisierung |
| | `pngquant` | Verlustbehaftete PNG-Kompression |
| | `jbig2` / `jbig2dec` | JBIG2-Monochrom-Kompression für Sandwich-Ebenen |
| **Neusatz (Typografie)** | `typst` | **0.11.1+** (Moderner Rust-basierter Vektorsatz) |
| | `fonts-linuxlibertine` | Klassische Buchantiqua (Linux Libertine O) |
| | `fonts-dejavu-core` | Serifen- & Sans-Fallbacks |
| | `fonts-noto-core` | Unicode-Abdeckung für Sonderzeichen & Diakritika |
| **Python-Laufzeit** | `python3` (3.12+), `pip` | Laufzeitumgebung der Pipeline-Skripte |

#### Python-Pakete im Worker:
- `ocrmypdf` (16.x / 17.x): Erzeugung standardkonformer Sandwich-PDFs (Text Rendering Mode 3).
- `img2pdf` (0.5+): Verlustfreie Einbettung von Rasterbildern in PDF-Container.
- `mistralai` (1.x / 2.x): API-Client für LLM-Vision-Fallback bei niedriger Tesseract-Konfidenz.
- `pikepdf` & `lxml`: Low-Level-Manipulation von PDF-Objektbäumen und hOCR/XML.

---

### 2.2 Web-UI-Container (`alexandria_ui`)
Basis: `python:3.12-slim`.

| Paket | Version | Zweck |
| :--- | :--- | :--- |
| `fastapi` | 0.115+ | Asynchrones Backend für Dashboard, Upload und REST-API |
| `uvicorn[standard]` | 0.30+ | ASGI-Webserver |
| `jinja2` | 3.1+ | HTML5-Templates (QA Viewer, Dashboard, Job Detail) |
| `httpx` | 0.27+ | Asynchroner HTTP-Client für n8n-Webhook-Trigger |
| `python-multipart` | 0.0.9+ | Datei-Upload via Formular |
| `poppler-utils` | OS-Paket | PDF-Seitenrasterung für Path B Editor |

---

### 2.3 Orchestrator (`alexandria_n8n`)
Basis: `docker.n8n.io/n8nio/n8n:latest`.

- **Docker-CLI (`/usr/bin/docker`)**: Vom Host eingebunden, um `docker exec` in den Worker abzusetzen.
- **Docker-Socket (`/var/run/docker.sock`)**: Zur Steuerung der Container.
- **Environment**: `NODES_EXCLUDE=[]` (zwingend erforderlich, damit der Node `ExecuteCommand` in n8n v2 aktiviert ist).

---

## 3. Host-Voraussetzungen & Dateisystem

### 3.1 Betriebssystem
- Getestet auf: **Ubuntu 22.04 / 24.04 LTS (x86_64)** sowie **macOS Sonoma/Sequoia (Apple Silicon / ARM64)**.
- Docker Engine >= 24.0 und Docker Compose v2.

### 3.2 Speicherpfade anlegen
Auf dem Server müssen folgende Verzeichnisse existieren und Schreibrechte besitzen:

```bash
sudo mkdir -p /data/input /data/processing /data/output
sudo chown -R $USER:$USER /data
mkdir -p /opt/alexandria
```

### 3.3 Berechtigungen für Docker ohne sudo
Der Deployment-Benutzer muss Mitglied der Gruppe `docker` sein:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 4. Schritt-für-Schritt Installation

### Schritt 1: Repository klonen
```bash
git clone https://github.com/marcodem/AlexandriaSandwich.git /opt/alexandria
cd /opt/alexandria
```

### Schritt 2: Umgebungskonfiguration (`.env`)
Erstelle `.env` (Dateirechte `600`):
```bash
cp .env.example .env
# Optional: MISTRAL_API_KEY und Pfade anpassen
chmod 600 .env
```

Beispielinhalt:
```bash
# Mistral API-Schlüssel für OCR-Fallback (zwingend auf alex.local, für Monitoring auf synology.local)
MISTRAL_API_KEY=dein_mistral_api_key_hier

# Pipeline-Standards (deu+eng, eng+san, deu+san, deu+eng+san, san)
OCR_LANG=deu+eng
OCR_CONFIDENCE_THRESHOLD=85
DATA_DIR=./data
```

### Schritt 3: Docker-Netzwerk
Das gemeinsame Netzwerk **`alexandria_default`** wird von Docker Compose automatisch verwaltet. Ein manueller Eingriff ist nicht erforderlich (bei Bedarf: `docker network create alexandria_default || true`).

### Schritt 4: Worker-Container starten
Der OCR-Worker kann direkt über das Wurzel-Composefile gestartet werden (baut automatisch das lokale Image):

```bash
docker compose up -d --build ocr_worker
```

Verifikation:
```bash
docker exec alexandria_worker typst --version
# Ausgabe: typst 0.11.1 (...)
```

### Schritt 5: Optional — Vollständiger Stack (UI + n8n) via Compose-Profile
Statt einzelne Compose-Dateien zu kopieren, stehen Compose-Profile bereit:

```bash
# Nur UI starten:
docker compose --profile ui up -d --build

# Nur n8n Orchestrator starten:
docker compose --profile n8n up -d

# Den gesamten Stack (Worker + UI + n8n) auf einmal starten:
docker compose --profile all up -d --build
```

Workflow in n8n aktivieren (falls n8n genutzt wird):
```bash
# 1. Workflow importieren
docker exec alexandria_n8n n8n import:workflow --input=/opt/alexandria/workflows/n8n_ocr_pipeline.json

# 2. Workflow aktivieren/publizieren
docker exec alexandria_n8n n8n publish:workflow --id=alexandria-pipeline

# 3. Container neu starten, damit Trigger scharfgeschaltet wird
docker restart alexandria_n8n
```

Verifikation:
```bash
curl -fsS http://localhost:8080/health
# Ausgabe: {"status":"ok","data_dir":"/data","n8n_url":"http://alexandria_n8n:5678/webhook/alexandria/ocr"}
```

---

## 5. Lokale Entwicklungsumgebung ohne Docker (z. B. macOS)

Soll die Pipeline oder die UI direkt lokal auf macOS entwickelt werden:

### 1. Homebrew-Abhängigkeiten installieren
```bash
brew install tesseract tesseract-lang unpaper imagemagick poppler qpdf typst
```

### 2. Python-Umgebung einrichten
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ui/requirements.txt
pip install ocrmypdf img2pdf mistralai
```

### 3. Pipeline lokal ausführen
```bash
./scripts/run_pipeline.sh \
  --job mein_buch \
  --input ./data/input \
  --processing ./data/processing \
  --output ./data/output \
  --no-mistral
```

---

## 6. End-to-End Funktionstest (Smoke Test)

Zur Absicherung der Gesamtkette:

```bash
# 1. Testbild ablegen
mkdir -p /data/input/smoke_test
cp /opt/alexandria/docker/worker/test.png /data/input/smoke_test/page_01.png 2>/dev/null || \
convert -size 800x200 xc:white -fill black -pointsize 24 -annotate +50+100 "Alexandria Pipeline Test" /data/input/smoke_test/page_01.png

# 2. Durchlauf über Web-UI oder cURL starten
curl -X POST http://localhost:8080/jobs/smoke_test/trigger

# 3. Erzeugte Artefakte prüfen
ls -lh /data/output/pdf/smoke_test.sandwich.pdf
ls -lh /data/output/tei/smoke_test.tei.xml
ls -lh /data/output/pdf/smoke_test.digital.pdf
```

Alle drei Primär-Artefakte müssen in `/data/output/` vorliegen und über das Dashboard unter `http://<host>:8080/jobs/smoke_test` einsehbar sein.
