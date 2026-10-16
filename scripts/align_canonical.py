#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/align_canonical.py

Universal Canonical Alignment Engine.
Aligns extracted OCR text (from book.json or Markdown pages) against canonical
scholarly ground-truth databases (e.g. Aṣṭādhyāyī Sūtrapāṭha, Pāṇinīya-Dhātupāṭha,
Vedic indices, or dictionary headword registries).

Features:
- Sequential tracking and auto-correction of misrecognized numbering
- Multi-script digit support (Devanāgarī, Telugu, Gujarati, Arabic)
- Fuzzy and exact string matching on Sanskrit Devanāgarī and IAST
- Strips OCR boilerplates and stray script drift
- Outputs a schema-compliant canonical aligned master JSON
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def log(msg: str):
    print(f"[{time.strftime('%X')}] [align_canonical] {msg}", file=sys.stderr)


DIGIT_MAP = {
    # Devanagari
    "०": 0, "१": 1, "२": 2, "३": 3, "४": 4, "५": 5, "६": 6, "७": 7, "८": 8, "९": 9,
    # Telugu
    "౦": 0, "౧": 1, "౨": 2, "౩": 3, "౪": 4, "౫": 5, "౬": 6, "౭": 7, "౮": 8, "౯": 9,
    # Gujarati
    "૦": 0, "૧": 1, "૨": 2, "૩": 3, "૪": 4, "૫": 5, "૬": 6, "૭": 7, "૮": 8, "૯": 9,
}

PAT_SUTRA_DELIM = re.compile(r"(?:[॥|]{1,2}\s*[^॥|\n]{1,8}\s*[॥|]{1,2}|[\d/०-९౦-౯૦-૯]+\s*[॥|]{2})")
PAT_SECTION_REF = re.compile(r"\b(\d{1,2})\s*[,.]\s*(\d{1,2})\s*[,.]\s*(\d{1,3})\b")
PAT_ITEM_NUM = re.compile(r"^\s*([०-९౦-౯૦-૯\d]+)\s*[.)॥|]")

BOILERPLATE_PATTERNS = [
    re.compile(r"universit[äa]ts[-\s]*bibliothek\s+heidelberg", re.IGNORECASE),
    re.compile(r"badische\s+landesbibliothek", re.IGNORECASE),
    re.compile(r"bayerische\s+staatsbibliothek", re.IGNORECASE),
    re.compile(r"staatsbibliothek\s+zu\s+berlin", re.IGNORECASE),
    re.compile(r"digi\.ub\.uni-heidelberg\.de", re.IGNORECASE),
    re.compile(r"gef[öo]rdert\s+durch", re.IGNORECASE),
    re.compile(r"baden-w[üu]rttemberg", re.IGNORECASE),
    re.compile(r"^\[LOGO\]", re.IGNORECASE),
    re.compile(r"©\s*universit[äa]tsbibliothek", re.IGNORECASE),
]

ROGUE_SCRIPTS_PATTERN = re.compile(r"[\u0590-\u05FF\u0C00-\u0C7F]+")


def parse_multiscript_num(s: str) -> Optional[int]:
    """Parse number containing Devanāgarī, Telugu, Gujarati or Arabic digits."""
    s = s.strip()
    res = 0
    found = False
    for ch in s:
        if ch in DIGIT_MAP:
            res = res * 10 + DIGIT_MAP[ch]
            found = True
        elif ch.isdigit():
            res = res * 10 + int(ch)
            found = True
    return res if found else None


def clean_text_block(text: str) -> str:
    """Strip boilerplates and rogue script drift."""
    lines = text.splitlines()
    clean_lines = []
    for l in lines:
        stripped = l.strip()
        if not stripped:
            continue
        if any(p.search(stripped) for p in BOILERPLATE_PATTERNS):
            continue
        # Strip rogue characters
        cleaned_l = ROGUE_SCRIPTS_PATTERN.sub("", stripped).strip()
        if cleaned_l:
            clean_lines.append(cleaned_l)
    return "\n".join(clean_lines)


def load_canonical_reference(ref_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Load canonical reference JSON (supports list or dict structure).
    Returns (ordered_entries, lookup_map).
    """
    if not ref_path.is_file():
        raise FileNotFoundError(f"Canonical reference file not found: {ref_path}")

    with open(ref_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ordered: List[Dict[str, Any]] = []
    lookup: Dict[str, Dict[str, Any]] = {}

    if isinstance(data, list):
        ordered = data
        for item in data:
            for k in ("ref", "id", "sutra", "dhatu", "code"):
                if k in item and item[k]:
                    lookup[str(item[k])] = item
    elif isinstance(data, dict):
        # Could be {"sutras": [...]} or {"entries": [...]} or a map {"1.1.1": {...}}
        if "sutras" in data and isinstance(data["sutras"], list):
            ordered = data["sutras"]
            for item in ordered:
                if "ref" in item:
                    lookup[str(item["ref"])] = item
        elif "entries" in data and isinstance(data["entries"], list):
            ordered = data["entries"]
            for item in ordered:
                for k in ("ref", "id", "sutra", "dhatu"):
                    if k in item and item[k]:
                        lookup[str(item[k])] = item
        else:
            for k, v in data.items():
                if isinstance(v, dict):
                    v_copy = dict(v)
                    v_copy.setdefault("ref", str(k))
                    ordered.append(v_copy)
                    lookup[str(k)] = v_copy

    log(f"Loaded {len(ordered)} canonical reference item(s) from {ref_path.name}")
    return ordered, lookup


def string_similarity(a: str, b: str) -> float:
    """Compute normalized sequence similarity ratio."""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def align_book(
    book_data: Dict[str, Any],
    canonical_entries: List[Dict[str, Any]],
    canonical_lookup: Dict[str, Dict[str, Any]],
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Align book.json content against canonical references.
    """
    pages = book_data.get("pages", [])
    meta = book_data.get("metadata", {})
    
    aligned_results: List[Dict[str, Any]] = []
    matched_refs = set()

    current_ref_idx = 0
    total_refs = len(canonical_entries)

    for page in pages:
        p_num = page.get("page_num", 1)
        facs_url = page.get("facs") or page.get("iiif_url", "")
        blocks = page.get("blocks", [])

        current_heading = ""
        current_body: List[str] = []

        def flush_entry():
            nonlocal current_heading, current_body, current_ref_idx
            if not current_heading and not current_body:
                return

            body_str = clean_text_block("\n".join(current_body))
            h_clean = clean_text_block(current_heading)

            matched_item = None
            matched_key = ""

            # 1. Direct regex match on 3-tier reference (e.g. 1.1.1)
            m_sec = PAT_SECTION_REF.search(h_clean) or PAT_SECTION_REF.search(body_str[:120])
            if m_sec:
                cand_key = f"{int(m_sec.group(1))}.{int(m_sec.group(2))}.{int(m_sec.group(3))}"
                if cand_key in canonical_lookup:
                    matched_item = canonical_lookup[cand_key]
                    matched_key = cand_key

            # 2. Sequential pointer match
            if not matched_item and current_ref_idx < total_refs:
                cand = canonical_entries[current_ref_idx]
                target_str = cand.get("devanagari") or cand.get("dhatu") or cand.get("text") or ""
                if target_str and string_similarity(h_clean, target_str) >= threshold:
                    matched_item = cand
                    matched_key = str(cand.get("ref") or cand.get("id") or current_ref_idx)

            if matched_item:
                matched_refs.add(matched_key)
                # Advance sequential cursor
                try:
                    idx_in_ordered = canonical_entries.index(matched_item)
                    current_ref_idx = idx_in_ordered + 1
                except ValueError:
                    pass

                entry_record = {
                    "ref": matched_key,
                    "page": p_num,
                    "facs": facs_url,
                    "canonical": matched_item,
                    "ocr_heading": h_clean,
                    "ocr_body": body_str,
                }
                aligned_results.append(entry_record)

            current_heading = ""
            current_body = []

        for b in blocks:
            b_type = b.get("type", "p")
            text = b.get("text", "").strip()
            if not text:
                continue

            if b_type.startswith("h") or PAT_SUTRA_DELIM.search(text):
                flush_entry()
                current_heading = text
            else:
                current_body.append(text)

        flush_entry()

    coverage_pct = round((len(matched_refs) / total_refs * 100), 2) if total_refs > 0 else 0.0

    aligned_dataset = {
        "metadata": {
            "job": meta.get("job", "unknown_job"),
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "total_canonical_references": total_refs,
            "matched_references": len(matched_refs),
            "coverage_percent": coverage_pct,
            "aligned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pipeline": "AlexandriaSandwich",
        },
        "aligned_entries": aligned_results,
    }

    log(f"Alignment complete: {len(matched_refs)}/{total_refs} matched ({coverage_pct}% coverage)")
    return aligned_dataset


def main():
    parser = argparse.ArgumentParser(description="Align AlexandriaSandwich book content with canonical Ground Truth")
    parser.add_argument("--job", "-j", required=True, help="Job name (e.g. boethlingk1887)")
    parser.add_argument("--input", "-i", help="Path to book.json")
    parser.add_argument("--reference", "-r", required=True, help="Path to canonical reference JSON")
    parser.add_argument("--output", "-o", help="Path to output aligned master JSON")
    parser.add_argument("--threshold", type=float, default=0.50, help="Fuzzy match similarity threshold (0.0 - 1.0)")

    args = parser.parse_args()

    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    if not data_dir.exists() and Path("data").exists():
        data_dir = Path("data").resolve()

    input_file = Path(args.input) if args.input else data_dir / "output" / args.job / "book.json"
    ref_file = Path(args.reference)
    output_file = Path(args.output) if args.output else data_dir / "output" / args.job / f"{args.job}.canonical_aligned.json"

    if not input_file.is_file():
        log(f"Error: book.json not found: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    entries, lookup = load_canonical_reference(ref_file)
    aligned_data = align_book(book_data, entries, lookup, threshold=args.threshold)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(aligned_data, f, indent=2, ensure_ascii=False)

    log(f"Saved canonical aligned dataset ({output_file.stat().st_size} bytes): {output_file}")


if __name__ == "__main__":
    main()
