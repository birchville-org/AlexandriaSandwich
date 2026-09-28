# 📚 AlexandriaSandwich

> **Automatisierte Buch-Digitalisierung mit Hybrid-OCR (Tesseract + Mistral AI), GSD-Pipeline & Perfect Sandwich-PDF Output.**

![Build Status](https://img.shields.io/badge/docker-multi--arch-blue)
![Release](https://img.shields.io/badge/release-v1.2.0-blue)
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
  * **KI-Fallback:** Automatischer Wechsel auf **Mistral OCR (`mistral-ocr-latest`)** bei schlechten Scores (< 85% Confidence), Fraktur* 📝 **Multi-Format Export (Vollständige Zielformat-Matrix):**
  1. **1:1 Sandwich-PDF (Weg A & Weg B):** Unverändertes Faksimile mit unsichtbarem Textlayer (`<job>.sandwich.pdf`) bzw. semantisch mit Mistral OCR synchronisierter Textlayer ohne Rauschzeilen (`<job>.pathb.pdf`).
  2. **Reflowable EPUB 3 eBook:** Für Mobilgeräte und E-Reader (`<job>.epub`) mit 102+ Kapiteln und eingebetteten Unicode-Schriften (*Noto Serif Devanagari* + *Linux Libertine O*).
  3. **Digitales Neusatz-PDF:** Typografisch optimierter Vektorneusatz (`<job>.digital.pdf`) via Typst-Engine.
  4. **TEI-P5 XML:** Standardkonformes Archivformat (`<job>.tei.xml`) für Bibliotheken und Digital Humanities.
  5. **Semantischer AST & Markdown:** Strukturierte `book.json` (Single Source of Truth mit Bounding-Boxes) sowie bereinigtes `book.md` für KI- und Textpipelines.
  *(Siehe Dokumentation: [Zielformat-Architektur & Duale Reproduktion](docs/de/TARGET_FORMATS.md))*
* 🛠️ **Zwei Korrekturpfade:**
  * **Pfad A:** hOCR-Textkorrektur *vor* dem Zusammenbau des PDFs.
  * **Pfad B:** Direktes Token-Alignment und Editieren der unsichtbaren Textschicht *im* fertigen PDF via pikepdf & QA-Viewer.
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
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Multi-Artifact Assembly & Target Exports                                               │
 ├────────────────────────────┬───────────────────────────┬───────────────┬───────────────┤
 │ 5. Sandwich PDF Assembly   │ 6. TEI-P5 XML Export      │ 7. Typst Satz │ 8. EPUB 3     │
 │ (OCRmyPDF + Weg B Align)   │ (lxml + book.json Schema) │ (book.typ)    │ (Font Inlined)│
 └──────────┬─────────────────┴─────────────┬─────────────┴───────┬───────┴───────┬───────┘
            ▼                               ▼                     ▼               ▼
   <job>.sandwich / pathb.pdf        <job>.tei.xml          <job>.digital.pdf <job>.epub
 (Faksimile + korrigierter Text)  (Akademie-Standard)    (Vektor-Neusatz)  (eBook Mobil)
```

---

## 🛠️ Skripte im Überblick (`scripts/`)

| Skript | Typ | Funktion |
| :--- | :--- | :--- |
| [`run_pipeline.sh`](scripts/run_pipeline.sh) | Bash | Haupt-Orchestrator: steuert Preprocessing, Quality Gate, Fallback, Assembly und Multi-Format-Exporte. |
| [`align_mistral_pdf.py`](scripts/align_mistral_pdf.py) | Python | Weg B: Synchronisiert Mistral-Text mit Tesseract-Bounding-Boxes direkt im PDF-Inhaltsstrom. |
| [`export_epub.py`](scripts/export_epub.py) | Python | Baut standardkonformes EPUB 3 mit semantischem XHTML und eingebetteten Unicode-Schriften. |
| [`render_digital_pdf.py`](scripts/render_digital_pdf.py) | Python | Erzeugt ein typografisches Neusatz-PDF mit modernem Schriftsatz via Typst-Engine. |
| [`export_tei.py`](scripts/export_tei.py) | Python | Generiert standardkonformes TEI-P5 XML für Langzeitarchive und Metadatenkataloge. |
| [`consolidate_book.py`](scripts/consolidate_book.py) | Python | Führt Einzelseiten-hOCR/Markdown-Daten in ein einheitliches Zwischenformat (`book.json` / `book.md`) zusammen. |
| [`mistral_ocr.py`](scripts/mistral_ocr.py) | Python | Parallelisierter API-Client für LLM-Vision mit exponentiellem Backoff und Caching. |
| [`assemble_sandwich.py`](scripts/assemble_sandwich.py) | Python | Baut 1:1 Sandwich-PDFs mit unsichtbarer Textebene (Mode 3) aus bereinigten Seitenbildern. |
| [`quality_check.py`](scripts/quality_check.py) | Python | Führt Tesseract aus, analysiert Wort- und Seitenkonfidenzen und steuert das Quality Gate. |
| [`preprocess.sh`](scripts/preprocess.sh) | Bash | Bereinigt Scans via ImageMagick und unpaper (Deskew, Randentfernung, Kontrast). |
| [`hocr_correct.py`](scripts/hocr_correct.py) | Python | Ermöglicht hOCR-Textkorrekturen vor dem PDF-Bau (Pfad A). |
| [`pdf_text_correct.py`](scripts/pdf_text_correct.py) | Python | Low-Level-Stream-Editor für Post-Processing-Textkorrekturen in generierten PDFs (Pfad B). |
| [`sync_storage.sh`](scripts/sync_storage.sh) | Bash | Synchronisiert Eingabe- und Ausgabedaten optional mit zentralem NAS-/NFS-Storage. |

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

* 🇩🇪 **Installationsanleitung (DE):** [`docs/de/INSTALLATION.md`](docs/de/INSTALLATION.md)
* 🇬🇧 **Installation Guide (EN):** [`docs/en/INSTALLATION.md`](docs/en/INSTALLATION.md)
* 🛠️ **Korrekturpfade (Pfad A vs. Pfad B):** [`docs/de/CORRECTION_PATHS.md`](docs/de/CORRECTION_PATHS.md)
* ⚡ **n8n Workflow & Betrieb:** [`docs/de/N8N.md`](docs/de/N8N.md)
* 🗄️ **Storage & Verzeichnisstruktur:** [`docs/de/STORAGE.md`](docs/de/STORAGE.md)
* 📚 **Vollständige MkDocs Dokumentation:** [`docs/de/index.md`](docs/de/index.md)