#!/usr/bin/env python3
"""
AlexandriaSandwich - Post-Process PDF Metadata
Injects native PDF page labels (Roman for front matter, Arabic for body, or custom title/extract labels)
and hierarchical table-of-contents bookmarks via PyMuPDF.
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
    front_matter_count: int = 5,
    front_matter_style: str = "r",  # lowercase roman: i, ii, iii
    body_style: str = "D",         # decimal arabic: 1, 2, 3
    body_start_num: int = 1,
    has_title_page: bool = False,
    custom_labels: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Injects native PDF page labels into document catalog."""
    if custom_labels:
        labels = custom_labels
    elif has_title_page:
        # Title page followed by body starting at body_start_num
        labels = [
            {"startpage": 0, "prefix": "Titel", "style": "none"},
            {"startpage": 1, "firstpagenum": body_start_num, "style": body_style},
        ]
    else:
        labels = [
            {"startpage": 0, "prefix": "", "style": front_matter_style, "firstpagenum": 1},
            {"startpage": front_matter_count, "prefix": "", "style": body_style, "firstpagenum": body_start_num},
        ]

    try:
        doc.set_page_labels(labels)
        labels_preview = [p.get_label() for p in doc][:5]
        print(f"✓ Native PDF page labels injected: {labels_preview}...")
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
    body_start_num: int = 1,
    has_title_page: bool = False,
    custom_labels: Optional[List[Dict[str, Any]]] = None,
    toc: Optional[List[List[Any]]] = None,
    toc_json_path: Optional[Path] = None,
) -> None:
    """Performs metadata post-processing and safe atomic rewrite."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.", file=sys.stderr)
        return

    doc = pymupdf.open(str(pdf_path))
    inject_page_labels(
        doc,
        front_matter_count=front_matter_count,
        body_start_num=body_start_num,
        has_title_page=has_title_page,
        custom_labels=custom_labels,
    )

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
    parser.add_argument("--title-page", action="store_true", help="Document has a single title page ('Titel')")
    parser.add_argument("--body-start", type=int, default=1, help="First page number for body text")
    parser.add_argument("--labels-json", type=Path, help="Path to custom page labels JSON")
    parser.add_argument("--toc-json", type=Path, help="Path to TOC JSON [[level, title, pagenum], ...]")
    args = parser.parse_args()

    custom_labels = None
    if args.labels_json and args.labels_json.exists():
        with open(args.labels_json, encoding="utf-8") as f:
            custom_labels = json.load(f)

    postprocess_pdf(
        args.pdf,
        front_matter_count=args.front_matter,
        body_start_num=args.body_start,
        has_title_page=args.title_page,
        custom_labels=custom_labels,
        toc_json_path=args.toc_json,
    )


if __name__ == "__main__":
    main()
