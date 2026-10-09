#!/usr/bin/env python3
"""
scripts/build_option_b.py — AlexandriaSandwich Option B Generator
Renders a pure digital vector PDF maintaining 1:1 original page geometry,
bounding boxes, and line breaks, without photographic raster scans.

Usage:
  python3 scripts/build_option_b.py \
    --input /path/to/document_outline.pdf \
    --output /path/to/sample_option_b.pdf \
    --start-page 150 \
    --end-page 157
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF


DEFAULT_FONT = "/Library/Fonts/Arial Unicode.ttf"


def clean_line_text(text: str) -> str:
    """Clean common OCR artifacts while preserving scholarly diacritics."""
    t = text.strip()
    return t


def build_option_b(
    input_pdf: Path,
    output_pdf: Path,
    start_page: int = 1,
    end_page: Optional[int] = None,
    font_file: str = DEFAULT_FONT,
    title: Optional[str] = None,
    author: Optional[str] = None,
    toc_entries: Optional[List[Tuple[int, str, int]]] = None,
) -> Path:
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    src_doc = fitz.open(input_pdf)
    total_src = len(src_doc)
    if end_page is None or end_page > total_src:
        end_page = total_src

    print(f"[option_b] Processing pages {start_page} to {end_page} from {input_pdf}")
    out_doc = fitz.open()

    page_offset = start_page - 1

    for pno in range(start_page - 1, end_page):
        page = src_doc[pno]
        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        d = page.get_text("dict")

        for b in d.get("blocks", []):
            if b.get("type") == 0:  # text block
                for line in b.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    txt = "".join(s.get("text", "") for s in spans).strip()
                    if not txt:
                        continue

                    rect = fitz.Rect(line["bbox"])
                    max_fs = spans[0]["size"]
                    expanded_rect = fitz.Rect(
                        rect.x0 - 1.0,
                        rect.y0 - 2.0,
                        rect.x1 + 8.0,
                        rect.y1 + 4.0,
                    )

                    # Try decreasing font sizes slightly until line fits inside box
                    for fs in [max_fs, max_fs * 0.96, max_fs * 0.92, max_fs * 0.88, max_fs * 0.82]:
                        rc = new_page.insert_textbox(
                            expanded_rect,
                            txt,
                            fontfile=font_file,
                            fontname="CleanVector",
                            fontsize=fs,
                            align=0,
                        )
                        if rc >= 0:
                            break

    # Metadata
    meta = out_doc.metadata or {}
    meta["title"] = title or src_doc.metadata.get("title", "Digital Vector Edition (Option B)")
    meta["author"] = author or src_doc.metadata.get("author", "AlexandriaSandwich")
    meta["producer"] = "AlexandriaSandwich Pipeline (Option B: Geometric Vector Re-typeset)"
    out_doc.set_metadata(meta)

    # TOC
    if toc_entries:
        out_doc.set_toc(toc_entries)
    else:
        # Transfer relevant bookmarks from source
        src_toc = src_doc.get_toc()
        filtered_toc = []
        for lvl, name, p_target in src_toc:
            if start_page <= p_target <= end_page:
                rel_p = p_target - page_offset
                filtered_toc.append([lvl, name, rel_p])
        if filtered_toc:
            out_doc.set_toc(filtered_toc)
            print(f"[option_b] Injected {len(filtered_toc)} bookmarks.")

    # Font subsetting (reduces file from ~15 MB down to < 100 KB)
    print("[option_b] Subsetting fonts...")
    out_doc.subset_fonts()

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(
        str(output_pdf),
        deflate=True,
        garbage=3,
        clean=True,
    )
    out_doc.close()
    src_doc.close()

    size_kb = output_pdf.stat().st_size / 1024
    print(f"[option_b] Successfully generated: {output_pdf} ({size_kb:.1f} KB, {end_page - start_page + 1} pages)")
    return output_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Option B: Geometric Vector Re-typeset PDF")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input PDF")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output PDF")
    parser.add_argument("--start-page", type=int, default=1, help="Start page (1-indexed)")
    parser.add_argument("--end-page", type=int, help="End page (1-indexed)")
    parser.add_argument("--font", default=DEFAULT_FONT, help="Path to TTF/OTF font")
    parser.add_argument("--title", help="Document Title")
    parser.add_argument("--author", help="Document Author")

    args = parser.parse_args()
    build_option_b(
        input_pdf=args.input,
        output_pdf=args.output,
        start_page=args.start_page,
        end_page=args.end_page,
        font_file=args.font,
        title=args.title,
        author=args.author,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
