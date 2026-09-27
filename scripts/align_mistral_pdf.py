#!/usr/bin/env python3
"""
AlexandriaSandwich — align_mistral_pdf.py

Automatic Token Alignment (Weg B):
Aligns Tesseract-generated OCR text layer inside an assembled sandwich PDF
with high-precision Mistral OCR text, and injects the corrected words
into the PDF text layer to produce an ultra-accurate Sandwich PDF (<job>.pathb.pdf).
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Import Path B PDF text stream replacement engine
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from pdf_text_correct import replace_in_pdf
except ImportError as exc:
    print(f"Error: could not import pdf_text_correct: {exc}", file=sys.stderr)
    sys.exit(2)


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [align_mistral_pdf] {msg}", file=sys.stderr)


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def clean_markdown(md_text: str) -> str:
    """Strip YAML frontmatter, markdown formatting, and noise from Mistral text."""
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            md_text = parts[2]
    # Code blocks
    md_text = re.sub(r"```.*?```", " ", md_text, flags=re.DOTALL)
    # Headings
    md_text = re.sub(r"^\s*#+\s*", " ", md_text, flags=re.MULTILINE)
    # Table syntax
    md_text = re.sub(r"\|", " ", md_text)
    # Bold / Italic
    md_text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", md_text)
    # Links
    md_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md_text)
    return md_text


def extract_pdf_pages_text(pdf_path: Path) -> List[str]:
    """Extract text page by page from PDF using pdftotext."""
    bin_path = shutil.which("pdftotext")
    if not bin_path:
        die("pdftotext not found (poppler-utils required)")
    proc = subprocess.run([bin_path, "-layout", str(pdf_path), "-"], capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"pdftotext failed on {pdf_path}: {proc.stderr.strip()}")
    pages = proc.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def load_mistral_pages(mistral_dir: Optional[Path], book_json: Optional[Path]) -> List[Tuple[str, str]]:
    """
    Load Mistral text per page.
    Returns list of (page_identifier, cleaned_text).
    """
    results: List[Tuple[str, str]] = []

    # Priority 1: book.json if available
    if book_json and book_json.is_file():
        try:
            data = json.loads(book_json.read_text(encoding="utf-8"))
            pages = data.get("pages", [])
            for p in pages:
                facs = p.get("facs", "")
                blocks = p.get("blocks", [])
                text_parts = [b.get("text", "") for b in blocks if b.get("text")]
                results.append((facs, clean_markdown(" ".join(text_parts))))
            if results:
                return results
        except Exception as e:
            log(f"warn: failed reading book.json: {e}")

    # Priority 2: *.mistral.md or *.md in mistral_dir
    if mistral_dir and mistral_dir.is_dir():
        md_files = sorted(mistral_dir.glob("*.mistral.md"))
        if not md_files:
            md_files = sorted(mistral_dir.glob("*.md"))
        for mf in md_files:
            try:
                content = mf.read_text(encoding="utf-8")
                results.append((mf.name, clean_markdown(content)))
            except Exception as e:
                log(f"warn: failed reading {mf}: {e}")

    return results


def align_tokens(tess_text: str, mistral_text: str, min_similarity: float = 0.5) -> Dict[str, str]:
    """Find token corrections by aligning Tesseract word stream with Mistral text."""
    tess_words = [w for w in re.split(r"\s+", tess_text) if w]
    mistral_words = [w for w in re.split(r"\s+", mistral_text) if w]

    mapping: Dict[str, str] = {}
    matcher = difflib.SequenceMatcher(None, tess_words, mistral_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            # 1-to-1 word replacement
            if i2 - i1 == 1 and j2 - j1 == 1:
                tw = tess_words[i1]
                mw = mistral_words[j1]
                tw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", tw)
                mw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", mw)

                if tw_clean and mw_clean and tw_clean != mw_clean:
                    sim = difflib.SequenceMatcher(None, tw_clean.lower(), mw_clean.lower()).ratio()
                    if sim >= min_similarity:
                        mapping[tw_clean] = mw_clean
                        if tw != mw:
                            mapping[tw] = mw
                elif tw != mw:
                    sim = difflib.SequenceMatcher(None, tw.lower(), mw.lower()).ratio()
                    if sim >= min_similarity:
                        mapping[tw] = mw

            # 1-to-many: Tesseract merged words (e.g. "indem" -> "in dem")
            elif i2 - i1 == 1 and (j2 - j1) in (2, 3):
                tw = tess_words[i1]
                mw_combined = " ".join(mistral_words[j1:j2])
                tw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", tw)
                mw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", mw_combined)
                if tw_clean.lower() == mw_clean.replace(" ", "").lower():
                    mapping[tw_clean] = mw_clean

    return mapping


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AlexandriaSandwich — Align Mistral OCR with Sandwich PDF text layer (Weg B)"
    )
    parser.add_argument("--pdf", type=Path, required=True, help="Input Sandwich PDF (<job>.sandwich.pdf)")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output aligned PDF (<job>.pathb.pdf)")
    parser.add_argument("--mistral-dir", type=Path, default=None, help="Directory containing *.mistral.md files")
    parser.add_argument("--book-json", type=Path, default=None, help="Optional consolidated book.json path")
    parser.add_argument("--corrections", type=Path, default=None, help="Path to write generated corrections JSON")
    parser.add_argument("--min-similarity", type=float, default=0.5, help="Minimum word similarity (0.0 - 1.0)")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args(argv)

    if not args.pdf.is_file():
        die(f"input PDF not found: {args.pdf}")

    log(f"reading Sandwich PDF: {args.pdf}")
    pdf_pages = extract_pdf_pages_text(args.pdf)
    log(f"PDF contains {len(pdf_pages)} page(s)")

    mistral_pages = load_mistral_pages(args.mistral_dir, args.book_json)
    log(f"loaded {len(mistral_pages)} Mistral text page(s)")

    if not mistral_pages:
        log("no Mistral pages found to align; copying input PDF to output")
        shutil.copy2(args.pdf, args.output)
        if args.json:
            print(json.dumps({"ok": True, "replacement_hits": 0, "corrections": 0}))
        return 0

    combined_mapping: Dict[str, str] = {}
    page_stats = []

    # Align each page
    total_pages = min(len(pdf_pages), len(mistral_pages))
    for idx in range(total_pages):
        tess_text = pdf_pages[idx]
        m_ident, m_text = mistral_pages[idx]
        page_map = align_tokens(tess_text, m_text, min_similarity=args.min_similarity)
        combined_mapping.update(page_map)
        page_stats.append({
            "page_index": idx + 1,
            "mistral_source": m_ident,
            "corrections_found": len(page_map),
        })

    log(f"total unique word corrections identified: {len(combined_mapping)}")

    if args.corrections:
        args.corrections.parent.mkdir(parents=True, exist_ok=True)
        args.corrections.write_text(
            json.dumps({"corrections": combined_mapping, "page_stats": page_stats}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        log(f"wrote corrections to {args.corrections}")

    if not combined_mapping:
        log("text already in perfect agreement; copying base PDF to output")
        shutil.copy2(args.pdf, args.output)
        summary = {"source": str(args.pdf), "output": str(args.output), "replacement_hits": 0, "streams_touched": []}
    else:
        log(f"injecting corrections into PDF text layer -> {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        summary = replace_in_pdf(args.pdf, args.output, combined_mapping)
        log(f"applied {summary.get('replacement_hits', 0)} replacement(s) across {len(summary.get('streams_touched', []))} stream(s)")

    result = {
        "ok": True,
        "pdf_source": str(args.pdf),
        "pdf_output": str(args.output),
        "total_corrections_identified": len(combined_mapping),
        "replacement_hits": summary.get("replacement_hits", 0),
        "streams_touched": len(summary.get("streams_touched", [])),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
