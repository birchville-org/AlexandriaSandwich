#!/usr/bin/env python3
"""
scripts/inject_toc.py — Injects hierarchical outlines (bookmarks), metadata,
and page labels into a 1:1 Sandwich PDF without altering its visual layout or text layers.

Usage:
  python3 scripts/inject_toc.py \
    --input /path/to/document.pdf \
    --toc /path/to/toc.json \
    --output /path/to/document_outline.pdf \
    --title "Pāṇini: A Survey of Research" \
    --author "George Cardona" \
    --roman-end 13 \
    --arabic-start 14
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

import fitz  # PyMuPDF


def inject_toc(
    input_pdf: Path,
    output_pdf: Path,
    toc_data: List[List[Any]],
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    roman_end: Optional[int] = None,
    arabic_start: Optional[int] = None,
) -> Path:
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    print(f"[inject_toc] Opening: {input_pdf}")
    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    print(f"[inject_toc] Total pages: {total_pages}")

    # 1. Update Metadata
    meta = doc.metadata or {}
    if title:
        meta["title"] = title
    if author:
        meta["author"] = author
    if subject:
        meta["subject"] = subject
    if keywords:
        meta["keywords"] = keywords
    meta["producer"] = "AlexandriaSandwich Pipeline (PyMuPDF)"
    doc.set_metadata(meta)
    print(f"[inject_toc] Updated metadata: Title='{title}', Author='{author}'")

    # 2. Page Labels (e.g., Roman i..xvi, then Arabic 1..N)
    if roman_end is not None and arabic_start is not None:
        labels = [
            {"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1},
            {"startpage": arabic_start - 1, "prefix": "", "style": "D", "firstpagenum": 1},
        ]
        doc.set_page_labels(labels)
        print(f"[inject_toc] Set page labels: Roman 1–{roman_end}, Arabic {arabic_start}–{total_pages}")

    # 3. Validate and Set TOC
    valid_toc = []
    for entry in toc_data:
        lvl, name, page_num = entry[0], entry[1], entry[2]
        if not (1 <= page_num <= total_pages):
            print(f"[inject_toc] Warning: skipping out-of-range TOC entry '{name}' (p. {page_num})")
            continue
        valid_toc.append([lvl, name, page_num])

    doc.set_toc(valid_toc)
    print(f"[inject_toc] Injected {len(valid_toc)} hierarchical TOC entries.")

    # 4. Save 1:1 preserving existing images and fonts
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temp_out = output_pdf.parent / f".tmp_{output_pdf.name}"
    print(f"[inject_toc] Saving to: {output_pdf} (deflate=True, garbage=3)...")
    doc.save(
        str(temp_out),
        deflate=True,
        garbage=3,
        clean=True,
    )
    doc.close()
    temp_out.replace(output_pdf)

    print(f"[inject_toc] Successfully wrote {output_pdf.stat().st_size / (1024 * 1024):.2f} MB")
    return output_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject hierarchical TOC, metadata, and page labels into PDF")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input PDF file path")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF file path")
    parser.add_argument("-t", "--toc", type=Path, required=True, help="JSON file containing TOC list [[lvl, title, page], ...]")
    parser.add_argument("--title", help="Document Title metadata")
    parser.add_argument("--author", help="Document Author metadata")
    parser.add_argument("--subject", help="Document Subject metadata")
    parser.add_argument("--keywords", help="Document Keywords metadata")
    parser.add_argument("--roman-end", type=int, help="Last page of Roman numerals (1-indexed)")
    parser.add_argument("--arabic-start", type=int, help="First page of Arabic numerals (1-indexed)")

    args = parser.parse_args()

    out_path = args.output
    if not out_path:
        out_path = args.input.parent / f"{args.input.stem}_outline.pdf"

    toc_list = json.loads(args.toc.read_text(encoding="utf-8"))
    inject_toc(
        input_pdf=args.input,
        output_pdf=out_path,
        toc_data=toc_list,
        title=args.title,
        author=args.author,
        subject=args.subject,
        keywords=args.keywords,
        roman_end=args.roman_end,
        arabic_start=args.arabic_start,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
