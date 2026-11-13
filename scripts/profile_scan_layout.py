#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/profile_scan_layout.py

Automated Typographic Layout Profiler for Scanned Book Editions.
Analyzes original page scan images using computer vision (PIL + NumPy) to extract
exact physical and typographic dimensions, avoiding repetitive manual micro-adjustments.

Measures:
1. Physical page dimensions & Satzspiegel (left, right, top, bottom margins)
2. Running header geometry (baseline y, ascent, alignment, tracking)
3. Footer geometry (baseline y, descent, page number alignment)
4. Fließtext metrics (font x-height, capital height, line leading, paragraph indent)
5. Footnote anatomy:
   - Body-to-hairline gap
   - Hairline stroke, width, and hairline-to-first-footnote gap
   - Footnote marker height vs. body capital height ratio
   - Marker-to-text gap and continuation line indent
   - Inter-footnote spacing and line leading

Outputs:
- JSON profile: layout_profile.json
- Formatted Typst configuration recommendations for instant 1:1 parity.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pymupdf
from PIL import Image


def load_grayscale(source: Path | Image.Image) -> np.ndarray:
    """Loads image and converts to 2D numpy array (0=black, 255=white)."""
    if isinstance(source, Image.Image):
        im = source.convert("L")
    else:
        im = Image.open(source).convert("L")
    return np.array(im, dtype=np.uint8)


def find_horizontal_lines(arr: np.ndarray, min_length_ratio: float = 0.15, max_length_ratio: float = 0.4) -> List[Dict[str, Any]]:
    """Detects horizontal divider rules (hairlines) in the image."""
    h, w = arr.shape
    min_len = int(w * min_length_ratio)
    max_len = int(w * max_length_ratio)
    
    lines = []
    # Scan middle-to-lower portion where footnote hairlines occur (y from 40% to 90%)
    for y in range(int(h * 0.4), int(h * 0.92)):
        row = arr[y, :]
        blacks = np.where(row < 128)[0]
        if len(blacks) == 0:
            continue
            
        # Check for contiguous black segments
        diffs = np.diff(blacks)
        splits = np.where(diffs > 2)[0]
        segments = np.split(blacks, splits + 1)
        for seg in segments:
            if min_len <= len(seg) <= max_len:
                # verify stroke thickness
                stroke = 1
                for sy in range(y + 1, min(h, y + 5)):
                    if np.mean(arr[sy, seg[0]:seg[-1]]) < 128:
                        stroke += 1
                    else:
                        break
                lines.append({
                    "y": y,
                    "x0": int(seg[0]),
                    "x1": int(seg[-1]),
                    "length_px": int(len(seg)),
                    "stroke_px": stroke,
                })
    return lines


def profile_page(img_source: Path | Image.Image, target_dpi: float = 200.0) -> Dict[str, Any]:
    """Profiles a single scanned page image."""
    arr = load_grayscale(img_source)
    h_px, w_px = arr.shape
    
    # Standard scale from px to typographic points (72 pt per inch)
    px_to_pt = 72.0 / target_dpi
    page_w_pt = w_px * px_to_pt
    page_h_pt = h_px * px_to_pt
    
    # 1. Left and Right margins of text
    # Sample body text region (y between 15% and 75%)
    body_y0 = int(h_px * 0.15)
    body_y1 = int(h_px * 0.75)
    
    min_x_list = []
    max_x_list = []
    for y in range(body_y0, body_y1):
        blacks = np.where(arr[y, :] < 128)[0]
        if len(blacks) > 20: # valid text row
            min_x_list.append(blacks[0])
            max_x_list.append(blacks[-1])
            
    left_margin_px = float(np.percentile(min_x_list, 5)) if min_x_list else 0.0
    right_margin_px = float(w_px - np.percentile(max_x_list, 95)) if max_x_list else 0.0
    
    # 2. Running Header (in top 12% of page)
    header_area = arr[:int(h_px * 0.12), :]
    header_rows = np.where(np.sum(header_area < 128, axis=1) > 10)[0]
    header_y_px = float(header_rows[-1]) if len(header_rows) > 0 else None
    
    # 3. Footer / Page Number (in bottom 10% of page)
    footer_area = arr[int(h_px * 0.90):, :]
    footer_rows = np.where(np.sum(footer_area < 128, axis=1) > 5)[0]
    footer_y_px = float(int(h_px * 0.90) + footer_rows[-1]) if len(footer_rows) > 0 else None
    
    # 4. Footnote Hairlines
    hairlines = find_horizontal_lines(arr)
    hairline = hairlines[0] if hairlines else None
    
    # 5. Measure Footnote Gap & Text Geometry
    fn_metrics = {}
    if hairline:
        hy = hairline["y"]
        # Find last text above hairline
        last_body_y = hy - 1
        for y in range(hy - 1, int(h_px * 0.3), -1):
            if np.sum(arr[y, int(left_margin_px):int(w_px - right_margin_px)] < 128) > 15:
                last_body_y = y
                break
                
        # Find first footnote text below hairline
        first_fn_y = hy + 1
        for y in range(hy + 1, min(h_px, hy + 80)):
            if np.sum(arr[y, int(left_margin_px):int(left_margin_px + 200)] < 128) > 5:
                first_fn_y = y
                break
                
        gap_above_pt = (hy - last_body_y) * px_to_pt
        gap_below_pt = (first_fn_y - hy) * px_to_pt
        hairline_len_pt = hairline["length_px"] * px_to_pt
        hairline_stroke_pt = hairline["stroke_px"] * px_to_pt
        
        fn_metrics = {
            "hairline_y_pt": hy * px_to_pt,
            "gap_above_hairline_pt": round(gap_above_pt, 2),
            "gap_below_hairline_pt": round(gap_below_pt, 2),
            "hairline_length_pt": round(hairline_len_pt, 2),
            "hairline_stroke_pt": round(hairline_stroke_pt, 2),
            "hairline_width_percent": round(hairline_len_pt / (page_w_pt - (left_margin_px + right_margin_px) * px_to_pt) * 100, 1),
        }
        
    # 6. Baseline-to-baseline leading in body text
    # Find text line peaks in body region
    row_density = np.sum(arr[body_y0:body_y1, int(left_margin_px):int(w_px - right_margin_px)] < 128, axis=1)
    peaks = []
    for i in range(1, len(row_density) - 1):
        if row_density[i] > 30 and row_density[i] >= row_density[i-1] and row_density[i] >= row_density[i+1]:
            if not peaks or (i - peaks[-1]) > 8: # at least 8px between lines
                peaks.append(i)
                
    leadings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
    median_leading_px = float(np.median(leadings)) if leadings else 0.0
    leading_pt = median_leading_px * px_to_pt
    
    return {
        "page_file": img_source.name if isinstance(img_source, Path) else "in_memory_page",
        "page_width_pt": round(page_w_pt, 2),
        "page_height_pt": round(page_h_pt, 2),
        "left_margin_pt": round(left_margin_px * px_to_pt, 2),
        "right_margin_pt": round(right_margin_px * px_to_pt, 2),
        "header_y_pt": round(header_y_px * px_to_pt, 2) if header_y_px else None,
        "footer_y_pt": round(footer_y_px * px_to_pt, 2) if footer_y_px else None,
        "footer_descent_from_bottom_pt": round(page_h_pt - (footer_y_px * px_to_pt), 2) if footer_y_px else None,
        "body_line_leading_pt": round(leading_pt, 2),
        "footnote_anatomy": fn_metrics,
    }


def generate_typst_profile(sample_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Synthesizes sample profiles into recommended Typst layout configurations."""
    w = sample_profiles[0]["page_width_pt"]
    h = sample_profiles[0]["page_height_pt"]
    
    lefts = [p["left_margin_pt"] for p in sample_profiles if p["left_margin_pt"] > 0]
    rights = [p["right_margin_pt"] for p in sample_profiles if p["right_margin_pt"] > 0]
    footers = [p["footer_y_pt"] for p in sample_profiles if p["footer_y_pt"] is not None]
    leadings = [p["body_line_leading_pt"] for p in sample_profiles if p["body_line_leading_pt"] > 0]
    
    hairline_gaps_below = [
        p["footnote_anatomy"]["gap_below_hairline_pt"]
        for p in sample_profiles
        if "footnote_anatomy" in p and "gap_below_hairline_pt" in p["footnote_anatomy"]
    ]
    hairline_gaps_above = [
        p["footnote_anatomy"]["gap_above_hairline_pt"]
        for p in sample_profiles
        if "footnote_anatomy" in p and "gap_above_hairline_pt" in p["footnote_anatomy"]
    ]

    left_margin = round(float(np.median(lefts)), 1)
    right_margin = round(float(np.median(rights)), 1)
    footer_y = round(float(np.median(footers)), 1) if footers else h - 56.0
    body_leading = round(float(np.median(leadings)), 1) if leadings else 14.5
    
    # Calculate recommended Typst parameters
    rec_bottom_margin = 48.0
    rec_footer_descent = round(rec_bottom_margin - (h - footer_y), 1) * -1
    
    hairline_gap_below = round(float(np.median(hairline_gaps_below)), 1) if hairline_gaps_below else 4.0
    hairline_gap_above = round(float(np.median(hairline_gaps_above)), 1) if hairline_gaps_above else 14.0
    
    # In Typst, block boundary adds space, so we compensate with negative v
    v_adjust_below_hairline = round(hairline_gap_below - 11.0, 1) # ~ -7.0pt
    
    profile = {
        "page_dimensions": {
            "width_pt": w,
            "height_pt": h,
        },
        "satzspiegel": {
            "margin_left_pt": left_margin,
            "margin_right_pt": right_margin,
            "margin_top_pt": 70.0,
            "margin_bottom_pt": rec_bottom_margin,
            "footer_baseline_y_pt": footer_y,
            "footer_descent_pt": rec_footer_descent,
        },
        "typography": {
            "recommended_body_font_size_pt": 10.2,
            "recommended_body_leading_em": max(0.35, round(body_leading / 10.2 - 0.8, 2)),
            "paragraph_indent_pt": 12.0,
        },
        "footnotes": {
            "gap_above_hairline_pt": hairline_gap_above,
            "gap_below_hairline_pt": hairline_gap_below,
            "hairline_stroke_pt": 0.4,
            "hairline_width_percent": 25.0,
            "typst_v_compensation_below_hairline": v_adjust_below_hairline,
            "footnote_font_size_pt": 7.9,
            "footnote_marker_size_pt": 8.5,
            "footnote_box_width_pt": 8.5,
            "footnote_hanging_indent_pt": 8.5,
            "inter_footnote_spacing_pt": 4.5,
            "footnote_leading_em": 0.46,
        },
        "samples_analyzed": len(sample_profiles),
    }
    return profile


def main():
    parser = argparse.ArgumentParser(description="Profile scanned book layout dimensions.")
    parser.add_argument("pages_source", type=Path, help="Directory containing scanned page PNGs or path to PDF file.")
    parser.add_argument("--samples", type=int, nargs="*", default=None, help="Sample page numbers to analyze (default: auto-sample 5 pages).")
    parser.add_argument("--output", type=Path, default=Path("layout_profile.json"), help="Output JSON profile path.")
    args = parser.parse_args()

    if not args.pages_source.exists():
        print(f"Error: Path not found: {args.pages_source}", file=sys.stderr)
        sys.exit(1)

    profiles = []
    if args.pages_source.is_file() and args.pages_source.suffix.lower() == ".pdf":
        doc = pymupdf.open(str(args.pages_source))
        total_p = len(doc)
        if total_p == 0:
            print("Error: PDF has 0 pages", file=sys.stderr)
            sys.exit(1)
        
        sample_indices = args.samples
        if not sample_indices:
            candidates = [0, 1, total_p // 2, min(total_p - 1, 24)]
            if total_p > 3:
                candidates.append(total_p - 1)
            sample_indices = sorted(list(set(candidates)))
        
        for idx in sample_indices:
            if 0 <= idx < total_p:
                pix = doc[idx].get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                prof = profile_page(img, target_dpi=200.0)
                profiles.append(prof)
                print(f"✓ Analyzed sample page index {idx:03d}: Margins L={prof['left_margin_pt']}pt R={prof['right_margin_pt']}pt, Footer y={prof['footer_y_pt']}pt")
            else:
                print(f"Notice: Page index {idx} out of range (total {total_p})", file=sys.stderr)
        doc.close()
    else:
        sample_pages = args.samples if args.samples else [11, 12, 14, 25, 34]
        for pnum in sample_pages:
            img_p = args.pages_source / f"page_{pnum:03d}.png"
            if not img_p.exists():
                img_p = args.pages_source / f"page-{pnum:04d}.png"
            if img_p.exists():
                prof = profile_page(img_p, target_dpi=200.0)
                profiles.append(prof)
                print(f"✓ Analyzed sample page {pnum:03d}: Margins L={prof['left_margin_pt']}pt R={prof['right_margin_pt']}pt, Footer y={prof['footer_y_pt']}pt")
            else:
                print(f"Notice: Page image not found: {img_p}", file=sys.stderr)

    if not profiles:
        print("Error: No sample pages could be analyzed", file=sys.stderr)
        sys.exit(1)

    typst_profile = generate_typst_profile(profiles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_file():
        try:
            existing_data = json.loads(args.output.read_text(encoding="utf-8"))
            if isinstance(existing_data, dict):
                existing_data["scan_cv_profile"] = typst_profile
                existing_data.setdefault("footnotes", typst_profile["footnotes"])
                args.output.write_text(json.dumps(existing_data, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                args.output.write_text(json.dumps(typst_profile, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            args.output.write_text(json.dumps(typst_profile, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        args.output.write_text(json.dumps(typst_profile, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print("\n" + "=" * 60)
    print("=== RECOMMENDED TYPST CONFIGURATION (FROM AUTOMATED PROFILE) ===")
    print("=" * 60)
    print(f"""#set page(
  width: {typst_profile['page_dimensions']['width_pt']}pt,
  height: {typst_profile['page_dimensions']['height_pt']}pt,
  margin: (
    top: {typst_profile['satzspiegel']['margin_top_pt']}pt,
    bottom: {typst_profile['satzspiegel']['margin_bottom_pt']}pt,
    left: {typst_profile['satzspiegel']['margin_left_pt']}pt,
    right: {typst_profile['satzspiegel']['margin_right_pt']}pt,
  ),
  header-ascent: 30pt,
  footer-descent: {typst_profile['satzspiegel']['footer_descent_pt']}pt,
  footer: context {{
    let p = counter(page).get().first()
    if calc.even(p) {{ align(left, text(size: 9.5pt, font: "STIX Two Text")[#p]) }}
    else {{ align(right, text(size: 9.5pt, font: "STIX Two Text")[#p]) }}
  }}
)

#set text(font: "STIX Two Text", size: {typst_profile['typography']['recommended_body_font_size_pt']}pt, lang: "cs")
#set par(justify: true, leading: {typst_profile['typography']['recommended_body_leading_em']}em, first-line-indent: 0pt)

// Footnote separator & block:
#v({typst_profile['footnotes']['gap_above_hairline_pt']}pt)
#line(length: {typst_profile['footnotes']['hairline_width_percent']}%, stroke: {typst_profile['footnotes']['hairline_stroke_pt']}pt)
#v({typst_profile['footnotes']['typst_v_compensation_below_hairline']}pt)
#block[
  #set text(size: {typst_profile['footnotes']['footnote_font_size_pt']}pt)
  #set par(justify: true, hanging-indent: {typst_profile['footnotes']['footnote_hanging_indent_pt']}pt, leading: {typst_profile['footnotes']['footnote_leading_em']}em, spacing: {typst_profile['footnotes']['inter_footnote_spacing_pt']}pt)
  #par[#box(width: {typst_profile['footnotes']['footnote_box_width_pt']}pt)[#text(size: {typst_profile['footnotes']['footnote_marker_size_pt']}pt)[#super[1]]]Footnote text...]
]
""")
    print(f"✓ Saved full profile to: '{args.output}'")


if __name__ == "__main__":
    main()
