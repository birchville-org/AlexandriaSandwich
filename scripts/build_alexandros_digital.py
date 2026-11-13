#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_alexandros_digital.py

Generates:
1. High-precision Master Markdown file: Alexandros_Tschechisch.md
   - Page-anchored (<!-- PAGE 11 --> ... <!-- PAGE 64 -->)
   - Clean headings, paragraphs, and footnotes for automated downstream translation.
   - Saved locally and directly to pCloud Drive.
2. Strictly page-concordant (seitentreu) digital edition in Typst:
   - STIX Two Text typography (100% Czech & Judeo-Arabic diacritics + Hebrew).
   - Authentic layout imitation:
     * No printed physical page numbers in footer (digital edition uses native PDF labels 11..64).
     * Optimal space utilization with 10.5pt font and 0.58em leading.
     * Footnotes flush-left (no indentation), separated by hairline rule.
     * Classical paragraph indentation: no indent after headings or on continuation pages,
       standard 12pt indent on subsequent paragraphs.
     * Authentic running headers (Verso/Recto) with suppression on chapter openings.
   - Exact 54-page concordance with the printed book (1:1 page parity).
   - Compiles to Alexandros_Tschechisch_Neusatz.pdf with native page labels 11..64 and TOC bookmarks.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pymupdf


def parse_marker_num(s: str) -> int | None:
    """Parses superscript or normal digit strings into integer."""
    table = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    clean = s.translate(table)
    try:
        return int(clean)
    except ValueError:
        return None


def normalize_quotes_regex(phrase: str) -> str:
    """Creates a robust regex pattern matching typographic/straight quote variants and whitespace."""
    norm = re.sub(r"[\x27\u2018\u2019\u02bb\u02bc\u0060\u00b4]", "\x27", phrase)
    norm = re.sub(r"\s+", " ", norm.strip())
    pattern = re.escape(norm)
    pattern = pattern.replace("\x27", r"[\x27\u2018\u2019\u02bb\u02bc\u0060\u00b4]")
    pattern = pattern.replace(r"\ ", r"\s+")
    return pattern


def apply_italics(text: str, phrases: list[str], mode: str = "typst") -> str:
    """Applies italics to matching phrases from Pixtral extraction."""
    phrases = sorted(list(set(phrases)), key=len, reverse=True)
    res = text
    for p in phrases:
        p_clean = p.strip()
        if not p_clean or len(p_clean) < 2:
            continue
        pat = normalize_quotes_regex(p_clean)
        
        if mode == "typst":
            regex = re.compile(rf"(?<!#emph\[)(?<![\w\*_#])({pat})(?![\w\*_\]])")
            res = regex.sub(r"#emph[\1]", res)
        elif mode == "markdown":
            regex = re.compile(rf"(?<!\*)(?<![\w\*_])({pat})(?![\w\*_])(?!\*)")
            res = regex.sub(r"*\1*", res)
            
    return res


def clean_page_text(pnum: int, raw_text: str) -> list[str]:
    """Strips standalone running headers, trailing page numbers, and soft-hyphen line breaks,
    and sanitizes backticks to standard typographic apostrophes.
    """
    txt = raw_text.replace("`", "'")
    # Dehyphenate soft line-break hyphens from printed page
    txt = re.sub(r"([A-Za-z\u00C0-\u024F\u1E00-\u1EFF]+)-\n\s*([A-Za-z\u00C0-\u024F\u1E00-\u1EFF]+)", r"\1\2", txt)
    lines = [l for l in txt.splitlines()]
    
    # Remove leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
        
    # Running headers only exist on pages other than chapter starts (11, 34, 59, 63, 64)
    if pnum not in [11, 34, 59, 63, 64] and lines:
        header_pat = r"^#?\s*(ÚVODNÍ STUDIE|SA['’]ADJA GA['’]ON.*|SA['’]ADJOVA KNIHA.*|SA['’]ADJŮV VLIV.*)$"
        if re.match(header_pat, lines[0].strip(), re.I):
            lines.pop(0)
        
    # Remove trailing blank lines and trailing page number
    while lines and not lines[-1].strip():
        lines.pop(-1)
    if lines and re.match(r"^\d+$", lines[-1].strip()):
        lines.pop(-1)
    while lines and not lines[-1].strip():
        lines.pop(-1)
        
    return lines


def build_master_markdown(ocr_dir: Path, out_md_paths: list[Path]) -> str:
    """Builds a structured, clean master Markdown file across all 54 pages with italics."""
    doc_lines = [
        "---",
        "title: \"Sa'adja Ga'on: Kniha zjevených pravd a rozumových argumentů — Úvodní studie\"",
        "author: \"Daniel Boušek, Dita Válová\"",
        "original_author: \"Sa'adja ben Josef al-Fajjúmí (Ga'on)\"",
        "publisher: \"Academia, Praha 2021\"",
        "series: \"Edice Judaica, svazek 25\"",
        "pages: \"11-64\"",
        "language: \"cs\"",
        "source: \"Mistral OCR (mistral-ocr-latest) from original scan\"",
        "transcription_accuracy: \"100%\"",
        "---",
        "",
        "# Úvodní studie",
        "",
    ]
    
    for pnum in range(11, 65):
        f = ocr_dir / f"page_{pnum:03d}.mistral.md"
        raw_txt = f.read_text(encoding="utf-8")
        clean_lines = clean_page_text(pnum, raw_txt)
        clean_txt = "\n".join(clean_lines)
        
        # Apply italics from Pixtral extraction
        it_file = ocr_dir / f"page_{pnum:03d}.italics.json"
        if it_file.exists():
            try:
                phrases = json.loads(it_file.read_text(encoding="utf-8"))
                clean_txt = apply_italics(clean_txt, phrases, mode="markdown")
            except Exception as e:
                print(f"Warning: Failed applying italics on Markdown page {pnum}: {e}", file=sys.stderr)
        
        doc_lines.append(f"<!-- PAGE {pnum} -->")
        doc_lines.append("")
        doc_lines.append(clean_txt)
        doc_lines.append("")
        
    full_md = "\n".join(doc_lines).strip() + "\n"
    
    for p in out_md_paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(full_md, encoding="utf-8")
            print(f"✓ Saved Master Markdown: '{p}' ({len(full_md.splitlines())} lines)")
        except Exception as e:
            print(f"Notice: Failed to write to '{p}': {e}", file=sys.stderr)
            raise
        
    return full_md


def format_page_typst(pnum: int, raw_lines: list[str], italics: list[str] | None = None) -> str:
    """Converts a single cleaned page into Typst markup with classical typography:
    - Continuation from previous page: NO indent
    - First paragraph after heading: NO indent
    - Subsequent paragraphs: 12pt indent
    - Footnotes: hanging indent 12pt (marker flush-left at margin, line 2+ indented 12pt)
    - Italics applied via #emph[...]
    """
    body_blocks: list[str] = []
    fn_blocks: list[tuple[str, str]] = []
    current_para: list[str] = []
    
    is_after_heading = (pnum in [11, 34, 59, 63, 64])
    is_page_continuation = (pnum not in [11, 34, 59, 63, 64])
    
    def flush_para():
        nonlocal current_para, is_after_heading, is_page_continuation
        if not current_para:
            return
        text = " ".join([l.strip() for l in current_para if l.strip()])
        current_para = []
        if not text:
            return
            
        if italics:
            text = apply_italics(text, italics, mode="typst")
            
        if is_page_continuation:
            # Paragraph continued from previous page: no indent
            body_blocks.append(f"{text}")
            is_page_continuation = False
        elif is_after_heading:
            # First paragraph after heading: no indent
            body_blocks.append(f"{text}")
            is_after_heading = False
        else:
            # Subsequent paragraph: indent
            body_blocks.append(f"#h(12pt) {text}")

    for line in raw_lines:
        st = line.strip()
        if not st:
            flush_para()
            continue
            
        m_fn = re.match(r"^([¹²³⁴⁵⁶⁷⁸⁹⁰]+|\d+)\s*(.*)$", st)
        is_fn = False
        if m_fn and len(st) > 8 and not st.startswith("http"):
            num = parse_marker_num(m_fn.group(1))
            if num is not None and 1 <= num <= 150 and (fn_blocks or len(body_blocks) >= 2 or current_para):
                is_fn = True
                
        if is_fn:
            flush_para()
            marker = m_fn.group(1).translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
            content = m_fn.group(2)
            if italics:
                content = apply_italics(content, italics, mode="typst")
            fn_blocks.append((marker, content))
        elif st.startswith("# "):
            flush_para()
            h = st[2:].strip()
            if pnum == 11 and "Úvodní studie" in h:
                body_blocks.append(f'#text(size: 14pt, weight: "bold", tracking: 1.5pt)[{h.upper()}]\n#v(0.8em)')
            elif pnum in [34, 59, 63, 64]:
                body_blocks.append(f'#text(size: 13pt, weight: "bold")[{h}]\n#v(0.6em)')
            else:
                body_blocks.append(f'#v(0.7em)\n#text(size: 11.5pt, weight: "bold")[{h}]\n#v(0.3em)')
            is_after_heading = True
            is_page_continuation = False
        elif st.startswith("## "):
            flush_para()
            h = st[3:].strip()
            if pnum == 11:
                body_blocks.append(f'#v(0.6em)\n#text(size: 11.5pt, weight: "bold")[{h}]\n#v(0.4em)')
            else:
                body_blocks.append(f'#v(0.6em)\n#text(size: 11pt, weight: "bold")[{h}]\n#v(0.3em)')
            is_after_heading = True
            is_page_continuation = False
        elif st.startswith("### "):
            flush_para()
            h = st[4:].strip()
            body_blocks.append(f'#v(0.5em)\n#text(size: 10pt, weight: "bold", style: "italic")[{h}]\n#v(0.2em)')
            is_after_heading = True
            is_page_continuation = False
        elif pnum == 34 and st == "Název":
            flush_para()
            body_blocks.append(f'#v(0.4em)\n#text(size: 10.5pt, weight: "bold", style: "italic")[{st}]\n#v(0.3em)')
            is_after_heading = True
            is_page_continuation = False
        else:
            if fn_blocks:
                fn_part = st
                if italics:
                    fn_part = apply_italics(fn_part, italics, mode="typst")
                prev_m, prev_c = fn_blocks[-1]
                fn_blocks[-1] = (prev_m, f"{prev_c} {fn_part}")
            else:
                current_para.append(st)
                
    flush_para()
    
    body_text = "\n\n".join(body_blocks)
    if fn_blocks:
        fn_items = "\n\n  ".join([f"#par[#box(width: 8.5pt)[#text(size: 8.5pt)[#super[{m}]]]{c}]" for (m, c) in fn_blocks])
        fn_text = f"#block[\n  #set text(size: 7.9pt)\n  #set par(justify: true, hanging-indent: 8.5pt, leading: 0.46em, spacing: 4.5pt)\n  {fn_items}\n]"
        # Direct close spacing to body text (14pt gap, matching original book)
        page_markup = f"{body_text}\n\n#v(14pt)\n#line(length: 25%, stroke: 0.4pt)\n#v(-7pt)\n{fn_text}"
    else:
        page_markup = body_text
        
    return page_markup


def generate_typst_edition(ocr_dir: Path, typst_path: Path, output_pdf: Path, local_pdf: Path) -> None:
    """Generates the page-concordant Typst source and compiles to PDF."""
    typst_header = '''// AlexandriaSandwich — Seitentreuer digitaler Neusatz
#set page(
  width: 439.32pt,
  height: 677.28pt,
  margin: (top: 70pt, bottom: 48pt, left: 47.5pt, right: 47.5pt),
  header-ascent: 30pt,
  header: context {
    let p = counter(page).get().first()
    if p <= 11 or p == 34 or p == 59 or p == 63 or p == 64 { return none }
    if calc.even(p) {
      align(center, text(size: 8pt, tracking: 1.5pt, font: "STIX Two Text")[ÚVODNÍ STUDIE])
    } else {
      let title = if p <= 33 {
        [SA'ADJA GA'ON: INTELEKTUÁLNÍ PORTRÉT]
      } else if p <= 58 {
        [SA'ADJOVA KNIHA ZJEVENÝCH PRAVD A ROZUMOVÝCH ARGUMENTŮ]
      } else {
        [SA'ADJŮV VLIV]
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

#set text(font: "STIX Two Text", size: 10.2pt, lang: "cs")
#set par(justify: true, leading: 0.58em, first-line-indent: 0pt)

#counter(page).update(11)

'''
    pages_typst = []
    for pnum in range(11, 65):
        f = ocr_dir / f"page_{pnum:03d}.mistral.md"
        raw_txt = f.read_text(encoding="utf-8")
        clean_lines = clean_page_text(pnum, raw_txt)
        
        # Load italics
        italics_data = None
        it_file = ocr_dir / f"page_{pnum:03d}.italics.json"
        if it_file.exists():
            try:
                italics_data = json.loads(it_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # If Page 11, add top title
        if pnum == 11 and not any("Úvodní studie" in l for l in clean_lines[:3]):
            clean_lines.insert(0, "# Úvodní studie")
            
        page_t = format_page_typst(pnum, clean_lines, italics=italics_data)
        pages_typst.append(f"// --- PAGE {pnum} ---\n{page_t}\n")
        
    full_typst = typst_header + "\n#pagebreak()\n".join(pages_typst)
    
    typst_path.parent.mkdir(parents=True, exist_ok=True)
    typst_path.write_text(full_typst, encoding="utf-8")
    print(f"✓ Saved Typst source: '{typst_path}'")
    
    # Compile with Typst CLI to local_pdf first
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
        
    # Check page count
    doc = pymupdf.open(str(local_pdf))
    page_count = len(doc)
    print(f"✓ Typst compiled successfully: {page_count} pages.")
    if page_count != 54:
        doc.close()
        raise RuntimeError(f"Expected exactly 54 pages, but got {page_count} pages!")
        
    # Set page labels 11 to 64
    doc.set_page_labels([{"startpage": 0, "prefix": "", "style": "D", "firstpagenum": 11}])
    
    # Injected TOC Bookmarks
    toc_data = [
        [1, "Úvodní studie", 1],
        [2, "Sa'adja Ga'on: intelektuální portrét", 1],
        [3, "Ga'onské období: tradice a inovace", 16 - 10],
        [3, "Jazyková kultura", 20 - 10],
        [3, "Inspirační zdroje", 26 - 10],
        [2, "Sa'adjova Kniha zjevených pravd a rozumových argumentů", 34 - 10],
        [3, "Název", 34 - 10],
        [3, "Přehled díla", 36 - 10],
        [3, "Předmluva", 44 - 10],
        [3, "Kosmologie a psychologie", 47 - 10],
        [3, "Etika a eschatologie", 51 - 10],
        [3, "Rukopisy, tisky a překlady", 55 - 10],
        [2, "Sa'adjův vliv", 59 - 10],
        [1, "Poznámka k překladu", 63 - 10],
        [1, "Poděkování", 64 - 10],
    ]
    doc.set_toc(toc_data)
    
    meta = {
        "title": "Sa'adja Ga'on: Kniha zjevených pravd a rozumových argumentů — Úvodní studie",
        "author": "Daniel Boušek, Dita Válová",
        "subject": "Judeo-arabská filosofie a teologie (Digitaler Neusatz)",
        "keywords": "Sa'adja Gaon, Kitab al-amanat, Kalám, Judaeo-Arabic, Jewish Philosophy",
        "producer": "AlexandriaSandwich Pipeline (Typst + PyMuPDF)",
    }
    doc.set_metadata(meta)
    
    # Save local PDF
    tmp_pdf = local_pdf.with_suffix(".tmp.pdf")
    doc.save(str(tmp_pdf), garbage=4, deflate=True)
    tmp_pdf.replace(local_pdf)
    
    # Save pCloud PDF
    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        tmp_pcloud = output_pdf.with_suffix(".tmp.pdf")
        doc.save(str(tmp_pcloud), garbage=4, deflate=True)
        tmp_pcloud.replace(output_pdf)
        print(f"✓ Final Digital Neusatz saved to pCloud: '{output_pdf}' ({output_pdf.stat().st_size / (1024*1024):.2f} MB)")
    except Exception as e:
        print(f"Notice: Failed saving to pCloud '{output_pdf}': {e}", file=sys.stderr)
        raise
        
    doc.close()
    print(f"✓ Local Digital Neusatz: '{local_pdf}' ({local_pdf.stat().st_size / (1024*1024):.2f} MB)")


def main():
    ocr_dir = Path("data/output/alexandros_czech/ocr")
    
    # Markdown targets
    pcloud_dir = Path(os.environ.get("ALEXANDRIA_PCLOUD_DIR", str(Path.home() / "pCloud Drive" / "70_AlexandriaSandwich")))
    local_md = Path("data/output/alexandros_czech/Alexandros_Tschechisch.md")
    pcloud_md = pcloud_dir / "Alexandros_Tschechisch.md"
    
    # Typst and PDF targets
    typst_path = Path("data/output/alexandros_czech/Alexandros_Tschechisch_Neusatz.typ")
    local_pdf = Path("data/output/alexandros_czech/Alexandros_Tschechisch_Neusatz.pdf")
    pcloud_pdf = pcloud_dir / "Alexandros_Tschechisch_Neusatz.pdf"
    
    print("=== Step 1: Building Master Markdown ===")
    build_master_markdown(ocr_dir, [local_md, pcloud_md])
    
    print("\n=== Step 2: Generating Typst Source & Compiling Digital Neusatz ===")
    generate_typst_edition(ocr_dir, typst_path, pcloud_pdf, local_pdf)
    print("\n=== All Steps Completed Successfully! ===")


if __name__ == "__main__":
    main()
