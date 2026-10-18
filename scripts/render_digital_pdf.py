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
from typing import Any, Dict, List, Optional, Tuple


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
    text = re.sub(r"\\sqrt\{([^}]+)\}", r"√\1", text)
    text = text.replace("\\sqrt", "√")
    text = text.replace("\\rightarrow", "→").replace("\\Rightarrow", "⇒")
    text = text.replace("\\dot{N}", "Ṅ").replace("\\dot{n}", "ṅ")
    text = text.replace("\\bar{a}", "ā").replace("\\bar{u}", "ū").replace("\\bar{i}", "ī")
    text = text.replace("\\emptyset", "∅")
    text = text.replace("\\quad", " ")

    return text


SUTRA_PREFIX_RE = re.compile(r"^#?\s*\d+\.\d+(?:\.\d+)?\b|^#?\s*\d+\.\s+\d+\.\d+\b")
ITEM_RE = re.compile(
    r"^(?:[-*+]\s+)?(\(\s*(?:[0-9]{1,3}|[a-zA-Z]|[ivxLCDM]{1,6}|[0-9l][a-z]|[a-z]-[a-z])\s*\)|\b[0-9]{1,3}\.(?!\d)|\b[a-zA-Z]\.(?!\w))\s+(.*)$"
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
        line = raw_lines[0]
        sub_m = re.match(r"^([a-zA-Z]\.|\([a-zA-Z0-9]+\)|[ivxLCDM]+\.)\s+(.*)$", line)
        if sub_m and not re.match(r"^[A-Z]\.\s+[A-Z]\.", line):
            lbl = format_inline_markdown(sub_m.group(1))
            body = format_inline_markdown(sub_m.group(2))
            return f"""#block(inset: (left: 3.8em), spacing: 0.38em)[
  #set par(hanging-indent: 1.5em)
  {lbl} {body}
]"""
        num_m = re.match(r"^(\b\d{1,3}\.)\s+(.*)$", line)
        if num_m and not SUTRA_PREFIX_RE.match(line):
            lbl = format_inline_markdown(num_m.group(1))
            body = format_inline_markdown(num_m.group(2))
            return f"""#block(spacing: 0.85em)[
  #set par(justify: true, leading: 0.52em)
  #grid(
    columns: (2.0em, 1fr),
    [{lbl}],
    [{body}]
  )
]"""
        return format_inline_markdown(line)

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

        is_main_num_list = any(re.match(r"^\d{1,3}\.$", it[0].strip()) for it in items)
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
        if is_main_num_list:
            res_parts.append(f"""#block(spacing: 0.85em)[
  #set par(leading: 0.52em)
  #grid(
    columns: (2.0em, 1fr),
    row-gutter: 0.85em,
{cells_str}
  )
]""")
        else:
            res_parts.append(f"""#block(inset: (left: 3.8em), spacing: 0.45em)[
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

    # 5. Normal prose paragraph or single numbered section that had soft newlines
    joined_text = " ".join(raw_lines)
    num_m = re.match(r"^(\b\d{1,3}\.)\s+(.*)$", joined_text)
    if num_m and not SUTRA_PREFIX_RE.match(joined_text):
        lbl = format_inline_markdown(num_m.group(1))
        body = format_inline_markdown(num_m.group(2))
        return f"""#block(spacing: 0.85em)[
  #set par(justify: true, leading: 0.52em)
  #grid(
    columns: (2.0em, 1fr),
    [{lbl}],
    [{body}]
  )
]"""
    sub_m = re.match(r"^([a-zA-Z]\.|\([a-zA-Z0-9]+\)|[ivxLCDM]+\.)\s+(.*)$", joined_text)
    if sub_m and not re.match(r"^[A-Z]\.\s+[A-Z]\.", joined_text):
        lbl = format_inline_markdown(sub_m.group(1))
        body = format_inline_markdown(sub_m.group(2))
        return f"""#block(inset: (left: 3.8em), spacing: 0.38em)[
  #set par(hanging-indent: 1.5em)
  {lbl} {body}
]"""
    return format_inline_markdown(joined_text)


def format_inline_markdown(text: str) -> str:
    """Convert Markdown inline formatting (bold, italic, code) to Typst syntax."""
    text = clean_latex_to_unicode(text)
    # Strip dead markdown image placeholders like ![img-0.jpeg](img-0.jpeg)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text).strip()

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
    text = text.replace("`", "\\`")
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

        # Normalize and balance margins for digital typesetting to maximize usable reading space
        side_margin = round(min(42.0, max(28.0, (l + r) / 2.0)), 1)
        top_margin = round(min(45.0, max(28.0, t)), 1)
        bottom_margin = round(min(48.0, max(32.0, b)), 1)

        cal = {
            "width": w,
            "height": h,
            "left": side_margin,
            "right": side_margin,
            "top": top_margin,
            "bottom": bottom_margin,
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

    # General multi-column table (open whitespace grid without hallucinated borders)
    content_rows = data[1:] if len(data) > 1 else data
    col_max_lens = [max((len(r[c_idx]) for r in content_rows), default=0) for c_idx in range(num_cols)]
    total_len = sum(col_max_lens)

    col_widths = []
    col_aligns = []
    for c_idx in range(num_cols):
        max_l = col_max_lens[c_idx]
        col_cells = [r[c_idx] for r in content_rows]
        is_numeric = all(c == "" or c.isdigit() or len(c) <= 2 or c in {",,", '"', "°"} for c in col_cells)

        if c_idx > 0 and (is_numeric or max_l <= 12):
            col_aligns.append("center")
        else:
            col_aligns.append("left")

        if total_len <= 55 or max_l <= 8:
            col_widths.append("auto")
        elif max_l <= 16:
            col_widths.append("1.5fr")
        else:
            col_widths.append("3fr")

    is_compact = all(w == "auto" for w in col_widths)
    col_spec = ", ".join(col_widths)
    gutter_spec = "  column-gutter: 24pt,\n  row-gutter: 0.35em,\n" if is_compact else "  row-gutter: 0.35em,\n"
    block_width = "auto" if is_compact else "100%"

    typ_cells = []
    for row in data:
        for c in row:
            tc = format_inline_markdown(c)
            typ_cells.append(f"[{tc}]")
    cells_str = ", \n    ".join(typ_cells)

    align_entries = [f"if col == {i} {{ {align} }}" for i, align in enumerate(col_aligns)]
    align_body = " else ".join(align_entries)
    align_fn = f"(col, row) => {align_body} else {{ left }}" if num_cols > 1 else "left"

    t_font_size = "7.5pt" if num_cols >= 10 else ("8.2pt" if len(data) > 28 else ("8.8pt" if len(data) > 14 else "9.2pt"))
    inset_x = "2pt" if is_compact else ("2pt" if num_cols >= 10 else "4pt")
    inset_y = "1.5pt" if len(data) > 14 else "2.0pt"

    return f"""#align(center)[#block(width: {block_width})[
#set text(size: {t_font_size})
#table(
  columns: ({col_spec}),
{gutter_spec}  stroke: none,
  inset: (x: {inset_x}, y: {inset_y}),
  fill: none,
  align: {align_fn},
  {cells_str}
)]]"""


def is_title_page_candidate(
    blocks: List[Dict[str, Any]],
    page_num: int,
    meta_title: str = "",
    meta_author: str = "",
) -> Optional[Dict[str, str]]:
    """Detect if a front-matter page is a half-title or full title page."""
    if page_num > 4:
        return None
    full_text = " ".join(b.get("text", "") for b in blocks)
    lower = full_text.lower()
    if len(full_text) > 400:
        return None
    if any(k in lower for k in ("contents", "table of contents", "isbn", "copyright", "all rights reserved", "also available at")):
        return None

    clean_meta_title = re.sub(r"\(.*?\)", "", meta_title).strip().lower()
    has_title = bool(
        (clean_meta_title and len(clean_meta_title) >= 4 and clean_meta_title in lower)
        or (clean_meta_title and any(word in lower for word in clean_meta_title.split() if len(word) >= 4))
    )
    if not has_title:
        return None

    clean_meta_author = meta_author.strip().lower()
    has_author = bool(clean_meta_author and len(clean_meta_author) >= 3 and clean_meta_author in lower)
    has_publisher = any(k in lower for k in ("publisher", "publishers", "press", "verlag", "edition", "published by", "limited", "ltd"))

    subtitle = None
    if "part one" in lower:
        subtitle = "Part One"
    elif "part two" in lower:
        subtitle = "Part Two"
    elif ":" in meta_title:
        subtitle = meta_title.split(":", 1)[1].strip()

    book_title = meta_title.split("(")[0].strip() if meta_title else ""
    author_name = meta_author.strip() if meta_author else ""

    if has_author or has_publisher:
        pub_lines = [
            b.get("text", "").strip() for b in blocks
            if any(k in b.get("text", "").lower() for k in ("publisher", "publishers", "press", "verlag", "edition", "published by", "limited", "ltd"))
        ]
        pub_text = "\n".join(pub_lines) if pub_lines else ""
        return {
            "type": "full_title",
            "title": book_title,
            "subtitle": subtitle or "",
            "author": author_name if (has_author or author_name) else None,
            "publisher": pub_text
        }
    elif has_title and len(blocks) <= 5:
        return {
            "type": "half_title",
            "title": book_title,
            "subtitle": subtitle or ""
        }
    return None


def is_imprint_page_candidate(blocks: List[Dict[str, Any]], page_num: int) -> Optional[Dict[str, Any]]:
    """Detect if a front-matter page is an imprint/copyright page and extract structured sections."""
    if page_num > 5:
        return None
    full_text = " ".join(b.get("text", "") for b in blocks)
    lower = full_text.lower()
    if len(full_text) > 1600:
        return None
    if any(k in lower for k in ("contents", "table of contents", "inhalt")):
        return None

    has_imprint_marker = (
        ("isbn" in lower)
        or ("all rights reserved" in lower)
        or ("copyright" in lower or "©" in lower)
        or ("first edition" in lower or "first published" in lower)
        or ("printed in" in lower and "press" in lower)
    )
    if not has_imprint_marker:
        return None

    editions: List[str] = []
    copyright_lines: List[str] = []
    isbn_txt = ""
    available_at = ""
    pub_name = ""
    addresses: List[str] = []
    sales_restriction = ""
    colophon: List[str] = []
    in_colophon = False

    for b in blocks:
        raw = b.get("text", "").strip()
        if not raw:
            continue
        l_text = raw.lower()

        if "for sale in" in l_text or "territory" in l_text:
            sales_restriction = raw
            continue

        if "printed in" in l_text or ("printed by" in l_text) or ("press" in l_text and "printed" in l_text):
            in_colophon = True

        if in_colophon:
            colophon.append(raw)
            continue

        if "isbn:" in l_text:
            isbn_txt = raw
            continue

        if "©" in l_text or "all rights reserved" in l_text:
            copyright_lines.append(raw)
            continue

        if "also available at" in l_text or "available at:" in l_text:
            available_at = raw
            continue

        if any(k in l_text for k in ("publisher", "publishers", "press", "verlag")) and len(raw) < 70 and not addresses:
            pub_name = raw
            continue

        if any(k in l_text for k in ("delhi 110", "mumbai 400", "bangalore 560", "kolkata 700", "calcutta 700", "varanasi 221", "chennai 600", "pune 411", "patna 800")):
            split_text = re.sub(r"(\b\d{3}\s*\d{3}\b|\b\d{6}\b)\s+", r"\1\n", raw)
            for addr in split_text.splitlines():
                if addr.strip():
                    addresses.append(addr.strip())
            continue

        if any(k in l_text for k in ("edition:", "published:", "reprint:")):
            split_eds = [p.strip() for p in re.split(r"(?<=\d{4})\s+(?=[A-Z])", raw) if p.strip()]
            editions.extend(split_eds)
            continue

        if not isbn_txt and not pub_name:
            editions.append(raw)
        else:
            colophon.append(raw)

    return {
        "editions": editions,
        "copyright": "\n".join(copyright_lines),
        "isbn": isbn_txt,
        "available_at": available_at,
        "pub_name": pub_name,
        "addresses": addresses,
        "sales_restriction": sales_restriction,
        "colophon": colophon,
    }


def is_toc_page_candidate(
    blocks: List[Dict[str, Any]],
    page_num: int,
    prev_was_toc: bool = False,
    first_body_idx: Optional[int] = None,
) -> bool:
    """Detect whether a page in front-matter is a Table of Contents page."""
    if first_body_idx and page_num >= first_body_idx:
        return False
    if page_num > 25:
        return False

    for b in blocks:
        t = b.get("text", "").strip()
        clean = re.sub(r'[*_`]', '', t).strip()
        if clean.upper() in ("CONTENTS", "TABLE OF CONTENTS", "INHALT"):
            return True
        for l in clean.splitlines():
            if l.strip().upper() in ("CONTENTS", "TABLE OF CONTENTS", "INHALT"):
                return True

    if prev_was_toc:
        txt = " ".join(b.get("text", "") for b in blocks)
        pno_count = sum(1 for line in txt.splitlines() if re.search(r'\b(?:\d+|[ivxlcdm]+)$', line.strip(), re.IGNORECASE))
        has_lessons = bool(re.search(r'LESSON\s+[A-Z\d\-]+', txt, re.IGNORECASE))
        has_subcats = bool(re.search(r'(Alphabet|Grammar|Vocabulary|Recitation):', txt))
        has_tables = "TABLES" in txt.upper() or "INDEX" in txt.upper()
        if (has_lessons or has_subcats or has_tables) and pno_count >= 2:
            return True

    return False


def format_toc_page_as_typst(blocks: List[Dict[str, Any]], is_first_toc_page: bool = False, roman_label: str = "") -> str:
    PAGE_NUM_REGEX = r'(\d+|[ivxlcdm]+)$'

    if not roman_label or not re.match(r'^[ivxlcdm]+$', roman_label.lower()):
        roman_label = ""

    def parse_toc_line(line: str) -> Optional[List[Dict[str, Any]]]:
        line = line.strip()
        if not line:
            return None
        clean_line = re.sub(r'[*_`]', '', line).strip()
        if clean_line.upper() in ('CONTENTS', 'TABLE OF CONTENTS', 'INHALT'):
            return [{'type': 'header', 'text': clean_line}]
        if re.match(r'^[ivxlcdm]+$', clean_line.lower()):
            return [{'type': 'roman_page', 'text': clean_line}]

        if line.startswith('|') and '|' in line[1:]:
            parts = [p.strip() for p in line.strip('|').split('|')]
            if all(re.match(r'^-+$', p) for p in parts if p):
                return None
            if len(parts) >= 3:
                return [{'type': 'sub', 'cat': parts[0], 'topic': parts[1], 'page': parts[2]}]
            elif len(parts) == 2:
                return [{'type': 'sub', 'cat': '', 'topic': parts[0], 'page': parts[1]}]

        m_tables = re.match(rf'^TABLES\s+(.*?)\s+{PAGE_NUM_REGEX}$', clean_line, re.IGNORECASE)
        if m_tables:
            return [
                {'type': 'major', 'title': 'TABLES', 'page': ''},
                {'type': 'sub', 'cat': '', 'topic': m_tables.group(1).strip(), 'page': m_tables.group(2).strip()}
            ]

        m_major = re.match(rf'^(LESSON\s+[A-Z\d\-]+|INTRODUCTION|PREFACE|FOREWORD|ANSWERS\s+TO\s+EXERCISES|TABLES(?:\s+[A-Za-z\s]+)?|APPENDICES?|INDEX\s+OF\s+[A-Z\s]+|GENERAL\s+INDEX|READINGS?)(?:\s+PAGE)?(?:\s+{PAGE_NUM_REGEX})?$', clean_line, re.IGNORECASE)
        if m_major:
            return [{'type': 'major', 'title': m_major.group(1).strip(), 'page': (m_major.group(2) or '').strip()}]

        m_sub = re.match(rf'^(.*?)\s+{PAGE_NUM_REGEX}$', clean_line, re.IGNORECASE)
        if m_sub:
            full_desc = m_sub.group(1).strip()
            pno = m_sub.group(2).strip()
            m_cat = re.match(r'^([A-Z][a-zA-Z\s]+[:;])\s*(.*)$', full_desc)
            if m_cat:
                cat = m_cat.group(1).replace(';', ':').strip()
                topic = m_cat.group(2).strip()
            else:
                cat = ''
                topic = full_desc
            return [{'type': 'sub', 'cat': cat, 'topic': topic, 'page': pno}]

        return [{'type': 'other', 'text': clean_line}]

    raw_lines = []
    for b in blocks:
        t = b.get('text', '').strip()
        t = re.sub(r'!\[.*?\]\(.*?\)', '', t).strip()
        for l in t.splitlines():
            l_str = l.strip()
            if not l_str:
                continue
            clean = re.sub(r'[*_`]', '', l_str).strip()
            if clean.upper() in ('CONTENTS', 'TABLE OF CONTENTS', 'INHALT'):
                continue
            if re.match(r'^[ivxlcdm]+$', clean.lower()):
                if not roman_label:
                    roman_label = clean.lower()
                continue
            raw_lines.append(l_str)

    merged = []
    idx = 0
    while idx < len(raw_lines):
        curr = raw_lines[idx]
        has_page = bool(re.search(rf'\s+{PAGE_NUM_REGEX}', curr, re.IGNORECASE)) or curr.startswith('|')
        is_major = bool(re.match(r'^(LESSON\s+[A-Z\d\-]+|INTRODUCTION|PREFACE|FOREWORD|ANSWERS\s+TO\s+EXERCISES|TABLES|APPENDICES?)$', curr, re.IGNORECASE))

        if not has_page and not is_major and idx + 1 < len(raw_lines):
            next_line = raw_lines[idx + 1]
            if re.search(rf'\s+{PAGE_NUM_REGEX}', next_line, re.IGNORECASE) and not next_line.startswith('|'):
                merged.append(f"{curr} {next_line}")
                idx += 2
                continue
        merged.append(curr)
        idx += 1

    grid_rows = []
    if is_first_toc_page:
        grid_rows.append('  [], [], [#align(right)[#text(size: 8pt, weight: "bold", tracking: 0.08em)[PAGE]]],')

    for line in merged:
        items = parse_toc_line(line)
        if not items:
            continue
        for res in items:
            if res['type'] in ('header', 'roman_page'):
                continue

            if res['type'] == 'major':
                title = format_inline_markdown(res['title'])
                pno = escape_typst(res.get('page', ''))
                pno_cell = f'[#v(0.32cm)#align(right)[#text(size: 9.5pt, weight: "bold")[{pno}]]]' if pno else '[]'
                grid_rows.append(f'  grid.cell(colspan: 2)[#v(0.32cm)#text(size: 9.5pt, weight: "bold")[{title}]],')
                grid_rows.append(f'  {pno_cell},')

            elif res['type'] == 'sub':
                cat = format_inline_markdown(res.get('cat', ''))
                cat_cell = f'[#text(size: 8.5pt, weight: "medium")[{cat}]]' if cat else '[]'
                topic = format_inline_markdown(res.get('topic', ''))
                topic_cell = f'[#text(size: 8.5pt)[{topic}]]'
                pno = escape_typst(res.get('page', ''))
                pno_cell = f'[#align(right)[#text(size: 8.5pt)[{pno}]]]'
                grid_rows.append(f'  {cat_cell}, {topic_cell}, {pno_cell},')

            elif res['type'] == 'other':
                txt = format_inline_markdown(res['text'])
                grid_rows.append(f'  grid.cell(colspan: 3)[#v(0.2cm)#text(size: 7.2pt, fill: luma(80), style: "italic")[{txt}]],')

    rows_str = '\n'.join(grid_rows)
    first_arg = "true" if is_first_toc_page else "false"
    label_arg = f'"{roman_label}"' if roman_label else '""'

    return f'''#book-toc-page(
  is_first: {first_arg},
  roman_label: {label_arg}
)[
#grid(
  columns: (82pt, 1fr, 32pt),
  column-gutter: 8pt,
  row-gutter: 0.40em,
  align: (left, left, right),
{rows_str}
)
]'''


WORD_TO_NUM = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
    "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13,
    "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19, "TWENTY": 20, "TWENTY-ONE": 21, "TWENTY-TWO": 22, "TWENTY-THREE": 23,
    "TWENTY-FOUR": 24, "TWENTY-FIVE": 25, "TWENTY-SIX": 26, "TWENTY-SEVEN": 27,
    "TWENTY-EIGHT": 28, "TWENTY-NINE": 29, "THIRTY": 30, "THIRTY-ONE": 31, "THIRTY-TWO": 32
}

KNOWN_LESSON_CATS = [
    "Alphabet:", "Aphabet:", "Grammar:", "Vocabulary:", "Recitation:", "Readings:",
    "Exercises:", "Conversation:", "Pronunciation:", "Meter:", "Sandhi:"
]


def parse_syllabus_from_lines(lines: List[str]) -> List[Tuple[str, List[str]]]:
    syllabus = []
    current_cat = None
    current_items = []
    cat_re = re.compile(r"^([A-Z][a-zA-Z\s]+:)(.*)$")

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or re.match(r"^LESSON\s+[A-Z\-]+$", line, re.IGNORECASE):
            continue
        m = cat_re.match(line)
        if m and any(m.group(1).lower().startswith(c.lower().rstrip(":")) for c in KNOWN_LESSON_CATS):
            if current_cat:
                syllabus.append((current_cat, [it for it in current_items if it]))
            cat_name = m.group(1).strip()
            if cat_name.lower() == "aphabet:":
                cat_name = "Alphabet:"
            current_cat = cat_name
            rest = m.group(2).strip()
            current_items = [rest] if rest else []
        else:
            if current_cat:
                current_items.append(line)
    if current_cat:
        syllabus.append((current_cat, [it for it in current_items if it]))
    return syllabus


def is_lesson_page_candidate(
    blocks: List[Dict],
    p_num: int,
    job_name: Optional[str] = None,
    project_root: Optional[Path] = None
) -> Optional[Dict]:
    """Detect if a page is a dedicated lesson opening page (drop numeral + syllabus)."""
    if not blocks or len(blocks) > 12:
        return None
    full_text = " ".join(b.get("text", "") for b in blocks)
    m = re.search(r"\bLESSON\s+([A-Z\-]+|\d+)\b", full_text, re.IGNORECASE)
    if not m:
        return None

    has_cats = sum(bool(re.search(r"\b" + c, full_text, re.IGNORECASE)) for c in KNOWN_LESSON_CATS)
    if has_cats < 2:
        return None

    word = m.group(1).upper()
    num = WORD_TO_NUM.get(word)
    if not num and word.isdigit():
        num = int(word)
    title = f"LESSON {word}"

    # Prefer reading raw lines from mistral.json for un-wrapped pristine line breaks
    lines = []
    if job_name:
        root = project_root if project_root else Path(".")
        for fname in [f"page-{p_num:03d}.mistral.json", f"page-{p_num}.mistral.json"]:
            m_path = root / "data" / "processing" / "quality" / job_name / fname
            if m_path.exists():
                try:
                    with open(m_path, "r", encoding="utf-8") as mf:
                        md = json.load(mf).get("markdown", "")
                    lines = md.splitlines()
                    break
                except Exception:
                    pass
    if not lines:
        for b in blocks:
            lines.extend(b.get("text", "").splitlines())

    syllabus = parse_syllabus_from_lines(lines)
    if len(syllabus) < 2:
        return None

    return {
        "number": str(num) if num else "",
        "title": title,
        "syllabus": syllabus
    }


def format_lesson_page_as_typst(cand: Dict, sh_dx: float = -168.0) -> str:
    """Format a lesson opening page as a Typst #book-lesson-page macro call."""
    num_str = escape_typst(cand.get("number", ""))
    title_str = escape_typst(cand.get("title", ""))
    syllabus = cand.get("syllabus", [])

    cat_typ_entries = []
    for cat, items in syllabus:
        cat_esc = escape_typst(cat)
        item_typ_list = []
        for it in items:
            it_clean = it.strip()
            if it_clean:
                it_clean = re.sub(r"^#\s*(\d+\.\d+)", r"\1", it_clean)
                it_fmt = format_inline_markdown(it_clean)
                item_typ_list.append(f'[{it_fmt}]')
        items_arr = f'({", ".join(item_typ_list)}{"," if len(item_typ_list) == 1 else ""})' if item_typ_list else '()'
        cat_typ_entries.append(f'    ("{cat_esc}", {items_arr})')

    cats_typ = "(\n" + ",\n".join(cat_typ_entries) + "\n  )" if cat_typ_entries else "()"
    return f'''#book-lesson-page(
  number: "{num_str}",
  title: "{title_str}",
  num_dx: {sh_dx}pt,
  syllabus: {cats_typ}
)'''


def int_to_roman(n: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]
    res = ""
    for v, s in zip(val, syb):
        while n >= v:
            res += s
            n -= v
    return res


def roman_to_int(s: str) -> int:
    s = s.lower().strip()
    roman_map = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    res = 0
    prev = 0
    for ch in reversed(s):
        val = roman_map.get(ch, 0)
        if val < prev:
            res -= val
        else:
            res += val
            prev = val
    return res


RH_PATTERN = re.compile(
    r"^(?:LESSON\s+[A-Z0-9]+|CHAPTER\s+[A-Z0-9]+|INTRODUCTION|CONTENTS|INDEX(?:\s+OF\s+[A-Z\s]+)?|APPENDIX(?:\s+[A-Z0-9]+)?|GLOSSARY|ANSWERS\s+TO\s+EXERCISES|TABLES)$",
    re.IGNORECASE,
)


def build_book_page_labels(
    pages: List[Dict[str, Any]],
    toc_path: Optional[Path] = None,
) -> Tuple[int, List[str]]:
    """Build accurate printed page labels supporting unnumbered front matter, roman numerals, and arabic body pages."""
    total = len(pages)
    first_body_idx = None

    # 1. Try from toc_path: search top-level entries for the first main body lesson/chapter
    if toc_path and Path(toc_path).is_file():
        try:
            text = Path(toc_path).read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith(" ") or line.startswith("\t") or line.startswith("#"):
                    continue
                m = re.match(r"^\s*(?:Lesson|Chapter|Kapitel|Teil|Part)\s*(?:1|One|I|Erstes|19)\b.*?\|\s*(\d+)", line, re.IGNORECASE)
                if m:
                    first_body_idx = int(m.group(1))
                    break
            if not first_body_idx:
                for line in text.splitlines():
                    if line.startswith(" ") or line.startswith("\t") or line.startswith("#"):
                        continue
                    m = re.match(r"^\s*(?:Lesson|Chapter|Kapitel)\s*\d+.*?\|\s*(\d+)", line, re.IGNORECASE)
                    if m:
                        first_body_idx = int(m.group(1))
                        break
        except Exception:
            pass

    # 2. Heuristic fallback from page blocks
    if not first_body_idx:
        for idx, page in enumerate(pages[:35]):
            p_blocks = page.get("blocks", [])
            txt = " ".join(b.get("text", "") for b in p_blocks[:3]).strip()
            if re.match(r"^(?:LESSON\s+(?:ONE|1|NINETEEN|19)|CHAPTER\s+(?:ONE|1)|KAPITEL\s+1)\b", txt, re.IGNORECASE):
                first_body_idx = idx + 1
                break

    if not first_body_idx:
        first_body_idx = 1

    labels = [""] * total

    # Arabic labels for body pages starting at first_body_idx
    for idx in range(first_body_idx - 1, total):
        labels[idx] = str(idx - (first_body_idx - 1) + 1)

    # Front matter: scan for explicit roman numerals in blocks
    for idx in range(first_body_idx - 1):
        page = pages[idx]
        blocks = page.get("blocks", [])
        found_roman = None
        for b in blocks[:4]:
            t = b.get("text", "").strip().lower()
            if re.match(r"^[ivxlcdm]+$", t) and len(t) <= 6:
                found_roman = t
                break
        if found_roman:
            labels[idx] = found_roman

    # Backward interpolate front matter
    for idx in range(first_body_idx - 2, -1, -1):
        if not labels[idx] and labels[idx + 1]:
            nxt_val = roman_to_int(labels[idx + 1])
            if nxt_val > 1:
                labels[idx] = int_to_roman(nxt_val - 1)

    # Forward interpolate front matter
    for idx in range(1, first_body_idx - 1):
        if not labels[idx] and labels[idx - 1]:
            prv_val = roman_to_int(labels[idx - 1])
            if prv_val > 0:
                labels[idx] = int_to_roman(prv_val + 1)

    # Blank out very first unnumbered pages (cover, half-title, title, imprint)
    for idx in range(min(3, first_body_idx - 1)):
        labels[idx] = ""

    return first_body_idx, labels


def strip_running_headers(
    blocks: List[Dict[str, Any]],
    pr_label: str,
    ch_title: str,
    is_chapter_page: bool,
) -> List[Dict[str, Any]]:
    """Strip scanned running headers (page numbers, chapter running headers) from page blocks."""
    if not blocks:
        return blocks
    clean_ch = ch_title.strip().upper() if ch_title else ""

    if is_chapter_page:
        skip = 0
        while skip < min(len(blocks), 2):
            t = blocks[skip].get("text", "").strip()
            btype = blocks[skip].get("type", "")
            if btype in {"h1", "h2"} or (clean_ch and clean_ch in t.upper()) or (pr_label and t.lower() == pr_label.lower()):
                skip += 1
            else:
                break
        return blocks[skip:]

    if len(blocks) >= 2:
        t0 = blocks[0].get("text", "").strip()
        t1 = blocks[1].get("text", "").strip()
        t0_u = t0.upper()
        t1_u = t1.upper()

        is_p0_label = (pr_label and t0.lower() == pr_label.lower()) or bool(re.match(r"^(?:[ivxlcdm]+|\d+)$", t0, re.IGNORECASE))
        is_p1_label = (pr_label and t1.lower() == pr_label.lower()) or bool(re.match(r"^(?:[ivxlcdm]+|\d+)$", t1, re.IGNORECASE))

        is_p0_hdr = bool(RH_PATTERN.match(t0)) or (clean_ch and clean_ch in t0_u and len(t0) < 65)
        is_p1_hdr = bool(RH_PATTERN.match(t1)) or (clean_ch and clean_ch in t1_u and len(t1) < 65)

        if (is_p0_label and is_p1_hdr) or (is_p0_hdr and is_p1_label):
            return blocks[2:]

    if len(blocks) >= 1:
        t0 = blocks[0].get("text", "").strip()
        t0_u = t0.upper()
        is_p0_label = pr_label and (t0.lower() == pr_label.lower()) and len(t0) <= 6
        is_p0_hdr = bool(RH_PATTERN.match(t0)) or (clean_ch and clean_ch in t0_u and len(t0) < 65)
        if is_p0_hdr or is_p0_label:
            return blocks[1:]

    return blocks


def ensure_extracted_images(
    job_name: Optional[str],
    data_dir: Path,
    project_root: Optional[Path] = None,
) -> Dict[Tuple[int, str], Dict[str, Any]]:
    """
    Ensure all images referenced in mistral.json quality files are cropped
    from preprocessed scans and cached in data/output/{job_name}/images/.
    Returns mapping (page_num, img_id) -> metadata dict with path, x, y, w, h, page_w, page_h.
    """
    img_map: Dict[Tuple[int, str], Dict[str, Any]] = {}
    if not job_name:
        return img_map

    try:
        from PIL import Image
    except ImportError:
        log("PIL (Pillow) not installed; image extraction unavailable.")
        return img_map

    quality_dir = data_dir / "processing" / "quality" / job_name
    preproc_dir = data_dir / "processing" / "preprocessed" / job_name
    out_dir = data_dir / "output" / job_name / "images"

    if not quality_dir.is_dir():
        for alt in (
            (project_root / "data" / "processing" / "quality" / job_name) if project_root else None,
            Path("data/processing/quality") / job_name,
        ):
            if alt and alt.is_dir():
                quality_dir = alt
                break

    if not quality_dir.is_dir():
        return img_map

    out_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(quality_dir.glob("page-*.mistral.json"))
    for jf in json_files:
        m_p = re.search(r"page-(\d+)\.mistral\.json", jf.name)
        if not m_p:
            continue
        p_num = int(m_p.group(1))

        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        pages = data.get("pages", [])
        for page in pages:
            dims = page.get("dimensions", {})
            pw = dims.get("width", 2480)
            ph = dims.get("height", 3509)
            images = page.get("images", [])
            if not images:
                continue

            scan_path = None
            for ext in (".png", ".jpg", ".jpeg"):
                cand = preproc_dir / f"page-{p_num:03d}{ext}"
                if cand.is_file():
                    scan_path = cand
                    break

            for img in images:
                img_id = img.get("id")
                if not img_id:
                    continue
                x1 = int(img.get("top_left_x", 0))
                y1 = int(img.get("top_left_y", 0))
                x2 = int(img.get("bottom_right_x", 0))
                y2 = int(img.get("bottom_right_y", 0))
                w = max(1, x2 - x1)
                h = max(1, y2 - y1)

                target_file = out_dir / f"page-{p_num:03d}_{img_id}"

                if not target_file.is_file() and scan_path and scan_path.is_file():
                    try:
                        with Image.open(scan_path) as im:
                            crop_box = (
                                max(0, x1),
                                max(0, y1),
                                min(im.width, x2),
                                min(im.height, y2),
                            )
                            cropped = im.crop(crop_box)
                            cropped.save(target_file, quality=95)
                    except Exception as e:
                        log(f"Error cropping {img_id} from {scan_path}: {e}")

                if target_file.is_file():
                    img_map[(p_num, img_id)] = {
                        "path": str(target_file.resolve()),
                        "x": x1,
                        "y": y1,
                        "w": w,
                        "h": h,
                        "page_w": pw,
                        "page_h": ph,
                    }

    if img_map:
        log(f"Loaded {len(img_map)} extracted images for job '{job_name}' in {out_dir}")
    return img_map


def detect_glyph_pairs(
    blocks: List[Dict[str, Any]],
    start_idx: int,
    p_num: int,
    img_map: Dict[Tuple[int, str], Dict[str, Any]],
) -> Tuple[Optional[str], List[Tuple[str, str]], int]:
    """Detect consecutive sequences of labeled calligraphy glyphs."""
    idx = start_idx
    pairs_a: List[Tuple[str, str]] = []
    while idx < len(blocks) - 1:
        b1 = blocks[idx]
        b2 = blocks[idx + 1]
        t1 = b1.get("text", "").strip()
        t2 = b2.get("text", "").strip()
        m2 = re.match(r"^!\[(.*?)\]\((img-.*?\.(?:jpe?g|png))\)$", t2)
        if len(t1) <= 6 and not t1.startswith("![") and m2:
            iid = m2.group(2)
            if (p_num, iid) in img_map:
                pairs_a.append((t1, iid))
                idx += 2
                continue
        break

    if len(pairs_a) >= 2:
        return "label_beside", pairs_a, idx - start_idx

    idx = start_idx
    pairs_b: List[Tuple[str, str]] = []
    while idx < len(blocks) - 1:
        b1 = blocks[idx]
        b2 = blocks[idx + 1]
        t1 = b1.get("text", "").strip()
        t2 = b2.get("text", "").strip()
        m1 = re.match(r"^!\[(.*?)\]\((img-.*?\.(?:jpe?g|png))\)$", t1)
        if m1 and len(t2) <= 6 and not t2.startswith("!["):
            iid = m1.group(2)
            if (p_num, iid) in img_map:
                pairs_b.append((iid, t2))
                idx += 2
                continue
        break

    if len(pairs_b) >= 2:
        return "label_below", pairs_b, idx - start_idx

    return None, [], 0


def format_glyph_grid_beside(
    pairs: List[Tuple[str, str]],
    p_num: int,
    img_map: Dict[Tuple[int, str], Dict[str, Any]],
) -> str:
    """Format 2-column calligraphy glyph table with roman labels beside letters."""
    rows = []
    idx = 0
    while idx < len(pairs):
        left_label, left_id = pairs[idx]
        left_meta = img_map.get((p_num, left_id))
        left_path = left_meta["path"] if left_meta else None

        right_pair = None
        if idx + 1 < len(pairs):
            next_label, next_id = pairs[idx + 1]
            next_meta = img_map.get((p_num, next_id))
            if next_meta and next_meta["x"] >= next_meta["page_w"] * 0.52:
                right_pair = (next_label, next_meta["path"])
                idx += 1

        rows.append(((left_label, left_path), right_pair))
        idx += 1

    cells = []
    for left, right in rows:
        l_lbl, l_path = left
        l_txt = format_inline_markdown(l_lbl)
        l_img = f'image("{l_path}", height: 44pt)' if l_path else "[]"
        row_str = f"  [#strong[{l_txt}]], {l_img}, []"
        if right:
            r_lbl, r_path = right
            r_txt = format_inline_markdown(r_lbl)
            r_img = f'image("{r_path}", height: 44pt)' if r_path else "[]"
            row_str += f", [#strong[{r_txt}]], {r_img},"
        else:
            row_str += ", [], [],"
        cells.append(row_str)

    body = "\n".join(cells)
    return f"""#align(center)[
  #grid(
    columns: (24pt, 90pt, 36pt, 24pt, 90pt),
    align: (horizon + right, horizon + center, horizon, horizon + right, horizon + center),
    row-gutter: 12pt,
{body}
  )
]"""


def format_glyph_grid_below(
    pairs: List[Tuple[str, str]],
    p_num: int,
    img_map: Dict[Tuple[int, str], Dict[str, Any]],
) -> str:
    """Format horizontal calligraphy glyph row with roman labels below each letter."""
    n = len(pairs)
    col_width = "65pt"
    cols = ", ".join([col_width] * n)
    aligns = ", ".join(["horizon + center"] * n)

    img_cells = []
    lbl_cells = []
    for img_id, label in pairs:
        meta = img_map.get((p_num, img_id))
        path = meta["path"] if meta else None
        if path:
            img_cells.append(f'image("{path}", height: 42pt)')
        else:
            img_cells.append("[]")
        lbl_txt = format_inline_markdown(label)
        lbl_cells.append(f"[#strong[{lbl_txt}]]")

    img_row = "    " + ", ".join(img_cells) + ","
    lbl_row = "    " + ", ".join(lbl_cells) + ","

    return f"""#align(center)[
  #grid(
    columns: ({cols}),
    align: ({aligns}),
    row-gutter: 6pt,
    column-gutter: 14pt,
{img_row}
{lbl_row}
  )
]"""


def format_standalone_image(
    img_id: str,
    p_num: int,
    img_map: Dict[Tuple[int, str], Dict[str, Any]],
) -> str:
    """Format standalone figure or diagram centered with proportional width."""
    meta = img_map.get((p_num, img_id))
    if not meta:
        return ""
    path = meta["path"]
    w = meta["w"]
    pw = meta["page_w"]
    w_ratio = w / pw
    if w_ratio > 0.5:
        return f'#align(center)[#image("{path}", width: 85%)]'
    elif w_ratio > 0.3:
        return f'#align(center)[#image("{path}", width: 55%)]'
    else:
        return f'#align(center)[#image("{path}", height: 50pt)]'


def build_typst_document(
    book_data: Dict[str, Any],
    template_path: str = "/templates/book.typ",
    paper: Optional[str] = None,
    preserve_pages: bool = True,
    layout_calibration: Optional[Dict[str, float]] = None,
    typeset_mode: Optional[str] = None,
    toc_path: Optional[Path] = None,
    job_name: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> str:
    """Generate complete Typst source code from book dictionary."""
    meta = book_data.get("metadata", {})
    job_id = job_name or meta.get("job", "")
    data_dir = project_root / "data" if project_root else Path("data")
    img_map = ensure_extracted_images(job_id, data_dir=data_dir, project_root=project_root)
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

    # Check layout profile from metadata or book_data
    layout_profile = meta.get("layout_profile") or book_data.get("layout_profile")
    macro_layout = layout_profile.get("macro_layout", "single_column") if layout_profile else "single_column"
    is_sideheads = (macro_layout == "marginal_sideheads") or (heuristics.get("layout_mode") == "sidehead")

    sh_dx = -160.0
    sh_width = 115.0
    if layout_profile and layout_profile.get("marginal_zone"):
        mz = layout_profile["marginal_zone"]
        cm = layout_profile.get("calibrated_margins", {})
        m_left = cm.get("left_pt", 210.0)
        sh_dx = -round(m_left - mz.get("x0", 45.0), 1)
        sh_width = round(mz.get("width_pt", 115.0), 1)

    # Determine page dimensions
    pages = book_data.get("pages", [])
    dim_args: List[str] = []

    # Robust detection of front-matter vs main body boundary
    last_fm_page = 0
    in_toc = False
    for i, p in enumerate(pages[:30], start=1):
        txt = " ".join(b.get("text", "") for b in p.get("blocks", [])).strip()
        lower = txt.lower()
        has_contents = any(b.get("text", "").strip().upper() in ("CONTENTS", "TABLE OF CONTENTS", "INHALT") for b in p.get("blocks", [])) or "table of contents" in lower
        is_imprint = any(k in lower for k in ("isbn", "all rights reserved", "first edition", "first published", "printed in"))
        is_title = is_title_page_candidate(p.get("blocks", []), i, title, author) is not None
        
        if has_contents:
            in_toc = True
            last_fm_page = i
        elif in_toc:
            if "contents" in lower or sum(1 for line in txt.splitlines() if any(line.strip().endswith(str(n)) for n in range(1, 400))) >= 3:
                last_fm_page = i
            else:
                in_toc = False
        elif is_title or is_imprint or (i <= 3 and len(txt) < 300):
            last_fm_page = i

    first_body_idx = last_fm_page + 1 if last_fm_page > 0 else 1
    if layout_profile and layout_profile.get("pages"):
        sh_pages = [int(p) for p, v in layout_profile["pages"].items() if v.get("has_sideheads")]
        valid_sh = [p for p in sh_pages if p >= 4]
        if valid_sh and first_body_idx < min(valid_sh):
            first_body_idx = min(valid_sh)

    if is_sideheads and layout_profile and "calibrated_margins" in layout_profile:
        cm = layout_profile["calibrated_margins"]
        dim_args.append(f'  width: {layout_profile["page_dimensions"]["width_pt"]}pt,')
        dim_args.append(f'  height: {layout_profile["page_dimensions"]["height_pt"]}pt,')
        if first_body_idx > 1:
            dim_args.append(f'  margin: (x: 54pt, top: 60pt, bottom: 60pt),')
        else:
            dim_args.append(f'  margin: (left: {cm["left_pt"]}pt, right: {cm["right_pt"]}pt, top: {cm["top_pt"]}pt, bottom: {cm["bottom_pt"]}pt),')
    elif layout_calibration:
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

    fb_idx, page_labels = build_book_page_labels(pages, toc_path=toc_path)
    if fb_idx > 1:
        first_body_idx = fb_idx
    labels_typst = ", ".join(f'"{l}"' for l in page_labels)

    lines = [
        f'#import "{template_path}": book, orig-page, fit-page, page-footnotes, sidehead, book-half-title, book-title-page, book-imprint-page, book-toc-page, book-lesson-page',
        f'#show: book.with(',
        f'  title: "{escape_typst(title)}",',
        f'  author: "{escape_typst(author)}",',
        f'  date: "{date_val}",',
        *dim_args,
        f'  preserve_pages: {"true" if preserve_pages else "false"},',
        f'  lang: "{typst_lang}",',
        f'  page_labels: ({labels_typst}),',
        f'  front_matter_pages: {max(0, first_body_idx - 1)}',
        f')',
        '',
        '// Auto-scale layout macro ensuring each original page stays strictly within 1 page without row clumping',
        '#let page_content = fit-page',
        ''
    ]

    # Build TOC chapter mapping to recognize real chapter titles vs running headers
    toc_map: Dict[str, str] = {}
    if toc_path and Path(toc_path).is_file():
        try:
            with open(toc_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(" ") or line.startswith("\t") or line.startswith("#"):
                        continue
                    line = line.strip()
                    if "|" in line:
                        parts = line.split("|")
                        t_entry = parts[0].strip()
                        p_entry = parts[1].strip()
                        if p_entry.isdigit():
                            toc_map[p_entry] = t_entry
        except Exception:
            pass

    if not toc_map:
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

    in_toc = False
    current_ch_title = ""
    for idx, page in enumerate(pages):
        p_num = page.get("page_num", idx + 1)
        pr_label = page_labels[idx] if idx < len(page_labels) else str(page.get("printed_page", "")).strip()
        raw_blocks = page.get("blocks", [])
        
        # Filter hallucinated prompts on blank pages
        blocks = [
            b for b in raw_blocks
            if "ground truth image displays" not in b.get("text", "").lower()
            and "underscore & line rules" not in b.get("text", "").lower()
            and b.get("text", "").strip()
        ]

        # Margin switch: from symmetrical front-matter to asymmetrical sideheads at first_body_idx
        if is_sideheads and (idx + 1) == first_body_idx and first_body_idx > 1:
            cm = layout_profile.get("calibrated_margins", {}) if layout_profile else {}
            m_l = cm.get("left_pt", 224.8)
            m_r = cm.get("right_pt", 104.8)
            m_t = cm.get("top_pt", 80.0)
            m_b = cm.get("bottom_pt", 80.0)
            lines.append(f'#set page(margin: (left: {m_l}pt, right: {m_r}pt, top: {m_t}pt, bottom: {m_b}pt))')
            lines.append('')

        # Check if page is half-title or full title page
        t_cand = is_title_page_candidate(blocks, p_num, title, author)
        if t_cand:
            page_elements = []
            if t_cand["type"] == "half_title":
                sub_arg = f', subtitle: "{escape_typst(t_cand["subtitle"])}"' if t_cand.get("subtitle") else ""
                page_elements.append(f'#book-half-title(title: "{escape_typst(t_cand["title"])}"{sub_arg})')
            elif t_cand["type"] == "full_title":
                sub_arg = f', subtitle: "{escape_typst(t_cand["subtitle"])}"' if t_cand.get("subtitle") else ""
                auth_arg = f', author: "{escape_typst(t_cand["author"])}"' if t_cand.get("author") else ""
                pub_val = t_cand.get("publisher", "")
                if pub_val:
                    pub_lines = [escape_typst(pl.strip()) for pl in pub_val.splitlines() if pl.strip()]
                    pub_typ = " \\ ".join(pub_lines)
                    pub_arg = f', publisher: [{pub_typ}]'
                else:
                    pub_arg = ""
                page_elements.append(f'#book-title-page(title: "{escape_typst(t_cand["title"])}"{sub_arg}{auth_arg}{pub_arg})')

            content_body = "\n\n".join(page_elements)
            lines.append(f"// --- Original Page {p_num} (printed: {pr_label}) ---")
            if preserve_pages:
                lines.append(f"#fit-page[\n{content_body}\n]")
                if idx < len(pages) - 1:
                    lines.append("#pagebreak()")
            else:
                cite_label = pr_label if pr_label else str(p_num)
                lines.append(f"#orig-page(\"{cite_label}\")")
                lines.append(content_body)
            lines.append("")
            continue

        # Check if page is an imprint/copyright page
        imp_cand = is_imprint_page_candidate(blocks, p_num)
        if imp_cand:
            eds_list = [f'"{escape_typst(e)}"' for e in imp_cand["editions"]]
            eds_arg = f'({", ".join(eds_list)}{"," if len(eds_list) == 1 else ""})' if eds_list else '()'
            c_val = escape_typst(imp_cand["copyright"]).replace("\n", " \\ ")
            c_arg = f'[{c_val}]' if c_val else '""'
            isbn_arg = f'"{escape_typst(imp_cand["isbn"])}"' if imp_cand["isbn"] else '""'
            pub_arg = f'"{escape_typst(imp_cand["pub_name"])}"' if imp_cand["pub_name"] else '""'
            av_arg = f'"{escape_typst(imp_cand["available_at"])}"' if imp_cand["available_at"] else "none"
            addr_list = [f'"{escape_typst(a)}"' for a in imp_cand["addresses"]]
            addr_arg = f'({", ".join(addr_list)}{"," if len(addr_list) == 1 else ""})' if addr_list else '()'
            sr_arg = f'"{escape_typst(imp_cand["sales_restriction"])}"' if imp_cand["sales_restriction"] else "none"
            col_list = [f'"{escape_typst(c)}"' for c in imp_cand["colophon"]]
            col_arg = f'({", ".join(col_list)}{"," if len(col_list) == 1 else ""})' if col_list else '()'

            page_elements = [f'''#book-imprint-page(
  editions: {eds_arg},
  copyright: {c_arg},
  isbn: {isbn_arg},
  available_at: {av_arg},
  publisher_name: {pub_arg},
  addresses: {addr_arg},
  sales_restriction: {sr_arg},
  colophon: {col_arg}
)''']
            content_body = "\n\n".join(page_elements)
            lines.append(f"// --- Original Page {p_num} (printed: {pr_label}) ---")
            if preserve_pages:
                lines.append(f"#fit-page[\n{content_body}\n]")
                if idx < len(pages) - 1:
                    lines.append("#pagebreak()")
            else:
                cite_label = pr_label if pr_label else str(p_num)
                lines.append(f"#orig-page(\"{cite_label}\")")
                lines.append(content_body)
            lines.append("")
            continue

        # Check if page is a Table of Contents page
        if is_toc_page_candidate(blocks, p_num, prev_was_toc=in_toc, first_body_idx=first_body_idx):
            is_first_toc = not in_toc
            in_toc = True
            content_body = format_toc_page_as_typst(blocks, is_first_toc_page=is_first_toc, roman_label=pr_label)
            lines.append(f"// --- Original Page {p_num} (printed: {pr_label}) ---")
            if preserve_pages:
                lines.append(f"#fit-page[\n{content_body}\n]")
                if idx < len(pages) - 1:
                    lines.append("#pagebreak()")
            else:
                cite_label = pr_label if pr_label else str(p_num)
                lines.append(f"#orig-page(\"{cite_label}\")")
                lines.append(content_body)
            lines.append("")
            continue
        else:
            in_toc = False

        # Check if page is a Lesson opening page (drop numeral + structured syllabus)
        job_id = job_name or meta.get("job", "")
        lesson_cand = is_lesson_page_candidate(blocks, p_num, job_name=job_id, project_root=project_root)
        if lesson_cand:
            current_ch_title = lesson_cand["title"]
            content_body = format_lesson_page_as_typst(lesson_cand, sh_dx=sh_dx)
            lines.append(f"// --- Original Page {p_num} (printed: {pr_label}) ---")
            if preserve_pages:
                lines.append(f"#fit-page[\n{content_body}\n]")
                if idx < len(pages) - 1:
                    lines.append("#pagebreak()")
            else:
                cite_label = pr_label if pr_label else str(p_num)
                lines.append(f"#orig-page(\"{cite_label}\")")
                lines.append(content_body)
            lines.append("")
            continue

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
        is_chapter_page = False
        ch_title_cand = ""
        p_str = str(idx + 1)
        if p_str in toc_map:
            is_chapter_page = True
            ch_title_cand = toc_map[p_str]
        elif blocks:
            b0_text = blocks[0].get("text", "").strip()
            b0_type = blocks[0].get("type", "")
            if b0_type in {"h1", "h2"} and RH_PATTERN.match(b0_text):
                is_chapter_page = True
                ch_title_cand = b0_text

        if is_chapter_page:
            clean_display_title = ""
            if blocks:
                b0_t = blocks[0].get("text", "").strip()
                if RH_PATTERN.match(b0_t):
                    clean_display_title = b0_t.upper()
            if not clean_display_title:
                clean_display_title = re.sub(r":.*$", "", ch_title_cand).strip().upper()
            current_ch_title = clean_display_title
            page_elements.append(f"= {format_inline_markdown(clean_display_title)}")

        blocks_to_process = strip_running_headers(blocks, pr_label, current_ch_title, is_chapter_page)

        b_idx = 0
        while b_idx < len(blocks_to_process):
            # Check for Calligraphy Glyphs Grid (label_beside or label_below)
            glyph_style, glyph_pairs, consumed = detect_glyph_pairs(blocks_to_process, b_idx, p_num, img_map)
            if consumed > 0:
                flush_table()
                if glyph_style == "label_beside":
                    page_elements.append(format_glyph_grid_beside(glyph_pairs, p_num, img_map))
                else:
                    page_elements.append(format_glyph_grid_below(glyph_pairs, p_num, img_map))
                b_idx += consumed
                continue

            block = blocks_to_process[b_idx]
            b_idx += 1
            b_type = block.get("type", "p")
            text = block.get("text", "").strip()

            # Check for Standalone or embedded images
            m_img = re.search(r"!\[(.*?)\]\((img-.*?\.(?:jpe?g|png))\)", text)
            if m_img:
                img_id = m_img.group(2)
                if (p_num, img_id) in img_map:
                    flush_table()
                    before_t = text[:m_img.start()].strip()
                    after_t = text[m_img.end():].strip()
                    if before_t:
                        page_elements.append(format_block_as_typst(before_t))
                    img_elem = format_standalone_image(img_id, p_num, img_map)
                    if img_elem:
                        page_elements.append(img_elem)
                    if after_t:
                        page_elements.append(format_block_as_typst(after_t))
                    continue
                else:
                    text = re.sub(r"!\[.*?\]\(.*?\)", "", text).strip()
                    if not text:
                        continue
            else:
                text = re.sub(r"!\[.*?\]\(.*?\)", "", text).strip()
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

            if b_type == "sidehead":
                esc_txt = format_inline_markdown(text).replace("\n", " \\ ")
                page_elements.append(f"#sidehead(dx: {sh_dx}pt, width: {sh_width}pt)[{esc_txt}]")
            elif b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                level = int(b_type[1])
                # Demote internal h1 to h2 so it does not collide with book chapter heading
                if level == 1:
                    level = 2
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
        if not has_table and is_two_col_profile and not is_front_matter_page and len(page_elements) >= 3:
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

    # 2b. Discover layout profile if not embedded in book_data
    if "layout_profile" not in book_data.get("metadata", {}):
        for lp_cand in (
            input_file.parent / "layout.profile.json",
            output_file.parent / "layout.profile.json",
            data_root / "output" / job_name / "layout.profile.json",
            data_root / "input" / job_name / "layout.profile.json",
        ):
            if lp_cand.is_file():
                try:
                    with open(lp_cand, "r", encoding="utf-8") as f:
                        book_data.setdefault("metadata", {})["layout_profile"] = json.load(f)
                    log(f"Discovered layout profile: {lp_cand}")
                    break
                except Exception:
                    pass

    # 2c. Discover TOC file for bookmarks and printed page structure
    cand_tocs = [
        output_file.parent / f"{job_name}.toc.txt",
        output_file.parent / "toc.txt",
        input_file.parent / f"{job_name}.toc.txt",
        input_file.parent / "toc.txt",
        project_root / "data" / "input" / job_name / f"{job_name}.toc.txt",
        project_root / "data" / "input" / job_name / "toc.txt",
    ]
    toc_file = next((p for p in cand_tocs if p.is_file()), None)
    if toc_file:
        log(f"Discovered TOC structure: {toc_file}")

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
        toc_path=toc_file,
        job_name=job_name,
        project_root=project_root,
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
