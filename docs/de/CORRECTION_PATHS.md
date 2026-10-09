# Korrekturverfahren: Pre-Assembly vs. Post-Assembly

## Pre-Assembly hOCR-Korrektur

Korrektur von OCR-Tokens im hOCR-Format vor oder parallel zum Zusammenbau des Sandwich-PDFs.

### Befehle

```bash
# Wörter mit niedriger Konfidenz extrahieren
python3 scripts/hocr_correct.py dump path/to/page.hocr --max-conf 90 -o words.json

# Korrektur-Template erzeugen
python3 scripts/hocr_correct.py init path/to/page.hocr --max-conf 90 -o page.corrections.json

# page.corrections.json editieren und anwenden
python3 scripts/hocr_correct.py apply \
  --hocr path/to/page.hocr \
  --corrections page.corrections.json \
  -o path/to/page.corrected.hocr

# Klartext-Export zur Kontrolle
python3 scripts/hocr_correct.py text path/to/page.corrected.hocr -o page.txt
```

### corrections.json

```json
{
  "by_id": { "word_1_1": "korrigiert" },
  "by_index": { "0": "Erstes" },
  "replace": { "Teh": "The" }
}
```

### Speicherorte in der Pipeline

```text
/data/processing/quality/<job>/*.hocr
/data/processing/quality/<job>/*.corrections.json
/data/processing/quality/<job>/*.corrected.hocr
/data/output/pdf/<job>.sandwich.pdf
```

### Rahmenbedingungen

- Pre-Assembly editiert hOCR für Review / Export / Human-in-the-Loop.
- `assemble_sandwich.py` baut die 1:1 Bildebene aus bereinigten Seitenbildern via OCRmyPDF auf.

---

## Post-Assembly Textlayer-Korrektur (In-PDF)

Direktes Editieren der **unsichtbaren** OCR-Textebene im fertigen Faksimile-PDF. Die visuelle Scanbildebene bleibt zu 100 % unberührt.

Im OCRmyPDF-Sandwich liegt der Text in Form-XObjects unter Verwendung von GlyphLessFont / Identity-H als UTF-16BE hex-kodierte Strings vor, z. B. `[ <0041006C...> ] TJ`.

### Befehle

```bash
# Durchsuchbaren Text extrahieren
python3 scripts/pdf_text_correct.py dump path/to/book.sandwich.pdf

# Korrektur-Template aus extrahierten Tokens initialisieren
python3 scripts/pdf_text_correct.py init path/to/book.sandwich.pdf -o book.aligned.corrections.json

# Ersetzungen anwenden (manuell oder via Substitution)
python3 scripts/pdf_text_correct.py replace path/to/book.sandwich.pdf \
  -c book.aligned.corrections.json \
  -s 'Teh=The' \
  -o path/to/book.aligned.pdf --json

# Vollautomatisches KI-Alignment (Mistral -> PDF Content-Stream)
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

### Verifikation

```bash
pdftotext -layout book.aligned.pdf -
```

### Rahmenbedingungen

- Zielt auf OCRmyPDF-Sandwich-Schriften (UTF-16BE hex in TJ-Arrays) und plain PDF-Literal-Strings ab.
- Optimal für wort- und zeilengenaue Korrekturen ohne Änderung der originalen Bildkoordinaten.
- Das Original-Faksimile (`<job>.sandwich.pdf`) bleibt stets unverändert als Archiv-Master erhalten; die Korrektur erzeugt `<job>.aligned.pdf`.
