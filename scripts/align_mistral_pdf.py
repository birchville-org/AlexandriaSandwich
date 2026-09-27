#!/usr/bin/env python3
"""
AlexandriaSandwich — align_mistral_pdf.py

Automatic Token Alignment (Weg B):
Aligns Tesseract-generated OCR text layer inside an assembled sandwich PDF
with high-precision Mistral OCR text, and injects the corrected words
into the PDF text layer to produce an ultra-accurate Sandwich PDF (<job>.pathb.pdf).
Preserves pixel-exact bounding-box coordinates while correcting OCR errors and
stripping dot-line / noise hallucinations.
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
    import pikepdf
    from pikepdf import Pdf
    from pdf_text_correct import iter_stream_objects, replace_in_pdf, utf16be_hex_decode
except ImportError as exc:
    print(f"Error: could not import pikepdf or pdf_text_correct: {exc}", file=sys.stderr)
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


def extract_pdf_stream_tokens_per_page(pdf_path: Path) -> List[List[str]]:
    """
    Extract token strings directly from PDF Form XObjects page by page.
    This preserves the exact token sequence without column interleaving.
    """
    pdf = Pdf.open(pdf_path)
    pages_tokens: List[List[str]] = []

    for page_idx in range(len(pdf.pages)):
        page_prefix = f"page{page_idx}."
        tokens: List[str] = []
        for label, obj in iter_stream_objects(pdf):
            if label.startswith(page_prefix) and "xobject" in label:
                try:
                    data = obj.read_bytes()
                except Exception:
                    continue
                for m in re.finditer(rb"<([0-9A-Fa-f\s]+)>", data):
                    txt = utf16be_hex_decode(m.group(1))
                    if txt and txt.strip():
                        tokens.append(txt.strip())
        # If no XObject tokens found, fallback to page contents
        if not tokens:
            for label, obj in iter_stream_objects(pdf):
                if label.startswith(page_prefix):
                    try:
                        data = obj.read_bytes()
                    except Exception:
                        continue
                    for m in re.finditer(rb"<([0-9A-Fa-f\s]+)>", data):
                        txt = utf16be_hex_decode(m.group(1))
                        if txt and txt.strip():
                            tokens.append(txt.strip())
        pages_tokens.append(tokens)

    pdf.close()
    return pages_tokens


def load_mistral_pages(mistral_dir: Optional[Path], book_json: Optional[Path]) -> List[Tuple[str, str]]:
    """
    Load Mistral text per page.
    Returns list of (page_identifier, cleaned_text).
    """
    results: List[Tuple[str, str]] = []

    # Priority 1: *.mistral.md or *.md in mistral_dir (authoritative LLM output)
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
        if results:
            return results

    # Priority 2: book.json if available
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

    return results


def is_confirmed_noise(w: str) -> bool:
    """Detect repetitive OCR noise, dot runs, or symbol-only hallucinations."""
    clean = w.strip()
    if not clean:
        return True
    if re.search(r"(.)\1{2,}", clean):
        return True
    if ".." in clean:
        return True
    if re.match(r"^[.\-_+=,;:~*^/\\|<>{}\[\]\d\s]+$", clean):
        return True
    if re.search(r"[\u0900-\u097F]", clean) and re.search(r"[0-9]", clean) and len(clean) <= 5:
        return True
    return False


def align_page_tokens(
    stream_tokens: List[str], mistral_text: str, min_similarity: float = 0.5
) -> Dict[str, str]:
    """Find token corrections by aligning Tesseract stream tokens with Mistral text."""
    mistral_words = [w for w in re.split(r"\s+", mistral_text) if w]
    mapping: Dict[str, str] = {}

    # Pass 1: Dot-glued and leader line noise detection
    for tw in stream_tokens:
        # Glued word + dot run + number (e.g. Verbalstamm....69)
        m = re.match(r"^([^\.\s]+?)(\.{2,})([0-9ivxLCDM]+)$", tw, re.I)
        if m:
            prefix = m.group(1)
            num = m.group(3)
            best_sim, best_mw = 0.0, None
            for mw in mistral_words:
                sim = difflib.SequenceMatcher(None, prefix.lower(), mw.lower()).ratio()
                if sim > best_sim:
                    best_sim, best_mw = sim, mw
            if best_sim >= 0.6 and best_mw:
                mapping[tw] = f"{best_mw} {num}"
            else:
                mapping[tw] = num
            continue

        # Glued word + dot run + noise (e.g. Inhält.......aesssssseresessunennesennn)
        m2 = re.match(r"^([^\.\s]+?)(\.{2,}.*)$", tw)
        if m2:
            prefix = m2.group(1)
            best_sim, best_mw = 0.0, None
            for mw in mistral_words:
                sim = difflib.SequenceMatcher(None, prefix.lower(), mw.lower()).ratio()
                if sim > best_sim:
                    best_sim, best_mw = sim, mw
            if best_sim >= 0.6 and best_mw:
                mapping[tw] = best_mw
            else:
                mapping[tw] = ""
            continue

        # Standalone noise tokens
        if is_confirmed_noise(tw):
            sims = [difflib.SequenceMatcher(None, tw.lower(), mw.lower()).ratio() for mw in mistral_words]
            if max(sims or [0]) < 0.6:
                mapping[tw] = ""

    # Pass 2: Sequence matcher for word-level OCR correction
    matcher = difflib.SequenceMatcher(None, [t.lower() for t in stream_tokens], [m.lower() for m in mistral_words])

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        tw_sub = stream_tokens[i1:i2]
        mw_sub = mistral_words[j1:j2]

        if tag == "replace":
            # 1-to-1 word replacement
            if len(tw_sub) == 1 and len(mw_sub) == 1:
                tw = tw_sub[0]
                mw = mw_sub[0]
                tw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", tw)
                mw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", mw)

                if len(tw_clean) <= 2 or len(mw_clean) <= 2:
                    if tw_clean.lower() == mw_clean.lower() and tw_clean != mw_clean:
                        mapping[tw] = mw
                    continue

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

            # Many-to-few: Tesseract inserted extra noise tokens during a phrase or leader line
            elif len(tw_sub) > len(mw_sub):
                used_tw = set()
                for mw in mw_sub:
                    if re.match(r"^[.\-_+=,;:~*^]+$", mw):
                        continue
                    best_sim, best_idx = 0.0, -1
                    for idx, tw in enumerate(tw_sub):
                        if idx in used_tw:
                            continue
                        clean_tw = re.sub(r"^[^\w]+|[^\w]+$", "", tw)
                        clean_mw = re.sub(r"^[^\w]+|[^\w]+$", "", mw)
                        sim = difflib.SequenceMatcher(None, clean_tw.lower(), clean_mw.lower()).ratio()
                        if sim > best_sim:
                            best_sim, best_idx = sim, idx
                    if best_idx >= 0 and best_sim >= min_similarity:
                        mapping[tw_sub[best_idx]] = mw
                        used_tw.add(best_idx)
                for idx, tw in enumerate(tw_sub):
                    if idx not in used_tw:
                        sims = [difflib.SequenceMatcher(None, tw.lower(), w.lower()).ratio() for w in mistral_words]
                        if max(sims or [0]) < 0.6:
                            mapping[tw] = ""

            # 1-to-many: Tesseract merged multiple words
            elif len(tw_sub) < len(mw_sub) and len(tw_sub) == 1:
                mw_combined = " ".join(mw_sub)
                tw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", tw_sub[0])
                mw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", mw_combined)
                if tw_clean.lower() == mw_clean.replace(" ", "").lower():
                    mapping[tw_clean] = mw_combined

        elif tag == "delete":
            # Extra Tesseract tokens not present in Mistral transcription
            for tw in tw_sub:
                sims = [difflib.SequenceMatcher(None, tw.lower(), w.lower()).ratio() for w in mistral_words]
                if max(sims or [0]) < 0.6:
                    mapping[tw] = ""

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
    pdf_tokens_per_page = extract_pdf_stream_tokens_per_page(args.pdf)
    log(f"PDF contains {len(pdf_tokens_per_page)} page stream(s)")

    mistral_pages = load_mistral_pages(args.mistral_dir, args.book_json)
    log(f"loaded {len(mistral_pages)} Mistral text page(s)")

    if not mistral_pages:
        log("no Mistral pages found to align; copying input PDF to output")
        shutil.copy2(args.pdf, args.output)
        if args.json:
            print(json.dumps({"ok": True, "replacement_hits": 0, "corrections": 0}))
        return 0

    page_mappings: List[Dict[str, str]] = []
    page_stats = []
    total_corrections = 0

    total_pages = min(len(pdf_tokens_per_page), len(mistral_pages))
    for idx in range(total_pages):
        stream_tokens = pdf_tokens_per_page[idx]
        m_ident, m_text = mistral_pages[idx]
        page_map = align_page_tokens(stream_tokens, m_text, min_similarity=args.min_similarity)
        page_mappings.append(page_map)
        total_corrections += len(page_map)
        page_stats.append({
            "page_index": idx + 1,
            "mistral_source": m_ident,
            "stream_tokens": len(stream_tokens),
            "corrections_found": len(page_map),
        })

    log(f"total token corrections across {total_pages} page(s): {total_corrections}")

    if args.corrections:
        args.corrections.parent.mkdir(parents=True, exist_ok=True)
        args.corrections.write_text(
            json.dumps({"page_mappings": page_mappings, "page_stats": page_stats}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log(f"wrote corrections to {args.corrections}")

    if total_corrections == 0:
        log("text already in perfect agreement; copying base PDF to output")
        shutil.copy2(args.pdf, args.output)
        summary = {"source": str(args.pdf), "output": str(args.output), "replacement_hits": 0, "streams_touched": []}
    else:
        log(f"injecting per-page corrections into PDF text layer -> {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        summary = replace_in_pdf(args.pdf, args.output, page_mappings)
        log(
            f"applied {summary.get('replacement_hits', 0)} replacement(s) across {len(summary.get('streams_touched', []))} stream(s)"
        )

    result = {
        "ok": True,
        "pdf_source": str(args.pdf),
        "pdf_output": str(args.output),
        "total_corrections_identified": total_corrections,
        "replacement_hits": summary.get("replacement_hits", 0),
        "streams_touched": len(summary.get("streams_touched", [])),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
