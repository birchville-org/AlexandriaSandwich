# AlexandriaSandwich - GSD Specification

## Core Goal
Automated book digitization producing 1:1 Sandwich PDFs with a local-first Quality Loop (Tesseract) and high-precision AI fallback (Mistral OCR).

## Execution Strategy
1. Local Image Processing via ScanTailor CLI on Proxmox Compute Worker.
2. OCR via Tesseract (hOCR output).
3. Confidence score check: If < 85%, trigger Mistral OCR fallback / Human-in-the-loop.
4. Assembly into Sandwich PDF via OCRmyPDF.

