# 🏛️ Systemarchitektur: AlexandriaSandwich

Diese Dokumentation beschreibt die technische Architektur, den Datenfluss und die Schnittstellen von **AlexandriaSandwich**.

---

## 1. Systemübersicht & Topologie

Das System ist in eine **Control Node** (NAS), eine **Compute Node** (Proxmox Hypervisor) und eine **Dev Node** (Mac mini M2) unterteilt.

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Dev Node (Mac mini M2)                                      │
 │                                                             │
 │  • VS Code IDE (Workspace Isolation)                        │
 │  • Local AI Agents (Hermes via Remote / Claude 3.5 Sonnet)  │
 │  • Docker Buildx (ARM64 & AMD64 Cross-Compilation)          │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Git / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Control Node (NAS)                                          │
 │                                                             │
 │  • n8n Workflow Orchestrator (Docker Container)            │
 │  • Central Storage (NFS/SMB Share)                          │
 │    ├── /data/input       (Unverarbeitete Scans)             │
 │    ├── /data/processing  (Temp-Cache auf NVMe)              │
 │    └── /data/output      (Fertige Sandwich-PDFs + MD)       │
 └──────────────────────────────┬──────────────────────────────┘
                                │ NFS Mount & REST / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Compute Node (Proxmox VM "alex" - 16GB RAM / 4 vCPUs)       │
 │                                                             │
 │  • Docker OCR Worker Container (`alexandria_worker`)        │
 │    ├── ImageMagick + unpaper (Deskew & Cleanup)             │
 │    ├── Tesseract OCR (Lokale Primary Engine, hOCR Export)   │
 │    ├── Mistral OCR Client (API-Fallback & Layout Analysis)  │
 │    └── OCRmyPDF / img2pdf (PDF Sandwich Assembly)           │
 └─────────────────────────────────────────────────────────────┘
```

---

## 2. Die Dual-Branch Architektur (Faksimile vs. Vektor-Neuedition)

AlexandriaSandwich löst das historische Dilemma zwischen archivalischer Beweiskraft und moderner Lesbarkeit durch zwei autarke Verarbeitungszweige:

```text
                           ┌──────────────────────────┐
                           │   Bereinigte Rohscans    │
                           └────────────┬─────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
 [ ZWEIG 1: FAKSIMILE-EBENE ]                           [ ZWEIG 2: VEKTOR-NEUEDITION ]
 • OCRmyPDF + Tesseract / Mistral                       • scripts/align_*.py (Fuzzy Match)
 • Text Rendering Mode 3 (unsichtbar)                   • scripts/build_typeset_edition.py
 • 100 % 1:1 Pixelauthentizität                         • Sektionsspezifischer Typst-Satz
 └──► *.perfect_sandwich.pdf                             └──► *.typeset_edition.pdf
```

1. **Zweig 1: Faksimile-Ebene (`*.perfect_sandwich.pdf`):**
   * Das historische Druckbild wird durch **Content-Aware Margin Masking** von störenden Buchfalzen, Schatten und Scannerkanten außerhalb des Textbereichs bereinigt und auf Reinweiß nivelliert.
   * Der unsichtbare Textlayer liegt auf pixelgenauen Bounding-Boxen der Originalzeilen (Mode 3).
   * Dient als bereinigte Referenzbasis für die automatische Vermessung via `profile_source_layout.py`.
2. **Zweig 2: Semantische Vektor-Neuedition (`*.digital.pdf` & `*.typeset_edition.pdf`):**
   * Kalibriert Typst-Satzspiegel, Durchschuss, Kolumnentitel und Paginierung direkt aus den Messwerten des bereinigten Faksimiles.
   * Semantisches Alignment gegen kanonische Ground-Truth-Datenbanken (z. B. `dhatupatha_canonical.json`, `sutras.json`) oder strukturierte `book.json` ASTs.
   * Typografische Standards: zentrierte Haupttitel, Einrückung bei Absatzbeginn (`1.5em`), symmetrische Kopfzeilen mit Original-Paginierung (Devanāgarī/Arabisch) und automatische Fußnotenabtrennung am Seitenende.

---

## 3. Headless Linux & Hermetisches Font-Vendoring

Für reproduzierbare, fehlerfreie Vektor-Kompilierung auf Headless-Linux-Servern (`alex.local`, Ubuntu 24.04 Docker-Worker):
* **Schrift-Vendoring:** Freie OpenType-Master-Schriften liegen direkt in `data/fonts/` (`NotoSerifDevanagari-*.ttf`, `LinLibertine_*.otf`).
* **Typst-Invocation:** Automatische Übergabe von `--font-path data/fonts` eliminiert Tofu-Zeichen (`?`).
* **Container-Abhängigkeiten:** `fonts-noto-extra` (APT) stellt sicher, dass indische Schriftsysteme unter Linux verfügbar sind; `pymupdf` (PIP) übernimmt Bounding-Box-Audits.
* **Volume-Mount:** `/opt/alexandria/data:/opt/alexandria/data:ro` in Docker Compose gewährt dem Worker Zugriff auf Schriften und kanonische Datenbanken.

---

## 4. Storage & Schnittstellen

* **Speicher-Architektur:** Siehe **[docs/STORAGE.md](docs/STORAGE.md)** für NFS-Mounts (`mount_nfs.sh`), rsync-Fallback (`sync_storage.sh`) und Ansible-Variablen.
* **Zielformate:** Siehe **[docs/de/TARGET_FORMATS.md](docs/de/TARGET_FORMATS.md)** für die 4-Ebenen-Pyramide und die 7-Artefakt-Matrix.
* **Fallstudien:** 
  * [Pāṇinis Grammatik (Otto von Böhtlingk 1887)](docs/de/case-study.md)
  * [Dhātu-Pāṭha nach dem Böhtlingk-Standard](docs/de/case-study-dhatupatha.md)
  * [Bṛhadāraṇyaka-Upaniṣad I.4](docs/de/case-study-bau.md)

---

## 5. Das Prinzip der Evolutionären Maschinerie (Engine vs. Payload)

AlexandriaSandwich folgt dem Paradigma einer **universellen, lernenden Pipeline-Engine**:
Skripte werden **niemals pro Job isoliert oder geforkt**. Jedes neue Dokument dient als Härtungstest für die zentrale Maschinerie in `scripts/`.

### 5.1 Strikte Trennung von Maschinerie und Nutzlast
1. **Zentrale Engine (`scripts/`):** Vollständig zustandslose, modulare Verarbeitungsstufen (Preprocessing, Quality Gate, OCR-Fallback, Sandwich-Assembly, Alignment, Vektor-Neusatz, TEI/EPUB-Export).
2. **Deklarative I/O-Behälter (`data/`):**
   * `/data/input/<job>/`: Eingehende Rohscans und optionale Profilkonfiguration (`job.config.json`).
   * `/data/processing/`: Temporärer Scratch-Cache (Preprocessed PNGs, hOCR, TSV, JSONL).
   * `/data/output/<job>/`: Alle fertigen Zielartefakte eines Jobs konzentriert an einem Ort.

### 5.2 Merkmalsbasierte Heuristiken (Feature Detection statt Job-Branching)
Um "Overfitting" und Spaghetti-Code zu verhindern, sind Verzweigungen nach konkreten Job-Namen (`if job == "xyz"`) im Code verboten. Problemlösungen müssen als **Merkmalserkennung** modelliert werden:
* **Spaltentrennung:** Erkennung über geometrische Projektionsprofile statt hartcodierter Bounding-Boxes.
* **Schriftsysteme:** Automatische Skript-Erkennung (Devanagari vs. Latein/IAST) via Unicode-Blockverteilung und Tesseract OSD.
* **Satzspiegel & Apparate:** Erkennung von Fußnotenblöcken und kritischen Apparaten über relative Zeilenabstände und Schriftgradstufen.

### 5.3 Deklarative Job-Profile (`job.config.json`)
Spezifische Randbedingungen eines Buchs (z. B. Sprachkombination `deu+san`, Konfidenz-Schwellenwert, Bindebreite für den Gutter-Crop) werden deklarativ im Eingangsverzeichnis hinterlegt:

```json
{
  "lang": "san+deu",
  "threshold": 90,
  "use_mistral": true,
  "use_unpaper": true,
  "template": "dictionary_two_column",
  "toc_offset": 14
}
```
Die Pipeline liest diese Parameter beim Start ein, bleibt im Programmcode jedoch 100 % generisch.

### 5.4 Das Regressions-Gate (Golden-Master-Prinzip)
Wird die Pipeline zur Bewältigung eines neuen Dokuments verfeinert, muss die bestehende Qualität etablierter Referenzjobs (`alex_smoke`, `stenzler_10p`, `katha_06`) unverändert bestehen bleiben. Automatische Testläufe (`scripts/test_golden_regression.sh`) sichern die Engine gegen funktionale Regressionen ab.

### 5.5 Der Standardisierte Abschlussbericht (`<job>.report.md`)
Am Ende jedes Pipeline-Durchlaufs generiert die Engine automatisch einen strukturierten, wissenschaftlichen Abschlussbericht (`data/output/<job>/<job>.report.md`). Dieser enthält:
1. **Executive Summary & Qualitätsurteil:** Gesamtmetriken, Schwellenwert-Quote, philologische Einstufung (Kategorie A/B/C).
2. **Bibliographische & Technische Stammdaten:** Titel, Autor, Editor, Jahr, Sprache, Layout-Heuristiken.
3. **Chronologische Kommentierung der Einzelschritte:** Detaillierte Würdigung aller 8 Stufen (Ingress bis EPUB 3/TOC).
4. **Per-Page Qualitätsanalyse:** Zeichenkonfidenz-Statistik, Schwellenwert-Entscheidungen, Ausreißerseiten mit Handlungsempfehlungen.
5. **Artefakt-Inventar:** Tabelle aller im Job-Verzeichnis erzeugten Dateien mit Größe, Format und Verwendungszweck.
