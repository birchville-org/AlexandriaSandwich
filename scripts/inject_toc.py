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
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF fallback


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


def extract_toc_from_book_json(book_json_path: Path) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Extract hierarchical TOC outlines and metadata from book.json if available."""
    if not book_json_path.is_file():
        return [], {}
    try:
        data = json.loads(book_json_path.read_text(encoding="utf-8"))
    except Exception:
        return [], {}
    meta = data.get("metadata", {})
    toc: List[List[Any]] = []
    prev_title = None
    for p in data.get("pages", []):
        pnum = p.get("page_num", 1)
        for b in p.get("blocks", []):
            b_type = b.get("type")
            text = (b.get("text") or "").strip()
            text = " ".join(text.split())
            if not text or len(text) > 80:
                continue
            if b_type == "h1":
                if text.lower() == prev_title:
                    continue
                prev_title = text.lower()
                toc.append([1, text, pnum])
            elif b_type == "h2":
                if text.lower() == prev_title:
                    continue
                prev_title = text.lower()
                toc.append([2, text, pnum])
    return toc, meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject hierarchical TOC, metadata, and page labels into PDF")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input PDF file path")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output PDF file path (default: in-place)")
    parser.add_argument("-t", "--toc", type=Path, default=None, help="JSON file containing TOC list [[lvl, title, page], ...] or dict")
    parser.add_argument("--book-json", type=Path, default=None, help="Optional book.json path to extract TOC and metadata")
    parser.add_argument("--title", help="Document Title metadata")
    parser.add_argument("--author", help="Document Author metadata")
    parser.add_argument("--subject", help="Document Subject metadata")
    parser.add_argument("--keywords", help="Document Keywords metadata")
    parser.add_argument("--roman-end", type=int, help="Last page of Roman numerals (1-indexed)")
    parser.add_argument("--arabic-start", type=int, help="First page of Arabic numerals (1-indexed)")

    args = parser.parse_args()

    title = args.title
    author = args.author
    subject = args.subject
    keywords = args.keywords
    roman_end = args.roman_end
    arabic_start = args.arabic_start
    toc_data: List[List[Any]] = []

    # 1. Load from explicit --toc file if available
    if args.toc and args.toc.is_file():
        try:
            raw = json.loads(args.toc.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                toc_data = raw
            elif isinstance(raw, dict):
                toc_data = raw.get("toc", [])
                meta = raw.get("meta", raw)
                title = title or meta.get("title")
                author = author or meta.get("author")
                subject = subject or meta.get("subject")
                keywords = keywords or meta.get("keywords")
                if roman_end is None:
                    roman_end = meta.get("roman_end")
                if arabic_start is None:
                    arabic_start = meta.get("arabic_start")
        except Exception as e:
            print(f"[inject_toc] Error reading {args.toc}: {e}", file=sys.stderr)

    # 2. Fallback to --book-json if TOC or metadata still missing
    if args.book_json and args.book_json.is_file():
        bj_toc, bj_meta = extract_toc_from_book_json(args.book_json)
        if not toc_data:
            toc_data = bj_toc
        title = title or bj_meta.get("title")
        author = author or bj_meta.get("author")
        subject = subject or bj_meta.get("subject")

    if not toc_data and not title and not author and roman_end is None and arabic_start is None:
        print("[inject_toc] No TOC or metadata specified or found; leaving PDF unchanged.")
        return 0

    out_path = args.output or args.input
    inject_toc(
        input_pdf=args.input,
        output_pdf=out_path,
        toc_data=toc_data,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        roman_end=roman_end,
        arabic_start=arabic_start,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
