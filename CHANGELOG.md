# 📓 Changelog: AlexandriaSandwich

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [1.3.0] - 2026-10-12

### Added
- **Job-zentriertes Artefakt-Layout (`data/output/<job>/`):**
  - Vollständige Konsolidierung aller pipeline-generierten Ausgabedateien (PDFs, TEI-P5, EPUB 3, Markdown, JSON, Text, Berichte) in dedizierte Unterverzeichnisse pro Job.
  - Beseitigung unstrukturierter Root-Dateien und veralteter Typ-Verzeichnisse (`pdf/`, `tei/`, `epub/`, `markdown/`, `sidecar/`, `reports/`).
  - Robuste Rückwärtskompatibilität in allen Generatoren und UI-Endpunkten für historische Pfade.
- **Abschlussbericht & Qualitätsaudit (`<job>.report.md`):**
  - Neues Skript `scripts/generate_job_report.py` erstellt nach jedem Pipeline-Lauf einen umfassenden, strukturierten Audit-Bericht.
  - Enthält Executive Summary, formales Qualitätsurteil (Kategorie A: 100% Facsimile-tauglich / Kategorie B / Kategorie C), detaillierte Kommentierung aller 8 Verarbeitungsstufen, aggregierte Konfidenz-Statistik, Outlier- und Schwellenwert-Log sowie ein lückenloses Artefakt-Inventar mit Checksummen und Größen.
  - Vollständige Integration in das Web-Frontend (`ui/templates/job_detail.html`, `ui/main.py`) inklusive In-Browser-Volltextansicht und Direkt-Download.
  - Backfill aller 14 Bestandsjobs im Repository.
- **Deklarative Profile (`job.config.json`):**
  - Formales JSON-Schema `schemas/job.config.schema.json` zur Konfigurationsvalidierung.
  - Automatische Vererbung von Parametern (OCR-Sprachen, Konfidenz-Schwellenwerte, Worker-Limits) und bibliografischen Metadaten (Titel, Autor, Herausgeber, Publikationsjahr, Heuristiken) in `book.json`, `book.md`, TEI-P5, EPUB 3 und Typst Digital PDF.
- **Automatisierte Golden-Master-Regressionssuite (`scripts/test_golden_regression.sh`):**
  - End-to-End-Prüfung aller 6 Phasen: Synthetische PDF-Generierung, Vorverarbeitung, vollständige Pipeline-Ausführung, Artefaktintegrität, Metadaten-Propagation und Web-UI-Serving.
  - Dient als kontinuierlicher Schutz vor Regressionsfehlern bei zukünftigen Erweiterungen.
- **Evolutionäre Maschinerie & Workflow-Dokumentation:**
  - Ausführliche Leitfäden zum evolutionären Entwicklungs- und Härtungsworkflow (`docs/de/EVOLUTION_WORKFLOW.md`, `docs/en/EVOLUTION_WORKFLOW.md`) in deutscher und englischer Sprache.

### Changed & Refactored
- **Pipeline-Orchestrierung (`scripts/run_pipeline.sh`):**
  - Automatische Profil-Erkennung (`data/input/<job>/job.config.json`) mit dynamischer Parameterübergabe an nachgelagerte Stufen.
  - Direkte Aufrufe von `generate_job_report.py` am Ende jedes Pipeline-Laufs.
- **Web-UI & Dashboard (`ui/main.py`, `ui/templates/job_detail.html`):**
  - Dynamische Erkennung und Anzeige des Abschlussberichts (`<job>.report.md`) in der Artefakt-Tabelle und als strukturierte Detailsektion.
  - Sichere Dateiauflösung und Pfadabsicherung über job-zentrierte Verzeichnisse.
- **Progress-Tracker (`scripts/job_progress.py`):**
  - Umstellung der Artefakt-Auflösung auf job-zentrierte Pfade mit Fallback auf Root-/Legacy-Pfade.

### Fixed & Hardened
- **PyMuPDF / PIL Vektor-Einbettung (`scripts/assemble_sandwich.py`):**
  - Robuster Fallback via `fitz.Pixmap` und `PIL.Image`, falls `page.insert_image(stream=...)` an defekten JPEG2000-Codecs scheitert.
- **Typst-Kompatibilität (`scripts/render_digital_pdf.py`):**
  - Anpassung der Metadaten-Übergabe an Typst 0.15.1 (`--input key=val` anstelle von veralteten Konstrukten).
- **Security Scanner & Pre-Push Gate:**
  - Validierung aller 129 Projektdateien gegen Leaks von privaten IP-Adressen, Pfaden und Secrets via `scripts/security_check.py`.

## [1.2.1] - 2026-10-09

### Added
- **Zweigleisige Rekonstruktions-Pipeline (`scripts/run_pipeline.sh`):**
  - **Pfad A (Perfect Sandwich):** `scripts/build_perfect_sandwich.py` trennt Text- und Bildblöcke automatisch, binarisiert den Hintergrund auf 98 % Weißgrad (Beseitigung von Scan-Schatten und Daumenabdrücken) und bettet eine unsichtbare, koordinatengenaue Vektor-Textebene ein.
  - **Pfad B (Semantic Typeset Edition):** `scripts/build_typeset_edition.py` erzeugt einen freilaufenden, zweispaltigen Typst-Neusatz (Boethlingk-Architektur) mit zentriertem vertikalem Mittelstrich (`grid.vline`), dynamischer Kolumnentrennung und automatischer Devanāgarī-Font-Kaskade.
- **Automatische TOC- & Metadaten-Injection (`scripts/inject_toc.py`):**
  - Injiziert hierarchische Lesezeichen (Outlines), Dokument-Metadaten und Seitennummerierungs-Labels (r/D) in alle generierten PDFs (`.sandwich.pdf`, `.aligned.pdf`, `.digital.pdf`, `.perfect_sandwich.pdf`, `.typeset_edition.pdf`).
  - Unterstützt manuelle `toc.json` sowie automatischen Fallback auf Gliederungen und Metadaten aus `book.json`.

### Security & Hardening
- **Web UI & API Sicherheitsarchitektur (`ui/main.py`):**
  - **Path-Traversal-Schutz:** Strikte Validierung von `job` (`_validate_job`) und `run_id` (`_validate_run_id`) über alle Routen; Absicherung aller Dateizugriffe und Löschoperationen mit `Path.is_relative_to()`.
  - **Upload-Schutz:** Streaming-Upload in 1-MB-Chunks (`_save_upload_file`) mit 500 MB Größenlimit, CSRF-Origin-Prüfung (`_check_csrf_origin`) und Schutz vor ZIP-Bomben (`MAX_ZIP_ENTRIES`, `MAX_ZIP_UNCOMPRESSED`).
  - **Open-Redirect-Prävention:** Weiterleitungsziele auf relative Pfade innerhalb derselben Domain beschränkt.
  - **Header-Encoding:** RFC-5987 / RFC-6266 konforme `Content-Disposition`-Header für Downloads.

### Fixed & Changed
- **Seitenvorschau-Fix (`ui/main.py`):** `job_preview_page` auf `pdftoppm -singlefile` im Thread-Pool (`asyncio.to_thread`) umgestellt; eliminiert pdftoppm-Dateinamensfallen und blockiert den Event-Loop nicht mehr.
- **Pipeline-Guards:** Caching-Guards für Vorverarbeitung und Qualitätsprüfungen in `scripts/run_pipeline.sh` ergänzt.
- **Terminologie-Refactoring:** Unspezifische Bezeichnungen durch präzise Fachbegriffe ersetzt (`sandwich`, `aligned`, `pre-assembly`, `post-assembly`).


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