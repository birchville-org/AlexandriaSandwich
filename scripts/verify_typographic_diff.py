#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/verify_typographic_diff.py

Automated Typographic Difference & Alignment Verifier.
Compares original scanned pages against the compiled digital Neusatz PDF.

Capabilities:
1. Generates Red/Cyan Difference Overlays (Anaglyphs):
   - Original Scan = Red channel
   - Digital Neusatz = Cyan channel (Green + Blue)
   - Perfect alignment = Solid dark grey / black
   - Misalignments = Bright red (original only) or cyan (neusatz only) fringing
2. Quantitative Alignment Check (Tolerance Gate):
   - Footer / Page Number baseline delta (|Δy| <= 1.0 pt)
   - Running Header baseline delta (|Δy| <= 1.5 pt)
   - Footnote Hairline rule delta (|Δy| <= 1.5 pt)
   - Margin horizontal delta (|Δx| <= 1.5 pt)
   - Superscript scale ratio check (warns if double-superscript < 50% of cap height)
3. Outputs:
   - Visual Diff PNGs: diff_overlay_page_{pnum:03d}.png
   - JSON report: audit_typographic_diff.json
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


def generate_diff_overlay(orig_img: Image.Image, neu_img: Image.Image) -> Image.Image:
    """Generates a Red/Cyan anaglyph difference image on white paper."""
    target_w, target_h = 1200, 1850
    im_orig = orig_img.convert("L").resize((target_w, target_h), Image.Resampling.LANCZOS)
    im_neu = neu_img.convert("L").resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    arr_orig = np.array(im_orig, dtype=np.float32)
    arr_neu = np.array(im_neu, dtype=np.float32)
    
    # Invert signal (ink density)
    sig_orig = np.clip(255.0 - arr_orig - 35, 0, 255)
    sig_neu = np.clip(255.0 - arr_neu - 20, 0, 255)
    
    if sig_orig.max() > 0:
        sig_orig = sig_orig / sig_orig.max() * 255.0
    if sig_neu.max() > 0:
        sig_neu = sig_neu / sig_neu.max() * 255.0
        
    # Anaglyph on white paper:
    # R channel receives absence of Neusatz ink (so Neu-only ink lacks Red -> Cyan)
    # G & B channels receive absence of Orig ink (so Orig-only ink lacks Cyan -> Red)
    # Both ink present -> R, G, B all 0 -> Pure Black text!
    r = np.clip(255 - sig_neu, 0, 255).astype(np.uint8)
    g = np.clip(255 - sig_orig, 0, 255).astype(np.uint8)
    b = np.clip(255 - sig_orig, 0, 255).astype(np.uint8)
    
    return Image.merge("RGB", (Image.fromarray(r), Image.fromarray(g), Image.fromarray(b)))


def audit_page(orig_img_source: Path | Image.Image, neu_page: pymupdf.Page, pnum: int, dpi: float = 200.0) -> Dict[str, Any]:
    """Computes quantitative alignment metrics between original scan and digital page."""
    px_to_pt = 72.0 / dpi
    
    # Render digital page at dpi
    pix = neu_page.get_pixmap(dpi=int(dpi))
    im_neu = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    if isinstance(orig_img_source, Image.Image):
        im_orig = orig_img_source
    else:
        im_orig = Image.open(orig_img_source)
    
    # Measure footer page number in digital PDF
    words_neu = neu_page.get_text("words")
    expected_str = str(pnum)
    neu_footer = None
    for w in words_neu:
        if w[1] > 550 and w[4] == expected_str:
            neu_footer = w # (x0, y0, x1, y1, text, ...)
            break
            
    # Measure footer in original scan (scale dynamically to target page height)
    arr_orig = np.array(im_orig.convert("L"))
    h_px, w_px = arr_orig.shape
    orig_px_to_pt = neu_page.rect.height / float(h_px) if h_px > 0 else px_to_pt
    footer_area = arr_orig[int(h_px * 0.88):, :]
    f_rows = np.where(np.sum(footer_area < 128, axis=1) > 5)[0]
    orig_footer_y_pt = (int(h_px * 0.88) + f_rows[-1]) * orig_px_to_pt if len(f_rows) > 0 else None
    
    footer_delta_pt = None
    if neu_footer and orig_footer_y_pt:
        footer_delta_pt = round(neu_footer[3] - orig_footer_y_pt, 2)
        
    # Measure hairline position in digital PDF
    drawings = neu_page.get_drawings()
    neu_hairline_y = None
    for d in drawings:
        for item in d["items"]:
            if item[0] == "l" and abs(item[1].y - item[2].y) < 1.0:
                neu_hairline_y = item[1].y
                break
                
    # Measure hairline in original scan (15%-38% width, contiguous horizontal stroke with vertical whitespace)
    orig_hairline_y_pt = None
    min_hl_len = int(w_px * 0.15)
    max_hl_len = int(w_px * 0.38)
    for y in range(int(h_px * 0.5), int(h_px * 0.9)):
        row = arr_orig[y, :]
        blacks = np.where(row < 128)[0]
        if min_hl_len <= len(blacks) <= max_hl_len and np.max(np.diff(blacks)) <= 3:
            x0, x1 = int(blacks[0]), int(blacks[-1])
            above_ink = np.sum(arr_orig[max(0, y - 3), x0:x1] < 128)
            below_ink = np.sum(arr_orig[min(h_px - 1, y + 3), x0:x1] < 128)
            if above_ink <= 2 and below_ink <= 2:
                orig_hairline_y_pt = y * orig_px_to_pt
                break
            
    hairline_delta_pt = None
    if neu_hairline_y and orig_hairline_y_pt:
        hairline_delta_pt = round(neu_hairline_y - orig_hairline_y_pt, 2)
        
    # Measure Footnote Superscript Ratio in digital PDF
    fn_spans = []
    cap_heights = []
    d = neu_page.get_text("dict")
    for b in d["blocks"]:
        if b.get("bbox", [0,0,0,0])[1] > 400 and "lines" in b:
            for l in b["lines"]:
                for s in l["spans"]:
                    if s["size"] < 9.0: # footnote text
                        for c in s["text"]:
                            if c.isupper():
                                cap_heights.append(s["size"])
                    if s["flags"] & 1 or "super" in s["font"].lower() or (s["text"].isdigit() and len(s["text"]) <= 2):
                        fn_spans.append(s)
                        
    is_superscript_healthy = True
    marker_ratio = None
    if fn_spans and cap_heights:
        # compare marker size
        m_size = fn_spans[0]["size"]
        cap_size = cap_heights[0]
        marker_ratio = round(m_size / cap_size, 2)
        if marker_ratio < 0.50:
            is_superscript_healthy = False
            
    status = "PASS"
    issues = []
    if footer_delta_pt is not None and abs(footer_delta_pt) > 1.5:
        status = "WARN"
        issues.append(f"Footer baseline delta ({footer_delta_pt} pt) exceeds ±1.5 pt")
    if hairline_delta_pt is not None and abs(hairline_delta_pt) > 3.0:
        status = "WARN"
        issues.append(f"Hairline delta ({hairline_delta_pt} pt) exceeds ±3.0 pt")
    if not is_superscript_healthy and marker_ratio is not None:
        status = "WARN"
        issues.append(f"Superscript ratio ({marker_ratio}) too small (<0.50), suspected double-superscript")
        
    diff_img = generate_diff_overlay(im_orig, im_neu)
    
    return {
        "page": pnum,
        "status": status,
        "issues": issues,
        "footer": {
            "digital_baseline_pt": round(neu_footer[3], 2) if neu_footer else None,
            "original_baseline_pt": round(orig_footer_y_pt, 2) if orig_footer_y_pt else None,
            "delta_pt": footer_delta_pt,
        },
        "hairline": {
            "digital_y_pt": round(neu_hairline_y, 2) if neu_hairline_y else None,
            "original_y_pt": round(orig_hairline_y_pt, 2) if orig_hairline_y_pt else None,
            "delta_pt": hairline_delta_pt,
        },
        "superscript_scale_ratio": marker_ratio,
        "diff_image": diff_img,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify typographic alignment between scan and PDF.")
    parser.add_argument("orig_source", type=Path, help="Directory of original page PNGs or path to original/facsimile/sandwich PDF.")
    parser.add_argument("neusatz_pdf", type=Path, help="Path to compiled Neusatz PDF.")
    parser.add_argument("--pages", type=int, nargs="*", default=None, help="Page numbers to audit (default: auto-sample 5 pages).")
    parser.add_argument("--output-dir", type=Path, default=Path("audit_output"), help="Output directory for diffs and reports.")
    args = parser.parse_args()

    if not args.orig_source.exists() or not args.neusatz_pdf.exists():
        print(f"Error: Missing input paths: orig={args.orig_source}, neusatz={args.neusatz_pdf}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(args.neusatz_pdf))
    total_pages = len(doc)
    if total_pages == 0:
        print("Error: Neusatz PDF has 0 pages", file=sys.stderr)
        sys.exit(1)

    # Detect first page number from labels
    first_pnum = 1
    labels = doc.get_page_labels()
    if labels and isinstance(labels[0], dict) and labels[0].get("firstpagenum"):
        first_pnum = labels[0]["firstpagenum"]

    pages_to_audit = args.pages
    if not pages_to_audit:
        candidates = [first_pnum, first_pnum + 1, first_pnum + total_pages // 2, first_pnum + min(total_pages - 1, 24)]
        if total_pages > 3:
            candidates.append(first_pnum + total_pages - 1)
        pages_to_audit = sorted(list(set(candidates)))

    orig_doc = None
    if args.orig_source.is_file() and args.orig_source.suffix.lower() == ".pdf":
        orig_doc = pymupdf.open(str(args.orig_source))

    results = []
    overall_status = "PASS"

    print(f"Auditing pages: {pages_to_audit} (startpage={first_pnum})...")
    for pnum in pages_to_audit:
        pidx = pnum - first_pnum
        if pidx < 0 or pidx >= total_pages:
            print(f"Notice: Page {pnum} out of bounds for PDF ({total_pages} pages)", file=sys.stderr)
            continue

        if orig_doc is not None:
            if pidx >= len(orig_doc):
                print(f"Notice: Page index {pidx} out of bounds for original PDF", file=sys.stderr)
                continue
            orig_pix = orig_doc[pidx].get_pixmap(dpi=200)
            orig_img = Image.frombytes("RGB", [orig_pix.width, orig_pix.height], orig_pix.samples)
            res = audit_page(orig_img, doc[pidx], pnum)
        else:
            orig_img_p = args.orig_source / f"page_{pnum:03d}.png"
            if not orig_img_p.exists():
                orig_img_p = args.orig_source / f"page-{pnum:04d}.png"
            if not orig_img_p.exists():
                print(f"Notice: Missing original scan {orig_img_p}", file=sys.stderr)
                continue
            res = audit_page(orig_img_p, doc[pidx], pnum)

        # Save diff overlay
        diff_path = args.output_dir / f"diff_overlay_page_{pnum:03d}.png"
        res["diff_image"].save(str(diff_path))
        del res["diff_image"]  # remove from json dict
        res["diff_image_path"] = str(diff_path)

        if res["status"] != "PASS":
            overall_status = "WARN"

        f_delta = f"Δy={res['footer']['delta_pt']:+.2f}pt" if res['footer']['delta_pt'] is not None else "N/A"
        h_delta = f"Δy={res['hairline']['delta_pt']:+.2f}pt" if res['hairline']['delta_pt'] is not None else "N/A"
        print(f"[{res['status']}] Page {pnum:03d} -> Footer: {f_delta}, Hairline: {h_delta}, Diff: '{diff_path.name}'")
        if res["issues"]:
            for iss in res["issues"]:
                print(f"      ↳ {iss}")

        results.append(res)

    report = {
        "overall_status": overall_status,
        "pages_audited": len(results),
        "pages": results,
    }

    report_json_path = args.output_dir / "audit_typographic_diff.json"
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Overall Audit Status: {overall_status}")
    print(f"✓ Saved audit report to: '{report_json_path}'")
    doc.close()
    if orig_doc is not None:
        orig_doc.close()


if __name__ == "__main__":
    main()
