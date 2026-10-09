#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/audit_digital_layout.py
Automated Optical & Vector Quality Auditor for Digital PDFs (Artifact 3).
Audits layout geometry, row clumping / collisions, font scaling, and page concordance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        print("Error: PyMuPDF is required. Please install via: pip install pymupdf", file=sys.stderr)
        sys.exit(2)


def audit_pdf_layout(
    pdf_path: Path,
    reference_pdf: Optional[Path] = None,
    collision_threshold: int = 12,
    min_width_ratio: float = 0.25,
    min_font_pt: float = 5.5,
) -> Dict[str, Any]:
    """
    Audits a digital PDF for visual layout glitches:
    - Text overlap collisions (rows collapsed on identical y-coordinate)
    - Narrow text column anomalies (e.g. single-word vertical threads)
    - Extreme font shrinkage (scale factor crushed text below readable threshold)
    - 1:1 page count concordance against reference PDF (if provided)
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)

    ref_pages = None
    if reference_pdf and reference_pdf.exists():
        ref_doc = pymupdf.open(reference_pdf)
        ref_pages = len(ref_doc)
        ref_doc.close()

    collision_pages: List[Dict[str, Any]] = []
    narrow_pages: List[Dict[str, Any]] = []
    extreme_font_pages: List[Dict[str, Any]] = []

    for pno in range(total_pages):
        page = doc[pno]
        rect = page.rect
        p_num = pno + 1

        words = page.get_text("words")
        blocks = page.get_text("blocks")

        # 1. Collision Check: detect physical text overlap (clashing words on same vertical band)
        y_buckets: Dict[float, List[Any]] = {}
        for w in words:
            b_y = round(w[1] / 1.5) * 1.5
            y_buckets.setdefault(b_y, []).append(w)

        clash_pairs = 0
        clash_y = 0.0
        clash_samples: List[str] = []
        for b_y, b_words in y_buckets.items():
            if len(b_words) < 2:
                continue
            b_words.sort(key=lambda w: w[0])
            for i in range(len(b_words) - 1):
                w1 = b_words[i]
                w2 = b_words[i + 1]
                overlap = min(w1[2], w2[2]) - max(w1[0], w2[0])
                if overlap > 3.0:
                    clash_pairs += 1
                    clash_y = b_y
                    if len(clash_samples) < 4:
                        clash_samples.append(f"{w1[4]} & {w2[4]}")

        if clash_pairs >= 2:
            collision_pages.append({
                "page": p_num,
                "clash_pairs": clash_pairs,
                "y": clash_y,
                "sample": ", ".join(clash_samples),
            })

        # 2. Narrow Column Check: detect text width span < 25% of printable width
        text_blocks = [b for b in blocks if len(b[4].strip()) > 8]
        if text_blocks and len(words) >= 25:
            min_x = min(b[0] for b in text_blocks)
            max_x = max(b[2] for b in text_blocks)
            w_span = max_x - min_x
            w_ratio = w_span / rect.width if rect.width > 0 else 1.0

            if w_ratio < min_width_ratio:
                narrow_pages.append({
                    "page": p_num,
                    "width_pt": round(w_span, 1),
                    "page_width_pt": round(rect.width, 1),
                    "width_ratio_pct": round(w_ratio * 100, 1),
                    "words_count": len(words),
                })

        # 3. Extreme Font Shrinkage Check: text scaled below readable threshold
        if len(words) >= 15:
            spans: List[float] = []
            page_dict = page.get_text("dict")
            for b in page_dict.get("blocks", []):
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        if len(s.get("text", "").strip()) > 0:
                            spans.append(s.get("size", 10.0))

            if spans:
                min_f = min(spans)
                if min_f < min_font_pt:
                    extreme_font_pages.append({
                        "page": p_num,
                        "min_font_pt": round(min_f, 1),
                        "words_count": len(words),
                    })

    doc.close()

    faulty_pages_set = {p["page"] for p in collision_pages} | {p["page"] for p in narrow_pages} | {p["page"] for p in extreme_font_pages}
    clean_pages_count = total_pages - len(faulty_pages_set)
    quality_score = round(clean_pages_count / total_pages * 100, 2) if total_pages > 0 else 100.0

    concordance_ok = (ref_pages is None) or (ref_pages == total_pages)

    return {
        "pdf": str(pdf_path),
        "total_pages": total_pages,
        "reference_pages": ref_pages,
        "concordance_ok": concordance_ok,
        "clean_pages": clean_pages_count,
        "quality_score_pct": quality_score,
        "collisions_count": len(collision_pages),
        "narrow_columns_count": len(narrow_pages),
        "extreme_font_count": len(extreme_font_pages),
        "issues": {
            "collisions": collision_pages,
            "narrow_columns": narrow_pages,
            "extreme_font": extreme_font_pages,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Audit digital PDF layout for collisions, squashed columns, and font anomalies")
    parser.add_argument("--pdf", "-p", required=True, help="Path to digital PDF to audit")
    parser.add_argument("--reference", "-r", help="Path to reference aligned/facsimile PDF")
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics")
    parser.add_argument("--threshold-collision", type=int, default=12, help="Word count threshold on same Y-bucket (default: 12)")
    args = parser.parse_args()

    pdf_p = Path(args.pdf)
    ref_p = Path(args.reference) if args.reference else None

    result = audit_pdf_layout(
        pdf_path=pdf_p,
        reference_pdf=ref_p,
        collision_threshold=args.threshold_collision,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("=" * 68)
    print(f"📖 Layout Audit Report: {pdf_p.name}")
    print("=" * 68)
    print(f"Total Pages:      {result['total_pages']}")
    if result['reference_pages'] is not None:
        status_c = "✅ Concordant" if result['concordance_ok'] else "❌ Mismatch"
        print(f"Reference Pages:  {result['reference_pages']} ({status_c})")
    print(f"Clean Pages:      {result['clean_pages']} / {result['total_pages']} ({result['quality_score_pct']} %)")
    print(f"Collisions:       {result['collisions_count']} pages")
    print(f"Narrow Columns:   {result['narrow_columns_count']} pages")
    print(f"Extreme Scaling:  {result['extreme_font_count']} pages")
    print("-" * 68)

    issues = result["issues"]
    if issues["collisions"]:
        print("\n⚠️ Row Collisions (Overlapping Text):")
        for item in issues["collisions"][:10]:
            print(f"  • Page {item['page']:3d}: {item['clash_pairs']} clashing pairs at y={item['y']} pt ({item['sample']})")
        if len(issues["collisions"]) > 10:
            print(f"  ... and {len(issues['collisions']) - 10} more pages.")

    if issues["narrow_columns"]:
        print("\n⚠️ Narrow Text Columns (< 25 % Width):")
        for item in issues["narrow_columns"][:10]:
            print(f"  • Page {item['page']:3d}: span {item['width_pt']} pt ({item['width_ratio_pct']} % of page, {item['words_count']} words)")
        if len(issues["narrow_columns"]) > 10:
            print(f"  ... and {len(issues['narrow_columns']) - 10} more pages.")

    if issues["extreme_font"]:
        print("\n⚠️ Extreme Font Shrinkage (< 5.5 pt):")
        for item in issues["extreme_font"][:10]:
            print(f"  • Page {item['page']:3d}: min font {item['min_font_pt']} pt")
        if len(issues["extreme_font"]) > 10:
            print(f"  ... and {len(issues['extreme_font']) - 10} more pages.")

    if not issues["collisions"] and not issues["narrow_columns"] and not issues["extreme_font"]:
        print("\n✨ All pages verified! Zero collisions, well-balanced columns, and crisp scholarly typography.")
    print("=" * 68)


if __name__ == "__main__":
    main()
