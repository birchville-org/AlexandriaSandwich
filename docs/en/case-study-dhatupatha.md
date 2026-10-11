# Case Study & Architecture: Dhātu-Pāṭha (Böhtlingk Standard)

> **Canonical ground truth, bilingual facing-page alignment pipeline, and hybrid Typst vector typesetting for 2,259 verbal roots across 410 book pages.**
> 🔗 **Project Repository:** [github.com/birchville-org/dhatupatha](https://github.com/birchville-org/dhatupatha)  
> 🌐 **Live QA Viewer:** [birchville-org.github.io/dhatupatha](https://birchville-org.github.io/dhatupatha/)

---

## 1. Context & The Core Problem

### 1.1 The Phenomenon: "Digitized without layout" vs. "Digitized AND original layout"
During the initial digitization of the *Dhātu-Pāṭha* (Pāṇinian catalog of verbal roots), a fundamental discrepancy became evident:
* The reference project **Otto von Böhtlingk (1887)** produced an output combining complete layout fidelity with sharp typography ("digitized AND original layout").
* In contrast, an early direct OCR-to-typeset attempt on *Dhātu-Pāṭha* resulted in an unstructured stream: two-column root listings collapsed, and meanings merged awkwardly into paragraphs ("digitized, but without layout").

Resolving this discrepancy and transferring the *Böhtlingk Standard* to the *Dhātu-Pāṭha* established core architectural insights for the entire AlexandriaSandwich pipeline.

### 1.2 Structure of the Historical Source
The 410-page volume features a complex two-fold internal organization:
1. **Section Hierarchy:**
   * **Front Matter (pp. 1–25):** Continuous single-column prose (preface, grammatical introduction, phonetic rules) structured into cohesive paragraphs.
   * **Main Matter (pp. 26–285):** Rigorous two-column dictionary grid across the 10 Gaṇas (root classes from Bhvādi to Curādi).
   * **Back Matter (pp. 286–410):** Alphabetic indices, concordance tables, and appendices.
2. **Bilingual Facing Pages:**
   * **Odd Pages (Right):** Primary Sanskrit text in Devanāgarī with traditional Aupadeśika markers and locative meanings (*arthas*).
   * **Even Pages (Left):** Facing scholarly transliteration (IAST) with English translations and grammatical tags.

---

## 2. Root Cause Analysis: Why Blind "Reverse-Layout" Fails

Attempting to mathematically or heuristically reverse-engineer the original layout directly from raw, sequential OCR text fails due to two structural barriers:

```text
[Raw OCR Data Stream] ──► Sequential Extraction (1D)
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[Problem 1: Serialization Loss]                  [Problem 2: Layout Constraint]
2D tabular root/meaning alignment                A global 2-column rule destroys
collapses into flat 1D paragraphs.               the single-column preface;
Typst must guess column breaks.                  1-column destroys the lexicon.
```

1. **Serialization Loss:** OCR engines (both Tesseract and multimodal VLMs) process text blocks sequentially. In multi-column lexicons, roots and their respective translations become interleaved or broken across lines.
2. **Blanket Layout Constraints:** Imposing a rigid global column count across an entire volume either squeezes the prose preface into unreadable narrow columns or dissolves the dictionary's tabular structure into an unstructured list.

---

## 3. The Solution: The 4-Pillar Böhtlingk Standard

AlexandriaSandwich strictly decouples archival facsimile preservation from semantically driven vector typesetting:

```text
                              ┌──────────────────────┐
                              │     Raw Scans        │
                              └──────────┬───────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   [ PILLAR 1: FACSIMILE GUARANTEE ]              [ PILLAR 2: CANONICAL ALIGNMENT ]
   • 1:1 untouched scan pixels                    • Fuzzy match vs dhatupatha_canonical.json
   • Invisible bbox text layer                    • Bilingual 10-Gaṇa state machine
   • Dhatu-patha.perfect_sandwich.pdf             • 100% gapless dhatupatha_complete.json
                                                                 │
                                                                 ▼
   [ PILLAR 4: HERMETIC FONT DEPLOY ]             [ PILLAR 3: TYPST VECTOR EDITION ]
   • data/fonts/ (Noto + Libertine)               • pp. 1–25:  1-column continuous prose
   • APT fonts-noto-extra on Linux                • pp. 26–285: 2-column grid + grid.vline
   • Zero tofu question marks (?)                 • Marginal concordance: [S. 26]
```

### Pillar 1: The Facsimile Guarantee (`*.perfect_sandwich.pdf`)
* The 410 original high-resolution scans remain visually untouched at 1:1 pixel fidelity.
* Corrected OCR text is embedded invisibly (PDF Text Rendering Mode 3) precisely along the bounding boxes of historical print lines.
* **Guarantee:** 100% archival authenticity, zero layout hallucination risk, instantaneous full-text search.

### Pillar 2: Canonical Ground Truth & Bilingual Facing-Page Alignment
Rather than typesetting uncurated OCR output, the text is structured through a two-step alignment pipeline:
1. **Canonical Ground-Truth Database (`scripts/build_dhatupatha_groundtruth.py`):**
   * Generates `data/dhatupatha_canonical.json` (2,259 roots across all 10 Gaṇas).
   * Contains canonical Devanāgarī, IAST, Aupadeśika markers (e.g., `टु`, `डु`, `इर्`), Sanskrit locative arthas (`भू सत्तायाम्`), English translations, and Pāṇinian classifications (Svarita-Anudātta, Sakarmaka/Akarmaka, Seṭ/Aniṭ).
2. **Bilingual Facing-Page Alignment Engine (`scripts/align_dhatupatha.py`):**
   * Leveraging the facing-page layout (odd pages Devanāgarī, even pages IAST), the 10-Gaṇa state machine matches OCR candidates against **both** scripts simultaneously.
   * Ambiguous or damaged Devanāgarī lead types are validated against the Romanized transliteration on the facing page, and vice versa.
   * **Result:** `data/dhatupatha_complete.json` (100% gapless master catalog linked to original scan page numbers).

### Pillar 3: Section-Specific Layout Fidelity in Typst (`scripts/build_typeset_edition.py`)
The vector edition dynamically shifts its typography to honor the book's logical sections:
* **Front Matter (pp. 1–25):**
  * Single-column continuous prose with generous margins.
  * Preserves historical paragraph divisions and section markers.
  * Marginal references link back to original scan pages (`[S. 6]`, `[S. 11]`).
* **Main Matter / Dictionary (pp. 26–285):**
  * Two-column dictionary grid separated by a vertical rule (`grid.vline`).
  * Centered Gaṇa headings (e.g., *1. Bhvādigaṇaḥ* / *भ्वादिगणः*).
  * Bold Devanāgarī roots with accents, accompanied by italic IAST, locative meanings, and English translations.
  * Marginal navigation anchors (`[S. 26]`).
* **Running Headers:**
  * Dynamic Typst headers in code mode: Even pages display the book title; odd pages display the current Gaṇa name and page counter.

### Pillar 4: Cross-Platform Font Vendoring & Linux Tofu Fix
A critical issue identified when moving from macOS development to headless Linux servers (`alex.local`, Docker):
* **The Problem:** Typst rendered cleanly on macOS because macOS provides system fonts for Indic scripts (`Devanagari MT`, `Kohinoor Devanagari`, `Baskerville`). However, inside the Linux worker container (Ubuntu 24.04), all Devanāgarī characters rendered as question marks inside boxes (`?`, tofu).
* **The Root Cause:**
  1. In Ubuntu 24.04, `fonts-noto-core` does NOT contain Indic scripts.
  2. Typst searches system directories by default and fails to locate Indic glyphs.
* **The Solution:**
  1. **Hermetic Font Vendoring:** Storing OpenType/TrueType master fonts directly inside the repository under `data/fonts/`:
     * `NotoSerifDevanagari-Regular.ttf` & `NotoSerifDevanagari-Bold.ttf`
     * `LinLibertine_R.otf`, `LinLibertine_RB.otf`, `LinLibertine_RI.otf`
  2. **Automatic Font Path:** Passing `--font-path data/fonts` to every Typst invocation.
  3. **Universal Font Cascade:**
     ```typst
     #set text(
       font: ("Linux Libertine O", "Baskerville", "Times New Roman", "Noto Serif Devanagari", "Devanagari MT", "Kohinoor Devanagari", "Noto Sans Devanagari"),
       size: 10pt,
       lang: "de"
     )
     ```
  4. **Container Packages:** Installing `fonts-noto-extra` (APT) and `pymupdf` (PIP) in the worker image.

---

## 4. Headless Linux Deployment Configuration

To guarantee automated execution on Linux workers (`alex.local`, Synology, Debian/Ubuntu) without manual intervention, configure:

### 4.1 Worker Dockerfile (`docker/worker/Dockerfile`)
```dockerfile
# System fonts including Indic script coverage
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-linuxlibertine \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python packages for bbox inspection and PDF processing
RUN pip install --no-cache-dir \
    pymupdf \
    pikepdf \
    lxml
```

### 4.2 Docker Compose Volume Mounts (`deploy/docker-compose.alex.yml`)
The `data/` directory must be mounted into the container to supply vendored fonts and canonical databases without container rebuilds:
```yaml
volumes:
  - /data/input:/data/input
  - /data/processing:/data/processing
  - /data/output:/data/output
  - /opt/alexandria/scripts:/opt/alexandria/scripts:ro
  - /opt/alexandria/templates:/opt/alexandria/templates:ro
  - /opt/alexandria/data:/opt/alexandria/data:ro
```

### 4.3 Pipeline Automation (`scripts/run_pipeline.sh`)
The master bash script automatically detects aligned canonical datasets:
```bash
if [ -f "data/dhatupatha_complete.json" ]; then
    echo "==> Generating typographical vector edition via Typst..."
    python3 scripts/build_typeset_edition.py \
        --input data/dhatupatha_complete.json \
        --output data/output/pdf/Dhatu-patha.typeset_edition.pdf
fi
```

---

## 5. Validation & Results

| Feature | Raw OCR Typesetting (Initial) | AlexandriaSandwich Böhtlingk Standard |
| :--- | :--- | :--- |
| **Facsimile Layer** | Missing or misaligned | **100% 1:1 Scan Facsimile** (`*.perfect_sandwich.pdf`) |
| **Front Matter Layout** | Cramped into 2 columns | **1-column continuous prose** with scan citations |
| **Dictionary Layout** | Mixed into 1 column | **2-column grid** with `grid.vline` & Gaṇa hierarchy |
| **Root Inventory** | ~1,850 noisy fragments | **2,259 roots (100% complete)** |
| **Devanāgarī Rendering** | Tofu question marks (`?`) on Linux | **100% sharp vector glyphs** (Noto Serif Devanagari) |
| **Compilation Time** | Several minutes | **~2.4 seconds** for 229 pages (Typst 0.11.1) |
| **File Size (Vector)** | Unoptimized | **2.96 MB Vector PDF** (searchable, crisp) |
| **Scholarly Citation** | Page mapping lost | **Marginal concordance `[S. XX]`** on every page |

---

## 6. Summary Conclusion

Production-grade fidelity is not achieved by attempting to "reverse-guess" layout from unstructured OCR text. It requires two distinct, complementary workflows:
1. The **Sandwich PDF** preserves historical authenticity and archival citation integrity at 1:1 pixel fidelity.
2. The **Typst Vector Edition** leverages canonical ground truth to build a publication-grade edition honoring original section-specific layout conventions.
