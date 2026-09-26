#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/consolidate_book.py
Consolidates per-page OCR outputs (hOCR, Mistral Markdown, or corrected text)
into a unified, structured book representation:
  1. data/output/books/<job>/book.json (structured AST with metadata, pages, blocks)
  2. data/output/books/<job>/book.md (clean Markdown with YAML frontmatter)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [consolidate_book] {msg}", file=sys.stderr)


def parse_hocr_page(hocr_path: Path) -> Dict[str, Any]:
    """Parse hOCR file and extract page geometry and structural blocks."""
    tree = ET.parse(hocr_path)
    root = tree.getroot()
    # Handle XHTML namespace if present
    ns = {"html": "http://www.w3.org/1999/xhtml"} if "http://www.w3.org/1999/xhtml" in root.tag else {}
    
    def find_all(tag: str):
        if ns:
            return root.findall(f".//html:{tag}", ns)
        return root.findall(f".//{tag}")

    pages = find_all("div")
    page_div = None
    for d in pages:
        if "ocr_page" in d.get("class", ""):
            page_div = d
            break

    facs_img = ""
    page_bbox = [0, 0, 0, 0]
    if page_div is not None:
        title = page_div.get("title", "")
        m_img = re.search(r'image\s+"([^"]+)"', title)
        if m_img:
            facs_img = Path(m_img.group(1)).name
        m_box = re.search(r'bbox\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', title)
        if m_box:
            page_bbox = [int(g) for g in m_box.groups()]

    blocks = []
    # Find all paragraph containers
    p_nodes = find_all("p")
    for p in p_nodes:
        if "ocr_par" in p.get("class", ""):
            p_text = " ".join("".join(p.itertext()).split()).strip()
            if not p_text:
                continue
            
            p_box = [0, 0, 0, 0]
            title = p.get("title", "")
            m_box = re.search(r'bbox\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', title)
            if m_box:
                p_box = [int(g) for g in m_box.groups()]
            
            blocks.append({
                "type": "p",
                "text": p_text,
                "bbox": p_box
            })

    # If no ocr_par found, fallback to full text
    if not blocks:
        full_text = " ".join("".join(root.itertext()).split()).strip()
        if full_text:
            blocks.append({
                "type": "p",
                "text": full_text,
                "bbox": page_bbox
            })

    return {
        "facs": facs_img,
        "bbox": page_bbox,
        "blocks": blocks
    }


def parse_markdown_page(md_path: Path) -> Dict[str, Any]:
    """Parse a single page markdown file (e.g. from Mistral OCR)."""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks = []
    current_p: List[str] = []

    def flush_p():
        if current_p:
            p_text = " ".join(current_p).strip()
            if p_text:
                blocks.append({"type": "p", "text": p_text, "bbox": [0, 0, 0, 0]})
            current_p.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_p()
            continue
        
        # Check headings
        if stripped.startswith("#"):
            flush_p()
            m = re.match(r'^(#+)\s+(.+)$', stripped)
            if m:
                level = len(m.group(1))
                blocks.append({"type": f"h{level}", "text": m.group(2).strip(), "bbox": [0, 0, 0, 0]})
            else:
                blocks.append({"type": "h1", "text": stripped.lstrip("#").strip(), "bbox": [0, 0, 0, 0]})
        elif stripped.startswith("|") and stripped.endswith("|"):
            flush_p()
            blocks.append({"type": "table_row", "text": stripped, "bbox": [0, 0, 0, 0]})
        else:
            current_p.append(stripped)

    flush_p()
    return {
        "facs": md_path.stem.replace(".mistral", "") + ".png",
        "bbox": [0, 0, 0, 0],
        "blocks": blocks
    }


def clean_page_artifacts(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove repetitive running headers, footers and standalone page numbers
    from page boundaries.
    """
    for page in pages:
        cleaned_blocks = []
        num_blocks = len(page["blocks"])
        for idx, block in enumerate(page["blocks"]):
            text = block["text"].strip()
            
            # Check if block is a standalone page number (e.g., "12", "- 12 -", "[12]")
            is_standalone_page_no = bool(re.match(r'^[-–—\[\(]?\s*\d{1,4}\s*[-–—\]\)]?$', text))
            
            # If it's near the top (first or second block) or near the bottom (last or second-to-last block), strip it
            if is_standalone_page_no and (idx <= 1 or idx >= max(0, num_blocks - 2)):
                continue
            
            cleaned_blocks.append(block)
        page["blocks"] = cleaned_blocks
    return pages


def consolidate_job(
    job_name: str,
    input_dir: Path,
    output_dir: Path,
    title: Optional[str] = None,
    author: Optional[str] = None,
    language: str = "deu+eng"
) -> Dict[str, Any]:
    """Consolidate OCR files into book.json and book.md."""
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_title = title or job_name.replace("_", " ").title()
    doc_author = author or "Alexandria Archive"
    
    # 1. Discover page files
    # Priority:
    # a) Corrected hOCR (*.corrected.hocr)
    # b) Standard hOCR (*.hocr)
    # c) Mistral Markdown (*.mistral.md / *.md)
    # d) Plain text (*.txt)
    
    all_hocr = list(input_dir.glob("*.hocr"))
    md_files = sorted(input_dir.glob("*.mistral.md"))
    if not md_files:
        md_files = sorted(input_dir.glob("*.md"))

    pages_data = []

    if all_hocr:
        # Group by page stem, prefer .corrected.hocr over .hocr
        page_map: Dict[str, Path] = {}
        for f in all_hocr:
            if f.name.endswith(".corrected.hocr"):
                base = f.name[:-15]
                page_map[base] = f
            elif f.name.endswith(".hocr"):
                base = f.name[:-5]
                if base not in page_map:
                    page_map[base] = f

        sorted_hocr = [page_map[k] for k in sorted(page_map.keys())]
        log(f"Found {len(sorted_hocr)} hOCR pages for job '{job_name}'")
        for idx, hocr in enumerate(sorted_hocr, start=1):
            p = parse_hocr_page(hocr)
            p["page_num"] = idx
            if not p["facs"]:
                p["facs"] = hocr.name.replace(".corrected.hocr", ".png").replace(".hocr", ".png")
            pages_data.append(p)
    elif md_files:
        log(f"Found {len(md_files)} Markdown pages for job '{job_name}'")
        for idx, md in enumerate(md_files, start=1):
            p = parse_markdown_page(md)
            p["page_num"] = idx
            pages_data.append(p)
    else:
        # Check if single all-pages markdown or txt exists
        single_md = input_dir / f"{job_name}.mistral.md"
        if single_md.exists():
            p = parse_markdown_page(single_md)
            p["page_num"] = 1
            pages_data.append(p)
        else:
            txt_files = sorted(input_dir.glob("*.txt"))
            if txt_files:
                log(f"Falling back to {len(txt_files)} plain text files")
                for idx, txt in enumerate(txt_files, start=1):
                    content = txt.read_text(encoding="utf-8").strip()
                    pages_data.append({
                        "page_num": idx,
                        "facs": txt.stem + ".png",
                        "bbox": [0, 0, 0, 0],
                        "blocks": [{"type": "p", "text": content, "bbox": [0, 0, 0, 0]}] if content else []
                    })
            else:
                log(f"Warning: No OCR page artifacts found in {input_dir}")

    # 2. Filter artifacts (running headers/footers)
    pages_data = clean_page_artifacts(pages_data)

    # 3. Build book structure
    book_data = {
        "metadata": {
            "job": job_name,
            "title": doc_title,
            "author": doc_author,
            "language": language,
            "page_count": len(pages_data),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pipeline": "AlexandriaSandwich"
        },
        "pages": pages_data
    }

    # 4. Write book.json
    json_path = output_dir / "book.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(book_data, f, indent=2, ensure_ascii=False)
    log(f"Wrote structured AST: {json_path}")

    # 5. Write book.md with YAML frontmatter
    md_path = output_dir / "book.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f"title: \"{doc_title}\"\n")
        f.write(f"author: \"{doc_author}\"\n")
        f.write(f"job: \"{job_name}\"\n")
        f.write(f"language: \"{language}\"\n")
        f.write(f"pages: {len(pages_data)}\n")
        f.write(f"date: \"{datetime.date.today().isoformat()}\"\n")
        f.write("---\n\n")

        for page in pages_data:
            p_num = page.get("page_num", 1)
            facs = page.get("facs", "")
            f.write(f"<!-- page: {p_num} facs: {facs} -->\n\n")
            
            for block in page.get("blocks", []):
                b_type = block.get("type", "p")
                text = block.get("text", "")
                if b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                    level = int(b_type[1])
                    f.write(f"{'#' * level} {text}\n\n")
                elif b_type == "table_row":
                    f.write(f"{text}\n")
                else:
                    f.write(f"{text}\n\n")
            f.write("\n")

    log(f"Wrote consolidated Markdown: {md_path}")
    return book_data


def main():
    parser = argparse.ArgumentParser(description="Consolidate OCR page outputs into unified book.json and book.md")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. e2e_m1)")
    parser.add_argument("--input-dir", "-i", help="Directory containing OCR page files (default: /data/processing/quality/<job> or /data/output/markdown/<job>)")
    parser.add_argument("--output-dir", "-o", help="Output directory (default: /data/output/books/<job>)")
    parser.add_argument("--title", help="Book title")
    parser.add_argument("--author", help="Book author")
    parser.add_argument("--lang", default="deu+eng", help="Document language")

    args = parser.parse_args()

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and Path("data").exists():
        data_dir = Path("data").resolve()

    if args.input_dir:
        input_dir = Path(args.input_dir)
    else:
        # Try quality directory first, then markdown
        cand1 = data_dir / "processing" / "quality" / args.job
        cand2 = data_dir / "output" / "markdown" / args.job
        if cand1.exists() and any(cand1.glob("*.hocr")):
            input_dir = cand1
        elif cand2.exists() and any(cand2.glob("*.md")):
            input_dir = cand2
        else:
            input_dir = cand1

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = data_dir / "output" / "books" / args.job

    consolidate_job(
        job_name=args.job,
        input_dir=input_dir,
        output_dir=output_dir,
        title=args.title,
        author=args.author,
        language=args.lang
    )


if __name__ == "__main__":
    main()
