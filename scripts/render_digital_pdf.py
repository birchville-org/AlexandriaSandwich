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
    return text


def calibrate_layout_from_pdf(pdf_path: Path) -> Optional[Dict[str, float]]:
    """
    Extract median page dimensions and printable text bounding box from reference PDF (aligned/sandwich).
    Returns dict with width, height, left, right, top, bottom in points.
    """
    try:
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
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

    # Determine column widths heuristically based on cell contents
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
            tc = escape_typst(c)
            typ_cells.append(f"[{tc}]")
    cells_str = ", \n    ".join(typ_cells)

    align_entries = [f"if col == {i} {{ {align} }}" for i, align in enumerate(col_aligns)]
    align_fn = f"(col, row) => {' else '.join(align_entries)} else {{ left }}" if num_cols > 1 else "left"

    t_font_size = "7.5pt" if len(data) > 28 else ("8.2pt" if len(data) > 14 else "8.8pt")
    inset_y = "1.2pt" if len(data) > 14 else "1.8pt"

    return f"""#align(center)[#block(width: 100%)[
#set text(size: {t_font_size})
#table(
  columns: ({col_spec}),
  stroke: none,
  inset: (x: 3pt, y: {inset_y}),
  fill: (x, y) => if y == 0 {{ luma(240) }} else {{ none }},
  align: {align_fn},
  {cells_str}
)]]"""


def build_typst_document(
    book_data: Dict[str, Any],
    template_path: str = "/templates/book.typ",
    paper: Optional[str] = None,
    preserve_pages: bool = True,
    layout_calibration: Optional[Dict[str, float]] = None,
) -> str:
    """Generate complete Typst source code from book dictionary."""
    meta = book_data.get("metadata", {})
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
            if w_pt > 150 and h_pt > 150:
                dim_args.append(f'  width: {w_pt}pt,')
                dim_args.append(f'  height: {h_pt}pt,')
    
    if not dim_args:
        dim_args.append('  paper: "b5",')

    lines = [
        f'#import "{template_path}": book',
        f'#show: book.with(',
        f'  title: "{escape_typst(title)}",',
        f'  author: "{escape_typst(author)}",',
        f'  date: "{date_val}",',
        *dim_args,
        f'  preserve_pages: {"true" if preserve_pages else "false"},',
        f'  lang: "{typst_lang}"',
        f')',
        '',
        '// Auto-scale layout macro ensuring each original page stays strictly within 1 page without row clumping',
        '#let page_content(body) = layout(size => context {',
        '  let content_block = block(width: size.width, height: auto, breakable: false)[#body]',
        '  let m = measure(content_block)',
        '  if m.height > size.height {',
        '    let scale_factor = (size.height / m.height) * 0.97',
        '    align(top + left)[',
        '      #scale(x: scale_factor * 100%, y: scale_factor * 100%, origin: top + left)[',
        '        #block(width: size.width, height: m.height + 10pt)[#body]',
        '      ]',
        '    ]',
        '  } else {',
        '    content_block',
        '  }',
        '})',
        ''
    ]

    for idx, page in enumerate(pages):
        p_num = page.get("page_num", idx + 1)
        blocks = page.get("blocks", [])
        
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

        for block in blocks:
            b_type = block.get("type", "p")
            text = block.get("text", "").strip()
            if not text:
                continue

            # Filter hallucinated prompts on blank pages
            t_lower = text.lower()
            if "ground truth image displays" in t_lower or "underscore & line rules" in t_lower:
                continue

            if b_type == "table_row":
                has_table = True
                table_acc.append(text)
                continue
            
            flush_table()

            if b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                level = int(b_type[1])
                eqs = "=" * level
                page_elements.append(f"{eqs} {escape_typst(text)}")
            else:
                p_blocks.append(text)
                page_elements.append(escape_typst(text))

        flush_table()

        # Multi-column heuristic: detect dictionary, list, or vocabulary pages without table syntax
        is_narrow_list = False
        if not has_table and len(p_blocks) >= 16:
            lens = [len(t) for t in p_blocks]
            avg_l = sum(lens) / len(lens) if lens else 0
            max_l = max(lens) if lens else 0
            if avg_l <= 45 and max_l < 120:
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
                two_cols = f"{col1}\n\n#colbreak()\n\n{col2}"
                col_block = f"#set text(size: 8.5pt)\n#set block(spacing: 0.25em)\n#set par(leading: 0.35em)\n#columns(2, gutter: 14pt)[\n{two_cols}\n]"
                if lead_headings:
                    content_body = "\n\n".join(lead_headings) + "\n\n" + col_block
                else:
                    content_body = col_block
            else:
                content_body = "\n\n".join(page_elements)
        else:
            content_body = "\n\n".join(page_elements)

        lines.append(f"// --- Original Page {p_num} ---")
        if preserve_pages:
            lines.append(f"#page_content[\n{content_body}\n]")
            if idx < len(pages) - 1:
                lines.append("#pagebreak(weak: true)")
        else:
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
        candidate_refs.extend([
            pdf_dir / f"{job_name}.aligned.pdf",
            pdf_dir / f"{job_name}.sandwich.pdf",
            pdf_dir / f"{job_name}.pdf",
            input_file.parent / f"{job_name}.aligned.pdf",
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

    log(f"Compiling with Typst: {typst_cmd} compile --root / {temp_typ} {output_file}")
    proc = subprocess.run(
        [typst_cmd, "compile", "--root", "/", str(temp_typ), str(output_file)],
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        log(f"Typst compilation failed: {proc.stderr}")
        raise RuntimeError(f"Typst failed with code {proc.returncode}: {proc.stderr}")

    elapsed = round(time.time() - start_time, 2)
    pdf_size = output_file.stat().st_size
    log(f"Successfully generated digital vector PDF ({pdf_size} bytes in {elapsed}s): {output_file}")

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
    parser.add_argument("--no-preserve-pages", action="store_true", help="Disable 1:1 page break preservation")
    parser.add_argument("--root", help="Project root for Typst imports (default: repo root)")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    project_root = Path(args.root).resolve() if args.root else repo_root

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and (repo_root / "data").exists():
        data_dir = repo_root / "data"

    input_file = Path(args.input) if args.input else data_dir / "output" / "books" / args.job / "book.json"
    output_file = Path(args.output) if args.output else data_dir / "output" / "pdf" / f"{args.job}.digital.pdf"
    ref_pdf = Path(args.reference_pdf) if args.reference_pdf else None

    render_pdf(
        job_name=args.job,
        input_file=input_file,
        output_file=output_file,
        project_root=project_root,
        paper=args.paper,
        preserve_pages=not args.no_preserve_pages,
        reference_pdf=ref_pdf,
    )


if __name__ == "__main__":
    main()
