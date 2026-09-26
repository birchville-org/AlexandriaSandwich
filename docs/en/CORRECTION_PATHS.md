# Correction Paths A and B

## Path A — Pre-PDF hOCR correction

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

### Limits

- Path A edits hOCR for review / export / HITL.
- `assemble_sandwich.py` builds the 1:1 image layer from page images via OCRmyPDF sandwich.
- Optional future work: inject corrected hOCR without re-OCR.

## Path B — Post-PDF text layer edit

Edit the **invisible** OCR text inside a finished sandwich PDF. The image layer is untouched.

OCRmyPDF sandwich text lives in Form XObjects using GlyphLessFont / Identity-H as UTF-16BE hex strings, e.g. `[ <0041006C...> ] TJ`.

### Commands

```bash
# Extract searchable text
python3 scripts/pdf_text_correct.py dump path/to/book.sandwich.pdf

# Template from tokens
python3 scripts/pdf_text_correct.py init path/to/book.sandwich.pdf -o book.pathb.corrections.json

# Apply map and/or inline substitutions
python3 scripts/pdf_text_correct.py replace path/to/book.sandwich.pdf \
  -c book.pathb.corrections.json \
  -s 'Teh=The' \
  -o path/to/book.pathb.pdf --json
```

### corrections.json

```json
{
  "replace": {
    "12345": "99999",
    "Second": "SECOND"
  }
}
```

### Verify

```bash
pdftotext -layout book.pathb.pdf -
```

### Limits

- Targets OCRmyPDF sandwich fonts (UTF-16BE hex in TJ arrays); also handles plain PDF literal strings.
- Best for token/phrase fixes, not full reflow or font metrics changes.
- Always write to a new output file; keep the original sandwich as archive master.
