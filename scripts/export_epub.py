#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/export_epub.py
Exports consolidated book data (book.json / book.md) into a standardized,
reflowable EPUB 3 eBook with embedded Unicode fonts (Noto Serif Devanagari + Linux Libertine)
for philological and bilingual (Sanskrit / German / English) editions.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [export_epub] {msg}", file=sys.stderr)


# Known font locations on Linux / Docker / macOS
CANDIDATE_FONTS = {
    "noto_devanagari_regular": [
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifDevanagari-Regular.otf",
        "/System/Library/Fonts/Supplemental/NotoSerifDevanagari.ttc",
        "/Library/Fonts/NotoSerifDevanagari-Regular.ttf",
    ],
    "noto_devanagari_bold": [
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifDevanagari-Bold.otf",
        "/System/Library/Fonts/Supplemental/NotoSerifDevanagari.ttc",
        "/Library/Fonts/NotoSerifDevanagari-Bold.ttf",
    ],
    "linux_libertine_regular": [
        "/usr/share/fonts/opentype/linux-libertine/LinLibertine_R.otf",
        "/usr/share/fonts/truetype/linux-libertine/LinLibertine_R.ttf",
        "/Library/Fonts/LinLibertine_R.otf",
    ],
    "linux_libertine_bold": [
        "/usr/share/fonts/opentype/linux-libertine/LinLibertine_RB.otf",
        "/usr/share/fonts/truetype/linux-libertine/LinLibertine_RB.ttf",
        "/Library/Fonts/LinLibertine_RB.otf",
    ],
    "linux_libertine_italic": [
        "/usr/share/fonts/opentype/linux-libertine/LinLibertine_RI.otf",
        "/usr/share/fonts/truetype/linux-libertine/LinLibertine_RI.ttf",
        "/Library/Fonts/LinLibertine_RI.otf",
    ]
}


def find_font(key: str) -> Optional[Path]:
    for path_str in CANDIDATE_FONTS.get(key, []):
        p = Path(path_str)
        if p.exists() and p.is_file():
            return p
    return None


EPUB_CSS = """/* AlexandriaSandwich Universal Scholarly EPUB 3 Stylesheet */
@namespace epub "http://www.idpf.org/2007/ops";

@font-face {
    font-family: "Linux Libertine O";
    font-style: normal;
    font-weight: normal;
    src: url("../fonts/LinLibertine_R.otf") format("opentype"),
         url("../fonts/LinLibertine_R.ttf") format("truetype");
}
@font-face {
    font-family: "Linux Libertine O";
    font-style: normal;
    font-weight: bold;
    src: url("../fonts/LinLibertine_RB.otf") format("opentype"),
         url("../fonts/LinLibertine_RB.ttf") format("truetype");
}
@font-face {
    font-family: "Linux Libertine O";
    font-style: italic;
    font-weight: normal;
    src: url("../fonts/LinLibertine_RI.otf") format("opentype"),
         url("../fonts/LinLibertine_RI.ttf") format("truetype");
}
@font-face {
    font-family: "Noto Serif Devanagari";
    font-style: normal;
    font-weight: normal;
    src: url("../fonts/NotoSerifDevanagari-Regular.ttf") format("truetype"),
         url("../fonts/NotoSerifDevanagari-Regular.otf") format("opentype");
}
@font-face {
    font-family: "Noto Serif Devanagari";
    font-style: normal;
    font-weight: bold;
    src: url("../fonts/NotoSerifDevanagari-Bold.ttf") format("truetype"),
         url("../fonts/NotoSerifDevanagari-Bold.otf") format("opentype");
}

body {
    font-family: "Linux Libertine O", "Noto Serif Devanagari", "DejaVu Serif", serif;
    font-size: 1.05em;
    line-height: 1.6;
    margin: 5% 7%;
    text-align: justify;
    text-rendering: optimizeLegibility;
    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    hyphens: auto;
}

h1, h2, h3, h4 {
    font-family: "Linux Libertine O", "Noto Serif Devanagari", serif;
    font-weight: bold;
    line-height: 1.25;
    margin-top: 1.8em;
    margin-bottom: 0.8em;
    text-align: left;
    page-break-after: avoid;
    break-after: avoid;
}

h1 {
    font-size: 1.8em;
    text-align: center;
    margin-top: 2.5em;
    margin-bottom: 1.2em;
}

h2 {
    font-size: 1.4em;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 1.2em;
}

p {
    margin: 0;
    text-indent: 1.5em;
    orphans: 2;
    widows: 2;
}

p.first, h1 + p, h2 + p, h3 + p, div.table-wrap + p {
    text-indent: 0;
}

.title-page {
    text-align: center;
    margin-top: 25%;
    margin-bottom: 25%;
}

.title-page h1 {
    font-size: 2.2em;
    margin-bottom: 0.4em;
}

.title-page .author {
    font-size: 1.3em;
    font-style: italic;
    margin-top: 1.5em;
}

.title-page .publisher {
    font-size: 0.9em;
    color: #666;
    margin-top: 4em;
}

.pagebreak {
    display: block;
    page-break-before: always;
    break-before: page;
    margin-top: 2em;
    border-top: 1px dotted #ccc;
    font-size: 0.75em;
    color: #888;
    text-align: right;
    padding-top: 0.2em;
    margin-bottom: 1em;
}

.devanagari {
    font-family: "Noto Serif Devanagari", serif;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5em 0;
    font-size: 0.92em;
}

th, td {
    border: 1px solid #ddd;
    padding: 6px 10px;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #f7f7f7;
    font-weight: bold;
}

code, pre {
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 0.9em;
    background-color: #f5f5f5;
    padding: 2px 4px;
    border-radius: 3px;
}

pre {
    padding: 10px;
    overflow-x: auto;
    white-space: pre-wrap;
}
"""


def build_epub_package(
    book_data: Dict[str, Any],
    output_path: Path,
    job_name: str,
    cover_image: Optional[Path] = None
) -> Path:
    """Build standardized EPUB 3 file from book.json dictionary."""
    meta = book_data.get("metadata", {})
    title = meta.get("title", job_name)
    author = meta.get("author", "Alexandria Archive")
    lang_raw = meta.get("language", "deu+san")
    primary_lang = "de" if "deu" in lang_raw or "ger" in lang_raw else "en"
    if "san" in lang_raw and "deu" not in lang_raw:
        primary_lang = "sa"
    
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, f'alexandriasandwich.{job_name}')}"
    date_str = meta.get("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())[:10]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / f"_epub_build_{job_name}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        oebps = temp_dir / "OEBPS"
        meta_inf = temp_dir / "META-INF"
        text_dir = oebps / "text"
        styles_dir = oebps / "styles"
        fonts_dir = oebps / "fonts"
        images_dir = oebps / "images"

        for d in [meta_inf, text_dir, styles_dir, fonts_dir, images_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 1. mimetype
        with open(temp_dir / "mimetype", "w", encoding="utf-8") as f:
            f.write("application/epub+zip")

        # 2. META-INF/container.xml
        with open(meta_inf / "container.xml", "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""")

        # 3. Stylesheet
        with open(styles_dir / "stylesheet.css", "w", encoding="utf-8") as f:
            f.write(EPUB_CSS)

        # 4. Copy Fonts
        manifest_fonts = []
        for key, font_file in [
            ("noto_devanagari_regular", "NotoSerifDevanagari-Regular.ttf"),
            ("noto_devanagari_bold", "NotoSerifDevanagari-Bold.ttf"),
            ("linux_libertine_regular", "LinLibertine_R.otf"),
            ("linux_libertine_bold", "LinLibertine_RB.otf"),
            ("linux_libertine_italic", "LinLibertine_RI.otf"),
        ]:
            src = find_font(key)
            if src:
                dst = fonts_dir / font_file
                shutil.copy2(src, dst)
                mtype = "font/otf" if font_file.endswith(".otf") else "font/ttf"
                manifest_fonts.append((f"font_{key}", f"fonts/{font_file}", mtype))
                log(f"Embedded font {key} -> {font_file}")
            else:
                log(f"Optional font {key} not found on host, using system fallback")

        # 5. Build Content Sections & Chapters
        pages = book_data.get("pages", [])
        
        # Partition pages into chapters based on h1/h2 or groups of pages
        sections: List[Dict[str, Any]] = []
        current_section = {
            "id": "titlepage",
            "title": "Titel",
            "items": [
                f'<div class="title-page">',
                f'<h1>{html.escape(title)}</h1>',
                f'<div class="author">{html.escape(author)}</div>',
                f'<div class="publisher">AlexandriaSandwich Digital Edition • {date_str}</div>',
                f'</div>'
            ]
        }
        sections.append(current_section)

        section_idx = 1
        current_section = {
            "id": f"sec_{section_idx:03d}",
            "title": f"Kapitel 1",
            "items": []
        }
        sections.append(current_section)

        for page in pages:
            p_num = page.get("page_num", 1)
            blocks = page.get("blocks", [])
            
            current_section["items"].append(f'<div class="pagebreak" id="page-{p_num}">[Seite {p_num}]</div>')

            first_p_in_block = True
            for b in blocks:
                b_type = b.get("type", "p")
                raw_text = b.get("text", "").strip()
                if not raw_text:
                    continue

                esc_text = html.escape(raw_text)

                if b_type == "h1":
                    # New chapter section
                    section_idx += 1
                    current_section = {
                        "id": f"sec_{section_idx:03d}",
                        "title": raw_text,
                        "items": [f'<h1>{esc_text}</h1>']
                    }
                    sections.append(current_section)
                    first_p_in_block = True
                elif b_type == "h2":
                    current_section["items"].append(f'<h2>{esc_text}</h2>')
                    first_p_in_block = True
                elif b_type == "h3":
                    current_section["items"].append(f'<h3>{esc_text}</h3>')
                    first_p_in_block = True
                elif b_type == "table_row":
                    current_section["items"].append(f'<div class="table-wrap"><pre><code>{esc_text}</code></pre></div>')
                    first_p_in_block = True
                else:
                    p_cls = ' class="first"' if first_p_in_block else ''
                    current_section["items"].append(f'<p{p_cls}>{esc_text}</p>')
                    first_p_in_block = False

        # Filter empty sections
        valid_sections = [s for s in sections if s["items"]]

        # Write section XHTMLs
        manifest_text = []
        spine_items = []
        for s in valid_sections:
            sec_file = f"{s['id']}.xhtml"
            sec_path = text_dir / sec_file
            content_html = "\n  ".join(s["items"])
            xhtml_code = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{primary_lang}" lang="{primary_lang}">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(s['title'])}</title>
  <link rel="stylesheet" type="text/css" href="../styles/stylesheet.css"/>
</head>
<body>
  <section epub:type="chapter" role="doc-chapter">
  {content_html}
  </section>
</body>
</html>
"""
            with open(sec_path, "w", encoding="utf-8") as f:
                f.write(xhtml_code)

            item_id = s["id"]
            manifest_text.append((item_id, f"text/{sec_file}", "application/xhtml+xml"))
            spine_items.append(item_id)

        # 6. Navigation Document (nav.xhtml - EPUB 3 required)
        nav_entries = []
        for s in valid_sections:
            nav_entries.append(f'<li><a href="text/{s["id"]}.xhtml">{html.escape(s["title"])}</a></li>')
        nav_list = "\n      ".join(nav_entries)

        nav_code = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{primary_lang}" lang="{primary_lang}">
<head>
  <meta charset="utf-8"/>
  <title>Inhaltsverzeichnis</title>
  <link rel="stylesheet" type="text/css" href="styles/stylesheet.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc" role="doc-toc">
    <h1>Inhaltsverzeichnis</h1>
    <ol>
      {nav_list}
    </ol>
  </nav>
</body>
</html>
"""
        with open(oebps / "nav.xhtml", "w", encoding="utf-8") as f:
            f.write(nav_code)

        # 7. Legacy NCX (toc.ncx - EPUB 2 backward compatibility)
        ncx_points = []
        for i, s in enumerate(valid_sections, 1):
            ncx_points.append(f"""    <navPoint id="np_{i}" playOrder="{i}">
      <navLabel><text>{html.escape(s["title"])}</text></navLabel>
      <content src="text/{s["id"]}.xhtml"/>
    </navPoint>""")
        ncx_body = "\n".join(ncx_points)

        ncx_code = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.openmobilealliance.org/tech/DTD/ncx-2005-1.dtd" version="2005-1" xml:lang="{primary_lang}">
  <head>
    <meta name="dtb:uid" content="{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <docAuthor><text>{html.escape(author)}</text></docAuthor>
  <navMap>
{ncx_body}
  </navMap>
</ncx>
"""
        with open(oebps / "toc.ncx", "w", encoding="utf-8") as f:
            f.write(ncx_code)

        # 8. Content OPF (content.opf)
        manifest_entries = [
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
            '    <item id="css" href="styles/stylesheet.css" media-type="text/css"/>'
        ]
        for fid, fhref, fmtype in manifest_fonts:
            manifest_entries.append(f'    <item id="{fid}" href="{fhref}" media-type="{fmtype}"/>')
        for tid, thref, tmtype in manifest_text:
            manifest_entries.append(f'    <item id="{tid}" href="{thref}" media-type="{tmtype}"/>')

        manifest_str = "\n".join(manifest_entries)
        spine_str = "\n".join([f'    <itemref idref="{sid}"/>' for sid in spine_items])

        opf_code = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="{primary_lang}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{book_id}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(author)}</dc:creator>
    <dc:language>{primary_lang}</dc:language>
    <dc:date>{date_str}</dc:date>
    <dc:publisher>AlexandriaSandwich</dc:publisher>
    <meta property="dcterms:modified">{datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
  </metadata>
  <manifest>
{manifest_str}
  </manifest>
  <spine toc="ncx">
{spine_str}
  </spine>
</package>
"""
        with open(oebps / "content.opf", "w", encoding="utf-8") as f:
            f.write(opf_code)

        # 9. Pack ZIP Archive (mimetype MUST be first and stored uncompressed)
        if output_path.exists():
            output_path.unlink()

        with zipfile.ZipFile(output_path, "w") as zf:
            # First entry: mimetype (uncompressed)
            mime_path = temp_dir / "mimetype"
            zf.write(mime_path, "mimetype", compress_type=zipfile.ZIP_STORED)

            # All other files: deflated
            for root_dir, _, files in os.walk(temp_dir):
                for file_name in files:
                    full_p = Path(root_dir) / file_name
                    if full_p == mime_path:
                        continue
                    arcname = full_p.relative_to(temp_dir)
                    zf.write(full_p, str(arcname), compress_type=zipfile.ZIP_DEFLATED)

        size_kb = output_path.stat().st_size / 1024
        log(f"Successfully generated EPUB 3 ({size_kb:.1f} KB): {output_path}")
        return output_path

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Export AlexandriaSandwich book data to standardized EPUB 3")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. stenzler)")
    parser.add_argument("--input", "-i", help="Path to book.json (default: /data/output/books/<job>/book.json)")
    parser.add_argument("--output", "-o", help="Path to output EPUB (default: /data/output/books/<job>/<job>.epub)")
    parser.add_argument("--cover", help="Path to cover image")

    args = parser.parse_args()

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and Path("data").exists():
        data_dir = Path("data").resolve()

    input_file = Path(args.input) if args.input else data_dir / "output" / "books" / args.job / "book.json"
    output_file = Path(args.output) if args.output else data_dir / "output" / "books" / args.job / f"{args.job}.epub"

    if not input_file.exists():
        log(f"Input file not found: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    cover_p = Path(args.cover) if args.cover and Path(args.cover).exists() else None
    build_epub_package(book_data, output_file, args.job, cover_image=cover_p)


if __name__ == "__main__":
    main()
