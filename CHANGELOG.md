# 📓 Changelog: AlexandriaSandwich

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [1.7.0] - 2026-10-23

### Added
- **Content-Aware Margin Masking (`scripts/build_perfect_sandwich.py`):**
  - Dynamische Erkennung des Textkörperbereichs pro Seite aus Mistral-JSON-BBoxes bzw. PyMuPDF-Wortvektoren.
  - Vollständige Eliminierung von Buchfalzen, Schatten, Bindungsstreifen und Scannerkanten außerhalb des Satzspiegels (`pad_x=75, pad_y=60`).
  - Mehrskaliges Hintergrund-Leveling mit Re-Nivellierung auf Reinweiß (`#FFFFFF`).
- **Layout-gesteuerte Neusatz-Kalibrierung (`scripts/render_digital_pdf.py`, `templates/book.typ`):**
  - Automatischer Einzug bei Absatzbeginn (`first-line-indent: 1.5em`).
  - Zentrierte Dokumententitel auf Satzspiegelmitte.
  - Symmetrische Drei-Spalten-Kopfzeilen mit Devanāgarī-Paginierung.
  - Automatische Erkennung, Abtrennung und Formatierung von Fußnoten am Seitenende.
- **Visuelle Side-by-Side-Differenzprüfungen (`scripts/compare_layout.py`):**
  - Automatisches Rendern von Vergleichsbildern (Faksimile vs. digitaler Neusatz) in `comparison_samples/`.

### Changed
- **Kausale Pipeline-Orchestrierung (`scripts/run_pipeline.sh`):**
  - Strikt sequentielle Reihenfolge: `assemble_sandwich` -> `consolidate_book` -> `align_mistral_pdf` -> `build_perfect_sandwich` -> `profile_source_layout` -> `render_digital_pdf` -> `inject_toc` -> `audit_layout_concordance` -> `compare_layout`.
  - Layout-Profilierung und Audit greifen priorisiert direkt auf das bereinigte `perfect_sandwich.pdf` zu.

## [1.6.0] - 2026-10-18

### Added
- **Perfect Sandwich PDF Builder (`scripts/build_perfect_sandwich.py`):**
  - Verlusterhaltendes PDF-Sandwich-Verfahren mit adaptiver Histogramm-Glättung und zlib-FlateDecode-Kompression.
  - Exakte Text-Positionierungsmatrix mit horizontaler Skalierung (`Tz`) und Wortabstandskompensation für pixelgenaue Durchsuchbarkeit.
- **Deklarativer 2D-Layout-Profiler & Konkordanz-Auditor (`scripts/profile_source_layout.py`, `scripts/audit_layout_concordance.py`):**
  - Automatisierte geometrische Profilierung historischer Quellscans (Satzspiegel, Randbreiten, Zeilenhöhen, Spaltenraster).
  - Strenges Konkordanz-Quality-Gate zur formalen Validierung von Seitenkongruenz und Zeilendichte zwischen Faksimile und digitalem Neusatz.
- **1:1 Typst Digital Reconstruction Engine (`scripts/render_digital_pdf.py`, `templates/book.typ`):**
  - Satzspiegelgetreue typografische Rekonstruktion mit Marginal-Sideheads, Initialen/Drop-Numerals, strukturierten Lehrplan-Syllabi, kalligrafischen Glyphen-Rastern sowie Titel- und Imprint-Makros.
- **Automatisierte UI-Sicherheits- & Concurrency-Testsuite (`tests/test_ui_safety.py`):**
  - Umfassende Pytest-Suite zur Absicherung von Path-Traversal-Prävention, Job-Sperren, Request-Validierung und dynamischem CSRF-Origin-Matching.

### Changed
- **Pipeline-Orchestrierung (`scripts/run_pipeline.sh`, `scripts/test_golden_regression.sh`):**
  - Nahtlose Integration des Perfect-Sandwich-Generators und Layout-Profilers in den standardmäßigen Pipeline-Durchlauf und die Golden-Master-Regressionssuite.
- **Dokumentations-Portal & Birchville Scholarly Synthesis:**
  - Standardisiertes Curation-Badge und responsives Quick-Access-Grid für das MkDocs-Portal gemäß Birchville Corporate Design.

### Security
- **Web-UI Concurrency & Härtung (`ui/main.py`):**
  - Implementierung asynchroner Concurrency-Locks (`asyncio.Lock`) und prozessweiter File-Locks (`.lock`), um Race-Conditions bei parallelen Job-Starts zu verhindern.
  - Strikte Wertebereichs- und Längenprüfungen für alle Request-Parameter.
  - Dynamischer CSRF-Schutz mit konfigurierten Whitelist-Origins statt statischer Host-Prüfung.
- **Container-Sicherheit (`docker-compose.yml`, `deploy/docker-compose.n8n.yml`):**
  - Standardmäßige Bindung aller exponierten Ports an `127.0.0.1` zur Vermeidung unbeabsichtigter Netzwerkfreigaben.

## [1.5.0] - 2026-10-16

### Added
- **Universal IIIF Presentation & Image Ingestion (`scripts/import_iiif.py`):**
  - Vollständige IIIF Presentation API v2 und v3 Unterstützung für digitale Bibliotheksbestände (UB Heidelberg, British Library, BnF Gallica, BSB München).
  - Paralleler Download von Hochauflösungs-Scans mit exponentiellem Backoff und `/full/max/` auf `/full/full/` Fallback.
  - Automatische Metadaten-Extraktion (Titel, Autor, Editor, Jahr, Manifest-URI) sowie Generierung von `job.config.json` und `iiif_pages.json`.
- **Kanonisches Sequence-Matching & Alignment (`scripts/align_canonical.py`):**
  - Universalisiertes Verfahren zur präzisen Synchronisation von OCR-Extrakten mit kanonischen Referenzdatenbanken (Sūtrapāṭha, Dhātupāṭha, Wörterbuch-Indices).
  - Sequentieller Tracker mit Erkennung von Abschnittsgrenzen, Multi-Script-Ziffern (Devanāgarī, Telugu, Gujarati, Arabisch) und Konfidenz-Audit.
- **TEI-P5 IIIF-Faksimile-Integration (`scripts/export_tei.py`):**
  - Vollständige dynamische Auflösung von `<pb n="..." facs="..."/>` über `iiif_pages.json` oder `iiif_template`.
  - Semantische Einbettung von IIIF-Manifest-Referenzen in `<sourceDesc>`.
- **Heuristische Text- & Scanbereinigung (`scripts/consolidate_book.py`):**
  - Automatische Filterung von Bibliotheks-Wasserzeichen, Scanbalken und Förderer-Logos (`strip_library_boilerplates`).
  - Bereinigung von typografischem Schrift-Drift (Hebräisch/Telugu-Rauschen auf beschädigten Diakritika, `strip_rogue_scripts`).
- **Typografisches Mehrspalten-Layout & Hermetisches Font-Vendoring (`scripts/render_digital_pdf.py`, `templates/book.typ`):**
  - Abschnittsspezifischer Vektor-Neusatz: 1-spaltige Prosa für Vorspann/Einleitung, 2-spaltiges Wörterbuch-Grid mit Trennlinie (`grid.vline`) für Lexika und Wortlisten (`dictionary_grid`).
  - Unterstützung für hermetisches Font-Vendoring via `--font-path` (Priorisierung von Noto Serif Devanagari und Linux Libertine O).

## [1.4.0] - 2026-10-16

### Added
- **Generischer 1:1 Vektor-Neusatz & Page-Preservation (`scripts/render_digital_pdf.py`):**
  - Universeller digitaler Neusatz mit strenger 1:1 Seitenkongruenz zum historischen Original (`--preserve-pages`).
  - Responsiver `#page_content`-Layoutmechanismus in `templates/book.typ` mit dynamischer Breitenbindung und Skalierung zur sicheren Vermeidung von Seitenüberläufen.
  - Sichere Wiederherstellung von Code-Spans und typografischen Satzzeichen ohne Backslash-Drift.
- **Hierarchisches TOC-Outline-Quality-Gate (`scripts/inject_toc.py`):**
  - Automatisierte Injektion hierarchischer PDF-Lesezeichen (Outlines/Bookmarks), Metadaten und nativer Page-Labels (römisch/arabisch) über alle PDF-Artefakte.
  - Automatische Ebenen-Normalisierung (Ebene 1-Initialisierung, Sprungkorrektur), um `ValueError`-Abbrüche bei manuell editierten TOCs zu verhindern.
  - Fallback-Extraktion von Kapitelüberschriften (`h1`/`h2`) aus `book.json` sowie Bereitstellung editierbarer `<job>.toc.txt`-Dateien zur verlustfreien Re-Injektion.
  - Transparente Warnmeldungen bei leerer Outline und `--require-toc`-Prüfmodus.
- **Sicherheits- & Pipeline-Härtung (`scripts/run_pipeline.sh`):**
  - Beseitigung von Command-Injection-Risiken beim Einlesen von `job.config.json` via `shlex.quote` und Regex-Whitelisting.
- **Zentrale Artefakt- & Qualitätsmatrix (`docs/de/PIPELINE_ARTIFACTS.md`, `docs/en/PIPELINE_ARTIFACTS.md`):**
  - Umfassender Katalog aller 7 Artefaktkategorien der AlexandriaSandwich-Pipeline (Preprocessed, OCR-Layer, Buchmodell, Faksimile-Sandwich, Vektor-Neusatz, TEI-P5/EPUB, Audit-Berichte).
  - Formales Reifegrad-Dashboard zur transparenten Dokumentation des kontinuierlichen Verbesserungsprozesses (CIP).
- **Birchville Design-System Layout-Integration:**
  - Aktivierung des integrierten linken Inhaltsverzeichnisses (`toc.integrate`) in `mkdocs.yml` gemäß Birchville „Scholarly Synthesis“ Standard.

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
  - Robuster Fallback via `pymupdf.Pixmap` und `PIL.Image`, falls `page.insert_image(stream=...)` an defekten JPEG2000-Codecs scheitert.
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