#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/render_digital_pdf.py
Renders consolidated book structure (book.json / book.md) into a clean,
publication-grade digital vector-text PDF using Typst (Artifact 3).
Preserves original page breaks and output distribution (1:1 page concordance).
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
from typing import Any, Dict, List, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [render_digital_pdf] {msg}", file=sys.stderr)


def escape_typst(text: str) -> str:
    """Escape special Typst syntax characters in plain text."""
    # Escape backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace("[", "\\[").replace("]", "\\]")
    text = text.replace("<", "\\<").replace(">", "\\>")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("@", "\\@")
    text = text.replace("`", "\\`")
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    text = text.replace("=", "\\=")
    # Escape leading slash to avoid Typst description list syntax
    text = re.sub(r"^(\s*)/", r"\1\\/", text, flags=re.MULTILINE)
    return text


def clean_latex_to_unicode(text: str) -> str:
    """Convert LaTeX formulas, superscripts, subscripts and arrows to clean Unicode text."""
    sup_map = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
    sub_map = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")

    # Superscripts: $^{1}$ or $^1$ or $^{10}$
    text = re.sub(r"\$\^\{?([0-9a-zA-Z+-]+)\}?\$", lambda m: m.group(1).translate(sup_map), text)

    # Subscripts: x_1 or x_{1}
    text = re.sub(r"([a-zA-Z])_\{?([0-9]+)\}?", lambda m: m.group(1) + m.group(2).translate(sub_map), text)

    # Simple math wrappers: \(...\) or $$...$$ or $...$
    text = re.sub(r"\\begin\{aligned\}(.*?)\\end\{aligned\}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text)
    text = re.sub(r"\$(.*?)\$", r"\1", text)

    # Formatting macros
    text = re.sub(r"\\(?:mathrm|mathbf|text|textbf|textit)\{([^}]+)\}", r"\1", text)
    text = text.replace("\\rightarrow", "→").replace("\\Rightarrow", "⇒")
    text = text.replace("\\dot{N}", "Ṅ").replace("\\dot{n}", "ṅ")
    text = text.replace("\\bar{a}", "ā").replace("\\bar{u}", "ū").replace("\\bar{i}", "ī")
    text = text.replace("\\emptyset", "∅")
    text = text.replace("\\quad", " ")

    return text


SUTRA_PREFIX_RE = re.compile(r"^#?\s*\d+\.\d+(?:\.\d+)?\b|^#?\s*\d+\.\s+\d+\.\d+\b")
ITEM_RE = re.compile(
    r"^(?:[-*+]\s+)?(\(\s*(?:[0-9]{1,3}|[a-zA-Z]|[ivxLCDM]{1,6}|[0-9l][a-z]|[a-z]-[a-z])\s*\)|\b[0-9]{1,3}\.(?!\d))\s+(.*)$"
)
GLOSS_RE = re.compile(r"^['‘\u2018\u2019\"“].*")
FORMULA_RE = re.compile(r"^(?:=|\+|→|\$\\rightarrow|\(?[0-9]+\.[0-9]+\.[0-9]+|b[0-9]\s*=)")


def is_item_line(l: str) -> Optional[re.Match]:
    clean = re.sub(r"^#\s*(\d+\.\d+)", r"\1", l.strip())
    if SUTRA_PREFIX_RE.match(clean):
        return None
    m = ITEM_RE.match(clean)
    if m and m.group(1).endswith(".") and re.match(r"^\d+\.", m.group(2)):
        return None
    return m


def parse_list(lines: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    lead_lines = []
    items = []
    curr_label = None
    curr_body: List[str] = []

    for line in lines:
        line_clean = re.sub(r"^#\s*(\d+\.\d+)", r"\1", line.strip())
        m = is_item_line(line_clean)
        if m:
            if curr_label is not None:
                items.append((curr_label, " \\ ".join(curr_body)))
            curr_label = m.group(1).strip()
            rest = m.group(2).strip()
            curr_body = [rest] if rest else []
        else:
            if curr_label is not None:
                curr_body.append(line_clean)
            else:
                lead_lines.append(line_clean)

    if curr_label is not None:
        items.append((curr_label, " \\ ".join(curr_body)))

    return lead_lines, items


def format_block_as_typst(text: str) -> str:
    """
    Format a block of text into Typst markup.
    Preserves list structures, linguistic examples with glosses,
    verse quotes, and derivation steps using clean Typst grids and blocks.
    Joins accidental soft breaks in normal prose into continuous paragraphs.
    """
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not raw_lines:
        return ""
    if len(raw_lines) == 1:
        return format_inline_markdown(raw_lines[0])

    item_matches = [bool(is_item_line(l)) for l in raw_lines]
    num_item_matches = sum(item_matches)

    # 1. Multi-item or single-item structured list
    is_list = False
    if num_item_matches >= 2:
        is_list = True
    elif num_item_matches == 1 and item_matches[0]:
        if any(GLOSS_RE.match(l) or FORMULA_RE.match(l) for l in raw_lines[1:]):
            is_list = True

    if is_list:
        lead_lines, items = parse_list(raw_lines)
        res_parts = []
        if lead_lines:
            res_parts.append(format_inline_markdown(" ".join(lead_lines)))

        grid_cells = []
        for lbl, body in items:
            lbl_typ = format_inline_markdown(lbl)
            body_parts = []
            for bl in body.split(" \\ "):
                bl_clean = bl.strip()
                bl_clean = re.sub(r"^#\s*(\d+\.\d+)", r"\1", bl_clean)
                bl_fmt = format_inline_markdown(bl_clean)
                if bl_clean.startswith("="):
                    bl_fmt = f"#h(1.2em) {bl_fmt}"
                body_parts.append(bl_fmt)
            body_typ = " \\\n      ".join(body_parts)
            grid_cells.append(f"    [{lbl_typ}], [\n      {body_typ}\n    ]")
        cells_str = ",\n".join(grid_cells)
        res_parts.append(f"""#block(inset: (left: 1.2em), spacing: 0.45em)[
  #set par(leading: 0.42em)
  #grid(
    columns: (auto, 1fr),
    column-gutter: 0.6em,
    row-gutter: 0.55em,
{cells_str}
  )
]""")
        return "\n\n".join(res_parts)

    # 2. Two-column index block (Index of Terms, etc.)
    if len(raw_lines) >= 15:
        idx_matches = sum(bool(re.search(r"\b\d+(?:[-–—]\d+)?(?:,\s*\d+)*$", l)) for l in raw_lines)
        if idx_matches / len(raw_lines) >= 0.55:
            formatted_items = []
            for l in raw_lines:
                m = re.match(r"^(\*?[a-zA-ZāīūṛṝḷṅñṭḍṇśṣṃḥA-ZĀĪŪṚṜḶṄÑṬḌṆŚṢṂḤ\s\-–—/]+\*?)\s+(.*)$", l)
                if m:
                    term = format_inline_markdown(m.group(1).strip())
                    pgs = format_inline_markdown(m.group(2).strip())
                    formatted_items.append(f"_{term}_ {pgs}")
                else:
                    formatted_items.append(format_inline_markdown(l))
            half = (len(formatted_items) + 1) // 2
            col1 = " \\\n      ".join(formatted_items[:half])
            col2 = " \\\n      ".join(formatted_items[half:])
            return f"""#block(spacing: 0.45em)[
  #set text(size: 8.5pt)
  #set par(leading: 0.38em, first-line-indent: 0pt, hanging-indent: 1.2em)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 18pt,
    [
      {col1}
    ],
    [
      {col2}
    ]
  )
]"""

    # 3. Index of Sutras entries (multiple sutra entries in a single block)
    sutra_re = re.compile(r"^.+?\(\d+\.\d+\.\d+\)")
    if len(raw_lines) >= 2 and sum(bool(sutra_re.match(l)) for l in raw_lines) >= 2:
        formatted_items = [format_inline_markdown(l) for l in raw_lines]
        body_str = " \\\n  ".join(formatted_items)
        return f"""#block(spacing: 0.45em)[
  #set par(first-line-indent: 0pt, hanging-indent: 1.5em, leading: 0.42em)
  {body_str}
]"""

    # 4. Verse / Poetry or Derivation block
    is_verse_or_formula = False
    if any(l.endswith(("/", "//", "|", "||")) for l in raw_lines):
        is_verse_or_formula = True
    elif sum(bool(FORMULA_RE.match(l)) for l in raw_lines) >= 2:
        is_verse_or_formula = True

    if is_verse_or_formula:
        formatted_lines = [format_inline_markdown(l) for l in raw_lines]
        body_str = " \\\n  ".join(formatted_lines)
        return f"""#block(inset: (left: 1.5em), spacing: 0.45em)[
  #set par(first-line-indent: 0pt, leading: 0.45em)
  {body_str}
]"""

    # 5. Normal prose paragraph that had soft newlines: join into one paragraph
    joined_text = " ".join(raw_lines)
    return format_inline_markdown(joined_text)


def format_inline_markdown(text: str) -> str:
    """Convert Markdown inline formatting (bold, italic, code) to Typst syntax."""
    text = clean_latex_to_unicode(text)
    # 1. Protect inline code spans `code`
    code_tokens: List[str] = []
    def save_code(m):
        code_tokens.append(m.group(1))
        return f"\x00CODE{len(code_tokens)-1}\x00"
    text = re.sub(r"`([^`]+)`", save_code, text)

    # 2. Bold: **text**
    bold_tokens: List[str] = []
    def save_bold(m):
        bold_tokens.append(m.group(1))
        return f"\x00BOLD{len(bold_tokens)-1}\x00"
    text = re.sub(r"\*\*(.+?)\*\*", save_bold, text)

    # 3. Italic: *text* or _text_
    italic_tokens: List[str] = []
    def save_italic(m):
        italic_tokens.append(m.group(1))
        return f"\x00ITALIC{len(italic_tokens)-1}\x00"
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", save_italic, text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", save_italic, text)

    # 4. Escape Typst syntax characters
    text = text.replace("\\", "\\\\")
    text = text.replace("[", "\\[").replace("]", "\\]")
    text = text.replace("<", "\\<").replace(">", "\\>")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("@", "\\@")
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    text = text.replace("=", "\\=")
    # Escape leading slash to avoid Typst description list syntax
    text = re.sub(r"^(\s*)/", r"\1\\/", text, flags=re.MULTILINE)

    # 5. Restore inline tokens with escaped contents (italic and bold)
    for i, it in enumerate(italic_tokens):
        it_escaped = format_inline_markdown(it)
        text = text.replace(f"\x00ITALIC{i}\x00", f"#emph[{it_escaped}]")

    for i, bd in enumerate(bold_tokens):
        bd_escaped = format_inline_markdown(bd)
        text = text.replace(f"\x00BOLD{i}\x00", f"#strong[{bd_escaped}]")

    # 6. Escape any `(` immediately following `#emph[...]` or `#strong[...]` to prevent Typst treating it as function arguments
    text = re.sub(r"(#(?:emph|strong)\[[^\]]+\])\(", r"\1\\(", text)

    # 7. Escape dot after numbers at word boundary to prevent accidental ordered lists and show rule recursion
    text = re.sub(r"(\b\d+)\.(?=\s|$)", r"\1\\.", text)

    # 8. Restore protected code spans (after all escaping rules so raw text remains untouched)
    for i, cd in enumerate(code_tokens):
        cd_escaped = cd.replace("\\", "\\\\").replace("`", "\\`")
        text = text.replace(f"\x00CODE{i}\x00", f"`{cd_escaped}`")

    return text


def calibrate_layout_from_pdf(pdf_path: Path) -> Optional[Dict[str, float]]:
    """
    Extract median page dimensions and printable text bounding box from reference PDF (aligned/sandwich).
    Returns dict with width, height, left, right, top, bottom in points.
    """
    try:
        import pymupdf
    except ImportError:
        log("PyMuPDF not available; skipping automated layout calibration.")
        return None

    if not pdf_path.exists():
        return None

    try:
        import statistics

        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        if total_pages == 0:
            return None

        # Sample up to 50 pages from the main body (avoiding cover/blank pages)
        start_p = min(10, max(0, total_pages - 1))
        end_p = min(60, total_pages)
        if end_p - start_p < 5:
            start_p = 0
            end_p = total_pages

        page_widths: List[float] = []
        page_heights: List[float] = []
        left_margins: List[float] = []
        right_margins: List[float] = []
        top_margins: List[float] = []
        bottom_margins: List[float] = []

        for pno in range(start_p, end_p):
            page = doc[pno]
            rect = page.rect
            page_widths.append(rect.width)
            page_heights.append(rect.height)

            blocks = [b for b in page.get_text("blocks") if len(b[4].strip()) > 5]
            if len(blocks) < 3:
                continue

            min_x = min(b[0] for b in blocks)
            max_x = max(b[2] for b in blocks)
            min_y = min(b[1] for b in blocks)
            max_y = max(b[3] for b in blocks)

            left_margins.append(min_x)
            right_margins.append(rect.width - max_x)
            top_margins.append(min_y)
            bottom_margins.append(rect.height - max_y)

        doc.close()

        if not left_margins:
            return None

        w = round(statistics.median(page_widths), 1)
        h = round(statistics.median(page_heights), 1)
        l = round(statistics.median(left_margins), 1)
        r = round(statistics.median(right_margins), 1)
        t = round(statistics.median(top_margins), 1)

        # Bottom margin: use the 20th percentile to measure full text pages (ignoring short chapter ends)
        sorted_b = sorted(bottom_margins)
        idx_20 = max(0, int(len(sorted_b) * 0.20))
        b = round(sorted_b[idx_20], 1)

        cal = {
            "width": w,
            "height": h,
            "left": l,
            "right": r,
            "top": t,
            "bottom": b,
        }
        log(f"Calibrated layout from {pdf_path.name}: {cal}")
        return cal
    except Exception as e:
        log(f"Warning: layout calibration failed: {e}")
        return None


def format_markdown_table(table_rows: List[str]) -> str:
    """Convert contiguous markdown table rows into native Typst #table with content-calibrated column widths."""
    data = []
    for r in table_rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        # Skip markdown separator row |---|---|
        if all(set(c).issubset({"-", ":", " "}) for c in cells if c):
            continue
        data.append(cells)
    if not data:
        return ""
    num_cols = max(len(r) for r in data)
    if num_cols == 0:
        return ""

    for row in data:
        while len(row) < num_cols:
            row.append("")

    # Check if this is a Table of Contents (2 columns, column 2 contains page numbers)
    is_toc = False
    if num_cols == 2:
        col2_cells = [r[1] for r in data]
        roman_or_digits = all(
            c == "" or c.isdigit() or c.lower() in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"}
            for c in col2_cells
        )
        if roman_or_digits and len(data) >= 5:
            is_toc = True

    if is_toc:
        grid_items = []
        for row in data:
            title = row[0].strip()
            page_no = row[1].strip() if len(row) > 1 else ""

            clean_t = title.lower()
            if title.startswith("1. ") or "bibliography" in clean_t:
                grid_items.append("grid.cell(colspan: 3)[#v(0.8em)]")

            m = re.match(r"^(\d+\.)\s*(.*)$", title)
            if m:
                num_col = m.group(1)
                title_text = m.group(2)
            else:
                num_col = ""
                title_text = title

            num_cell = f"[{num_col}]" if num_col else "[]"
            t_fmt = format_inline_markdown(title_text)
            p_fmt = format_inline_markdown(page_no)
            grid_items.append(f"{num_cell}, [{t_fmt}], [{p_fmt}]")

        items_str = ",\n  ".join(grid_items)
        return f"""#align(center)[#block(width: 82%)[
#set text(size: 9.5pt)
#grid(
  columns: (1.8em, 1fr, auto),
  column-gutter: 0.8em,
  row-gutter: 0.48em,
  align: (col, row) => if col == 0 {{ right }} else if col == 1 {{ left }} else {{ right }},
  {items_str}
)]]"""

    if num_cols == 2 and not is_toc:
        # Key-Value / Abbreviations table (e.g. Page 11)
        grid_items = []
        for row in data:
            key = row[0].strip()
            val = row[1].strip() if len(row) > 1 else ""
            k_fmt = format_inline_markdown(key)
            v_fmt = format_inline_markdown(val)
            grid_items.append(f"[{k_fmt}], [{v_fmt}]")
        items_str = ",\n  ".join(grid_items)
        return f"""#align(center)[#block(width: auto)[
#set text(size: 9.5pt)
#grid(
  columns: (auto, auto),
  column-gutter: 24pt,
  row-gutter: 0.65em,
  align: left,
  {items_str}
)]]"""

    # General multi-column table (Booktabs style)
    content_rows = data[1:] if len(data) > 1 else data
    col_widths = []
    col_aligns = []
    for c_idx in range(num_cols):
        col_cells = [r[c_idx] for r in content_rows]
        max_len = max((len(c) for c in col_cells), default=0)
        is_numeric = all(c == "" or c.isdigit() or len(c) <= 2 or c in {",,", '"', "°"} for c in col_cells)

        if is_numeric or max_len <= 3:
            col_widths.append("auto")
            col_aligns.append("center")
        elif max_len <= 8:
            col_widths.append("1.2fr")
            col_aligns.append("left")
        elif max_len <= 16:
            col_widths.append("2fr")
            col_aligns.append("left")
        else:
            col_widths.append("3fr")
            col_aligns.append("left")

    if all(w == "auto" for w in col_widths):
        col_widths = ["1fr"] * num_cols

    col_spec = ", ".join(col_widths)
    typ_cells = []
    for row in data:
        for c in row:
            tc = format_inline_markdown(c)
            typ_cells.append(f"[{tc}]")
    cells_str = ", \n    ".join(typ_cells)

    align_entries = [f"if col == {i} {{ {align} }}" for i, align in enumerate(col_aligns)]
    align_fn = f"(col, row) => {' else '.join(align_entries)} else {{ left }}" if num_cols > 1 else "left"

    t_font_size = "7.0pt" if num_cols >= 10 else ("7.8pt" if len(data) > 28 else ("8.2pt" if len(data) > 14 else "8.8pt"))
    inset_x = "2pt" if num_cols >= 10 else "4pt"
    inset_y = "1.5pt" if len(data) > 14 else "2.4pt"

    return f"""#align(center)[#block(width: 100%)[
#set text(size: {t_font_size})
#table(
  columns: ({col_spec}),
  stroke: (x, y) => if y == 0 {{ (bottom: 0.6pt + luma(100)) }} else if y == {len(data)} {{ (bottom: 0.6pt + luma(100)) }} else {{ none }},
  inset: (x: {inset_x}, y: {inset_y}),
  fill: none,
  align: {align_fn},
  {cells_str}
)]]"""


def build_typst_document(
    book_data: Dict[str, Any],
    template_path: str = "/templates/book.typ",
    paper: Optional[str] = None,
    preserve_pages: bool = True,
    layout_calibration: Optional[Dict[str, float]] = None,
    typeset_mode: Optional[str] = None,
) -> str:
    """Generate complete Typst source code from book dictionary."""
    meta = book_data.get("metadata", {})
    heuristics = meta.get("heuristics", {})
    mode = typeset_mode or heuristics.get("typeset_mode", "")
    is_two_col_profile = heuristics.get("two_column", False) or mode == "dictionary_grid"

    title = meta.get("title", "Untitled Book")
    author = meta.get("author", "Alexandria Archive")
    date_val = meta.get("generated_at", "")[:10]
    raw_lang = meta.get("language", "deu+eng")
    
    # Map OCR lang code to Typst language code
    lang_map = {
        "deu": "de", "ger": "de", "eng": "en", "fra": "fr", "fre": "fr",
        "ita": "it", "spa": "es", "lat": "la", "san": "sa"
    }
    first_lang = raw_lang.split("+")[0].strip().lower()
    typst_lang = lang_map.get(first_lang, "de")

    # Determine page dimensions
    pages = book_data.get("pages", [])
    dim_args: List[str] = []

    if layout_calibration:
        dim_args.append(f'  width: {layout_calibration["width"]}pt,')
        dim_args.append(f'  height: {layout_calibration["height"]}pt,')
        dim_args.append(f'  margin: (left: {layout_calibration["left"]}pt, right: {layout_calibration["right"]}pt, top: {layout_calibration["top"]}pt, bottom: {layout_calibration["bottom"]}pt),')
    elif paper:
        dim_args.append(f'  paper: "{paper}",')
    elif preserve_pages and pages:
        # Check if first page has geometry bbox [ymin, xmin, ymax, xmax] or [x0, y0, x1, y1]
        bbox = pages[0].get("bbox", [])
        if len(bbox) == 4 and bbox[2] > 0 and bbox[3] > 0:
            w_px = bbox[2] - bbox[0] if bbox[2] > bbox[0] else bbox[2]
            h_px = bbox[3] - bbox[1] if bbox[3] > bbox[1] else bbox[3]
            w_pt = round(w_px / 300.0 * 72.0, 1)
            h_pt = round(h_px / 300.0 * 72.0, 1)
            if w_pt > 280 and h_pt > 350:
                dim_args.append(f'  width: {w_pt}pt,')
                dim_args.append(f'  height: {h_pt}pt,')
    
    if not dim_args:
        dim_args.append('  paper: "iso-b5",')

    page_labels = [p.get("printed_page", str(p.get("page_num", i + 1))) for i, p in enumerate(pages)]
    labels_typst = ", ".join(f'"{l}"' for l in page_labels)

    lines = [
        f'#import "{template_path}": book, orig-page, fit-page, page-footnotes',
        f'#show: book.with(',
        f'  title: "{escape_typst(title)}",',
        f'  author: "{escape_typst(author)}",',
        f'  date: "{date_val}",',
        *dim_args,
        f'  preserve_pages: {"true" if preserve_pages else "false"},',
        f'  lang: "{typst_lang}",',
        f'  page_labels: ({labels_typst}),',
        f'  front_matter_pages: 6',
        f')',
        '',
        '// Auto-scale layout macro ensuring each original page stays strictly within 1 page without row clumping',
        '#let page_content = fit-page',
        ''
    ]

    # Build TOC chapter mapping to recognize real chapter titles vs running headers
    toc_map: Dict[str, str] = {}
    for p in pages:
        p_blocks = p.get("blocks", [])
        if any(b.get("text", "").strip() == "Contents" for b in p_blocks):
            for b in p_blocks:
                txt = b.get("text", "")
                if "|" in txt:
                    for line in txt.splitlines():
                        if not line.startswith("|") or "---" in line:
                            continue
                        parts = [pt.strip() for pt in line.strip("|").split("|")]
                        if len(parts) >= 2:
                            entry_title = parts[0].strip("* ").strip()
                            pno = parts[1].strip()
                            if pno:
                                toc_map[pno] = entry_title

    for idx, page in enumerate(pages):
        p_num = page.get("page_num", idx + 1)
        pr_label = str(page.get("printed_page", "")).strip()
        raw_blocks = page.get("blocks", [])
        
        # Filter hallucinated prompts on blank pages
        blocks = [
            b for b in raw_blocks
            if "ground truth image displays" not in b.get("text", "").lower()
            and "underscore & line rules" not in b.get("text", "").lower()
            and b.get("text", "").strip()
        ]

        page_elements: List[str] = []
        table_acc: List[str] = []

        def flush_table():
            if table_acc:
                tbl_typ = format_markdown_table(table_acc)
                if tbl_typ:
                    page_elements.append(tbl_typ)
                table_acc.clear()

        p_blocks = []
        has_table = False

        # Check if this page is a chapter/section start page
        is_chapter_page = pr_label in toc_map
        if is_chapter_page:
            ch_title = toc_map[pr_label]
            page_elements.append(f"= {format_inline_markdown(ch_title)}")
            skip_idx = 0
            while skip_idx < len(blocks) and skip_idx < 2:
                b_text = blocks[skip_idx].get("text", "").strip()
                b_type = blocks[skip_idx].get("type", "")
                if b_text.isdigit() or b_type in {"h1", "h2"} or b_text in ch_title:
                    skip_idx += 1
                else:
                    break
            blocks_to_process = blocks[skip_idx:]
        else:
            # Check if initial blocks are scanned running headers (e.g. [2] [The Astadhyayi...] or [Panini...] [3])
            skip_idx = 0
            if len(blocks) >= 2 and pr_label:
                b0_t = blocks[0].get("text", "").strip()
                b1_t = blocks[1].get("text", "").strip()
                if (b0_t == pr_label and len(b1_t) < 65) or (b1_t == pr_label and len(b0_t) < 65):
                    skip_idx = 2
            blocks_to_process = blocks[skip_idx:]

        for block in blocks_to_process:
            b_type = block.get("type", "p")
            text = block.get("text", "").strip()
            if not text:
                continue

            if b_type == "table_row":
                has_table = True
                table_acc.append(text)
                continue
            
            flush_table()

            # Check if block contains an embedded Markdown table
            blk_lines = [l.strip() for l in text.splitlines() if l.strip()]
            tbl_lines = [l for l in blk_lines if l.startswith("|")]
            if len(tbl_lines) >= 2 and any("---" in l for l in tbl_lines):
                has_table = True
                tbl_typ = format_markdown_table(tbl_lines)
                if tbl_typ:
                    page_elements.append(tbl_typ)
                continue

            if b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                level = int(b_type[1])
                eqs = "=" * level
                page_elements.append(f"{eqs} {format_inline_markdown(text)}")
            else:
                p_blocks.append(text)
                page_elements.append(format_block_as_typst(text))

        flush_table()

        # Multi-column heuristic: detect dictionary, list, or vocabulary pages without table syntax
        is_narrow_list = False
        is_front_matter_page = idx <= 4 or any(
            fm in str(page_elements).lower()
            for fm in ("preface", "introduction", "vorwort", "inhalt", "table of contents", "title")
        )
        if not has_table:
            if is_two_col_profile and not is_front_matter_page and len(page_elements) >= 3:
                is_narrow_list = True
            elif len(p_blocks) >= 12:
                lens = [len(t) for t in p_blocks]
                avg_l = sum(lens) / len(lens) if lens else 0
                max_l = max(lens) if lens else 0
                if avg_l <= 55 and max_l < 140:
                    is_narrow_list = True

        if is_narrow_list:
            lead_headings = []
            list_items = []
            for elem in page_elements:
                if not list_items and elem.startswith("="):
                    lead_headings.append(elem)
                else:
                    list_items.append(elem)

            if list_items:
                half = (len(list_items) + 1) // 2
                col1 = "\n\n".join(list_items[:half])
                col2 = "\n\n".join(list_items[half:])
                col_block = f"""#set text(size: 8.5pt)
#set block(spacing: 0.25em)
#set par(leading: 0.35em)
#grid(
  columns: (1fr, 1fr),
  column-gutter: 0pt,
  inset: (x, y) => if x == 0 {{ (right: 12pt) }} else {{ (left: 12pt) }},
  [
{col1}
  ],
  grid.vline(stroke: 0.35pt + luma(140)),
  [
{col2}
  ]
)"""
                if lead_headings:
                    content_body = "\n\n".join(lead_headings) + "\n\n" + col_block
                else:
                    content_body = col_block
            else:
                content_body = "\n\n".join(page_elements)
        else:
            content_body = "\n\n".join(page_elements)

        lines.append(f"// --- Original Page {p_num} (printed: {pr_label}) ---")
        if preserve_pages:
            lines.append(f"#fit-page[\n{content_body}\n]")
            if idx < len(pages) - 1:
                lines.append("#pagebreak()")
        else:
            cite_label = pr_label if pr_label else str(p_num)
            if is_chapter_page and idx > 0:
                lines.append("#pagebreak(weak: true)")
            lines.append(f"#orig-page(\"{cite_label}\")")
            lines.append(content_body)
        lines.append("")

    return "\n".join(lines)


def render_pdf(
    job_name: str,
    input_file: Path,
    output_file: Path,
    project_root: Path,
    paper: Optional[str] = None,
    preserve_pages: bool = True,
    reference_pdf: Optional[Path] = None,
    font_path: Optional[Path] = None,
    typeset_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile Typst document into high-quality digital PDF."""
    start_time = time.time()
    
    # 1. Load book data
    if input_file.suffix == ".json":
        with open(input_file, "r", encoding="utf-8") as f:
            book_data = json.load(f)
    elif input_file.suffix == ".md":
        sibling_json = input_file.parent / "book.json"
        if sibling_json.exists():
            with open(sibling_json, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        else:
            book_data = {
                "metadata": {"job": job_name, "title": job_name},
                "pages": [{"page_num": 1, "blocks": [{"type": "p", "text": input_file.read_text(encoding="utf-8")}]}]
            }
    else:
        raise ValueError(f"Unsupported input file format: {input_file}")

    # 2. Automated Satzspiegel- & Layout-Kalibrierung from reference PDF if available
    layout_cal: Optional[Dict[str, float]] = None
    cal_ref_used: Optional[Path] = None
    if preserve_pages:
        candidate_refs: List[Path] = []
        if reference_pdf:
            candidate_refs.append(reference_pdf)
        pdf_dir = output_file.parent
        data_root = project_root / "data"
        candidate_refs.extend([
            pdf_dir / f"{job_name}.aligned.pdf",
            pdf_dir / f"{job_name}.sandwich.pdf",
            pdf_dir / f"{job_name}.pdf",
            input_file.parent / f"{job_name}.aligned.pdf",
            data_root / "input" / job_name / f"{job_name}.pdf",
            data_root / "input" / f"{job_name}.pdf",
        ])
        for cand in candidate_refs:
            if cand.exists():
                layout_cal = calibrate_layout_from_pdf(cand)
                if layout_cal:
                    cal_ref_used = cand
                    break

    # 3. Generate Typst source
    template_file = (project_root / "templates" / "book.typ").resolve()
    if not template_file.exists():
        template_file = (Path(__file__).resolve().parent.parent / "templates" / "book.typ").resolve()
    
    typst_code = build_typst_document(
        book_data,
        template_path=str(template_file),
        paper=paper,
        preserve_pages=preserve_pages,
        layout_calibration=layout_cal,
        typeset_mode=typeset_mode,
    )

    # 4. Write temp .typ file in job directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_typ = output_file.parent / f"{job_name}.digital.typ"
    with open(temp_typ, "w", encoding="utf-8") as f:
        f.write(typst_code)

    # 5. Check for typst binary
    typst_cmd = shutil.which("typst")
    if not typst_cmd:
        if Path("/usr/local/bin/typst").exists():
            typst_cmd = "/usr/local/bin/typst"
        else:
            raise RuntimeError("Typst CLI not found. Please ensure typst is installed in PATH.")

    # 5a. Assemble compile arguments with font-path vendoring support
    compile_args = [typst_cmd, "compile", "--root", "/"]
    resolved_fonts: Optional[Path] = None
    if font_path and font_path.is_dir():
        resolved_fonts = font_path
    else:
        for cand_f in (project_root / "data" / "fonts", project_root / "fonts", Path("data/fonts")):
            if cand_f.is_dir():
                resolved_fonts = cand_f.resolve()
                break

    if resolved_fonts:
        compile_args.extend(["--font-path", str(resolved_fonts)])

    compile_args.extend([str(temp_typ), str(output_file)])
    log(f"Compiling with Typst: {' '.join(compile_args)}")
    proc = subprocess.run(
        compile_args,
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        log(f"Typst compilation failed: {proc.stderr}")
        raise RuntimeError(f"Typst failed with code {proc.returncode}: {proc.stderr}")

    elapsed = round(time.time() - start_time, 2)
    pdf_size = output_file.stat().st_size
    log(f"Successfully generated digital vector PDF ({pdf_size} bytes in {elapsed}s): {output_file}")

    # 5b. Automated TOC Outline & Page Labels Quality Gate
    try:
        inject_script = Path(__file__).resolve().parent / "inject_toc.py"
        if not inject_script.is_file():
            inject_script = project_root / "scripts" / "inject_toc.py"
        cand_tocs = [
            output_file.parent / f"{job_name}.toc.txt",
            output_file.parent / "toc.txt",
            input_file.parent / f"{job_name}.toc.txt",
            input_file.parent / "toc.txt",
            project_root / "data" / "input" / job_name / f"{job_name}.toc.txt",
            project_root / "data" / "input" / job_name / "toc.txt",
        ]
        toc_file = next((p for p in cand_tocs if p.is_file()), None)
        if toc_file and inject_script.is_file():
            log(f"Injecting TOC outline and page labels from {toc_file}...")
            proc_toc = subprocess.run([sys.executable, str(inject_script), "-i", str(output_file), "-t", str(toc_file)], capture_output=True, text=True)
            if proc_toc.returncode == 0:
                log("TOC outline and page labels successfully injected.")
            else:
                log(f"Warning: TOC outline injection failed (code {proc_toc.returncode}): {proc_toc.stderr.strip()}")
        else:
            log("Note: No TOC file or inject script found; outline injection skipped.")
    except Exception as e:
        log(f"Note: TOC outline injection skipped: {e}")

    # 6. Automated Optical & Vector Layout Audit
    audit_res = None
    try:
        from audit_digital_layout import audit_pdf_layout
        ref_for_audit = cal_ref_used if 'cal_ref_used' in locals() and cal_ref_used else (reference_pdf if reference_pdf else None)
        audit_res = audit_pdf_layout(output_file, reference_pdf=ref_for_audit)
        audit_json = output_file.parent / f"{job_name}.audit.json"
        with open(audit_json, "w", encoding="utf-8") as f:
            json.dump(audit_res, f, indent=2, ensure_ascii=False)
        log(f"Layout Audit: {audit_res['clean_pages']}/{audit_res['total_pages']} clean pages ({audit_res['quality_score_pct']}%), {audit_res['collisions_count']} collisions, {audit_res['narrow_columns_count']} narrow columns, {audit_res['extreme_font_count']} overscaled")
    except Exception as e:
        log(f"Note: layout audit skipped: {e}")

    return {
        "job": job_name,
        "digital_pdf": str(output_file),
        "size_bytes": pdf_size,
        "elapsed_sec": elapsed,
        "paper": paper,
        "audit": audit_res
    }


def main():
    parser = argparse.ArgumentParser(description="Render consolidated book to publication-grade digital PDF via Typst")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. e2e_m1)")
    parser.add_argument("--input", "-i", help="Path to book.json or book.md (default: /data/output/books/<job>/book.json)")
    parser.add_argument("--output", "-o", help="Path to output PDF (default: /data/output/pdf/<job>.digital.pdf)")
    parser.add_argument("--reference-pdf", "-r", help="Reference scan PDF for automated layout calibration (default: autodetect aligned/sandwich)")
    parser.add_argument("--paper", default=None, help="Paper size (b5, a4, a5, etc., default: matches source scan geometry)")
    parser.add_argument(
        "--mode",
        choices=["boehtlingk", "paginated"],
        default="boehtlingk",
        help="Render mode: 'boehtlingk' (default: reflow scholarly edition with marginal original page citations) or 'paginated' (experimental 1:1 facsimile pagination)",
    )
    parser.add_argument("--preserve-pages", action="store_true", help="Alias for --mode paginated")
    parser.add_argument("--no-preserve-pages", action="store_true", help="Alias for --mode boehtlingk")
    parser.add_argument("--root", help="Project root for Typst imports (default: repo root)")
    parser.add_argument("--font-path", help="Path to vendored font directory (default: autodetect data/fonts)")
    parser.add_argument("--typeset-mode", help="Typeset mode: reconstructed_1to1, scholarly_reflow, dictionary_grid")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    project_root = Path(args.root).resolve() if args.root else repo_root

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and (repo_root / "data").exists():
        data_dir = repo_root / "data"

    cand_inputs = [
        data_dir / "output" / args.job / f"{args.job}.book.json",
        data_dir / "output" / args.job / "book.json",
        data_dir / "output" / "books" / args.job / "book.json",
    ]
    resolved_input = next((p for p in cand_inputs if p.exists()), cand_inputs[0])
    input_file = Path(args.input) if args.input else resolved_input
    output_file = Path(args.output) if args.output else data_dir / "output" / args.job / f"{args.job}.digital.pdf"
    ref_pdf = Path(args.reference_pdf) if args.reference_pdf else None
    font_path = Path(args.font_path).resolve() if args.font_path else None

    mode = args.mode
    if args.preserve_pages:
        mode = "paginated"
    elif args.no_preserve_pages:
        mode = "boehtlingk"

    preserve_pages = (mode == "paginated")

    render_pdf(
        job_name=args.job,
        input_file=input_file,
        output_file=output_file,
        project_root=project_root,
        paper=args.paper,
        preserve_pages=preserve_pages,
        reference_pdf=ref_pdf,
        font_path=font_path,
        typeset_mode=args.typeset_mode,
    )


if __name__ == "__main__":
    main()
