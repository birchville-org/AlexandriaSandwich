# Case Study & Pipeline Architecture: Pāṇini's Grammar (Otto von Böhtlingk, 1887)

> **Complete historical digitization, canonical alignment, and generation of searchable Sandwich material for 3,997 Sūtras across 478 book pages.**
> 
> 🔗 **Project Repository:** [github.com/birchville-org/boethlingk](https://github.com/birchville-org/boethlingk)

---

## 1. Objective & Problem Statement

### 1.1 Source Work
Otto von Böhtlingk's edition *Pâṇini's Grammatik, herausgegeben, übersetzt, erläutert und mit verschiedenen Indices versehen* (Leipzig, H. Haessel, 1887) is the preeminent global philological reference work for the ancient Indian grammatical system of the Aṣṭādhyāyī.

### 1.2 Philological & Typographical Challenge
The work combines three disparate scripts and languages in tight physical proximity:
1. **Sanskrit in Devanagari:** Complex 19th-century movable lead type with historical ligatures, conjunct consonants, and Virāmas.
2. **German in historical Antiqua:** Scholarly translation and grammatical commentary with era-specific typography.
3. **Scientific Transliteration (IAST):** Latin alphabet with numerous combining diacritics (`ā`, `ī`, `ū`, `ṛ`, `ṝ`, `ḷ`, `ḹ`, `ṃ`, `ḥ`, `ṅ`, `ñ`, `ṭ`, `ḍ`, `ṇ`, `ś`, `ṣ`) and accent marks (Udātta, Svarita).

Conventional local OCR engines (Tesseract, Kraken, ABBYY) fail on this polyglossic layout with prohibitive error rates and script confusion.

### 1.3 Digitization Goal
The objective is the production of a multi-tiered, archive-grade digital corpus:
1. **1:1 Sandwich PDF:** Visually pristine, high-resolution original scans from Heidelberg University Library (pixel-preserved) with an invisible, geometrically registered full-text layer.
2. **Structured Single Source of Truth (Master JSON):** Exhaustive decomposition of the entire work into structured Sūtra objects (Sūtra number, canonical Devanagari, IAST, German translation, grammatical commentary, book page index).
3. **Standalone QA Viewer:** A lightweight web application following the *Payer Global Web Editor Standard* for visual verification and correction with split-pane view and Silent Auto-Repair.
4. **TEI-XML Foundation:** A standardized corpus conforming to Text Encoding Initiative (TEI-P5) for digital humanities and philological editions.

---

## 2. Implemented End-to-End Pipeline

```text
[Heidelberg University Facsimiles] 
       │ (Pages 1 to 478, JPG)
       ▼
[Step 1: Local Image Caching] ───────► data/img_cache/7_3A000000XXX_...jpg
       │
       ▼
[Step 2: Multimodal AI OCR] ─────────► mistral-ocr-latest (Mistral Python SDK)
       │                               ├── data/mistral/*.mistral.md   (Layout Markdown)
       │                               └── data/mistral/*.mistral.json (Bounding Box Geometry)
       ▼
[Step 3: Canonical Alignment] ───────► scripts/align_mistral_sutras.py
       │                               ├── Heuristic Sūtra segmentation (#, ##, ॥...॥)
       │                               ├── SequenceMatcher alignment against data/sutras.json
       │                               ├── 4-Pāda-per-Adhyāya state machine
       │                               └── Colophon and noise filtering
       ▼
[Step 4: Consolidation] ─────────────► data/ashtadhyayi_complete_boethlingk1887.json
       │                               (3,997 Sūtras = 100.0% coverage & 0 duplicates)
       ▼
[Step 5: Interactive QA Viewer] ─────► viewer.html (Split-Pane, Zoom/Pan, Silent Auto-Repair)
```

---

## 3. Detailed Processing Steps

### Step 1: Primary Source Acquisition & Caching
* **Source:** Facsimiles from Heidelberg University Library (*Bibliotheca Palatina*, boehtlingk1887).
* **Main Text Scope:** Pages 1 to 478 (Page 1 = Śiva-Sūtras, Pages 2–476 = Aṣṭādhyāyī 1.1.1 to 8.4.68, Pages 477–478 = Addenda).
* **Storage:** 484 scans cached locally at `data/img_cache/7_3A000000XXX_jpg_full_max_0_default_jpg.jpg`.

### Step 2: Multimodal AI OCR (`mistral-ocr-latest`)
* **Tool:** Official Mistral SDK with `mistral-ocr-latest` (`scripts/mistral_ocr.py`).
* **Batch Runner:** `scripts/batch_ocr_runner.py` processes page intervals automatically with cache skipping and cost monitoring.
* **Output Artifacts:**
  * `.mistral.md`: Semantically structured Markdown with heading hierarchies and running text.
  * `.mistral.json`: Detailed response containing page dimensions, text blocks, and bounding-box coordinates for Sandwich PDF layering.
* **Total OCR Cost:** 478 pages x 0.004 USD = exactly **1.912 USD** for the entire volume.

### Step 2.1: Local VLM Alternative & Model Benchmark (Mistral OCR vs. Qwen2.5-VL)
To evaluate an autonomous, offline-capable alternative for sensitive digitization workflows and air-gapped deployments alongside the Cloud API (`mistral-ocr-latest`), a local Vision-Language Model pipeline powered by **Qwen2.5-VL** (via MLX on Apple Silicon) was benchmarked:

#### 1. Antiqua / Introductory Prose (Latin Typography, e.g. Page 5)
On pure Latin typography and German philological explanations, the local model achieves near-complete concordance:

| Metric | Mistral Document AI (Cloud) | Qwen2.5-VL (Local, BF16 / 8-bit) | Difference / Evaluation |
| :--- | :--- | :--- | :--- |
| **Similarity** | Reference | **99.96 %** | Virtually identical text extraction |
| **Character Count** | 2,437 chars | 2,435 chars | -2 chars |
| **Word Count** | 338 words | 337 words | -1 word |
| **Processing Time** | approx. 1.8 s | approx. 161 s | Cloud approx. 90x faster |
| **API Costs** | 0.004 USD / page | **0.00 USD (Local)** | 100% free & offline |

#### 2. Polyglossic Setting / Historical Devanāgarī (e.g. Page 108)
On complex 19th-century Devanāgarī lead type featuring ligatures, Virāmas, and mixed commentary, specialization becomes pronounced:

| Metric | Mistral Document AI (Cloud) | Qwen2.5-VL BF16 (Local) | Qwen2.5-VL 8-bit (Local) |
| :--- | :--- | :--- | :--- |
| **Similarity** | Reference | **66.59 %** | **65.32 %** |
| **Devanāgarī Characters** | 1,304 chars | 1,212 chars (-92) | 1,210 chars (-94) |
| **Total Characters** | 1,825 chars | 1,782 chars (-43) | 1,779 chars (-46) |
| **Processing Time / Page** | approx. 1.8 s | 293.7 s (~4.9 min) | **196.5 s (~3.3 min, +33% speedup)** |
| **API Costs** | 0.004 USD / page | **0.00 USD** | **0.00 USD** |

#### Conclusion & Architectural Decision:
- **Mistral OCR:** Gold standard for historical Indic scripts and bulk processing (highest ligature accuracy, minimal latency).
- **Qwen2.5-VL 8-bit (Local):** Robust, privacy-preserving alternative for modern and European typography (99.96% accuracy). 8-bit quantization reduces inference latency by 33% with negligible character loss (-0.2%).

### Step 3: Canonical Alignment & Heuristics (`scripts/align_mistral_sutras.py`)
* **Fuzzy Canonical Matching:** When OCR misreads a Sūtra counter (e.g. reading Devanagari digit ८ as ६: `६५` instead of `८५`), a `SequenceMatcher` algorithm compares normalized Sanskrit text with expected Sūtras in `data/sutras.json`. At similarity >= 0.45, the counter is automatically adjusted.
* **Compensated Token Length:** Extremely long Sanskrit compounds (e.g. Sūtra 5.4.77 with 185 characters lacking a leading `#`) are reliably identified via Danda patterns (`॥...॥`) up to 350 characters.
* **Pāda and Adhyāya Rollover:** Because the Aṣṭādhyāyī strictly consists of 8 Adhyāyas with exactly 4 Pādas each, the state machine triggers an automatic increment after Pāda 4 (`state["adhyaya"] += 1, state["pada"] = 1`), even when printed colophons are broken or omitted.
* **Foreign Script Filtering:** Stray glyphs (e.g., stray Telugu or Hebrew artifacts caused by damaged metal types) are filtered prior to consolidation.
* **Addenda Isolation:** Content following concluding Sūtra 8.4.68 (`अ अ`) (Böhtlingk's *Nachträge und Verbesserungen*) is partitioned into separate addenda objects, preventing commentary pollution.

---

## 4. Validation Results

All 8 Adhyāyas and introductory Śiva-Sūtras were verified 1:1 against the canonical reference database:

| Section | Book Pages | Sūtras (Actual / Target) | Duplicates | Missing Translations | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Śiva-Sūtrāṇi** | 1 | 14 / 14 | 0 | 0 | **100.0% validated** |
| **Adhyāya 1** | 2–43 | 351 / 351 | 0 | 0 | **100.0% validated** |
| **Adhyāya 2** | 43–75 | 268 / 268 | 0 | 0 | **100.0% validated** |
| **Adhyāya 3** | 75–148 | 631 / 631 | 0 | 0 | **100.0% validated** |
| **Adhyāya 4** | 149–221 | 635 / 635 | 0 | 0 | **100.0% validated** |
| **Adhyāya 5** | 221–282 | 555 / 555 | 0 | 0 | **100.0% validated** |
| **Adhyāya 6** | 283–374 | 736 / 736 | 0 | 0 | **100.0% validated** |
| **Adhyāya 7** | 375–428 | 438 / 438 | 0 | 0 | **100.0% validated** |
| **Adhyāya 8** | 429–478 | 369 / 369 | 0 | 0 | **100.0% validated** |
| **Total** | **478 Pages** | **3,997 / 3,997** | **0** | **0** | **100.0% Complete** |

---

## 5. Sandwich PDF Assembly in AlexandriaSandwich

The completed Sandwich PDF was compiled via `scripts/build_sandwich_pdf.py`:
* **Target Artifact:** `data/output/boehtlingk1887_sandwich.pdf` (278.16 MB, 478 pages)
* **Visual Layer (Background):** The 478 high-resolution UB Heidelberg primary scans are embedded without re-compression (1:1 pixel fidelity).
* **Invisible Text Layer (Foreground):** Using PDF Text Rendering Mode 3 (*Neither fill nor stroke text*) and unicode font mapping (*Identity-H*), 14,267 text fragments are placed at their exact pixel coordinates.
* **Hierarchical Outline (Bookmarks):** All 8 Adhyāyas, 32 Pādas, the Śiva-Sūtras, and addenda are accessible via clickable bookmarks.
* **Result:** Reading presents the authentic historical facsimile of 1887. Text selection, copy-paste, and full-text search (Devanagari, IAST, German) interact directly with precise underlying vector coordinates.

---

## 6. Scholarly TEI-P5 Edition

For archival preservation and digital humanities interoperability:
* **Target File:** `data/tei/boehtlingk1887_p5.xml` (2.90 MB)
* **Validation:** 100% schema-valid against TEI All RelaxNG (`schemas/tei_all.rng`).
* **Structure:** 3,997 `<tei:entry>` elements, 478 `<tei:pb>` page breaks linked to Heidelberg IIIF facsimile URLs, 8 Adhyāya and 32 Pāda sections, and 50 corrigenda items in `<back>`.

---

## 7. QA Viewer (Payer Global Web Editor Standard)

For editorial review and long-term curation, `viewer.html` was implemented:
* **Split-Pane:** Left pane provides responsive zoom & pan of original scans; right pane provides the Sūtra editor.
* **Snippet Toolbar:** Instant insertion of Dandas (`॥`, `।`, `ऽ`, `°`), IAST diacritics, and philological notations (`∠±`, `∠_`, `v. l.`, `Kāç.`, `RV.`).
* **Silent Auto-Repair on Save:** On save (`⌘S`), ASCII pipes (`||`) silently convert to Dandas (`॥`), whitespace is normalized, and noise characters are stripped. Visual confirmation is indicated by button color pulses (Yellow = Auto-Repair, Green = Saved).
* **Local Storage First & Export:** Saves working revisions locally in browser storage and enables direct saving to disk via File System Access API (`showSaveFilePicker`).

---

## 8. Project Links & Source Code

* **GitHub Repository:** [birchville-org/boethlingk](https://github.com/birchville-org/boethlingk)
* **Artifacts & Datasets:** All pipeline scripts, TEI-P5 XML files, master JSON datasets, and the standalone QA viewer (`viewer.html`) are hosted in the repository.
