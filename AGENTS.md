# AlexandriaSandwich — Agent Guidelines

## Digital Typesetting Standard (Neusatz)
For any task involving digital typesetting, page-concordant facsimile recreation, or book reconstruction:
- Strictly follow the 6-phase pipeline defined in `.agents/rules/digital_typesetting.md`.
- Upfront layout profiling via `scripts/profile_scan_layout.py` is mandatory before writing Typst markup.
- Pre-flight verification with Red/Cyan diff overlays via `scripts/verify_typographic_diff.py` is mandatory before presenting results to the user.
- Always use `import pymupdf` (never `import fitz`).
- Strictly adhere to Birchville rules (plain Unicode/ASCII math only, factual tone, no unrequested git push).
