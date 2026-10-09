#!/usr/bin/env python3
"""
scripts/build_full_digital_edition.py — AlexandriaSandwich Complete Digital Edition Generator
Transforms an entire historical book into a high-grade digital vector book via Typst (Artifact 3 / Option A).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


def escape_typst(text: str) -> str:
    """Escape special Typst syntax characters in plain text."""
    # Order matters: escape backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace("[", "\\[").replace("]", "\\]")
    text = text.replace("<", "\\<").replace(">", "\\>")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("@", "\\@")
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    text = text.replace("`", "\\`")
    return text


def clean_ocr(text: str) -> str:
    """Clean common OCR artifacts while preserving scholarly diacritics."""
    # Fix soft hyphens and line-break hyphens
    t = re.sub(r'(\w+)[\u00ad\u2010\u2011\-\xad]\s+(\w+)', r'\1\2', text)
    
    # Common OCR name fixes in Cardona's work
    t = re.sub(r'Pa[J1;:I\.\!]\s*[\,;]?\s*lini(\'?s?)', r'Pāṇini\1', t)
    t = re.sub(r'P[aA][1I\!:i]\s*\)?\s*ini(\'?s?)', r'Pāṇini\1', t)
    t = re.sub(r'A[\$HÆƑ̻ࠛ][t\?][aā]dhy[aā][yY][I\?i]', 'Aṣṭādhyāyī', t)
    t = re.sub(r'K[aā]ty[aā][yY]ana(\'?s?)', r'Kātyāyana\1', t)
    t = re.sub(r'K[iI]ity[aā][yY]ana(\'?s?)', r'Kātyāyana\1', t)
    t = re.sub(r'Pata[nf][ij\]]ali(\'?s?)', r'Patañjali\1', t)
    t = re.sub(r'Mah[aā][\·\-]bha[²ȁŅüó][yY]a', 'Mahābhāṣya', t)
    t = re.sub(r'B[öoó6b]htlingk(\'?s?)', r'Böhtlingk\1', t)
    t = re.sub(r'Yudhi[sgthH]+ira\s+M[iī1lm]+[aā]?[rmnps1]+aka', 'Yudhiṣṭhira Mīmāṁsaka', t)
    t = re.sub(r's[uū]tra[\-\·]p[aā]t[h/z]a', 'sūtra-pāṭha', t)
    t = re.sub(r'dh[aā]tu[\-\·]p[aā]t[h/z]a', 'dhātu-pāṭha', t)
    t = re.sub(r'ga[lJ1\(\)]+a[\-\·]p[aā]t[h/z]a', 'gaṇa-pāṭha', t)
    t = re.sub(r'pr[aā]ti[\·\-]?s[aā]khya(s?)', r'prātiśākhya\1', t)
    t = re.sub(r'siva[\-\·]s[uūi]+tras', 'śiva-sūtras', t)
    return t


def build_full_digital_edition(
    input_pdf: Path,
    toc_json: Path,
    output_typ: Path,
    title: str = "Pāṇini: A Survey of Research",
    author: str = "George Cardona",
    date: str = "1976 / Digital Vector Edition",
) -> Path:
    t0 = time.time()
    print(f"[build_digital] Opening: {input_pdf}")
    doc = pymupdf.open(input_pdf)
    total_pages = len(doc)
    print(f"[build_digital] Total pages: {total_pages}")

    toc = json.loads(toc_json.read_text(encoding="utf-8"))
    toc_by_page: Dict[int, List[Tuple[int, str]]] = {}
    heading_titles_set = set()
    for lvl, t_name, pno in toc:
        toc_by_page.setdefault(pno, []).append((lvl, t_name))
        heading_titles_set.add(t_name.lower().strip())

    typ_lines = [
        '#import "/templates/book.typ": book',
        '',
        '#show: book.with(',
        f'  title: "{escape_typst(title)}",',
        f'  author: "{escape_typst(author)}",',
        f'  date: "{escape_typst(date)}",',
        '  paper: "a5",',
        '  lang: "en"',
        ')',
        '',
        '#set footnote(numbering: "1")',
        '',
        '#outline(',
        '  title: [Table of Contents],',
        '  indent: auto,',
        '  depth: 3',
        ')',
        '',
        '#pagebreak()',
        '',
    ]

    # Process pages
    for pno in range(1, total_pages + 1):
        # Skip title page & old scan TOC pages (7-13) since Typst generates outline dynamically
        if pno in [1, 2, 3, 7, 8, 9, 10, 11, 12, 13]:
            continue

        page = doc[pno - 1]
        
        # Determine printed page label
        if 4 <= pno <= 6:
            roman_numerals = {4: "v", 5: "viii", 6: "ix"}
            printed_label = f"Orig. p. {roman_numerals.get(pno, str(pno))}"
        elif pno >= 14:
            printed_label = f"Orig. p. {pno - 13}"
        else:
            printed_label = f"Orig. p. {pno}"

        # 1. Emit any TOC headings that start on this page
        page_headings = toc_by_page.get(pno, [])
        for lvl, h_title in page_headings:
            # Map level to Typst heading syntax: lvl 1 = '=', lvl 2 = '==', etc.
            eqs = "=" * min(lvl, 5)
            typ_lines.append(f"{eqs} {escape_typst(h_title)}")
            typ_lines.append("")

        # 2. Emit subtle citation anchor for this original page
        typ_lines.append(f'#text(size: 7.5pt, fill: rgb("#b45309"), weight: "bold")[[{printed_label}]]')
        typ_lines.append("")

        # 3. Extract and filter body blocks
        blocks = page.get_text("blocks")
        for b in blocks:
            x0, y0, x1, y1, b_text, b_no, b_type = b
            if b_type != 0:
                continue

            # Filter running headers (y1 < 36) or footers
            if y1 < 36.0 or y0 > 538.0:
                continue

            cleaned_b = b_text.strip()
            if not cleaned_b:
                continue

            # Skip block if it is identical to a TOC heading already emitted
            norm_b = re.sub(r'^[I|V|X\d\.\s\:\-]+', '', cleaned_b).lower().strip()
            if norm_b in heading_titles_set and len(cleaned_b) < 120:
                continue

            # Clean OCR artifacts and join lines within block
            cleaned_text = clean_ocr(" ".join(l.strip() for l in cleaned_b.splitlines() if l.strip()))
            
            # Format block
            typ_lines.append(escape_typst(cleaned_text))
            typ_lines.append("")

    output_typ.parent.mkdir(parents=True, exist_ok=True)
    output_typ.write_text("\n".join(typ_lines), encoding="utf-8")
    elapsed = time.time() - t0
    print(f"[build_digital] Wrote complete Typst source to: {output_typ} in {elapsed:.2f}s")
    return output_typ


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate complete digital vector edition via Typst")
    parser.add_argument("-i", "--input", type=Path, default=Path("/Users/marco/Downloads/Cardona_1976_Panini_A_Survey_of_Research_outline.pdf"))
    parser.add_argument("-t", "--toc", type=Path, default=Path("data/toc_cardona_1976.json"))
    parser.add_argument("-o", "--output", type=Path, default=Path("data/output/cardona_complete.typ"))
    parser.add_argument("--pdf", type=Path, default=Path("/Users/marco/Downloads/Cardona_1976_Panini_complete_digital.pdf"))

    args = parser.parse_args()
    build_full_digital_edition(args.input, args.toc, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
