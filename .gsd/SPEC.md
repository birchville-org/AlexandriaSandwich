# AlexandriaSandwich - GSD Specification

## Core Goal
Automated book digitization producing 1:1 Sandwich PDFs with a local-first Quality Loop (Tesseract) and high-precision AI fallback (Mistral OCR).

## Execution Strategy
1. Local image preprocessing on Compute Worker (`alex.local`): ImageMagick deskew + unpaper (via `scripts/preprocess.sh`).
2. OCR via Tesseract (hOCR / TSV output).
3. Confidence score check (`scripts/quality_check.py`): If mean confidence < 85%, trigger Mistral OCR fallback / Human-in-the-loop.
4. Assembly into Sandwich PDF via OCRmyPDF / img2pdf.
