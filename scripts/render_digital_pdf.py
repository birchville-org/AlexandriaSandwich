#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/render_digital_pdf.py
Renders consolidated book structure (book.json / book.md) into a clean,
publication-grade digital vector-text PDF using Typst (Artifact 3).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [render_digital_pdf] {msg}", file=sys.stderr)


def escape_typst(text: str) -> str:
    """Escape special Typst syntax characters in plain text."""
    # Special characters in Typst markup: [ ] $ # _ * ` \ < > @
    # For body text, escaping backslash, brackets and hashes is primary.
    text = text.replace("\\", "\\\\")
    text = text.replace("[", "\\[").replace("]", "\\]")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("@", "\\@")
    return text


def build_typst_document(
    book_data: Dict[str, Any],
    template_path: str = "/templates/book.typ",
    paper: str = "a5"
) -> str:
    """Generate complete Typst source code from book dictionary."""
    meta = book_data.get("metadata", {})
    title = meta.get("title", "Untitled Book")
    author = meta.get("author", "Alexandria Archive")
    date_val = meta.get("generated_at", "")[:10]
    raw_lang = meta.get("language", "deu+eng")
    
    # Map OCR lang code to Typst language code (e.g. deu -> de, eng -> en, san -> sa)
    lang_map = {
        "deu": "de", "ger": "de", "eng": "en", "fra": "fr", "fre": "fr",
        "ita": "it", "spa": "es", "lat": "la", "san": "sa"
    }
    first_lang = raw_lang.split("+")[0].strip().lower()
    typst_lang = lang_map.get(first_lang, "de")

    lines = [
        f'#import "{template_path}": book',
        f'#show: book.with(',
        f'  title: "{escape_typst(title)}",',
        f'  author: "{escape_typst(author)}",',
        f'  date: "{date_val}",',
        f'  paper: "{paper}",',
        f'  lang: "{typst_lang}"',
        f')',
        ''
    ]

    pages = book_data.get("pages", [])
    for page in pages:
        p_num = page.get("page_num", 1)
        blocks = page.get("blocks", [])
        
        for block in blocks:
            b_type = block.get("type", "p")
            text = block.get("text", "").strip()
            if not text:
                continue

            if b_type.startswith("h") and len(b_type) == 2 and b_type[1].isdigit():
                level = int(b_type[1])
                # Typst headings: = Title, == Subtitle, etc.
                eqs = "=" * level
                lines.append(f"{eqs} {escape_typst(text)}")
                lines.append("")
            elif b_type == "table_row":
                # Render table row as monospace or raw
                lines.append(f"`{text}`")
                lines.append("")
            else:
                lines.append(escape_typst(text))
                lines.append("")

    return "\n".join(lines)


def render_pdf(
    job_name: str,
    input_file: Path,
    output_file: Path,
    project_root: Path,
    paper: str = "a5"
) -> Dict[str, Any]:
    """Compile Typst document into high-quality digital PDF."""
    start_time = time.time()
    
    # 1. Load book data
    if input_file.suffix == ".json":
        with open(input_file, "r", encoding="utf-8") as f:
            book_data = json.load(f)
    elif input_file.suffix == ".md":
        # Check if sibling book.json exists
        sibling_json = input_file.parent / "book.json"
        if sibling_json.exists():
            with open(sibling_json, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        else:
            # Fallback simple book structure
            book_data = {
                "metadata": {"job": job_name, "title": job_name},
                "pages": [{"page_num": 1, "blocks": [{"type": "p", "text": input_file.read_text(encoding="utf-8")}]}]
            }
    else:
        raise ValueError(f"Unsupported input file format: {input_file}")

    # 2. Generate Typst source
    template_file = (project_root / "templates" / "book.typ").resolve()
    if not template_file.exists():
        template_file = (Path(__file__).resolve().parent.parent / "templates" / "book.typ").resolve()
    typst_code = build_typst_document(book_data, template_path=str(template_file), paper=paper)

    # 3. Write temp .typ file in job directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_typ = output_file.parent / f"{job_name}.digital.typ"
    with open(temp_typ, "w", encoding="utf-8") as f:
        f.write(typst_code)

    # 4. Check for typst binary
    typst_cmd = shutil.which("typst")
    if not typst_cmd:
        # Check standard docker / linux install path
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

    return {
        "job": job_name,
        "digital_pdf": str(output_file),
        "size_bytes": pdf_size,
        "elapsed_sec": elapsed,
        "paper": paper
    }


def main():
    parser = argparse.ArgumentParser(description="Render consolidated book to publication-grade digital PDF via Typst")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. e2e_m1)")
    parser.add_argument("--input", "-i", help="Path to book.json or book.md (default: /data/output/books/<job>/book.json)")
    parser.add_argument("--output", "-o", help="Path to output PDF (default: /data/output/pdf/<job>.digital.pdf)")
    parser.add_argument("--paper", default="a5", help="Paper size (a5, a4, b5, etc.)")
    parser.add_argument("--root", help="Project root for Typst imports (default: repo root)")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    project_root = Path(args.root).resolve() if args.root else repo_root

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and (repo_root / "data").exists():
        data_dir = repo_root / "data"

    input_file = Path(args.input) if args.input else data_dir / "output" / "books" / args.job / "book.json"
    output_file = Path(args.output) if args.output else data_dir / "output" / "pdf" / f"{args.job}.digital.pdf"

    render_pdf(
        job_name=args.job,
        input_file=input_file,
        output_file=output_file,
        project_root=project_root,
        paper=args.paper
    )


if __name__ == "__main__":
    main()
