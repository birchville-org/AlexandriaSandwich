#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_typeset_edition.py

Builds a modern, publication-grade typographically typeset vector PDF (using Typst),
flowing naturally across pages (the Boethlingk model), with:
- Continuous multi-column / single-column typography without rigid scan-scale clamping.
- Native OpenType fonts (Noto Serif Devanagari, Linux Libertine O).
- Preserved scholarly citation references ([S. <orig_page>]) in margins.
- Dynamic running headers and hierarchical bookmarks.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def log(msg: str):
    print(f"[{time.strftime('%X')}] [typeset_edition] {msg}", file=sys.stderr)


def escape_typst(text: str) -> str:
    """Escape special Typst syntax characters in content blocks."""
    # Backslash first
    out = text.replace("\\", "\\\\")
    for char in ['#', '$', '@', '[', ']', '`', '*', '_']:
        out = out.replace(char, f"\\{char}")
    return out


def parse_dhatupatha_roots_page(lines: List[str], orig_page: int) -> List[Dict[str, Any]]:
    """Parse a Sūtrapāṭha page containing root listings into structured items."""
    items = []
    
    # Filter out standalone page numbers
    clean_lines = []
    for l in lines:
        s = l.strip()
        if not s or s.isdigit():
            continue
        # Sanskrit digits alone
        if len(s) < 4 and all(c in "०१२३४५६७८९" for c in s):
            continue
        clean_lines.append(s)

    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        
        # Heading
        if line.startswith("#"):
            h_text = line.lstrip("#").strip()
            items.append({"type": "heading", "text": h_text, "orig_page": orig_page})
            i += 1
            continue
        
        # Section intro (e.g. अथ चत्वारः परस्मैभाषाः—)
        if line.startswith("अथ") or "भाषाः" in line or "इति" in line:
            items.append({"type": "section_meta", "text": line, "orig_page": orig_page})
            i += 1
            continue

        # Case 1: Inline entry (e.g. "विद ज्ञाने ।")
        if "।" in line and len(line.split()) >= 2:
            parts = line.split("।")[0].strip().split(maxsplit=1)
            if len(parts) == 2:
                root, meaning = parts[0], parts[1] + " ।"
                items.append({
                    "type": "entry",
                    "root": root,
                    "meaning": meaning,
                    "orig_page": orig_page
                })
                i += 1
                continue

        # Case 2: List of roots followed by list of meanings (two-column OCR split)
        # Check if next N lines are roots (no danda) and subsequent N lines are meanings (contain danda)
        roots_chunk = []
        j = i
        while j < len(clean_lines) and "।" not in clean_lines[j] and not clean_lines[j].startswith("अथ") and not clean_lines[j].startswith("#"):
            roots_chunk.append(clean_lines[j])
            j += 1
        
        meanings_chunk = []
        k = j
        while k < len(clean_lines) and "।" in clean_lines[k] and not clean_lines[k].startswith("अथ") and not clean_lines[k].startswith("#"):
            meanings_chunk.append(clean_lines[k])
            k += 1

        if roots_chunk and meanings_chunk and len(roots_chunk) == len(meanings_chunk):
            for r, m in zip(roots_chunk, meanings_chunk):
                items.append({
                    "type": "entry",
                    "root": r,
                    "meaning": m,
                    "orig_page": orig_page
                })
            i = k
            continue

        # Fallback: regular line
        items.append({"type": "text", "text": line, "orig_page": orig_page})
        i += 1

    return items


def generate_typst_dhatupatha(
    book_title: str,
    parsed_items: List[Dict[str, Any]],
    paper: str = "iso-b5",
) -> str:
    """Generate professional, publication-grade Typst document for Dhātu-Pāṭha."""
    header_code = f"""
#set page(
  paper: "{paper}",
  columns: 2,
  margin: (top: 2.2cm, bottom: 2.2cm, inside: 2.4cm, outside: 2.0cm),
  header: context {{
    let p = counter(page).get().first()
    let headings = query(selector(heading).before(here()))
    let current_h = if headings.len() > 0 {{ headings.last().body }} else {{ [{escape_typst(book_title)}] }}
    if calc.even(p) [
      #text(8.5pt, weight: "bold")[#p]
      #h(1fr)
      #text(8pt, font: ("Linux Libertine O", "Noto Serif Devanagari"), style: "italic")[{escape_typst(book_title)} — Kritische Ausgabe]
    ] else [
      #text(8pt, font: ("Noto Serif Devanagari", "Linux Libertine O"), style: "italic")[#current_h]
      #h(1fr)
      #text(8.5pt, weight: "bold")[#p]
    ]
  }}
)

#set columns(gutter: 20pt)
#set text(
  font: ("Noto Serif Devanagari", "Linux Libertine O"),
  size: 9.5pt,
  lang: "sa"
)
#set par(justify: true, leading: 0.55em)

#let entry(root, meaning, page_ref) = [
  #block(width: 100%, breakable: false, inset: (y: 1.5pt))[
    #text(weight: "bold")[#root]
    #h(0.4em)
    #meaning
    #if page_ref != [] and page_ref != "" [
      #h(1fr)
      #text(size: 7pt, fill: luma(120))[[S. #page_ref]]
    ]
  ]
]
"""
    body_parts = []

    for it in parsed_items:
        itype = it.get("type", "text")
        op = it.get("orig_page")

        if itype == "heading":
            htext = escape_typst(it.get("text", ""))
            body_parts.append(f"\n#v(0.6em)\n#heading(level: 1)[{htext}]\n#v(0.2em)\n")
        elif itype == "section_meta":
            stext = escape_typst(it.get("text", ""))
            body_parts.append(f"#v(0.3em)\n#text(8.5pt, style: \"italic\")[{stext}]\n#v(0.2em)\n")
        elif itype == "entry":
            root = escape_typst(it.get("root", ""))
            meaning = escape_typst(it.get("meaning", ""))
            pref = str(op) if op else ""
            body_parts.append(f"#entry[{root}][{meaning}][{pref}]")
        else:
            t = escape_typst(it.get("text", ""))
            body_parts.append(f"[{t}]\n")

    return header_code + "\n".join(body_parts)


def build_typeset_edition(
    job_name: str,
    book_json_path: Path,
    output_pdf_path: Path,
    markdown_dir: Optional[Path] = None,
) -> None:
    """Build complete typeset edition."""
    start_t = time.time()
    log(f"Building typeset edition for {job_name}...")

    with open(book_json_path, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    meta = book_data.get("metadata", {})
    title = meta.get("title", job_name.replace("_", " ").title())
    pages = book_data.get("pages", [])

    all_parsed_items = []
    
    # Process each page from markdown or book.json blocks
    for page in pages:
        p_num = page.get("page_num", 1)
        lines = []

        # Check if markdown file exists for cleaner lines
        md_file = None
        if markdown_dir:
            cand = markdown_dir / f"{job_name}-{p_num:03d}.mistral.md"
            if cand.exists():
                md_file = cand

        if md_file:
            lines = md_file.read_text(encoding="utf-8").splitlines()
        else:
            for b in page.get("blocks", []):
                t = b.get("text", "").strip()
                if t:
                    lines.extend(t.splitlines())

        parsed_items = parse_dhatupatha_roots_page(lines, orig_page=p_num)
        all_parsed_items.extend(parsed_items)

    log(f"Parsed {len(all_parsed_items)} structured items across {len(pages)} pages.")

    typst_content = generate_typst_dhatupatha(title, all_parsed_items)

    temp_typ = output_pdf_path.parent / f"{job_name}.typeset.typ"
    temp_typ.write_text(typst_content, encoding="utf-8")

    # Compile with Typst
    typst_bin = shutil.which("typst")
    if not typst_bin:
        log("Typst not found locally, delegating compilation to docker worker if available.")
        sys.exit(0)

    cmd = [typst_bin, "compile", str(temp_typ), str(output_pdf_path)]
    log(f"Compiling Typst PDF: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        log(f"Typst compilation error: {proc.stderr}")
        sys.exit(1)

    mb = output_pdf_path.stat().st_size / (1024 * 1024)
    log(f"Typeset PDF ready: {output_pdf_path} ({mb:.2f} MB in {time.time()-start_t:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="AlexandriaSandwich Typeset Edition Builder")
    parser.add_argument("--job", "-j", required=True, help="Job name")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to book.json")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output target PDF path")
    parser.add_argument("--markdown-dir", "-m", type=Path, default=None, help="Optional markdown dir")
    args = parser.parse_args()

    build_typeset_edition(
        job_name=args.job,
        book_json_path=args.input,
        output_pdf_path=args.output,
        markdown_dir=args.markdown_dir,
    )


if __name__ == "__main__":
    main()
