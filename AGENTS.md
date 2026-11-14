# AlexandriaSandwich — Agent Guidelines

## Digital Typesetting Standard (Neusatz)
For any task involving digital typesetting, page-concordant facsimile recreation, or book reconstruction:
- Strictly follow the 6-phase pipeline defined in `.agents/rules/digital_typesetting.md`.
- Upfront layout profiling via `scripts/profile_scan_layout.py` is mandatory before writing Typst markup.
- Pre-flight verification with Red/Cyan diff overlays via `scripts/verify_typographic_diff.py` is mandatory before presenting results to the user.
- Always use `import pymupdf` (never `import fitz`).
- Strictly adhere to Birchville rules (plain Unicode/ASCII math only, factual tone, no unrequested git push).

## Pipeline & Self-Service Parity Standard
Whenever pipeline stages, CLI flags, or `job.config.json` parameters are added or modified, verify 4-layer parity before `/code-review`:
1. **Core Pipeline**: `scripts/run_pipeline.sh` and Python stage scripts (`consolidate_book.py`, `render_digital_pdf.py`, etc.).
2. **Webhook / Runner Bridge**: `scripts/n8n_run_job.sh` and `workflows/n8n_ocr_pipeline.json`.
3. **Self-Service Web UI**: `ui/main.py` (`upload_submit`, `trigger_job`, `_trigger_n8n`, `_write_job_config`) and `ui/templates/upload.html`, `ui/templates/job_detail.html` (ensure no orphaned form fields).
4. **Method Documentation**: Bilingual docs in `docs/de/`, `docs/en/`, and `ARCHITECTURE.md` (verified with `mkdocs build --strict`).
