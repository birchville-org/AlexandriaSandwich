#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/profile_source_layout.py

Pre-typeset layout analysis and profiling tool.
Inspects 2D block coordinates, margin structures, and column geometry
of the source PDF using PyMuPDF.

Outputs a declarative layout profile (layout.profile.json) defining:
1. macro_layout: 'single_column' | 'marginal_sideheads' | 'multi_column_grid'
2. geometric Satzspiegel bounds (margins: left, right, top, bottom)
3. marginal zone & body text zone coordinates
4. page-by-page sidehead and heading catalog
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf


def log(msg: str):
    print(f"[{time.strftime('%X')}] [layout_profiler] {msg}", file=sys.stderr)


def clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def profile_pdf_layout(
    pdf_path: Path,
    sample_pages: Optional[int] = 60,
    header_threshold_pt: float = 85.0,
    footer_threshold_pt: float = 750.0,
) -> Dict[str, Any]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Source PDF not found: {pdf_path}")

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError(f"Empty PDF: {pdf_path}")

    # Determine pages to sample
    if sample_pages and sample_pages < total_pages:
        step = max(1, total_pages // sample_pages)
        sample_indices = list(range(0, total_pages, step))[:sample_pages]
    else:
        sample_indices = list(range(total_pages))

    first_page = doc[0]
    p_width = float(first_page.rect.width)
    p_height = float(first_page.rect.height)

    pages_with_marginalia = 0
    pages_with_multicolumn = 0
    
    left_column_x0_list: List[float] = []
    left_column_x1_list: List[float] = []
    main_column_x0_list: List[float] = []
    main_column_x1_list: List[float] = []
    inside_margins_list: List[float] = []
    outside_margins_list: List[float] = []
    top_y_list: List[float] = []
    bottom_y_list: List[float] = []
    font_sizes_list: List[float] = []
    line_spacings_list: List[float] = []

    per_page_profiles: Dict[str, Any] = {}

    try:
        for pno in range(total_pages):
            page = doc[pno]
            raw_blocks = page.get_text("blocks")
            
            # Filter non-text or tiny blocks
            text_blocks = []
            for b in raw_blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and b[6] == 0:  # block_type 0 is text
                    t = b[4].strip()
                    if len(t) >= 2:
                        text_blocks.append(b)
    
            # Ignore running headers and footers for margin detection
            content_blocks = [
                b for b in text_blocks
                if b[1] >= header_threshold_pt and b[3] <= footer_threshold_pt
            ]
    
            if not content_blocks:
                continue
    
            # Look for marginal blocks (left sideheads)
            # Typically x0 < 160 and x1 < 190
            sidehead_blocks = []
            main_blocks = []
    
            for b in content_blocks:
                t = clean_line(b[4])
                bw = b[2] - b[0]
                bh = b[3] - b[1]
                if bw < 18.0 or bh < 6.5 or len(t) < 3:
                    continue
                # If block is in the left 28% of page width and ends before 35% of page width
                if b[0] < p_width * 0.28 and b[2] < p_width * 0.35 and len(t) <= 80:
                    sidehead_blocks.append(b)
                else:
                    main_blocks.append(b)
    
            has_sideheads = len(sidehead_blocks) > 0 and len(main_blocks) >= 2
            if has_sideheads:
                pages_with_marginalia += 1
                for b in sidehead_blocks:
                    left_column_x0_list.append(b[0])
                    left_column_x1_list.append(b[2])
    
            if main_blocks:
                # Check for multiple columns inside main blocks
                # e.g., if there are parallel columns in main body
                x_mids = [(b[0] + b[2]) / 2.0 for b in main_blocks if (b[2] - b[0]) < p_width * 0.42]
                if len(x_mids) >= 6:
                    col1 = [x for x in x_mids if x < p_width * 0.5]
                    col2 = [x for x in x_mids if x >= p_width * 0.5]
                    if len(col1) >= 3 and len(col2) >= 3:
                        pages_with_multicolumn += 1
    
                p_min_x = min(b[0] for b in main_blocks)
                p_max_x = max(b[2] for b in main_blocks)
                if pno % 2 == 0:
                    inside_margins_list.append(p_min_x)
                    outside_margins_list.append(p_width - p_max_x)
                else:
                    inside_margins_list.append(p_width - p_max_x)
                    outside_margins_list.append(p_min_x)

                for b in main_blocks:
                    main_column_x0_list.append(b[0])
                    main_column_x1_list.append(b[2])
                    top_y_list.append(b[1])
                    bottom_y_list.append(b[3])

                try:
                    p_dict = page.get_text("dict")
                    for blk in p_dict.get("blocks", []):
                        lines = blk.get("lines", [])
                        for l_idx, l in enumerate(lines):
                            for s in l.get("spans", []):
                                txt = s.get("text", "").strip()
                                sz = s.get("size", 0.0)
                                if len(txt) >= 3 and 6.0 <= sz <= 24.0:
                                    font_sizes_list.append(sz)
                            if l_idx + 1 < len(lines):
                                gap = lines[l_idx + 1]["bbox"][1] - l["bbox"][3]
                                if 0.5 <= gap <= 25.0:
                                    line_spacings_list.append(gap)
                except Exception:
                    pass
    
            # Record page sidehead texts for concordance (merging vertically adjacent fragments)
            if sidehead_blocks:
                # Sort by vertical position
                sidehead_blocks.sort(key=lambda b: (b[1], b[0]))
                merged_sideheads: List[Tuple[float, float, float, float, str, int, int]] = []
                for b in sidehead_blocks:
                    if not merged_sideheads:
                        merged_sideheads.append(b)
                    else:
                        prev = merged_sideheads[-1]
                        # If vertical gap is small (< 16 pt) and both are on the left
                        if (b[1] - prev[3]) <= 16.0:
                            new_x0 = min(prev[0], b[0])
                            new_y0 = prev[1]
                            new_x1 = max(prev[2], b[2])
                            new_y1 = b[3]
                            new_txt = prev[4].strip() + "\n" + b[4].strip()
                            merged_sideheads[-1] = (new_x0, new_y0, new_x1, new_y1, new_txt, prev[5], prev[6])
                        else:
                            merged_sideheads.append(b)
    
                sh_entries = []
                for b in merged_sideheads:
                    sh_entries.append({
                        "text": clean_line(b[4]),
                        "raw_text": b[4].strip(),
                        "bbox": [round(coord, 1) for coord in b[:4]],
                    })
                per_page_profiles[str(pno + 1)] = {
                    "has_sideheads": True,
                    "sideheads": sh_entries,
                }
    finally:
        doc.close()

    # Decide macro layout
    marginal_ratio = pages_with_marginalia / max(total_pages, 1)
    multicol_ratio = pages_with_multicolumn / max(total_pages, 1)

    if marginal_ratio >= 0.08:
        macro_layout = "marginal_sideheads"
    elif multicol_ratio >= 0.25:
        macro_layout = "multi_column_grid"
    else:
        macro_layout = "single_column"

    # Compute geometric averages/medians
    def safe_median(vals: List[float], default: float) -> float:
        return float(statistics.median(vals)) if vals else default

    body_left = safe_median(main_column_x0_list, 50.0)
    body_right = safe_median(main_column_x1_list, p_width - 50.0)
    top_margin = safe_median(top_y_list, 55.0)
    bottom_margin = p_height - safe_median(bottom_y_list, p_height - 55.0)

    marginal_x0 = safe_median(left_column_x0_list, 45.0)
    marginal_x1 = safe_median(left_column_x1_list, 150.0)

    # Safety bounds without artificial clamping
    min_margin = 18.0
    max_h_margin = p_width * 0.45
    max_v_margin = p_height * 0.45

    margin_left = max(min_margin, min(body_left, max_h_margin))
    margin_right = max(min_margin, min(p_width - body_right, max_h_margin))
    margin_inside = max(min_margin, min(safe_median(inside_margins_list, margin_left), max_h_margin))
    margin_outside = max(min_margin, min(safe_median(outside_margins_list, margin_right), max_h_margin))
    margin_top = max(min_margin, min(top_margin, max_v_margin))
    margin_bottom = max(min_margin, min(bottom_margin, max_v_margin))

    is_asymmetric_gutter = abs(margin_inside - margin_outside) >= 4.0
    med_font = round(statistics.median(font_sizes_list), 1) if font_sizes_list else None
    med_leading = round(statistics.median(line_spacings_list), 1) if line_spacings_list else None

    profile = {
        "source_pdf": str(pdf_path.resolve()),
        "total_pages": total_pages,
        "page_dimensions": {
            "width_pt": round(p_width, 1),
            "height_pt": round(p_height, 1),
        },
        "macro_layout": macro_layout,
        "statistics": {
            "pages_with_marginalia": pages_with_marginalia,
            "marginalia_ratio": round(marginal_ratio, 3),
            "pages_with_multicolumn": pages_with_multicolumn,
            "multicolumn_ratio": round(multicol_ratio, 3),
        },
        "calibrated_margins": {
            "left_pt": round(margin_left, 1),
            "right_pt": round(margin_right, 1),
            "inside_pt": round(margin_inside, 1),
            "outside_pt": round(margin_outside, 1),
            "top_pt": round(margin_top, 1),
            "bottom_pt": round(margin_bottom, 1),
            "is_asymmetric_gutter": is_asymmetric_gutter,
        },
        "typography": {
            "font_size_pt": med_font,
            "leading_pt": med_leading,
        },
        "marginal_zone": {
            "x0": round(marginal_x0, 1),
            "x1": round(marginal_x1, 1),
            "width_pt": round(marginal_x1 - marginal_x0, 1),
            "gutter_pt": round(margin_left - marginal_x1, 1),
        } if macro_layout == "marginal_sideheads" else None,
        "body_zone": {
            "x0": round(margin_left, 1),
            "x1": round(p_width - margin_right, 1),
            "width_pt": round((p_width - margin_right) - margin_left, 1),
        },
        "pages": per_page_profiles,
    }

    return profile


def main():
    parser = argparse.ArgumentParser(description="Profile layout geometry from source PDF")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to reference or source PDF")
    parser.add_argument("--output", type=Path, default=None, help="Output path for layout.profile.json")
    parser.add_argument("--sample", type=int, default=60, help="Max pages to sample for geometry")
    args = parser.parse_args()

    log(f"Profiling source PDF: {args.pdf}")
    profile = profile_pdf_layout(args.pdf, sample_pages=args.sample)
    log(f"Detected layout: {profile['macro_layout']} (marginalia: {profile['statistics']['marginalia_ratio']*100:.1f}%)")
    log(f"Margins (pt): Left={profile['calibrated_margins']['left_pt']}, Right={profile['calibrated_margins']['right_pt']}, Top={profile['calibrated_margins']['top_pt']}, Bottom={profile['calibrated_margins']['bottom_pt']}")

    out_path = args.output or args.pdf.parent / "layout.profile.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    log(f"Saved layout profile to: {out_path}")


if __name__ == "__main__":
    main()
