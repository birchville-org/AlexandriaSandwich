# 📓 Changelog: AlexandriaSandwich

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [1.2.1] - 2026-10-09

### Changed
- **Terminologie-Refactoring (Sandwich & Aligned):**
  - Unspezifische Begriffe „Weg A / Weg B“ und „Path A / Path B“ durch präzise Fachbegriffe ersetzt:
    - Standard-Faksimile: `<job>.sandwich.pdf`
    - KI-synchronisiertes Faksimile: `<job>.aligned.pdf`
    - Vor-Montage-Ebene: „Pre-Assembly hOCR-Korrektur“ (`scripts/hocr_correct.py`)
    - Nach-Montage-Ebene: „Post-Assembly Textlayer-Korrektur“ (`scripts/pdf_text_correct.py`, `scripts/align_mistral_pdf.py`)
  - Volle Abwärtskompatibilität: Pipeline-Reports und UI erkennen weiterhin bestehende `.pathb.pdf`-Artefakte nahtlos.

## [1.2.0] - 2026-09-28

### Added
- **Vollständige 7-Zielformat-Matrix & Duale Rekonstruktion:**
  - **Reflowable EPUB 3 eBook (`scripts/export_epub.py`):** Semantisches XHTML5, hierarchische Navigation (`nav.xhtml` und `toc.ncx`) sowie eingebettete Vektor-Schriften (*Noto Serif Devanagari* Regular/Bold & *Linux Libertine O* Regular/Bold/Italic) für perfekte Darstellung von Devanagari und IAST-Diakritika auf Mobilgeräten und E-Readern.
  - **Automatisches Weg B Token-Alignment (`scripts/align_mistral_pdf.py`):** Synchronisiert Tesseract-Bounding-Boxes direkt im PDF-Inhaltsstrom mit KI-erkannter Mistral-Semantik. Beseitigt Rausch-Halluzinationen (z. B. auf gepunkteten Zeilen) und garantiert 1:1 Koordinatentreue bei 0 Rauschen.
  - **Typst Vektor-Neusatz (`scripts/render_digital_pdf.py`, `templates/book.typ`):** A5-Buchlayout mit automatischer Devanagari-Font-Kaskade und robuster Zeichen-Maskierung.
  - **TEI-P5 XML Archivformat (`scripts/export_tei.py`):** Standardkonforme Strukturierung (`teiHeader`, `pb`, `div`, `head`, `p`) nach Vorgaben der Digital Humanities.
  - **Single Source of Truth AST (`book.json`, `book.md`):** Universeller Zwischenstand mit Bounding-Boxes zur Nachgenerierung aller Formate ohne Re-OCR.
- **Batch Mistral OCR mit Parallelisierung & Caching (`scripts/mistral_ocr.py`):**
  - Parallele ThreadPool-Abarbeitung (`--batch-dir`, `--workers`).
  - Automatisches Rate-Limit-Handling mit exponentiellem Backoff bei HTTP 429.
  - Persistentes Caching (`*.mistral.md`), um redundante API-Kosten zu vermeiden.
- **Web UI & Upload-Erweiterungen (`ui/`):**
  - Vollständige Zielformat-Matrix auf der Upload- (`upload.html`) und Job-Detailseite (`job_detail.html`).
  - Direkte Download- und Vorschauaktionen für `.epub`, `.pathb.pdf`, `.digital.pdf`, `.tei.xml`, `book.json` und `book.md`.
  - Direkte Navigation vom Upload-Ergebnis zur Buchansicht.
  - Sprachprofil `deu+san` (Deutsch + Sanskrit Devanagari) als Schnellwahl.
- **End-to-End-Produktionsvalidierung:**
  - Erfolgreiche Konvertierung und Validierung eines 176-seitigen Sanskrit-Grammatikbands über alle 7 Zielformate.

## [1.1.0] - 2026-09-26

### Added
- **3-Schritte-Schnellstart:** Direkter Einstieg ohne Vorbedingungen (`clone -> compose up -> test run`) in `README.md`, `docs/de/index.md` und `docs/en/index.md`.
- **Beispieldaten:** Lizenzfreie synthetische Testseiten (`examples/sample_book/`) samt Dokumentation für sofortige Pipeline-Tests.
- **Konsolidiertes Docker Compose Setup:**
  - Services `ui` und `n8n` über Compose-Profile (`--profile ui`, `--profile n8n`, `--profile all`) in `docker-compose.yml` integriert.
  - Automatisches Lifecycle-Management des Docker-Netzwerks `alexandria_default`.
  - Relative Host-Mounts (`./data`, `./templates`, `./examples`) als universeller Standard.
- **Pipeline-Transparenz:**
  - Ablaufdiagramm aller Pipeline-Stufen in Text-/ASCII-Form.
  - Referenztabelle aller Skripte in `scripts/` mit Typ und Funktionsbeschreibung.
- **Vollständige `.env.example`:** Dokumentation aller Umgebungsvariablen (`MISTRAL_API_KEY`, `OCR_LANG`, `OCR_CONFIDENCE_THRESHOLD`, `DATA_DIR`, `PORT_UI`, `PORT_N8N`, `N8N_HOST`).

### Fixed
- Kaputter Dokumentationslink in `README.md` und `CHANGELOG.md` korrigiert (`docs/de/INSTALLATION.md`).
- Tippfehler `fallsFallback` in `docs/de/INSTALLATION.md` bereinigt.
- Umgebungsspezifische Pfade und Hostnamen in den Referenz-Bereich ausgelagert.

## [1.0.0] - 2026-09-26

### Added
- **Multi-Artifact Pipeline (Phase 5 / Milestone 3):**
  - Generisches TEI-P5 XML (`scripts/export_tei.py`) mit Facsimile- und Textstruktur.
  - 1:1 Sandwich-PDF (`scripts/assemble_sandwich.py`) mit verlustfreiem Scan und unsichtbarer Textebene.
  - Digitales Neusatz-PDF (`scripts/render_digital_pdf.py`) via Typst 0.11+ und modularem Template (`templates/book.typ`).
  - AST-Konsolidierung (`scripts/consolidate_book.py`) zu `book.json` und `book.md`.
- **End-to-End Orchestrierung & UI:**
  - Fast-API Web-UI (`ui/`) mit Dashboard, QA-Viewer und 3-Artefakt-Detailansicht.
  - n8n Orchestrierungsworkflow (`workflows/n8n_ocr_pipeline.json`).
  - Vollständiges CLI-Harness (`scripts/run_pipeline.sh`).
- **Dokumentations-Infrastruktur:**
  - Zweisprachige MkDocs-Material-Dokumentation (DE & EN) mit Sprachumschalter (`mkdocs.yml`, `docs/de/`, `docs/en/`).
  - GitHub Actions Workflow (`.github/workflows/docs.yml`) für automatisches Deployment auf GitHub Pages.
  - Detaillierte Installationsanleitung (`docs/de/INSTALLATION.md`).

## [0.1.1] - 2026-07-20

### Changed
- **Preprocess stack:** replaced ScanTailor (GUI-only) with headless **ImageMagick deskew + unpaper** (`scripts/preprocess.sh`).
- Slimmed `docker/worker/Dockerfile` (dropped Qt/ScanTailor source build) for smaller multi-arch images.

### Added
- `scripts/quality_check.py` — Tesseract confidence gate (default 85%).
- `scripts/mistral_ocr.py` — Mistral OCR API fallback (`mistral-ocr-latest`).
- Deploy target documented: `alex.local`.

## [0.1.0] - 2026-07-20

### Added
- Initiales Repository-Setup mit idempotenten Setup-Skripten (`setup_project.sh`).
- GSD-Framework-Spezifikation (`.gsd/SPEC.md`) und Agenten-Kontext (`.agent/CONTEXT.md`).
- Multi-Architektur Dockerfile für den OCR-Worker (Unterstützung für Apple Silicon M2 & Intel x86_64).
- Integration des Python SDKs für **Mistral OCR** (`mistralai`) als High-Precision Fallback Engine.
- VS Code Workspace-Isolation und Remote-Hermes Integration.