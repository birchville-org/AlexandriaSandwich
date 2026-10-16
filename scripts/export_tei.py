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


def resolve_iiif_facs(
    p_num_int: Optional[int],
    current_facs: str,
    iiif_pages_map: Dict[str, str],
    iiif_template: str,
) -> str:
    """Resolve full IIIF image URL if available, else retain current facs."""
    if current_facs.startswith("http://") or current_facs.startswith("https://"):
        return current_facs

    if p_num_int is not None:
        # Check in iiif_pages_map by number string or padded string
        for k in (str(p_num_int), f"{p_num_int:04d}", f"{p_num_int:08d}", f"{p_num_int:09d}"):
            if k in iiif_pages_map and iiif_pages_map[k]:
                return iiif_pages_map[k]

        if iiif_template:
            tpl = iiif_template
            tpl = tpl.replace("{page}", str(p_num_int))
            tpl = tpl.replace("{p}", str(p_num_int))
            tpl = re.sub(r"\{p:0?(\d+)d\}", lambda m: f"{p_num_int:0{int(m.group(1))}d}", tpl)
            tpl = re.sub(r"\{page:0?(\d+)d\}", lambda m: f"{p_num_int:0{int(m.group(1))}d}", tpl)
            return tpl

    return current_facs


def build_tei_tree(
    book_data: Dict[str, Any],
    iiif_pages_map: Optional[Dict[str, str]] = None,
    job_cfg: Optional[Dict[str, Any]] = None,
) -> ET.Element:
    """Build a TEI-P5 XML ElementTree from book.json dictionary."""
    meta = book_data.get("metadata", {})
    cfg = job_cfg or {}
    job_name = meta.get("job") or cfg.get("job", "unknown_job")
    title_text = meta.get("title") or cfg.get("title", job_name)
    author_text = meta.get("author") or cfg.get("author", "Alexandria Archive")
    lang_text = meta.get("language") or cfg.get("lang", "deu+eng")
    gen_date = meta.get("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())

    iiif_manifest = meta.get("iiif_manifest") or cfg.get("iiif_manifest", "")
    iiif_template = meta.get("iiif_template") or cfg.get("iiif_template", "")
    pages_map = iiif_pages_map or {}

    tei = ET.Element(f"{{{TEI_NS}}}TEI")

    # 1. <teiHeader>
    header = ET.SubElement(tei, f"{{{TEI_NS}}}teiHeader")
    
    file_desc = ET.SubElement(header, f"{{{TEI_NS}}}fileDesc")
    title_stmt = ET.SubElement(file_desc, f"{{{TEI_NS}}}titleStmt")
    t = ET.SubElement(title_stmt, f"{{{TEI_NS}}}title")
    t.text = title_text
    a = ET.SubElement(title_stmt, f"{{{TEI_NS}}}author")
    a.text = author_text
    editor_val = meta.get("editor") or cfg.get("editor")
    if editor_val:
        ed = ET.SubElement(title_stmt, f"{{{TEI_NS}}}editor")
        ed.text = str(editor_val)

    pub_stmt = ET.SubElement(file_desc, f"{{{TEI_NS}}}publicationStmt")
    p_pub = ET.SubElement(pub_stmt, f"{{{TEI_NS}}}p")
    p_pub.text = f"Digitized and structured via AlexandriaSandwich pipeline on {gen_date}."

    source_desc = ET.SubElement(file_desc, f"{{{TEI_NS}}}sourceDesc")
    publisher_val = meta.get("publisher") or cfg.get("publisher")
    year_val = meta.get("year") or cfg.get("year")
    
    if publisher_val or year_val or editor_val or iiif_manifest:
        bibl = ET.SubElement(source_desc, f"{{{TEI_NS}}}bibl")
        b_author = ET.SubElement(bibl, f"{{{TEI_NS}}}author")
        b_author.text = author_text
        b_title = ET.SubElement(bibl, f"{{{TEI_NS}}}title")
        b_title.text = title_text
        if editor_val:
            b_ed = ET.SubElement(bibl, f"{{{TEI_NS}}}editor")
            b_ed.text = str(editor_val)
        if publisher_val:
            b_pub = ET.SubElement(bibl, f"{{{TEI_NS}}}publisher")
            b_pub.text = str(publisher_val)
        if year_val:
            b_date = ET.SubElement(bibl, f"{{{TEI_NS}}}date")
            b_date.text = str(year_val)
        if iiif_manifest:
            ref_mani = ET.SubElement(bibl, f"{{{TEI_NS}}}ref", {"target": iiif_manifest, "type": "iiif-manifest"})
            ref_mani.text = "IIIF Presentation Manifest"
    else:
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

    for idx, page in enumerate(pages, start=1):
        raw_p_num = page.get("page_num", idx)
        p_num = str(raw_p_num)
        p_num_int = int(raw_p_num) if str(raw_p_num).isdigit() else idx
        facs_raw = page.get("facs") or page.get("iiif_url", "")
        facs = resolve_iiif_facs(p_num_int, facs_raw, pages_map, iiif_template)
        
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


def load_iiif_pages(pages_path: Optional[Path]) -> Dict[str, str]:
    """Parse iiif_pages.json into a lookup dictionary of page number -> image_url."""
    if not pages_path or not pages_path.is_file():
        return {}
    try:
        with open(pages_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pages_map = {}
        if isinstance(data, list):
            for i, item in enumerate(data, start=1):
                url = item.get("image_url") or item.get("url") or ""
                p_num = str(item.get("page_num", i))
                if url:
                    pages_map[p_num] = url
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    pages_map[str(k)] = v
                elif isinstance(v, dict):
                    url = v.get("image_url") or v.get("url") or ""
                    if url:
                        pages_map[str(k)] = url
        return pages_map
    except Exception as e:
        log(f"Warning: could not parse iiif_pages {pages_path}: {e}")
        return {}


def export_tei(
    job_name: str,
    input_file: Path,
    output_file: Path,
    config_file: Optional[Path] = None,
    iiif_pages_file: Optional[Path] = None,
) -> Path:
    """Generate TEI-P5 XML file from book.json."""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(input_file, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    # Resolve job config
    job_cfg: Dict[str, Any] = {}
    if config_file and config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                job_cfg = json.load(f)
        except Exception:
            pass

    # Resolve iiif_pages
    iiif_pages_map = load_iiif_pages(iiif_pages_file)

    tei_elem = build_tei_tree(book_data, iiif_pages_map=iiif_pages_map, job_cfg=job_cfg)
    pretty_xml = prettify_xml(tei_elem)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    log(f"Generated standard TEI-P5 XML ({output_file.stat().st_size} bytes): {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Export AlexandriaSandwich book.json to standard TEI-P5 XML")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. e2e_m1)")
    parser.add_argument("--input", "-i", help="Path to book.json (default: /data/output/<job>/book.json)")
    parser.add_argument("--output", "-o", help="Path to output TEI XML (default: /data/output/<job>/<job>.tei.xml)")
    parser.add_argument("--config", "-c", help="Path to job.config.json")
    parser.add_argument("--iiif-pages", help="Path to iiif_pages.json")

    args = parser.parse_args()

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and Path("data").exists():
        data_dir = Path("data").resolve()

    cand_input = data_dir / "output" / args.job / "book.json"
    input_file = Path(args.input) if args.input else (cand_input if cand_input.exists() else data_dir / "output" / "books" / args.job / "book.json")
    output_file = Path(args.output) if args.output else data_dir / "output" / args.job / f"{args.job}.tei.xml"

    # Search for job.config.json if not provided
    config_file = Path(args.config) if args.config else None
    if not config_file:
        for cand_cfg in (
            data_dir / "input" / args.job / "job.config.json",
            data_dir / "output" / args.job / "job.config.json",
        ):
            if cand_cfg.is_file():
                config_file = cand_cfg
                break

    # Search for iiif_pages.json if not provided
    iiif_pages_file = Path(args.iiif_pages) if args.iiif_pages else None
    if not iiif_pages_file:
        for cand_iiif in (
            data_dir / "input" / args.job / "iiif_pages.json",
            data_dir / "processing" / args.job / "iiif_pages.json",
            data_dir / "output" / args.job / "iiif_pages.json",
        ):
            if cand_iiif.is_file():
                iiif_pages_file = cand_iiif
                break

    export_tei(
        job_name=args.job,
        input_file=input_file,
        output_file=output_file,
        config_file=config_file,
        iiif_pages_file=iiif_pages_file,
    )


if __name__ == "__main__":
    main()

