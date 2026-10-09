# Correction Workflows: Pre-Assembly vs. Post-Assembly

## Pre-Assembly hOCR Correction

Correct OCR tokens in hOCR before or beside sandwich assembly.

### Commands

```bash
# Low-confidence words
python3 scripts/hocr_correct.py dump path/to/page.hocr --max-conf 90 -o words.json

# Corrections template
python3 scripts/hocr_correct.py init path/to/page.hocr --max-conf 90 -o page.corrections.json

# Edit page.corrections.json then apply
python3 scripts/hocr_correct.py apply \
  --hocr path/to/page.hocr \
  --corrections page.corrections.json \
  -o path/to/page.corrected.hocr

# Plaintext export
python3 scripts/hocr_correct.py text path/to/page.corrected.hocr -o page.txt
```

### corrections.json

```json
{
  "by_id": { "word_1_1": "corrected" },
  "by_index": { "0": "First" },
  "replace": { "Teh": "The" }
}
```

### Pipeline locations

```text
/data/processing/quality/<job>/*.hocr
/data/processing/quality/<job>/*.corrections.json
/data/processing/quality/<job>/*.corrected.hocr
/data/output/pdf/<job>.sandwich.pdf
```

### Constraints

- Pre-Assembly edits hOCR for review / export / HITL.
- `assemble_sandwich.py` builds the 1:1 image layer from page images via OCRmyPDF sandwich.

---

## Post-Assembly Textlayer Correction (In-PDF)

Edit or align the **invisible** OCR text inside a finished facsimile PDF. The visual image layer is 100% untouched.

OCRmyPDF sandwich text lives in Form XObjects using GlyphLessFont / Identity-H as UTF-16BE hex strings, e.g. `[ <0041006C...> ] TJ`.

### Commands

```bash
# Extract searchable text
python3 scripts/pdf_text_correct.py dump path/to/book.sandwich.pdf

# Template from tokens
python3 scripts/pdf_text_correct.py init path/to/book.sandwich.pdf -o book.aligned.corrections.json

# Apply manual map and/or inline substitutions
python3 scripts/pdf_text_correct.py replace path/to/book.sandwich.pdf \
  -c book.aligned.corrections.json \
  -s 'Teh=The' \
  -o path/to/book.aligned.pdf --json

# Fully automatic AI token alignment (Mistral -> PDF Content-Stream)
python3 scripts/align_mistral_pdf.py \
  --pdf path/to/book.sandwich.pdf \
  --mistral-dir path/to/markdown/ \
  -o path/to/book.aligned.pdf
```

### corrections.json

```json
{
  "replace": {
    "12345": "99999",
    "Secvnd": "Second"
  }
}
```

### Verify

```bash
pdftotext -layout book.aligned.pdf -
```

### Constraints

- Targets OCRmyPDF sandwich fonts (UTF-16BE hex in TJ arrays); also handles plain PDF literal strings.
- Best for token/phrase fixes and AI alignment without altering bounding boxes.
- Always write to `<job>.aligned.pdf`; keep the original sandwich as archive master.
