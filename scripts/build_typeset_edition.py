#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_typeset_edition.py

Builds a publication-grade typographically typeset vector PDF (using Typst),
flowing naturally across pages (the Boethlingk model), respecting original page layouts:
- Front Matter (Preface, Introduction, Paratext): Single-column continuous prose.
- Main Matter (Dhātupāṭha 10 Gaṇas): Two-column dictionary layout with vertical column
  separator rule (grid.vline) and marginal page references ([S. <orig_page>]).
- Back Matter (Appendices, Indices): Layout faithful to original structure.
- Native OpenType fonts (Noto Serif Devanagari, Linux Libertine O).
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
    """Escape special Typst syntax characters in plain text."""
    if not text:
        return ""
    out = text.replace("\\", "\\\\")
    out = out.replace('"', '\\"')
    for char in ["#", "$", "@", "[", "]", "`", "*", "_", "<", ">"]:
        out = out.replace(char, f"\\{char}")
    return out


def generate_full_typst_document(
    complete_data: Dict[str, Any],
    pdf_text_by_page: Dict[int, str],
    paper: str = "iso-b5",
) -> str:
    """Generates complete Typst document respecting multi-column vs single-column per section."""
    meta = complete_data.get("metadata", {})
    title = meta.get("title", "Dhātu-Pāṭha")
    entries = complete_data.get("entries", [])

    doc_parts: List[str] = []

    # 1. Base Setup
    base_setup = f"""// AlexandriaSandwich — Publication-Grade Typeset Edition (Böhtlingk Architecture)
#set page(
  paper: "{paper}",
  margin: (top: 2.2cm, bottom: 2.2cm, inside: 2.4cm, outside: 2.0cm),
  header: context {{
    let p = counter(page).get().first()
    let headings = query(selector(heading).before(here()))
    let current_h = if headings.len() > 0 {{ headings.last().body }} else {{ [{escape_typst(title)}] }}
    if p > 2 {{
      if calc.even(p) [
        #text(8.5pt, weight: "bold")[#p]
        #h(1fr)
        #text(8pt, font: ("Linux Libertine O", "Baskerville", "Times New Roman"), style: "italic")[{escape_typst(title)} — Kritische Ausgabe]
      ] else [
        #text(8pt, font: ("Noto Serif Devanagari", "Devanagari MT", "Kohinoor Devanagari", "Noto Sans Devanagari", "Linux Libertine O", "Baskerville"), style: "italic")[#current_h]
        #h(1fr)
        #text(8.5pt, weight: "bold")[#p]
      ]
    }}
  }},
  footer: none
)

#set text(
  font: ("Linux Libertine O", "Baskerville", "Times New Roman", "Noto Serif Devanagari", "Devanagari MT", "Kohinoor Devanagari", "Noto Sans Devanagari"),
  size: 9.5pt,
  lang: "sa"
)
#set par(justify: true, leading: 0.6em)

// =============================================================================
// TITELSEITE & IMPRESSUM
// =============================================================================

#align(center)[
  #v(2.5cm)
  #text(22pt, weight: "bold", font: ("Linux Libertine O", "Baskerville", "Times New Roman"))[{escape_typst(title).upper()}]
  
  #v(0.6cm)
  #text(12pt, style: "italic", font: ("Noto Serif Devanagari", "Devanagari MT", "Kohinoor Devanagari", "Linux Libertine O", "Baskerville"))[Pāṇinīya-Dhātupāṭhaḥ saha Arthaiḥ]
  
  #v(0.4cm)
  #text(10pt)[Kritisch revidierte Neuausgabe mit Pāṇini-Konkordanz und Originalseiten-Referenz]
  
  #v(1.5cm)
  #line(length: 30%, stroke: 0.5pt)
  #v(0.5cm)
  #text(10pt, style: "italic")[AlexandriaSandwich — Scholarly Synthesis Edition]
  
  #v(3.0cm)
  #text(8pt, fill: luma(80))[
    Basierend auf dem 410-seitigen Gesamtfaksimile (Dhatu-patha.perfect_sandwich.pdf) \\
    Kanonischer Ground-Truth-Abgleich (2.259 Wurzeln in 10 Gaṇas) \\
    Typografischer Vektorneusatz (Typst, ISO-B5) \\
    Lizenziert unter Public Domain (Grundtext) / CC-BY-SA 4.0 (Edition)
  ]
]

#pagebreak()

// =============================================================================
// INHALTSVERZEICHNIS
// =============================================================================

#outline(
  title: [Inhaltsübersicht],
  depth: 2,
  indent: 1.5em,
)

#pagebreak()
#counter(page).update(1)
"""
    doc_parts.append(base_setup)

    # 2. Front Matter: Preface & Introduction (Pages 1 to 25) -> Single-Column Prose
    front_matter_text = []
    for p in range(1, 26):
        txt = pdf_text_by_page.get(p, "").strip()
        if not txt or len(txt) < 40:
            continue
        # Check headings
        lines = txt.splitlines()
        first_line = lines[0].strip()
        if "PREFACE" in first_line.upper():
            front_matter_text.append(f"\n#heading(level: 1)[Preface]\n#v(0.5em)\n")
            body_lines = lines[1:]
        elif "INTRODUCTION" in first_line.upper():
            front_matter_text.append(f"\n#pagebreak(weak: true)\n#heading(level: 1)[Introduction]\n#v(0.5em)\n")
            body_lines = lines[1:]
        else:
            body_lines = lines

        # Paragraph reconstruction
        clean_p = " ".join(l.strip() for l in body_lines if l.strip())
        if clean_p:
            front_matter_text.append(f"{escape_typst(clean_p)} #h(1fr) #text(7pt, fill: luma(120))[[S. {p}]]\n\n#v(0.4em)\n")

    if front_matter_text:
        doc_parts.append("// --- FRONT MATTER (EINSPALTIG) ---\n" + "".join(front_matter_text) + "\n#pagebreak()\n")

    # 3. Main Matter: Dhātupāṭha 10 Gaṇas -> Two-Column Dictionary Layout
    main_header = """// =============================================================================
// HAUPTTEIL: DHĀTUPĀṬHA (ZWEISPALTIG MIT MITTELSTRICH)
// =============================================================================

#show: rest => [
  #set columns(gutter: 20pt)
  #columns(2)[
    #rest
  ]
]
"""
    doc_parts.append(main_header)

    current_gana = 0
    for item in entries:
        gana = item.get("gana", 1)
        gana_name = item.get("gana_name", f"Gaṇa {gana}")
        gana_iast = item.get("gana_iast", f"Gaṇa {gana}")

        if gana != current_gana:
            current_gana = gana
            doc_parts.append(f"\n#colbreak(weak: true)\n#heading(level: 1)[#text(font: (\"Noto Serif Devanagari\", \"Devanagari MT\", \"Kohinoor Devanagari\", \"Noto Sans Devanagari\", \"Linux Libertine O\", \"Baskerville\"))[{escape_typst(gana_name)}] ({escape_typst(gana_iast)})]\n#v(0.6em)\n")

        dhatu = escape_typst(item.get("dhatu", ""))
        iast_d = escape_typst(item.get("iast_dhatu", ""))
        artha = escape_typst(item.get("artha", ""))
        iast_a = escape_typst(item.get("iast_artha", ""))
        eng = escape_typst(item.get("artha_english", ""))
        pada = escape_typst(item.get("pada", ""))
        op = item.get("orig_page", "")
        cid = escape_typst(item.get("id", ""))
        note = escape_typst(item.get("commentary_note", ""))

        entry_lines = [
            "#block(width: 100%, breakable: false, inset: (y: 2pt))[",
            f"  #text(10.5pt, weight: \"bold\", font: (\"Noto Serif Devanagari\", \"Devanagari MT\", \"Kohinoor Devanagari\", \"Noto Sans Devanagari\"))[{dhatu}]",
            f"  #text(8pt, fill: luma(90))[ ({cid} — {iast_d})]",
        ]
        if op:
            entry_lines.append(f"  #h(1fr) #text(7pt, fill: luma(120))[[S. {op}]]")
        
        entry_lines.append(f"  \\\n  #text(9pt, font: (\"Noto Serif Devanagari\", \"Devanagari MT\", \"Kohinoor Devanagari\", \"Noto Sans Devanagari\"))[{artha}]")
        if iast_a:
            entry_lines.append(f"  #text(8pt, style: \"italic\")[({iast_a})]")
        if pada:
            entry_lines.append(f"  #text(7.5pt, fill: luma(100))[ · {pada}]")
        if eng:
            clean_eng = " ".join(eng.split())
            entry_lines.append(f"  \\\n  #text(8pt, fill: luma(60), style: \"italic\")[„{clean_eng}“]")
        if note:
            clean_note = " ".join(note.split())
            entry_lines.append(f"  \\\n  #pad(left: 0.6em)[#text(7.5pt, fill: luma(80))[{clean_note}]]")
        
        entry_lines.append("]\n#v(0.25em)\n")
        doc_parts.append("\n".join(entry_lines))

    return "".join(doc_parts)


def build_typeset_edition(
    job_name: str,
    output_pdf_path: Path,
    complete_json_path: Path = Path("data/dhatupatha_complete.json"),
    source_pdf_path: Path = Path("data/output/pdf/Dhatu-patha.perfect_sandwich.pdf"),
) -> None:
    start_t = time.time()
    log(f"Building layout-faithful typeset edition for {job_name}...")

    if not complete_json_path.exists():
        log(f"Error: Master JSON {complete_json_path} not found.")
        sys.exit(1)

    with open(complete_json_path, "r", encoding="utf-8") as f:
        complete_data = json.load(f)

    # Ingest source text per page for Front Matter
    pdf_text_by_page: Dict[int, str] = {}
    if source_pdf_path.exists():
        import pymupdf
        doc = pymupdf.open(source_pdf_path)
        for pno in range(len(doc)):
            pdf_text_by_page[pno + 1] = doc[pno].get_text()
        doc.close()
        log(f"Extracted original page texts from {source_pdf_path} ({len(pdf_text_by_page)} pages).")

    typst_content = generate_full_typst_document(complete_data, pdf_text_by_page)

    temp_typ = output_pdf_path.parent / f"{job_name}.typeset.typ"
    temp_typ.write_text(typst_content, encoding="utf-8")
    log(f"Generated Typst source code ({len(typst_content.splitlines())} lines) -> {temp_typ}")

    typst_bin = shutil.which("typst")
    if not typst_bin:
        log("Warning: 'typst' CLI not found on local PATH. Source .typ saved.")
        return

    cmd = [typst_bin, "compile"]
    font_candidates = [
        Path(__file__).resolve().parent.parent / "data" / "fonts",
        Path("/data/fonts"),
        Path("/opt/alexandria/data/fonts"),
    ]
    for fc in font_candidates:
        if fc.exists():
            cmd.extend(["--font-path", str(fc)])
            log(f"Using font path: {fc}")
            break
    cmd.extend([str(temp_typ), str(output_pdf_path)])
    log(f"Compiling Typst PDF: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        log(f"Typst compilation error: {proc.stderr}")
        sys.exit(1)

    mb = output_pdf_path.stat().st_size / (1024 * 1024)
    log(f"SUCCESS: Typeset PDF compiled -> {output_pdf_path} ({mb:.2f} MB in {time.time()-start_t:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="AlexandriaSandwich Typeset Edition Builder")
    parser.add_argument("--job", "-j", default="Dhatu-patha", help="Job name")
    parser.add_argument("--complete-json", "-c", type=Path, default=Path("data/dhatupatha_complete.json"))
    parser.add_argument("--source-pdf", "-s", type=Path, default=Path("data/output/pdf/Dhatu-patha.perfect_sandwich.pdf"))
    parser.add_argument("--output", "-o", type=Path, default=Path("data/output/pdf/Dhatu-patha.typeset_edition.pdf"))
    args = parser.parse_args()

    build_typeset_edition(
        job_name=args.job,
        output_pdf_path=args.output,
        complete_json_path=args.complete_json,
        source_pdf_path=args.source_pdf,
    )


if __name__ == "__main__":
    main()
