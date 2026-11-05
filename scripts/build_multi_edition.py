#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_multi_edition.py

Multi-Edition Generator for Critical and Philological Editions
(Birchville Scholarly Synthesis Standard):
Takes a canonical structured dataset (lines, footnotes, translations, verses) and
generates up to four synchronized editions with strict 1:1 line and page parity:
  1. 'original': Monolingual source script (e.g. Devanāgarī).
  2. 'interlinear': Dual script / interlinear (e.g. Devanāgarī + IAST).
  3. 'transliteration': Monolingual romanized (e.g. pure IAST).
  4. 'bilingual': Transliteration + line-by-line translation (e.g. IAST + German/English).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf

from scripts.indic_normalizer import (
    normalize_apparatus_iast,
    to_arabic_numerals,
    to_deva_numerals,
    to_iast,
)
from scripts.postprocess_pdf_metadata import postprocess_pdf


def generate_typst_content(
    edition_type: str,
    meta: Dict[str, Any],
    pages_data: Dict[int, Dict[str, Any]],
) -> str:
    """
    Constructs the complete Typst markup string for the requested edition type.
    edition_type: 'original' | 'interlinear' | 'transliteration' | 'bilingual'
    """
    paper = meta.get("paper", "a5")
    font_main = meta.get("font_main", "STIX Two Text")
    font_deva = meta.get("font_deva", "Devanagari MT")
    start_page = meta.get("start_page", 10)
    has_title_page = meta.get("has_title_page", True)
    title = meta.get("title", "TANTRASĀRAḤ")
    author = meta.get("author", "Śrīmad Abhinavagupta")
    chapter_num = meta.get("chapter_num", 3)
    chapter_title = meta.get("chapter_title", "Śāmbhavopāya")

    typ_lines: List[str] = []

    # Title Page
    if has_title_page:
        badge_map = {
            "original": "KRITISCHER NEUSATZ (DEVANĀGARĪ)",
            "interlinear": "DEVANĀGARĪ & IAST INTERLINEAR EDITION",
            "transliteration": "ROMAN TRANSLITERATION (IAST) EDITION",
            "bilingual": "IAST-NEUSATZ MIT ZEILENWEISER ÜBERSETZUNG",
        }
        badge = badge_map.get(edition_type, "STUDIENAUSGABE")
        typ_lines.append(rf"""
// ==================== TITELBLATT ====================
#set page(
  paper: "{paper}",
  margin: (inside: 1.8cm, outside: 1.8cm, top: 2.0cm, bottom: 1.6cm),
  header: none
)

#align(center)[
  #stack(spacing: 4pt)[
    #text(font: "{font_main}", size: 10.5pt, weight: "medium", tracking: 0.04em)[kaśmīra-saṃskṛta-granthāvalī — granthāṅkaḥ 17]
  ][
    #text(font: "{font_main}", size: 8.5pt, fill: rgb("#6b7280"))[Kashmir Series of Texts and Studies · No. XVII]
  ]

  #v(1.4cm)

  #stack(spacing: 3pt)[
    #text(font: "{font_main}", size: 13pt, style: "italic", fill: rgb("#374151"))[śrīmadabhinavaguptācāryaviracitaḥ]
  ][
    #text(font: "{font_main}", size: 10pt, fill: rgb("#6b7280"))[Von {author}]
  ]

  #v(0.5cm)

  #text(font: "{font_main}", size: 27pt, weight: "bold", tracking: 0.03em)[{title}]

  #v(0.5cm)

  #stack(spacing: 3pt)[
    #text(font: "{font_main}", size: 15pt, weight: "bold", fill: rgb("#374151"))[tṛtīyam āhnikam · atha śāmbhavopāyaḥ]
  ][
    #text(font: "{font_main}", size: 12pt, style: "italic", fill: rgb("#4b5563"))[Kapitel {chapter_num}: {chapter_title}]
  ]

  #v(0.8cm)

  #block(stroke: 0.5pt + rgb("#9ca3af"), inset: (x: 14pt, y: 6pt), radius: 3pt)[
    #stack(spacing: 2.5pt)[
      #text(font: "{font_main}", size: 8.8pt, weight: "bold", tracking: 0.05em, fill: rgb("#1f2937"))[
        {badge}
      ]
    ][
      #text(font: "{font_main}", size: 7.8pt, style: "italic", fill: rgb("#6b7280"))[
        Zeilen- und seitentreue wissenschaftliche Studienausgabe
      ]
    ]
  ]

  #v(1.0cm)

  #line(length: 22%, stroke: 0.5pt + rgb("#cbd5e1"))
  #v(0.35cm)

  #stack(spacing: 2.5pt)[
    #text(font: "{font_main}", size: 9pt, style: "italic", fill: rgb("#6b7280"))[saṃśodhakaḥ]
  ][
    #text(font: "{font_main}", size: 11pt, weight: "bold", fill: rgb("#1f2937"))[Mahāmahopādhyāya Paṇḍita Mukundarāma Śāstrī]
  ]

  #v(1fr)

  #stack(spacing: 3pt)[
    #text(font: "{font_main}", size: 8.5pt, fill: rgb("#6b7280"))[mūlamudraṇam : Nirṇaya Sāgara Press, Bombay, 1918]
  ][
    #text(font: "{font_main}", size: 8.5pt, fill: rgb("#9ca3af"))[Birchville Scholarly Synthesis Standard]
  ]
]

#pagebreak()
""")

    # Body Setup & Headers
    # Formula for pno: if title page exists, body starts at page 2, so offset = start_page - 2
    offset = (start_page - 2) if has_title_page else (start_page - 1)

    typ_lines.append(rf"""
#set page(
  paper: "{paper}",
  margin: (inside: 1.2cm, outside: 1.2cm, top: 0.85cm, bottom: 0.85cm),
  header: context {{
    let p = here().page()
    let pno = p + {offset}
    let dev_digits = ("०", "१", "२", "३", "४", "५", "६", "७", "८", "९")
    let dev_str = str(pno).clusters().map(c => dev_digits.at(int(c))).join()
    
    if p == 1 and {str(has_title_page).lower()} {{
      none
    }} else if calc.even(pno) {{
      grid(
        columns: (1fr, 3fr, 1fr),
        align: (left, center, right),
        text(font: "{font_main}", size: 8.8pt)[#pno],
        text(font: "{font_main}", size: 8.8pt, weight: "bold")[{title} · KAPITEL {chapter_num}],
        text(font: "{font_main}", size: 8.8pt)[\[ {chapter_num} Ā. \]]
      )
    }} else {{
      grid(
        columns: (1fr, 3fr, 1fr),
        align: (left, center, right),
        text(font: "{font_main}", size: 8.8pt)[\[ {chapter_num} Ā. \]],
        text(font: "{font_main}", size: 8.8pt, style: "italic")[{chapter_title.upper()}],
        text(font: "{font_main}", size: 8.8pt)[#pno]
      )
    }}
  }}
)

// Macro: Interlinear Pair
#let il(top, bottom, top_font: "{font_main}") = block(spacing: 7.2pt, breakable: false)[
  #stack(spacing: 2.6pt)[
    #text(font: top_font, size: 9.6pt, weight: "medium")[#top]
  ][
    #text(font: "{font_main}", size: 8.0pt, style: "italic", fill: rgb("#374151"))[#bottom]
  ]
]

// Macro: Monolingual Line
#let ml(txt, font: "{font_main}") = block(spacing: 12.0pt, breakable: false)[
  #text(font: font, size: 11.2pt)[#txt]
]

// Macro: Footnote Pair
#let il_fn(top, bottom, top_font: "{font_main}") = block(spacing: 6.2pt, breakable: false)[
  #stack(spacing: 2.2pt)[
    #text(font: top_font, size: 7.5pt, weight: "medium")[#top]
  ][
    #text(font: "{font_main}", size: 6.8pt, style: "italic", fill: rgb("#4b5563"))[#bottom]
  ]
]

// Macro: Monolingual Footnote
#let ml_fn(txt, font: "{font_main}") = block(spacing: 8.0pt, breakable: false)[
  #text(font: font, size: 8.0pt)[#txt]
]
""")

    # Render Pages
    sorted_pages = sorted(pages_data.keys())
    for idx, pno in enumerate(sorted_pages):
        pdata = pages_data[pno]
        typ_lines.append(f"// ==================== PAGE {pno} ====================")

        # Optional page-top heading on first page
        if pno == start_page:
            typ_lines.append(rf"""
#align(center)[
  #stack(spacing: 2.5pt)[
    #text(font: "{font_main}", size: 12.0pt, weight: "bold")[atha tṛtīyam āhnikam]
  ][
    #text(font: "{font_main}", size: 9.5pt, style: "italic", fill: rgb("#4b5563"))[Nun das {chapter_num}. Kapitel]
  ]
  #v(2.5pt)
  #stack(spacing: 2.5pt)[
    #text(font: "{font_main}", size: 10.5pt, weight: "bold")[atha śāmbhavopāyaḥ]
  ][
    #text(font: "{font_main}", size: 9.0pt, style: "italic", fill: rgb("#4b5563"))[Nun das Mittel Śivas]
  ]
]
#v(3pt)
""")

        # Main text lines
        lines_orig = pdata.get("lines_orig", [])
        lines_translit = pdata.get("lines_translit") or [to_iast(l) for l in lines_orig]
        lines_trans = pdata.get("lines_trans", [])

        for i in range(len(lines_orig)):
            l_orig = lines_orig[i]
            l_iast = lines_translit[i] if i < len(lines_translit) else to_iast(l_orig)
            l_de = lines_trans[i] if i < len(lines_trans) else ""

            if edition_type == "original":
                typ_lines.append(f'#ml("{l_orig}", font: "{font_deva}")')
            elif edition_type == "interlinear":
                typ_lines.append(f'#il("{l_orig}", "{l_iast}", top_font: "{font_deva}")')
            elif edition_type == "transliteration":
                typ_lines.append(f'#ml("{l_iast}", font: "{font_main}")')
            elif edition_type == "bilingual":
                typ_lines.append(f'#il("{l_iast}", "{l_de}", top_font: "{font_main}")')

        # Extra Verses (if present)
        verses = pdata.get("verses", [])
        for v in verses:
            typ_lines.append(r"#v(2.5pt) #align(center)[ #block(width: 90%)[ #set align(left)")
            for v_idx in range(0, len(v), 2):
                v_top = v[v_idx]
                v_bot = v[v_idx + 1] if v_idx + 1 < len(v) else ""
                indent = " #pad(left: 1.8em)[" if (v_idx // 2) % 2 == 1 else ""
                closing = "]" if indent else ""

                if edition_type == "original":
                    typ_lines.append(f'{indent}#ml("{v_top}", font: "{font_deva}"){closing}')
                elif edition_type == "transliteration":
                    typ_lines.append(f'{indent}#ml("{to_iast(v_top)}", font: "{font_main}"){closing}')
                elif edition_type == "interlinear":
                    typ_lines.append(f'{indent}#il("{v_top}", "{to_iast(v_top)}", top_font: "{font_deva}"){closing}')
                elif edition_type == "bilingual":
                    typ_lines.append(f'{indent}#il("{to_iast(v_top)}", "{v_bot}", top_font: "{font_main}"){closing}')
            typ_lines.append(r"] ]")

        # Colophon (if present)
        colophon = pdata.get("colophon")
        if colophon:
            top_colo, bot_colo = colophon
            top_colo_safe = top_colo.replace("//", r"\/\/")
            bot_colo_safe = bot_colo.replace("//", r"\/\/")
            typ_lines.append(rf"""
#v(0.4cm)
#align(center)[
  #block(stroke: 0.8pt + luma(120), inset: (x: 16pt, y: 10pt), radius: 3pt)[
    #stack(spacing: 4pt)[
      #text(font: "{font_main}", size: 9.6pt, weight: "bold")[{top_colo_safe}]
    ][
      #text(font: "{font_main}", size: 8.2pt, style: "italic", fill: rgb("#374151"))[{bot_colo_safe}]
    ]
  ]
]
#v(0.35cm)
#align(center)[
  #text(font: "{font_main}", size: 10.5pt, weight: "bold", fill: luma(70))[— ❖ oṃ tatsat ❖ —]
]
""")

        # Footnotes
        fns = pdata.get("footnotes", [])
        fns_trans = pdata.get("footnotes_trans", [])
        if fns:
            typ_lines.append(r"""
#v(1fr, weak: true)
#v(2pt)
#line(length: 30%, stroke: 0.5pt + luma(100))
#v(2.5pt)
""")
            for f_idx, fn in enumerate(fns):
                fn_top = fn
                if edition_type == "original":
                    typ_lines.append(f'#ml_fn("{fn_top}", font: "{font_deva}")')
                elif edition_type == "transliteration":
                    fn_iast = normalize_apparatus_iast(fn_top)
                    typ_lines.append(f'#ml_fn("{fn_iast}", font: "{font_main}")')
                elif edition_type == "interlinear":
                    fn_iast = normalize_apparatus_iast(fn_top)
                    typ_lines.append(f'#il_fn("{fn_top}", "{fn_iast}", top_font: "{font_deva}")')
                elif edition_type == "bilingual":
                    fn_iast = normalize_apparatus_iast(fn_top)
                    fn_de = fns_trans[f_idx] if f_idx < len(fns_trans) else ""
                    typ_lines.append(f'#il_fn("{fn_iast}", "{fn_de}", top_font: "{font_main}")')

        if idx < len(sorted_pages) - 1:
            typ_lines.append("#pagebreak()")

    return "\n".join(typ_lines)


def build_edition(
    dataset_path: Path,
    output_dir: Path,
    edition_type: str = "bilingual",
) -> Path:
    """Builds a single edition PDF from the canonical dataset."""
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    pages_data = {int(k): v for k, v in data.get("pages", {}).items()}
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = meta.get("base_filename", "Edition")
    suffix_map = {
        "original": "Neusatz Deva",
        "interlinear": "Neusatz interlinear IAST",
        "transliteration": "Neusatz rein IAST",
        "bilingual": "Neusatz IAST mit DE Übersetzung",
    }
    filename = f"{base_name} ({suffix_map.get(edition_type, edition_type)})"
    typ_path = output_dir / f"{filename}.typ"
    pdf_path = output_dir / f"{filename}.pdf"

    typ_code = generate_typst_content(edition_type, meta, pages_data)
    with open(typ_path, "w", encoding="utf-8") as f:
        f.write(typ_code)

    print(f"Compiling {edition_type} -> {pdf_path.name}...")
    res = subprocess.run(["typst", "compile", str(typ_path), str(pdf_path)], capture_output=True, text=True)
    if res.returncode != 0:
        print("Typst error:", res.stderr, file=sys.stderr)
        raise RuntimeError(f"Failed to compile {typ_path}")

    # Inject PDF page labels
    start_page = meta.get("start_page", 1)
    has_title = meta.get("has_title_page", True)
    postprocess_pdf(pdf_path, body_start_num=start_page, has_title_page=has_title)

    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Multi-Edition Generator for AlexandriaSandwich")
    parser.add_argument("dataset", type=Path, help="Path to canonical dataset JSON")
    parser.add_argument("out_dir", type=Path, help="Output directory for generated PDFs")
    parser.add_argument(
        "--format",
        choices=["original", "interlinear", "transliteration", "bilingual", "all"],
        default="all",
        help="Edition format to build",
    )
    args = parser.parse_args()

    formats = (
        ["original", "interlinear", "transliteration", "bilingual"]
        if args.format == "all"
        else [args.format]
    )

    for fmt in formats:
        out_pdf = build_edition(args.dataset, args.out_dir, edition_type=fmt)
        print(f"✓ Successfully generated {fmt} edition: {out_pdf.name} ({out_pdf.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
