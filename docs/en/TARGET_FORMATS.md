# Target Format Architecture & Dual Reproduction

## 1. The Target Structure: The 4-Tier Pyramid

In scientific digitization and scholarly editing, no single format satisfies all practical needs:
- **Facsimiles** are essential for verification and citations, but useless on mobile e-readers (no reflow).
- **Reflowable text** is ideal for mobile devices and AI, but loses the historical typographical layout.
- **XML** ensures 50+ years of archival safety, but is difficult for humans to read casually.

AlexandriaSandwich resolves this dilemma with a **4-tier architecture** where every book is transformed into a complementary set of digital formats:

```text
              ┌───────────────────────────────────────┐
              │ 1. Reception Layer (End User)         │
              │    • EPUB 3 (Reflowable E-Reader)     │
              │    • Digital PDF (Typst Vector Reset) │
              └───────────────────▲───────────────────┘
                                  │ Compilation
              ┌───────────────────┴───────────────────┐
              │ 2. Working & AI Layer                 │
              │    • book.md (UTF-8 Plain Markdown)   │
              └───────────────────▲───────────────────┘
                                  │ Consolidation
              ┌───────────────────┴───────────────────┐
              │ 3. Semantic & Archival Layer          │
              │    • book.json (Single Source of Truth│
              │    • tei.xml   (TEI-P5 Academy Standard)
              └───────────────────▲───────────────────┘
                                  │ OCR & Token Alignment
              ┌───────────────────┴───────────────────┐
              │ 4. Facsimile & Proof Layer            │
              │    • <id>.sandwich.pdf (Scan + Layer) │
              │    • <id>.aligned.pdf  (AI-Aligned)   │
              └───────────────────────────────────────┘
```

---

## 2. Target Formats in Detail

### 1. Facsimile Layer: Sandwich PDF (`*.sandwich.pdf` / `*.aligned.pdf`)
* **Role:** Authentic, citable document archive.
* **Architecture:**
  * Visual top: 300 DPI high-resolution facsimile scan with original letterpress fonts, marginalia, and layout.
  * Invisible bottom: Vector text layer with pixel-exact bounding-box coordinates for every word.
* **Post-Assembly Textlayer Correction (AI Alignment):** The invisible text layer is synchronized with Mistral OCR. OCR errors and noise hallucinations (e.g. along dotted leader lines) are eliminated while preserving exact bounding box coordinates (`*.aligned.pdf`).

### 2. Machine-Readable Single Source of Truth: `book.json` (AST)
* **Role:** Central, software-agnostic intermediate format.
* **Architecture:** Hierarchical Abstract Syntax Tree (AST) combining metadata, pages, paragraphs, headings, token lists, confidences, and bounding boxes (`[ymin, xmin, ymax, xmax]`).
* **Significance:** From this file, any new target format (HTML, EPUB, Typst, LaTeX, SQL) can be compiled at any time without re-running OCR.

### 3. Scholarly Academy Standard: `tei.xml` (TEI-P5)
* **Role:** Long-term preservation (50+ years) and interoperability with academic repositories (DTA, SARIT, Perseus).
* **Architecture:** Strictly valid TEI-P5 XML featuring `<teiHeader>`, facsimile mappings (`<surface>`, `<zone>`), and semantic structural divisions (`<body>`, `<div n="..." type="...">`, `<p>`, `<table>`).

### 4. Plain Text & AI Layer: `book.md` (UTF-8 Markdown)
* **Role:** Direct editing, version control, and LLM input.
* **Architecture:** Clean UTF-8 Markdown without proprietary overhead.
* **Usage:** Line-by-line versioning in Git (`git diff`), fast CLI inspection (`grep`), and optimal ingestion for Retrieval-Augmented Generation (RAG) vector stores.

### 5. Reader Reception Layer: `*.epub` (EPUB 3) & `*.digital.pdf`
* **Role:** Human reading experience on modern devices.
* **EPUB 3:** Dynamic reflow for e-readers (Tolino, Kindle, Kobo, iPad) with embedded Unicode fonts for Devanagari (*Noto Serif Devanagari*) and IAST transliteration (*Linux Libertine* / *Charis SIL*).
* **Digital PDF (Typst):** Crisp vector typesetting for print-on-demand or desktop study.

---

## 3. The Duality: Reproduce Original Layout vs. Complete Re-layout

By strictly separating image data, geometric coordinates, and semantic text, AlexandriaSandwich enables two complementary publication strategies:

```text
                        ┌──────────────────┐
                        │ Raw Scan Source  │
                        └────────┬─────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
     [ STRATEGY 1: REPRODUCTION ]     [ STRATEGY 2: RE-LAYOUT ]
     • Pixel-exact Sandwich PDF       • Reflowable EPUB 3
     • Vector reset via bbox coords   • Responsive Web / HTML
     • Preserves historical fonts     • Study workbook format (Typst)
     • Page citations match original  • Variable font size & Dark Mode
```

### Strategy 1: Reproducing the Original Layout

1. **As AI-Aligned Facsimile (`*.aligned.pdf`):**
   * The historical print layout is retained 1:1. Line breaks, hyphens, printer quirks, ligatures, and footnote placements remain identical to the physical library copy.
2. **As Geometric Vector Reset:**
   * Because `book.json` stores bounding boxes (`bbox`), line heights, and column widths, the original layout can be mathematically reconstructed in modern vector typesetting engines (identical page grid, but without scan noise).

### Strategy 2: Complete Re-layout of Content

1. **Dynamic E-Reader Book (EPUB 3):**
   * Text flows freely. On small smartphone or tablet displays, margins, font sizes, and line spacing adapt dynamically to reader preferences.
2. **New Print Layouts (e.g. Student Workbook via Typst):**
   * Re-generate the entire work into an entirely different publication format:
     * Format shift (e.g. from historical Octavo to DIN A4).
     * Generous margins for handwritten student notes.
     * Modern typography (e.g. *EB Garamond* + *Noto Serif Devanagari*).
     * Bilingual parallel columns (Sanskrit on the left, German on the right).

---

## 4. Standard Directory Layout per Book

Every work processed by AlexandriaSandwich generates the following standardized file structure:

```text
output/books/<book_id>/
├── <book_id>.sandwich.pdf   # 1:1 Facsimile + Tesseract text layer
├── <book_id>.aligned.pdf    # Facsimile + Mistral-aligned text layer (0 noise)
├── <book_id>.digital.pdf    # Vector reset via Typst
├── <book_id>.epub           # Reflowable eBook with embedded fonts
├── <book_id>.tei.xml        # TEI-P5 Archival XML
├── book.json                # Complete semantic syntax tree (AST)
└── book.md                  # Consolidated UTF-8 Markdown text
```
