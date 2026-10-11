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
   * Das historische Druckbild bleibt 1:1 und ohne Rasterungsverlust erhalten.
   * Der unsichtbare Textlayer liegt auf pixelgenauen Bounding-Boxen der Originalzeilen.
2. **Zweig 2: Semantische Vektor-Neuedition (`*.typeset_edition.pdf`):**
   * Kein blindes Raten des Layouts aus flachem OCR-Text (*Reverse-Layout*).
   * Semantisches Alignment gegen kanonische Ground-Truth-Datenbanken (z. B. `dhatupatha_canonical.json`, `sutras.json`).
   * Sektionsspezifische Typografie: 1-spaltiger Fließtext für Front Matter (Einleitungen), 2-spaltiges Tabellengitter mit `grid.vline` für Lexika und Wörterbücher.

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
