#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/export_tei.py
Exports structured book data (book.json) into standardized TEI-P5 XML (Artifact 1).
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [export_tei] {msg}", file=sys.stderr)


TEI_NS = "http://www.tei-c.org/ns/1.0"
ET.register_namespace("", TEI_NS)


def build_tei_tree(book_data: Dict[str, Any]) -> ET.Element:
    """Build a TEI-P5 XML ElementTree from book.json dictionary."""
    meta = book_data.get("metadata", {})
    job_name = meta.get("job", "unknown_job")
    title_text = meta.get("title", job_name)
    author_text = meta.get("author", "Alexandria Archive")
    lang_text = meta.get("language", "deu+eng")
    gen_date = meta.get("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())

    tei = ET.Element(f"{{{TEI_NS}}}TEI")

    # 1. <teiHeader>
    header = ET.SubElement(tei, f"{{{TEI_NS}}}teiHeader")
    
    file_desc = ET.SubElement(header, f"{{{TEI_NS}}}fileDesc")
    title_stmt = ET.SubElement(file_desc, f"{{{TEI_NS}}}titleStmt")
    t = ET.SubElement(title_stmt, f"{{{TEI_NS}}}title")
    t.text = title_text
    a = ET.SubElement(title_stmt, f"{{{TEI_NS}}}author")
    a.text = author_text

    pub_stmt = ET.SubElement(file_desc, f"{{{TEI_NS}}}publicationStmt")
    p_pub = ET.SubElement(pub_stmt, f"{{{TEI_NS}}}p")
    p_pub.text = f"Digitized and structured via AlexandriaSandwich pipeline on {gen_date}."

    source_desc = ET.SubElement(file_desc, f"{{{TEI_NS}}}sourceDesc")
    p_src = ET.SubElement(source_desc, f"{{{TEI_NS}}}p")
    p_src.text = f"Source scan facsimiles for job: {job_name} ({meta.get('page_count', 0)} pages)."

    profile_desc = ET.SubElement(header, f"{{{TEI_NS}}}profileDesc")
    lang_usage = ET.SubElement(profile_desc, f"{{{TEI_NS}}}langUsage")
    lang_elem = ET.SubElement(lang_usage, f"{{{TEI_NS}}}language", {"ident": lang_text})
    lang_elem.text = lang_text

    # 2. <text>
    text = ET.SubElement(tei, f"{{{TEI_NS}}}text")
    body = ET.SubElement(text, f"{{{TEI_NS}}}body")

    pages = book_data.get("pages", [])
    
    # We organize content into structural <div>
    current_div = ET.SubElement(body, f"{{{TEI_NS}}}div", {"type": "content"})

    for page in pages:
        p_num = str(page.get("page_num", ""))
        facs = page.get("facs", "")
        
        # <pb n="..." facs="..."/>
        pb_attrs = {}
        if p_num:
            pb_attrs["n"] = p_num
        if facs:
            pb_attrs["facs"] = facs
        ET.SubElement(current_div, f"{{{TEI_NS}}}pb", pb_attrs)

        for block in page.get("blocks", []):
            b_type = block.get("type", "p")
            b_text = block.get("text", "").strip()
            if not b_text:
                continue

            if b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                level = b_type[1]
                # Close current_div and open new div if top-level heading
                if level == "1" and len(list(current_div)) > 1:
                    current_div = ET.SubElement(body, f"{{{TEI_NS}}}div", {"type": "chapter"})
                head = ET.SubElement(current_div, f"{{{TEI_NS}}}head", {"level": level})
                head.text = b_text
            elif b_type == "table_row":
                p = ET.SubElement(current_div, f"{{{TEI_NS}}}p", {"rend": "table_row"})
                p.text = b_text
            else:
                p = ET.SubElement(current_div, f"{{{TEI_NS}}}p")
                p.text = b_text

    return tei


def prettify_xml(element: ET.Element) -> str:
    """Return pretty-printed XML string with XML declaration."""
    raw_xml = ET.tostring(element, encoding="utf-8")
    dom = xml.dom.minidom.parseString(raw_xml)
    return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def export_tei(
    job_name: str,
    input_file: Path,
    output_file: Path
) -> Path:
    """Generate TEI-P5 XML file from book.json."""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(input_file, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    tei_elem = build_tei_tree(book_data)
    pretty_xml = prettify_xml(tei_elem)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    log(f"Generated standard TEI-P5 XML ({output_file.stat().st_size} bytes): {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Export AlexandriaSandwich book.json to standard TEI-P5 XML")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. e2e_m1)")
    parser.add_argument("--input", "-i", help="Path to book.json (default: /data/output/books/<job>/book.json)")
    parser.add_argument("--output", "-o", help="Path to output TEI XML (default: /data/output/tei/<job>.tei.xml)")

    args = parser.parse_args()

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and Path("data").exists():
        data_dir = Path("data").resolve()

    input_file = Path(args.input) if args.input else data_dir / "output" / "books" / args.job / "book.json"
    output_file = Path(args.output) if args.output else data_dir / "output" / "tei" / f"{args.job}.tei.xml"

    export_tei(
        job_name=args.job,
        input_file=input_file,
        output_file=output_file
    )


if __name__ == "__main__":
    main()
