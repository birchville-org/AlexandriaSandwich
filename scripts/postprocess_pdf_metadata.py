#!/usr/bin/env python3
"""
AlexandriaSandwich - Post-Process PDF Metadata
Injects native PDF page labels (Roman for front matter, Arabic for body) and
hierarchical table-of-contents bookmarks via PyMuPDF.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


def inject_page_labels(
    doc: pymupdf.Document,
    front_matter_count: int,
    front_matter_style: str = "r",  # lowercase roman: i, ii, iii
    body_style: str = "D",         # decimal arabic: 1, 2, 3
) -> None:
    """Injects native PDF page labels into document catalog."""
    labels = [
        {"startpage": 0, "prefix": "", "style": front_matter_style, "firstpagenum": 1},
        {"startpage": front_matter_count, "prefix": "", "style": body_style, "firstpagenum": 1},
    ]
    try:
        doc.set_page_labels(labels)
        print(f"✓ Native PDF page labels injected (Front matter: 0..{front_matter_count-1}, Body: {front_matter_count}..end).")
    except Exception as e:
        print(f"Warning setting page labels: {e}", file=sys.stderr)


def inject_bookmarks(doc: pymupdf.Document, toc: List[List[Any]]) -> None:
    """Injects hierarchical TOC bookmark outline: [[level, title, pagenum], ...]."""
    try:
        doc.set_toc(toc)
        print(f"✓ {len(toc)} hierarchical bookmarks successfully injected.")
    except Exception as e:
        print(f"Warning setting TOC: {e}", file=sys.stderr)


def postprocess_pdf(
    pdf_path: Path,
    front_matter_count: int = 5,
    toc: Optional[List[List[Any]]] = None,
    toc_json_path: Optional[Path] = None,
) -> None:
    """Performs metadata post-processing and safe atomic rewrite."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.", file=sys.stderr)
        return

    doc = pymupdf.open(str(pdf_path))
    inject_page_labels(doc, front_matter_count)

    if toc_json_path and Path(toc_json_path).exists():
        with open(toc_json_path, encoding="utf-8") as f:
            toc = json.load(f)

    if toc:
        inject_bookmarks(doc, toc)

    tmp_path = pdf_path.with_name(f"{pdf_path.stem}_tmp.pdf")
    doc.save(str(tmp_path), deflate=True)
    doc.close()
    tmp_path.replace(pdf_path)
    print(f"✓ Post-processing complete for {pdf_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-process PDF metadata and bookmarks")
    parser.add_argument("pdf", type=Path, help="Path to PDF")
    parser.add_argument("--front-matter", type=int, default=5, help="Number of front matter pages")
    parser.add_argument("--toc-json", type=Path, help="Path to TOC JSON [[level, title, pagenum], ...]")
    args = parser.parse_args()

    postprocess_pdf(args.pdf, front_matter_count=args.front_matter, toc_json_path=args.toc_json)


if __name__ == "__main__":
    main()
