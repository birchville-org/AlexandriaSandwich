# User Manual: Capabilities, Workflows & Parameters

The **AlexandriaSandwich system** is a specialized digitization and scholarly editing pipeline for historical books, critical editions, and manuscripts. It links four core steps into a continuous workflow:

1. **Scan Restoration**: Removes paper yellowing, gutter shadows, and scan artifacts without degrading delicate hairline strokes or diacritical dots.
2. **Hybrid AI OCR**: Combines pixel-accurate local coordinates with modern multimodal Vision-Language Models (VLM like Mistral OCR) for error-free transcription of challenging typography (e.g., Devanāgarī, IAST diacritics, Fraktur, Polytonic Greek).
3. **1:1 Sandwich PDF**: Produces a searchable facsimile where an invisible vector text layer aligns precisely behind the cleaned original scan image.
4. **Digital Typesetting (Typst)**: Generates razor-sharp vector publications with strict page and line parity matching the original historical print.

??? info "Glossary: Key Concepts at a Glance (Click to expand)"
    - **VLM (Vision-Language Model)**: A multimodal AI model that understands visual image features (scans) and text simultaneously, enabling accurate recognition of complex historical scripts, line breaks, and tables.
    - **OCR (Optical Character Recognition)**: Automated optical conversion of raster scan text into machine-readable characters.
    - **Sandwich PDF**: A PDF document displaying the original scan image while embedding an invisible, geometrically aligned vector text layer underneath for search and text selection.
    - **Typst**: A modern, high-performance typesetting engine (modern alternative to LaTeX) for scholarly book publishing.
    - **IAST (International Alphabet of Sanskrit Transliteration)**: The standard academic romanization scheme for Indic scripts using Latin characters with diacritical marks (e.g. *ś*, *ṣ*, *ṛ*, *ṃ*, *ḥ*).
    - **Devanāgarī**: The traditional Indic script used for Sanskrit, Hindi, and Marathi.
    - **Deskewing**: Automated rotational alignment of tilted book page scans via projection profiles.
    - **Despeckling**: Selective removal of dust particles in whitespace while preserving diacritical dots close to text lines.
    - **TEI-P5 XML**: The Text Encoding Initiative international standard for long-term digital humanities archiving.
    - **EPUB 3**: Reflowable digital book format with customizable font rendering and embedded vector typography.

---

## 1. Comprehensive System Capabilities

Across numerous case studies and primary source genres (Böhtlingk 1887 *Pāṇini*, Cardona 1976 *Recent Research in Pāṇinian Studies*, Thieme 1952 *Bráhman*, Abhinavagupta 1918 *Tantrasāra*, William James *Principles of Psychology*), AlexandriaSandwich has evolved into a modular engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                 ALEXANDRIASANDWICH CAPABILITY MATRIX                   │
├─────────────────────────┬────────────────────────┬─────────────────────┤
│ 1. Image & Facsimile    │ 2. Text & Geometry     │ 3. Digital Editions │
├─────────────────────────┼────────────────────────┼─────────────────────┤
│ • Verso/Recto Deskew    │ • Tesseract BBoxes     │ • Typst Vector PDF  │
│ • Illumination-Subtract │ • Mistral VLM Token-AI │ • 1:1 Page Parity   │
│ • Distance Despeckle    │ • Fuzzy Token-Anchor   │ • Interlinear Stack │
│ • Margin Border Wipe    │ • Indic Normalizer     │ • Logical Labels    │
│ • Colophon Blanking     │ • Apparatus Expansion  │ • EPUB 3 & TEI-P5   │
└─────────────────────────┴────────────────────────┴─────────────────────┘
```

### A. Scan Restoration & Image Preprocessing
- **Independent Rotational Deskewing**: Automatic angle detection for left (verso) and right (recto) pages via projection profiling.
- **Adaptive Illumination Normalization**: Division by morphological closing surfaces removes paper yellowing, shadows, and ink bleed-through without eroding delicate hairline glyph strokes.
- **Diacritics-Safe Distance-Transform Despeckling**: Dual-zone processing: page margins are completely cleared to pure `#FFFFFF`, while inside the text bounding box the Euclidean distance to the nearest text line is evaluated. Tiny diacritics (anusvāras, visargas, candrabindus, accents) near text baselines are 100% preserved; isolated dust speckles in whitespace are removed.
- **Colophon Blanking**: Clean erasure of trailing blank space after chapter colophons on final pages.

### B. Hybrid OCR & Token Geometry
- **Local Tesseract Geometry**: Sub-pixel bounding boxes for invisible searchable text layers.
- **Multimodal VLM (Mistral OCR)**: High-accuracy recognition for complex scripts (Devanāgarī, Polytonic Greek, Fraktur, ligature-rich typography).
- **Fuzzy Token-Anchor Alignment**: Dynamic matching between VLM plain text and scan coordinates eliminates phantom text hits in empty margins.

### C. Digital Typesetting & Typst Architecture
- **1:1 Page & Line Parity**: Every line break and page break faithfully matches the original historical print.
- **The Interlinear `#stack` Architecture**: A robust typographic hierarchy ensures that the distance between paired lines (intra-pair: ~2.6 pt) is strictly smaller than the distance to the next pair (inter-pair: ~7.2 pt), preventing visual mis-association.
- **Bottom-Anchored Footnotes**: Footnotes are pinned cleanly to the page bottom via `#v(1fr, weak: true)` above a standardized 30% rule.
- **Birchville Scholarly Synthesis Standard**: Crested title pages, alternating running headers (even: work/chapter; odd: section/subtitle).

### D. Digital Archival Formats
- **1:1 Sandwich PDF**: Original scan with invisible, perfectly aligned vector text layer.
- **EPUB 3**: Reflowable eBook with embedded fonts (*STIX Two Text*, *Devanagari MT*).
- **TEI-P5 XML**: Standardized academic long-term archiving standard.
- **Structured AST**: `book.json` (hierarchical tokens with coordinates) and `book.md` (clean markdown).

---

## 2. Multi-Edition Matrix: Four Synchronized Formats

From a single canonical dataset, the pipeline generates four synchronized editions:

1. **Monolingual Original (`original`)**: Pure vector typesetting of the source script (e.g. Devanāgarī).
2. **Interlinear Transliteration (`interlinear`)**: Source script on top, academic romanization (IAST) directly underneath.
3. **Monolingual Transliteration (`transliteration`)**: Pure IAST with enlarged type size for reading ease.
4. **Interlinear Translation (`bilingual`)**: IAST on top, line-by-line German or English translation in italic slate typography underneath.

---

## 3. User Parameters for the Service Portal

Decisions that cannot or should not be made purely by automated heuristics are presented as user choices in the portal:

| Parameter | Values / Options | Default | Description & Guidance |
| :--- | :--- | :--- | :--- |
| **`target_edition`** | `all`, `sandwich`, `original`, `interlinear`, `transliteration`, `bilingual` | `all` | Determines which documents of the multi-edition matrix to build. |
| **`spread_mode`** | `auto`, `split_spreads`, `single_page`, `raw` | `auto` | Automatically splits 2-page landscape scans into verso and recto pages. |
| **`despeckle_mode`** | `safe_philological`, `aggressive`, `off` | `safe_philological` | `safe_philological` preserves accents/dots; `aggressive` clears heavy library copier noise; `off` retains raw paper texture. |
| **`colophon_blank`** | `true`, `false` | `false` | Blanks out empty space following the chapter colophon on the last page. |
| **`font_family`** | `stix`, `libertine`, `noto_deva` | `stix` | **STIX Two Text** supports complete IAST and philological diacritics; **Libertine** for Western texts. |
| **`body_start_page`** | Integer (e.g. `10`) | `1` | Starting page number for PDF page labels when processing extracts. |
| **`title_page_style`** | `birchville`, `minimal`, `none` | `birchville` | Crested title page following Birchville Scholarly Synthesis standard vs. minimal header. |
| **`apparatus_translit`**| `true`, `false` | `true` | Automatically expands Indic manuscript sigla (`पं०`, `ख० पु०`) to standardized IAST. |

---

## 4. User Onboarding, 2FA Authorization & Portal Usage

To safeguard GPU compute resources and ensure verifiable job assignment, the entire Alexandria service portal (`https://alex.birchville.org`) including the AlexandriaSandwich and TOC-Injection Studio services is secured via the **Birchville Onboarding Meccano** and Authelia (Two-Factor Authentication).

```
┌────────────────────────────────────────────────────────────────────────┐
│                      4-STAGE ONBOARDING MECCANO                        │
├──────────────────┬──────────────────┬──────────────────┬───────────────┤
│ 1. Request       │ 2. Provisioning  │ 3. 2FA & Login   │ 4. Portal     │
├──────────────────┼──────────────────┼──────────────────┼───────────────┤
│ • Interactive    │ • CLI hash gener.│ • auth.birchville│ • Alexandria  │
│   mail builder   │ • Authelia YAML  │ • TOTP QR scan   │   pipeline    │
│ • Service choice │ • Job assignment │   (Bitwarden/    │ • TOC Studio  │
│   (Alex / TOC)   │ • Invitation mail│   Aegis/YubiKey) │ • Download    │
└──────────────────┴──────────────────┴──────────────────┴───────────────┘
```

### The 4-Stage Workflow for Users

1. **Request via Onboarding Meccano (`https://birchville.org/onboarding`)**:
   The user accesses the onboarding page. A streamlined assistant generates a formatted email template requesting access for the desired service (AlexandriaSandwich or TOC-Injection Studio), which is sent directly to the administration.

2. **Provisioning & Invitation by Administration**:
   The administrator provisions the Authelia account using `scripts/birchville_onboard.py` and optionally assigns pre-formulated jobs. The user receives a bilingual invitation email containing temporary credentials and portal links.

3. **2-Factor Authentication (2FA) at `auth.birchville.org`**:
   The user signs in with initial credentials, links an authenticator app (Aegis, Bitwarden, Google Authenticator, or YubiKey FIDO2), and selects a personal password.

4. **Portal Access at `alex.birchville.org`**:
   Inside the protected portal, the user accesses the book digitization pipeline for new or pre-formulated jobs, or launches the TOC-Injection Studio (`/toc`). Pre-formulated jobs can be triggered with one click on **`▶ Launch Now`**. Once finished, sandwich PDF, typeset PDF, TEI-P5, and Markdown are available for instant download.

### Administrator CLI Tools (`scripts/birchville_onboard.py`)

Administrators can automate credential hashing, invitation drafting, and job staging:

```bash
# 1. Provision user, generate Argon2id hash, and print invitation mail
python3 scripts/birchville_onboard.py create \
  --username scholar1 \
  --display-name "Dr. Maria Scholar" \
  --email "scholar@example.org" \
  --job boethlingk_sample

# 2. Assign an existing job to a user as staged
python3 scripts/birchville_onboard.py stage \
  --job tantrasara_kap3 \
  --user scholar1

# 3. List all jobs and their staging status
python3 scripts/birchville_onboard.py list
```

---

## 5. Command Line Usage (CLI)

### Build Multi-Edition from Canonical JSON
```bash
# Build all 4 editions simultaneously with native PDF labels
python scripts/build_multi_edition.py \
  data/tantrasara_chap3_canonical.json \
  output/tantrasara/ \
  --format all

# Build only the bilingual study edition
python scripts/build_multi_edition.py \
  data/tantrasara_chap3_canonical.json \
  output/tantrasara/ \
  --format bilingual
```

### Diacritics-Preserving Scan Cleaning
```bash
# Clean PDF spreads and split into single pages
python scripts/image_restoration.py \
  scans/raw_book.pdf \
  output/cleaned_book.pdf \
  --split-spreads \
  --dpi 300
```

### Indic Normalization & Transliteration
```bash
# Normalize apparatus entry to IAST
python scripts/indic_normalizer.py \
  "पं० १० ख० पु० बिम्बप्रतिबिम्बेति पाठः ।" \
  --apparatus
# Output: paṃ. 10 kha. pu. bimbapratibimbeti pāṭhaḥ .
```

### PDF Page Labels Injection
```bash
python scripts/postprocess_pdf_metadata.py \
  document.pdf \
  --title-page \
  --body-start 10
```

---

*[VLM]: Vision-Language Model: A multimodal AI model capable of understanding images (scans) and text simultaneously, enabling accurate recognition of complex historical typography.
*[OCR]: Optical Character Recognition: Automated software conversion of raster scanned text into machine-readable characters.
*[Sandwich PDF]: A PDF displaying the visual scan while embedding an invisible, geometrically aligned vector text layer underneath for search and text selection.
*[Typst]: A modern, high-performance typesetting engine (modern alternative to LaTeX) for scholarly book publishing.
*[IAST]: International Alphabet of Sanskrit Transliteration: The standard academic romanization scheme for Indic scripts using Latin characters with diacritical marks.
*[Devanāgarī]: The traditional Indic script used for Sanskrit, Hindi, and Marathi.
*[Deskewing]: Automated rotational alignment of tilted book page scans via projection profiles.
*[Despeckling]: Selective removal of dust particles in whitespace while preserving diacritical dots close to text lines.
*[TEI-P5]: Text Encoding Initiative: An international standard for long-term digital humanities archiving in XML.
*[EPUB 3]: Reflowable digital book format with customizable font rendering and embedded vector typography.
*[BBox]: Bounding Box: The exact pixel rectangle coordinates of a word or character on a page scan.
*[AST]: Abstract Syntax Tree: Hierarchical, structured representation of document contents (pages, paragraphs, lines, words).
