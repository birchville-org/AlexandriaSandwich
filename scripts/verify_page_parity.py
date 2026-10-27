#!/usr/bin/env python3
"""
AlexandriaSandwich - Verify Page Parity
Validates that each original historical page corresponds 1:1 to exactly one PDF page.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


def verify_page_parity(
    pdf_path: Path,
    pages_data: List[Dict[str, Any]],
    front_matter_pages: int = 5,
    page_num_key: str = "page_num",
    items_key: str = "sutras",
    ref_extractor: Optional[Callable[[Dict[str, Any]], str]] = None,
) -> bool:
    """Verifies that all expected items per page exist on the exact corresponding PDF page."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file {pdf_path} does not exist.", file=sys.stderr)
        return False

    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    print("=" * 70)
    print(f"Page Parity Check: {pdf_path.name}")
    print(f"Total PDF pages: {total_pages} | Front matter: {front_matter_pages} | Expected body pages: {len(pages_data)}")
    print("=" * 70)

    def default_ref(item: Dict[str, Any]) -> str:
        if "adhyaya" in item and "pada" in item and "sutra_num" in item:
            return f"{item['adhyaya']}, {item['pada']}, {item['sutra_num']}."
        return str(item.get("ref", ""))

    extractor = ref_extractor or default_ref
    overflows = 0

    for p_info in pages_data:
        orig_p = p_info[page_num_key]
        pdf_idx = front_matter_pages + (orig_p - 1)
        if pdf_idx >= total_pages:
            print(f"FAIL: Original page {orig_p} is beyond end of PDF ({pdf_idx} >= {total_pages})!")
            overflows += 1
            continue

        page_text = doc[pdf_idx].get_text()
        missing = []
        for item in p_info.get(items_key, []):
            ref_str = extractor(item)
            if ref_str and ref_str not in page_text:
                missing.append(ref_str)

        if missing:
            overflows += 1
            print(f"OVERFLOW on original page {orig_p} (PDF page {pdf_idx + 1}): Missing items: {missing}")

    doc.close()

    if overflows == 0:
        print("✓ PERFECT 1:1 PAGE PARITY: All historical pages match exactly 1 PDF page with 0 overflows.")
        print("=" * 70)
        return True
    else:
        print(f"FAIL: {overflows} page(s) with overflow or missing content.")
        print("=" * 70)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify 1:1 Page Parity for AlexandriaSandwich")
    parser.add_argument("pdf", type=Path, help="Path to compiled PDF")
    parser.add_argument("--data", type=Path, required=True, help="Path to page data JSON")
    parser.add_argument("--front-matter", type=int, default=5, help="Number of front matter pages before body page 1")
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as f:
        pages_data = json.load(f)

    success = verify_page_parity(args.pdf, pages_data, front_matter_pages=args.front_matter)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
