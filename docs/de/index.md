# 📚 AlexandriaSandwich

> **Automatisierte Buch-Digitalisierung mit Hybrid-OCR (Tesseract + Mistral AI), GSD-Pipeline & Perfect Sandwich-PDF Output.**

![Build Status](https://img.shields.io/badge/docker-multi--arch-blue)
![Release](https://img.shields.io/badge/release-v1.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12-yellow)

**AlexandriaSandwich** ist eine containergestützte Pipeline zur Archivierung und Digitalisierung historischer und moderner Bücher. Sie verwandelt rohe Buchscans in perfekte **1:1 Sandwich-PDFs** (visuelles Originalbild mit punktgenau hinterlegter, unsichtbarer Textebene), standardkonformes **TEI-P5 XML** für Langzeitarchive sowie typografisch neu gesetzte **Vektor-PDFs** via Typst.

---

## 🚀 Schnellstart (CLI in 3 Schritten)

Voraussetzung: [Docker Engine](https://docs.docker.com/engine/install/) mit Docker Compose v2.

### 1. Repository klonen & Konfiguration anlegen
```bash
git clone https://github.com/birchville-org/AlexandriaSandwich.git
cd AlexandriaSandwich
cp .env.example .env
```

### 2. OCR-Worker starten
```bash
docker compose up -d ocr_worker
```

### 3. Beispiel-Job ausführen
Die Pipeline enthält synthetische Testseiten unter `examples/sample_book`:
```bash
docker exec alexandria_worker /opt/alexandria/scripts/run_pipeline.sh \
  --job sample_book \
  --input /opt/alexandria/examples/sample_book \
  --no-mistral
```

**Ergebnis:** Die fertigen Artefakte liegen sofort im Host-Verzeichnis `./data/output/`:
* 📄 **1:1 Sandwich-PDF:** `./data/output/pdf/sample_book.sandwich.pdf`
* 🏛️ **TEI-P5 XML:** `./data/output/tei/sample_book.tei.xml`
* 📖 **Neusatz-PDF:** `./data/output/pdf/sample_book.digital.pdf`
* 📊 **Ausführlicher JSON-Report:** `./data/output/reports/sample_book.pipeline.json`

> **Web-UI & n8n gewünscht?** Der gesamte Stack lässt sich mit einem Befehl starten:
> ```bash
> docker compose --profile all up -d
> ```
> * **QA Viewer & Dashboard:** [http://localhost:8080/](http://localhost:8080/)
> * **n8n Orchestrator:** [http://localhost:5678/](http://localhost:5678/)

---

## ✨ Features

* 🪓 **Automatisches Pre-Processing:** Ausrichten (Deskewing) und Reinigen vergilbter Seiten via **ImageMagick + unpaper** (`scripts/preprocess.sh`).
* 🤖 **Hybrid Quality Loop:**
  * **Lokal & Schnell:** Erste OCR-Ebene mit Tesseract OCR auf der lokalen Compute-Node.
  * **KI-Fallback:** Automatischer Wechsel auf **Mistral OCR (`mistral-ocr-latest`)** bei schlechten Scores (< 85% Confidence), Frakturschriften oder beschädigten Seiten.
* 📝 **Multi-Format Export (Drei Primär-Artefakte):**
  1. **Generisches TEI-P5 XML** (`<job>.tei.xml`) für Langzeitarchivierung und Bibliothekskataloge.
  2. **1:1 Sandwich-PDF** (`<job>.sandwich.pdf`) mit unverändertem Scan und unsichtbarer Textebene (PDF Mode 3).
  3. **Neusatz-PDF** (`<job>.digital.pdf`) via modernem Typst-Vektorsatz.
* 🛠️ **Zwei Korrekturpfade:**
  * **Pfad A:** hOCR-Textkorrektur *vor* dem Zusammenbau des PDFs.
  * **Pfad B:** Direktes Editieren der unsichtbaren Textschicht *im* fertigen PDF via QA-Viewer.
* 🐳 **Multi-Architektur Support:** Native Unterstützung für `linux/amd64` (Server / Proxmox VM) und `linux/arm64` (Apple Silicon M-Serie).

---

## 🔄 Pipeline-Ablauf

```text
Scans (PNG / TIFF / JPEG)
         │
         ▼
 ┌──────────────────────┐
 │ 1. Preprocessing     │ ──► ImageMagick & unpaper (Deskew, Entflecken, Ränder)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 2. Tesseract OCR     │ ──► Lokale OCR-Engine (hOCR, Bounding Boxes, Konfidenz)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 3. Quality Gate      │ ── Konfidenz < 85%? ──► ┌───────────────────────────┐
 └──────────┬───────────┘                          │ 4. Mistral OCR Fallback   │
            │ Pass (>= 85%)                        │ (LLM-Vision Extraktion)   │
            │                                      └─────────────┬─────────────┘
            ├────────────────────────────────────────────────────┘
            │
            ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ Multi-Artifact Assembly & Export                                           │
 ├────────────────────────────┬───────────────────────────┬───────────────────┤
 │ 5. Sandwich PDF Assembly   │ 6. TEI-P5 XML Export      │ 7. Typst Neusatz  │
 │ (OCRmyPDF + img2pdf)       │ (lxml + book.json Schema) │ (book.typ Vektor) │
 └──────────┬─────────────────┴─────────────┬─────────────┴─────────────┬─────┘
            ▼                               ▼                           ▼
   <job>.sandwich.pdf                 <job>.tei.xml               <job>.digital.pdf
 (Original + unsichtbare Ebene)     (Bibliotheksstandard)       (Digitales Lese-PDF)
```

---

## 🛠️ Skripte im Überblick (`scripts/`)

| Skript | Typ | Funktion |
| :--- | :--- | :--- |
| [`run_pipeline.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/run_pipeline.sh) | Bash | Haupt-Orchestrator: steuert Preprocessing, Quality Gate, Fallback, Assembly und JSON-Reporting. |
| [`preprocess.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/preprocess.sh) | Bash | Bereinigt Scans via ImageMagick und unpaper (Deskew, Randentfernung, Kontrast). |
| [`quality_check.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/quality_check.py) | Python | Führt Tesseract aus, analysiert Wort- und Seitenkonfidenzen und entscheidet über Pass/Fallback. |
| [`mistral_ocr.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/mistral_ocr.py) | Python | API-Client für LLM-Vision-Fallback bei schlechter Scanqualität oder komplexen Layouts. |
| [`assemble_sandwich.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/assemble_sandwich.py) | Python | Baut 1:1 Sandwich-PDFs mit unsichtbarer Textebene (Mode 3) aus bereinigten Seitenbildern. |
| [`consolidate_book.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/consolidate_book.py) | Python | Führt Einzelseiten-hOCR/Markdown-Daten in ein einheitliches Zwischenformat (`book.json`) zusammen. |
| [`export_tei.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/export_tei.py) | Python | Generiert standardkonformes TEI-P5 XML für Langzeitarchive und Metadatenkataloge. |
| [`render_digital_pdf.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/render_digital_pdf.py) | Python | Erzeugt ein typografisches Neusatz-PDF mit modernem Schrifsatz via Typst-Engine. |
| [`hocr_correct.py`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/hocr_correct.py) | Python | Ermöglicht hOCR-Textkorrekturen vor dem PDF-Bau (Pfad A). |
| [`sync_storage.sh`](https://github.com/birchville-org/AlexandriaSandwich/blob/main/scripts/sync_storage.sh) | Bash | Synchronisiert Eingabe- und Ausgabedaten optional mit zentralem NAS-/NFS-Storage. |

---

## 🏛️ Architektur & Referenz-Deployment

Das Standard-Setup läuft vollständig auf jedem Entwicklungsrechner mit Docker (`localhost`). In größeren Produktivumgebungen kann AlexandriaSandwich verteilt betrieben werden:

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Control Node / NAS                                          │
 │                                                             │
 │  • n8n Workflow Orchestrator (Docker Container)             │
 │  • Central Storage (NFS/SMB Share für Scans & Artefakte)    │
 └──────────────────────────────┬──────────────────────────────┘
                                │ NFS Mount & REST / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Compute Node (z. B. Proxmox VM "alex" - 16 GB RAM / 4 vCPUs)│
 │                                                             │
 │  • Docker OCR Worker Container (`alexandria_worker`)        │
 │    ├── ImageMagick + unpaper (Deskew & Cleanup)             │
 │    ├── Tesseract OCR (Lokale Primary Engine, hOCR Export)   │
 │    ├── Mistral OCR Client (API-Fallback & Layout Analysis)  │
 │    └── OCRmyPDF / img2pdf / Typst (Artifact Assembly)       │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📖 Dokumentation & weiterführende Links

* 🇩🇪 **Installationsanleitung:** [`INSTALLATION.md`](INSTALLATION.md)
* 🛠️ **Korrekturpfade (Pfad A vs. Pfad B):** [`CORRECTION_PATHS.md`](CORRECTION_PATHS.md)
* ⚡ **n8n Workflow & Betrieb:** [`N8N.md`](N8N.md)
* 🗄️ **Storage & Verzeichnisstruktur:** [`STORAGE.md`](STORAGE.md)
* 🧪 **Pipeline-Verfahren & Historie:** [`WIKI_VERFAHREN.md`](WIKI_VERFAHREN.md)