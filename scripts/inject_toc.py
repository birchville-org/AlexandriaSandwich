#!/usr/bin/env python3
"""
scripts/inject_toc.py — Injects hierarchical outlines (bookmarks), metadata,
and page labels into a 1:1 Sandwich PDF without altering its visual layout or text layers.

Supports both machine JSON (*.toc.json) and human-editable plain text (*.toc.txt).

Usage:
  # Inject from human-editable text file:
  python3 scripts/inject_toc.py -i document.pdf --toc toc.txt

  # Extract existing TOC into an editable text file:
  python3 scripts/inject_toc.py -i document.pdf --extract-toc document.toc.txt

  # Inject and auto-export editable .toc.txt artifact:
  python3 scripts/inject_toc.py -i document.pdf --toc toc.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf


def parse_toc_text(text: str) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Parse human-editable plain-text TOC specification.

    Format:
      # Optional metadata headers
      Title: Book Title
      Author: Author Name
      Subject: Subject line
      Keywords: tag1, tag2
      Roman-End: 12
      Arabic-Start: 13

      # Outline entries: [Indentation 2 spaces or 1 tab per level] Title | Page
      1 Chapter Title | 1
        1.1 Section Title | 5
        1.2 Another Section | 10
          1.2.1 Subsection | 12
    """
    lines = text.splitlines()
    toc: List[List[Any]] = []
    meta: Dict[str, Any] = {}

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Check for metadata headers
        m_meta = re.match(
            r'^(Title|Author|Subject|Keywords|Roman-End|Arabic-Start|Roman_End|Arabic_Start):\s*(.+)$',
            stripped,
            re.IGNORECASE,
        )
        if m_meta:
            key = m_meta.group(1).lower().replace("-", "_")
            val = m_meta.group(2).strip()
            if key in ("roman_end", "arabic_start"):
                try:
                    meta[key] = int(val)
                except ValueError:
                    pass
            else:
                meta[key] = val
            continue

        # Ignore comments unless it is a markdown heading (# Title | Page)
        m_h = re.match(r'^(#+)\s+(.+)$', stripped)
        if m_h:
            content = m_h.group(2).strip()
            # If line doesn't contain page number delimiter, treat as comment
            if "|" not in content and "\t" not in content and not re.search(r'\s+\d+$', content):
                continue
            lvl = len(m_h.group(1))
            entry_line = content
        elif stripped.startswith("#"):
            continue
        else:
            m_h = None
            entry_line = stripped

        # Determine level if not from markdown heading
        if not m_h:
            # Check explicit [1], [2], etc.
            m_lvl = re.match(r'^\[(\d+)\]\s*(.+)$', entry_line)
            if m_lvl:
                lvl = int(m_lvl.group(1))
                entry_line = m_lvl.group(2).strip()
            else:
                # Count leading spaces/tabs from raw_line
                indent = 0
                for ch in raw_line:
                    if ch == ' ':
                        indent += 1
                    elif ch == '\t':
                        indent += 4
                    else:
                        break
                lvl = (indent // 2) + 1

        # Strip bullet points like "- Title" or "* Title"
        entry_line = re.sub(r'^[\-\*]\s+', '', entry_line)

        # Split into Title and Page number
        # Delimiters: ' | ', '\t', ' ... ', '…', or trailing integer
        if "|" in entry_line:
            parts = entry_line.rsplit("|", 1)
            t_str = parts[0].strip()
            p_str = parts[1].strip()
        elif "\t" in entry_line:
            parts = entry_line.rsplit("\t", 1)
            t_str = parts[0].strip()
            p_str = parts[1].strip()
        elif "..." in entry_line:
            parts = entry_line.rsplit("...", 1)
            t_str = parts[0].strip()
            p_str = parts[1].strip()
        elif "…" in entry_line:
            parts = entry_line.rsplit("…", 1)
            t_str = parts[0].strip()
            p_str = parts[1].strip()
        else:
            m_p = re.search(r'\s+(\d+)$', entry_line)
            if m_p:
                t_str = entry_line[:m_p.start()].strip()
                p_str = m_p.group(1)
            else:
                continue

        try:
            page_num = int(p_str)
            if t_str and page_num > 0:
                toc.append([lvl, t_str, page_num])
        except ValueError:
            continue

    return toc, meta


def dump_toc_text(
    toc_data: List[List[Any]],
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Format hierarchical TOC data and metadata as human-editable plain text."""
    lines: List[str] = [
        "# AlexandriaSandwich — Table of Contents Specification",
        "# Syntax: Indentation (2 spaces per level) Title | Page",
        "# You can edit titles, levels, and page numbers directly in this file.",
        "# Lines starting with # are comments.",
    ]
    if meta:
        if meta.get("title"):
            lines.append(f"Title: {meta['title']}")
        if meta.get("author"):
            lines.append(f"Author: {meta['author']}")
        if meta.get("subject"):
            lines.append(f"Subject: {meta['subject']}")
        if meta.get("keywords"):
            lines.append(f"Keywords: {meta['keywords']}")
        if meta.get("roman_end"):
            lines.append(f"Roman-End: {meta['roman_end']}")
        if meta.get("arabic_start"):
            lines.append(f"Arabic-Start: {meta['arabic_start']}")
    lines.append("")

    for entry in toc_data:
        lvl, title, page = entry[0], entry[1], entry[2]
        indent = "  " * max(0, lvl - 1)
        lines.append(f"{indent}{title} | {page}")

    lines.append("")
    return "\n".join(lines)


def extract_toc_from_pdf(pdf_path: Path) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Extract existing TOC bookmarks and metadata from any PDF file."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    doc = pymupdf.open(pdf_path)
    toc = doc.get_toc()
    m = doc.metadata or {}
    meta = {
        "title": m.get("title", ""),
        "author": m.get("author", ""),
        "subject": m.get("subject", ""),
        "keywords": m.get("keywords", ""),
    }
    doc.close()
    return toc, meta


def normalize_toc_hierarchy(toc_entries: List[List[Any]]) -> List[List[Any]]:
    """
    Normalizes a list of [lvl, title, page] entries so that:
    1. The first entry is level 1.
    2. Levels never jump by more than +1 relative to the previous entry.
    3. Minimum level is 1.
    Prevents ValueError in doc.set_toc().
    """
    if not toc_entries:
        return []
    
    normalized = []
    prev_lvl = 0
    for lvl, title, page in toc_entries:
        try:
            lvl_val = max(1, int(lvl))
        except (ValueError, TypeError):
            lvl_val = 1

        if not normalized:
            lvl_val = 1
        else:
            if lvl_val > prev_lvl + 1:
                lvl_val = prev_lvl + 1
        normalized.append([lvl_val, str(title).strip(), int(page)])
        prev_lvl = lvl_val
    return normalized


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
    export_toc_txt: Optional[Path] = None,
) -> int:
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    print(f"[inject_toc] Opening: {input_pdf}")
    doc = pymupdf.open(input_pdf)
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

    # 3. Validate, Normalize and Set TOC
    valid_toc = []
    for entry in toc_data:
        lvl, name, page_num = entry[0], entry[1], entry[2]
        if not (1 <= page_num <= total_pages):
            print(f"[inject_toc] Warning: skipping out-of-range TOC entry '{name}' (p. {page_num})")
            continue
        valid_toc.append([lvl, name, page_num])

    valid_toc = normalize_toc_hierarchy(valid_toc)

    if valid_toc:
        doc.set_toc(valid_toc)
        print(f"[inject_toc] Injected {len(valid_toc)} hierarchical TOC entries.")
    else:
        print("[inject_toc] Warning: Injected 0 hierarchical TOC entries.")

    # 4. Save 1:1 preserving existing images and fonts
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temp_out = output_pdf.parent / f"_tmp_{output_pdf.name}"
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

    # 5. Export human-editable text file artifact alongside PDF
    if export_toc_txt is not None:
        try:
            export_meta = {
                "title": title or meta.get("title", ""),
                "author": author or meta.get("author", ""),
                "subject": subject or meta.get("subject", ""),
                "keywords": keywords or meta.get("keywords", ""),
                "roman_end": roman_end,
                "arabic_start": arabic_start,
            }
            txt_content = dump_toc_text(valid_toc, export_meta)
            export_toc_txt.parent.mkdir(parents=True, exist_ok=True)
            export_toc_txt.write_text(txt_content, encoding="utf-8")
            print(f"[inject_toc] Exported human-editable TOC artifact: {export_toc_txt}")
        except Exception as e:
            print(f"[inject_toc] Warning: Could not export TOC artifact {export_toc_txt}: {e}", file=sys.stderr)

    return len(valid_toc)


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
    parser.add_argument("-t", "--toc", type=Path, default=None, help="TOC file path: plain-text (*.toc.txt) or JSON (*.toc.json)")
    parser.add_argument("--book-json", type=Path, default=None, help="Optional book.json path to extract TOC and metadata")
    parser.add_argument("--extract-toc", type=Path, nargs="?", const=Path("__AUTO__"), default=None,
                        help="Extract existing TOC from input PDF into human-editable text file (default: <input>.toc.txt)")
    parser.add_argument("--export-toc", type=Path, default=None,
                        help="Explicit path to export human-editable *.toc.txt artifact")
    parser.add_argument("--no-export-toc", action="store_true",
                        help="Disable automatic export of *.toc.txt artifact alongside output PDF")
    parser.add_argument("--title", help="Document Title metadata")
    parser.add_argument("--author", help="Document Author metadata")
    parser.add_argument("--subject", help="Document Subject metadata")
    parser.add_argument("--keywords", help="Document Keywords metadata")
    parser.add_argument("--roman-end", type=int, help="Last page of Roman numerals (1-indexed)")
    parser.add_argument("--arabic-start", type=int, help="First page of Arabic numerals (1-indexed)")
    parser.add_argument("--require-toc", action="store_true",
                        help="Fail with exit code 1 if no TOC entries were injected")

    args = parser.parse_args()

    # Mode 1: Extraction only
    if args.extract_toc is not None:
        target_txt = args.extract_toc
        if str(target_txt) == "__AUTO__":
            target_txt = args.input.with_suffix(".toc.txt")
        toc, meta = extract_toc_from_pdf(args.input)
        txt = dump_toc_text(toc, meta)
        target_txt.parent.mkdir(parents=True, exist_ok=True)
        target_txt.write_text(txt, encoding="utf-8")
        print(f"[inject_toc] Extracted {len(toc)} TOC entries into: {target_txt}")
        return 0

    title = args.title
    author = args.author
    subject = args.subject
    keywords = args.keywords
    roman_end = args.roman_end
    arabic_start = args.arabic_start
    toc_data: List[List[Any]] = []

    # 1. Load from explicit --toc file if available (supports both JSON and Plain Text)
    if args.toc and args.toc.is_file():
        raw_content = args.toc.read_text(encoding="utf-8")
        parsed_as_json = False
        if not args.toc.name.endswith(".txt"):
            try:
                raw = json.loads(raw_content)
                parsed_as_json = True
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
            except Exception:
                parsed_as_json = False

        if not parsed_as_json:
            txt_toc, txt_meta = parse_toc_text(raw_content)
            if txt_toc:
                toc_data = txt_toc
                title = title or txt_meta.get("title")
                author = author or txt_meta.get("author")
                subject = subject or txt_meta.get("subject")
                keywords = keywords or txt_meta.get("keywords")
                if roman_end is None:
                    roman_end = txt_meta.get("roman_end")
                if arabic_start is None:
                    arabic_start = txt_meta.get("arabic_start")
                print(f"[inject_toc] Parsed {len(toc_data)} TOC entries from text file: {args.toc}")

    # 2. Fallback to --book-json if TOC or metadata still missing
    if args.book_json and args.book_json.is_file():
        bj_toc, bj_meta = extract_toc_from_book_json(args.book_json)
        if not toc_data:
            toc_data = bj_toc
        title = title or bj_meta.get("title")
        author = author or bj_meta.get("author")
        subject = subject or bj_meta.get("subject")

    if not toc_data and not title and not author and roman_end is None and arabic_start is None:
        print("[inject_toc] Warning: No TOC or metadata specified or found; leaving PDF unchanged.")
        if args.require_toc:
            return 1
        return 0

    out_path = args.output or args.input

    # Determine TOC text artifact path
    export_txt_path: Optional[Path] = None
    if not args.no_export_toc:
        if args.export_toc:
            export_txt_path = args.export_toc
        else:
            export_txt_path = out_path.with_suffix(".toc.txt")

    injected_count = inject_toc(
        input_pdf=args.input,
        output_pdf=out_path,
        toc_data=toc_data,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        roman_end=roman_end,
        arabic_start=arabic_start,
        export_toc_txt=export_txt_path,
    )
    if args.require_toc and injected_count == 0:
        print("[inject_toc] Error: --require-toc was set but 0 TOC entries were injected.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
