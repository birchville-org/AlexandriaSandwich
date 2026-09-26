# M1 Ergebnisse — AlexandriaSandwich (2026-07-20)

## Status
**PASS** — Milestone 1 complete (11/11 plans).

## Chain verified
1. ImageMagick + unpaper preprocess
2. Tesseract quality gate (`quality_check.py`, threshold 85)
3. Optional Mistral fallback (API wired; E2E used `--no-mistral`)
4. Sandwich PDF (`assemble_sandwich.py` / OCRmyPDF sandwich)
5. Path A hOCR corrections (`hocr_correct.py`)
6. Path B PDF text layer (`pdf_text_correct.py`, UTF-16BE hex TJ)

## Evidence
- Report: `data/output/reports/e2e_m1.e2e.json`
- Pipeline: `data/output/reports/e2e_m1.pipeline.json`
- PDFs: `data/output/pdf/e2e_m1.sandwich.pdf`, `e2e_m1.pathb.pdf`

## Architecture decisions
- ScanTailor dropped (GUI-only) → IM + unpaper
- Deploy target: `alex.local`
- Secrets via `.env` (gitignored)
