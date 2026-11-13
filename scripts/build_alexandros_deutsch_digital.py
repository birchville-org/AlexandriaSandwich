#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_alexandros_deutsch_digital.py

Generates the page-concordant German Digital Edition in Typst:
- Source: Alexandros_Deutsch.md (54 pages: 11..64).
- Exactly identical layout parameters as the Czech digital edition:
  * Dimensions: 439.32pt x 677.28pt
  * Margins: top 70pt, bottom 48pt, left 47.5pt, right 47.5pt
  * Header-ascent: 30pt, footer-descent: -17pt (baseline y = 620.8pt)
  * German running headers (Einführende Studie / Kapitelüberschriften)
  * Footnotes: hanging indent 8.5pt, flush text column at x = 56.0pt, marker at x = 47.5pt
  * Compact footnote spacing (spacing: 4.5pt, leading: 0.46em)
  * Hairline separator: 25% width, 0.4pt stroke, close to footnotes (#v(-7pt))
  * STIX Two Text typography with complete German, Hebrew, and Arabic diacritics
- Compiles to Alexandros_Deutsch_Neusatz.pdf with native page labels 11..64 and German TOC bookmarks.
- Saves directly to pCloud Drive and local output directory.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pymupdf


def parse_marker_num(s: str) -> int | None:
    table = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    clean = s.translate(table)
    try:
        return int(clean)
    except ValueError:
        return None


def clean_de_text(pnum: int, raw_text: str) -> list[str]:
    txt = raw_text.replace("`", "'")
    lines = [l for l in txt.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    if pnum not in [11, 34, 59, 63, 64] and lines:
        header_pat = r"^#?\s*(EINFÜHRENDE STUDIE|SA['’]ADJA GA['’]ON.*|SA['’]ADJAS BUCH.*|SA['’]ADJAS EINFLUSS.*)$"
        if re.match(header_pat, lines[0].strip(), re.I):
            lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop(-1)
    if lines and re.match(r"^\d+$", lines[-1].strip()):
        lines.pop(-1)
    while lines and not lines[-1].strip():
        lines.pop(-1)
    return lines


def md_to_typst(text: str) -> str:
    """Converts markdown *italic* to Typst #emph[...], escaping problematic characters."""
    # Sanitize unescaped quotes or backticks
    clean = text.replace("`", "'")
    # Replace *phrase* with #emph[phrase]
    clean = re.sub(r"\*([^\*\n]+)\*", r"#emph[\1]", clean)
    return clean


def format_de_page(pnum: int, raw_lines: list[str]) -> str:
    body_blocks: list[str] = []
    fn_blocks: list[tuple[str, str]] = []
    current_para: list[str] = []

    is_after_heading = (pnum in [11, 34, 59, 63, 64])
    is_page_continuation = (pnum not in [11, 34, 59, 63, 64])

    def flush_para():
        nonlocal current_para, is_after_heading, is_page_continuation
        if not current_para:
            return
        t = " ".join([l.strip() for l in current_para if l.strip()])
        current_para = []
        if not t:
            return
        t = md_to_typst(t)
        if is_page_continuation:
            body_blocks.append(f"{t}")
            is_page_continuation = False
        elif is_after_heading:
            body_blocks.append(f"{t}")
            is_after_heading = False
        else:
            body_blocks.append(f"#h(12pt) {t}")

    for line in raw_lines:
        st = line.strip()
        if not st:
            flush_para()
            continue

        m_fn = re.match(r"^([¹²³⁴⁵⁶⁷⁸⁹⁰]+|\d+)\s*(.*)$", st)
        is_fn = False
        if m_fn and len(st) > 8 and not st.startswith("http"):
            num = parse_marker_num(m_fn.group(1))
            if num is not None and 1 <= num <= 150 and (fn_blocks or len(body_blocks) >= 1 or current_para):
                is_fn = True

        if is_fn:
            flush_para()
            table = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
            marker = m_fn.group(1).translate(table)
            content = md_to_typst(m_fn.group(2))
            fn_blocks.append((marker, content))
        elif st.startswith("# "):
            flush_para()
            h = md_to_typst(st[2:].strip())
            if pnum == 11 and "Einführende Studie" in h:
                body_blocks.append(f'#text(size: 14pt, weight: "bold", tracking: 1.5pt)[{h.upper()}]\n#v(0.8em)')
            elif pnum in [34, 59, 63, 64]:
                body_blocks.append(f'#text(size: 13pt, weight: "bold")[{h}]\n#v(0.6em)')
            else:
                body_blocks.append(f'#v(0.7em)\n#text(size: 11.5pt, weight: "bold")[{h}]\n#v(0.3em)')
            is_after_heading = True
            is_page_continuation = False
        elif st.startswith("## "):
            flush_para()
            h = md_to_typst(st[3:].strip())
            if pnum == 11:
                body_blocks.append(f'#v(0.6em)\n#text(size: 11.5pt, weight: "bold")[{h}]\n#v(0.4em)')
            else:
                body_blocks.append(f'#v(0.6em)\n#text(size: 11pt, weight: "bold")[{h}]\n#v(0.3em)')
            is_after_heading = True
            is_page_continuation = False
        elif st.startswith("### "):
            flush_para()
            h = md_to_typst(st[4:].strip())
            body_blocks.append(f'#v(0.5em)\n#text(size: 10pt, weight: "bold", style: "italic")[{h}]\n#v(0.2em)')
            is_after_heading = True
            is_page_continuation = False
        else:
            if fn_blocks:
                prev_m, prev_c = fn_blocks[-1]
                fn_blocks[-1] = (prev_m, f"{prev_c} {md_to_typst(st)}")
            else:
                current_para.append(st)

    flush_para()
    body_text = "\n\n".join(body_blocks)
    if fn_blocks:
        fn_items = "\n\n  ".join([f"#par[#box(width: 8.5pt)[#text(size: 8.5pt)[#super[{m}]]]{c}]" for (m, c) in fn_blocks])
        fn_text = f"#block[\n  #set text(size: 7.8pt)\n  #set par(justify: true, hanging-indent: 8.5pt, leading: 0.44em, spacing: 4.2pt)\n  {fn_items}\n]"
        page_markup = f"{body_text}\n\n#v(14pt)\n#line(length: 25%, stroke: 0.4pt)\n#v(-7pt)\n{fn_text}"
    else:
        page_markup = body_text

    return page_markup


def generate_deutsch_typst_edition(de_md_path: Path, typst_path: Path, output_pdf: Path, local_pdf: Path) -> None:
    txt = de_md_path.read_text(encoding="utf-8")
    parts = re.split(r"<!-- PAGE (\d+) -->", txt)
    pages_dict: dict[int, str] = {}
    for i in range(1, len(parts), 2):
        pages_dict[int(parts[i])] = parts[i+1].strip()

    typst_header = '''// AlexandriaSandwich — Seitentreuer digitaler Neusatz (Deutsche Ausgabe)
#set page(
  width: 439.32pt,
  height: 677.28pt,
  margin: (top: 70pt, bottom: 48pt, left: 47.5pt, right: 47.5pt),
  header-ascent: 30pt,
  header: context {
    let p = counter(page).get().first()
    if p <= 11 or p == 34 or p == 59 or p == 63 or p == 64 { return none }
    if calc.even(p) {
      align(center, text(size: 8pt, tracking: 1.5pt, font: "STIX Two Text")[EINFÜHRENDE STUDIE])
    } else {
      let title = if p <= 33 {
        [SA'ADJA GA'ON: EIN INTELLEKTUELLES PORTRÄT]
      } else if p <= 58 {
        [SA'ADJAS BUCH DER OFFENBARTEN WAHRHEITEN UND VERNÜNFTIGEN ARGUMENTE]
      } else {
        [SA'ADJAS EINFLUSS]
      }
      align(center, text(size: 8pt, tracking: 1.5pt, font: "STIX Two Text")[#title])
    }
  },
  footer-descent: -17pt,
  footer: context {
    let p = counter(page).get().first()
    if calc.even(p) {
      align(left, text(size: 9.5pt, font: "STIX Two Text")[#p])
    } else {
      align(right, text(size: 9.5pt, font: "STIX Two Text")[#p])
    }
  }
)

#set text(font: "STIX Two Text", size: 9.5pt, lang: "de")
#set par(justify: true, leading: 0.49em, first-line-indent: 0pt)

#counter(page).update(11)

'''
    pages_typst = []
    for pnum in range(11, 65):
        raw_txt = pages_dict.get(pnum, "")
        clean_lines = clean_de_text(pnum, raw_txt)

        if pnum == 11 and not any("Einführende Studie" in l for l in clean_lines[:3]):
            clean_lines.insert(0, "# Einführende Studie")

        page_t = format_de_page(pnum, clean_lines)
        pages_typst.append(f"// --- PAGE {pnum} ---\n{page_t}\n")

    full_typst = typst_header + "\n#pagebreak()\n".join(pages_typst)
    typst_path.parent.mkdir(parents=True, exist_ok=True)
    typst_path.write_text(full_typst, encoding="utf-8")
    print(f"✓ Saved German Typst source: '{typst_path}'")

    print(f"Compiling Typst to '{local_pdf}'...")
    res = subprocess.run(
        [
            "typst",
            "compile",
            "--font-path",
            "/System/Library/Fonts/Supplemental",
            str(typst_path),
            str(local_pdf),
        ],
        capture_output=True,
    )
    if res.returncode != 0:
        print("Typst compile error:", res.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        raise RuntimeError("Typst compilation failed")

    doc = pymupdf.open(str(local_pdf))
    page_count = len(doc)
    print(f"✓ Typst compiled successfully: {page_count} pages.")
    if page_count != 54:
        doc.close()
        raise RuntimeError(f"Expected exactly 54 pages, but got {page_count} pages!")

    # Set native page labels 11 to 64
    doc.set_page_labels([{"startpage": 0, "prefix": "", "style": "D", "firstpagenum": 11}])

    # German TOC Bookmarks
    toc_data = [
        [1, "Einführende Studie", 1],
        [2, "Sa'adja Ga'on: Ein intellektuelles Porträt", 1],
        [3, "Gaonische Epoche: Tradition und Innovation", 16 - 10],
        [3, "Sprachkultur", 20 - 10],
        [3, "Inspirationsquellen", 26 - 10],
        [2, "Sa'adjas Buch der offenbarten Wahrheiten und vernünftigen Argumente", 34 - 10],
        [3, "Der Titel", 34 - 10],
        [3, "Überblick über das Werk", 36 - 10],
        [3, "Vorrede", 44 - 10],
        [3, "Kosmologie und Psychologie", 47 - 10],
        [3, "Ethik und Eschatologie", 51 - 10],
        [3, "Handschriften, Drucke und Übersetzungen", 55 - 10],
        [2, "Sa'adjas Einfluss", 59 - 10],
        [1, "Anmerkung zur Übersetzung", 63 - 10],
        [1, "Danksagung", 64 - 10],
    ]
    doc.set_toc(toc_data)

    meta = {
        "title": "Sa'adja Ga'on: Buch der offenbarten Wahrheiten und vernünftigen Argumente — Einführende Studie",
        "author": "Daniel Boušek, Dita Válová",
        "subject": "Judeo-arabische Philosophie und Theologie (Deutsche Ausgabe — Digitaler Neusatz)",
        "keywords": "Sa'adja Gaon, Kitab al-amanat, Kalam, Judaeo-Arabic, Jewish Philosophy",
        "producer": "AlexandriaSandwich Pipeline (Typst + PyMuPDF)",
    }
    doc.set_metadata(meta)

    # Save local PDF
    tmp_local = local_pdf.with_suffix(".tmp.pdf")
    doc.save(str(tmp_local), garbage=4, deflate=True)
    tmp_local.replace(local_pdf)
    print(f"✓ Local German Digital Neusatz saved: '{local_pdf}' ({local_pdf.stat().st_size / (1024*1024):.2f} MB)")

    # Save pCloud PDF
    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        tmp_pcloud = output_pdf.with_suffix(".tmp.pdf")
        doc.save(str(tmp_pcloud), garbage=4, deflate=True)
        tmp_pcloud.replace(output_pdf)
        print(f"✓ pCloud German Digital Neusatz saved: '{output_pdf}' ({output_pdf.stat().st_size / (1024*1024):.2f} MB)")
    except Exception as e:
        print(f"Notice: Failed saving to pCloud: {e}", file=sys.stderr)
        raise

    doc.close()


def main():
    pcloud_dir = Path(os.environ.get("ALEXANDRIA_PCLOUD_DIR", str(Path.home() / "pCloud Drive" / "70_AlexandriaSandwich")))
    de_md = pcloud_dir / "Alexandros_Deutsch.md"
    typst_path = Path("data/output/alexandros_czech/Alexandros_Deutsch_Neusatz.typ")
    local_pdf = Path("data/output/alexandros_czech/Alexandros_Deutsch_Neusatz.pdf")
    pcloud_pdf = pcloud_dir / "Alexandros_Deutsch_Neusatz.pdf"

    generate_deutsch_typst_edition(de_md, typst_path, pcloud_pdf, local_pdf)


if __name__ == "__main__":
    main()
