#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/audit_layout_concordance.py

Post-typeset Layout Quality Gate & Page-by-Page Concordance Auditor.
Compares digital vector PDF (digital.pdf) against original/reference PDF
(source.pdf or sandwich.pdf) using PyMuPDF.

Audits:
1. Per-page Satzspiegel fill ratio & whitespace divergence
2. Structural zone concordance (marginal sideheads vs. main column)
3. Horizontal center of mass / density distribution
4. Token overlap and text truncation detection
5. Generates structured JSON and Markdown audit dashboards
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
    print(f"[{time.strftime('%X')}] [layout_audit] {msg}", file=sys.stderr)


def clean_tokens(text: str) -> List[str]:
    words = re.findall(r"\b[\wāīūṛṝḷṅñṭḍṇśṣḥṃ\-_]+\b", text.lower())
    return [w for w in words if len(w) > 1 or w in {"a", "i", "u"}]


def compute_jaccard(tok_a: List[str], tok_b: List[str]) -> float:
    set_a = set(tok_a)
    set_b = set(tok_b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def audit_page_pair(
    orig_page: pymupdf.Page,
    dig_page: pymupdf.Page,
    page_index: int,
    marginal_x_threshold: float = 175.0,
) -> Dict[str, Any]:
    p_w = orig_page.rect.width
    p_h = orig_page.rect.height

    orig_blocks = [b for b in orig_page.get_text("blocks") if len(b[4].strip()) >= 2]
    dig_blocks = [b for b in dig_page.get_text("blocks") if len(b[4].strip()) >= 2]

    orig_text = orig_page.get_text()
    dig_text = dig_page.get_text()

    tok_orig = clean_tokens(orig_text)
    tok_dig = clean_tokens(dig_text)
    overlap = compute_jaccard(tok_orig, tok_dig)

    # 1. Satzspiegel vertical fill ratio
    def get_fill_ratio(blocks: List[Any], h: float) -> Tuple[float, float, float]:
        if not blocks:
            return 0.0, 0.0, 0.0
        min_y = min(b[1] for b in blocks)
        max_y = max(b[3] for b in blocks)
        extent = max(0.0, max_y - min_y)
        return round(extent / max(h, 1.0), 3), round(min_y, 1), round(max_y, 1)

    orig_fill, orig_min_y, orig_max_y = get_fill_ratio(orig_blocks, p_h)
    dig_fill, dig_min_y, dig_max_y = get_fill_ratio(dig_blocks, p_h)
    fill_delta = round(abs(dig_fill - orig_fill), 3)

    # 2. Horizontal center of mass (density)
    def get_center_of_mass_x(blocks: List[Any], w: float) -> float:
        total_chars = 0
        sum_x = 0.0
        for b in blocks:
            c_count = len(b[4].strip())
            mid_x = (b[0] + b[2]) / 2.0
            sum_x += mid_x * c_count
            total_chars += c_count
        if total_chars == 0:
            return 0.5
        return round((sum_x / total_chars) / max(w, 1.0), 3)

    orig_com_x = get_center_of_mass_x(orig_blocks, p_w)
    dig_com_x = get_center_of_mass_x(dig_blocks, p_w)
    com_delta = round(abs(dig_com_x - orig_com_x), 3)

    # 3. Structural zone concordance (marginal sideheads via word-level coordinates)
    orig_words = [w for w in orig_page.get_text("words") if len(w[4].strip()) >= 2]
    dig_words = [w for w in dig_page.get_text("words") if len(w[4].strip()) >= 2]

    orig_sh_words = [w for w in orig_words if w[0] < marginal_x_threshold and w[1] > 80 and w[3] < p_h - 60]
    dig_sh_words = [w for w in dig_words if w[0] < marginal_x_threshold and w[1] > 80 and w[3] < p_h - 60]

    has_orig_sh = len(orig_sh_words) >= 2
    has_dig_sh = len(dig_sh_words) >= 2
    sh_concordance = (has_orig_sh == has_dig_sh)

    # 4. Grading
    status = "PASS"
    warnings: List[str] = []

    if overlap < 0.45 and (len(tok_orig) > 20 or len(tok_dig) > 20):
        status = "FAIL"
        warnings.append(f"Low token overlap ({overlap*100:.1f}%)")
    elif overlap < 0.65 and len(tok_orig) > 15:
        if status != "FAIL":
            status = "WARN"
        warnings.append(f"Moderate token overlap ({overlap*100:.1f}%)")

    if has_orig_sh and not has_dig_sh:
        if status != "FAIL":
            status = "WARN"
        warnings.append("Original has marginal sidehead but digital does not")

    if fill_delta > 0.35 and orig_fill > 0.40:
        if status != "FAIL":
            status = "WARN"
        warnings.append(f"Significant vertical fill discrepancy (delta={fill_delta*100:.1f}%)")

    if com_delta > 0.18:
        if status != "FAIL":
            status = "WARN"
        warnings.append(f"Horizontal density shift (orig={orig_com_x}, dig={dig_com_x})")

    return {
        "page_index": page_index,
        "status": status,
        "token_overlap": round(overlap, 3),
        "orig_tokens": len(tok_orig),
        "dig_tokens": len(tok_dig),
        "vertical_fill": {
            "orig": orig_fill,
            "dig": dig_fill,
            "delta": fill_delta,
        },
        "center_of_mass_x": {
            "orig": orig_com_x,
            "dig": dig_com_x,
            "delta": com_delta,
        },
        "sideheads": {
            "orig_count": len(orig_sh_words),
            "dig_count": len(dig_sh_words),
            "concordance": sh_concordance,
            "orig_sample": " ".join(w[4] for w in orig_sh_words[:5]) if orig_sh_words else None,
            "dig_sample": " ".join(w[4] for w in dig_sh_words[:5]) if dig_sh_words else None,
        },
        "warnings": warnings,
    }


def audit_layout_concordance(
    orig_pdf: Path,
    dig_pdf: Path,
    marginal_x_threshold: float = 175.0,
) -> Dict[str, Any]:
    if not orig_pdf.exists():
        raise FileNotFoundError(f"Original PDF not found: {orig_pdf}")
    if not dig_pdf.exists():
        raise FileNotFoundError(f"Digital PDF not found: {dig_pdf}")

    doc_orig = pymupdf.open(orig_pdf)
    doc_dig = pymupdf.open(dig_pdf)
    try:
        n_orig = len(doc_orig)
        n_dig = len(doc_dig)

        total_pages = min(n_orig, n_dig)
        pages_audit = []
    
        pass_count = 0
        warn_count = 0
        fail_count = 0
        overlaps = []
    
        for idx in range(total_pages):
            res = audit_page_pair(
                doc_orig[idx],
                doc_dig[idx],
                page_index=idx + 1,
                marginal_x_threshold=marginal_x_threshold,
            )
            pages_audit.append(res)
            overlaps.append(res["token_overlap"])
            if res["status"] == "PASS":
                pass_count += 1
            elif res["status"] == "WARN":
                warn_count += 1
            else:
                fail_count += 1
    
        overall_status = "PASS"
        if fail_count > 0 or n_orig != n_dig:
            overall_status = "FAIL" if (fail_count > total_pages * 0.05 or abs(n_orig - n_dig) > 2) else "WARN"
        elif warn_count > total_pages * 0.20:
            overall_status = "WARN"
    
        mean_overlap = statistics.mean(overlaps) if overlaps else 0.0
    
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "original_pdf": str(orig_pdf.resolve()),
            "digital_pdf": str(dig_pdf.resolve()),
            "page_counts": {
                "orig": n_orig,
                "digital": n_dig,
                "concordant": (n_orig == n_dig),
            },
            "overall_status": overall_status,
            "summary": {
                "total_audited_pages": total_pages,
                "pass_pages": pass_count,
                "warn_pages": warn_count,
                "fail_pages": fail_count,
                "mean_token_overlap": round(mean_overlap, 3),
            },
            "pages": pages_audit,
        }
    finally:
        doc_orig.close()
        doc_dig.close()


def generate_markdown_report(audit_data: Dict[str, Any], job_name: str) -> str:
    summary = audit_data["summary"]
    page_counts = audit_data["page_counts"]
    status = audit_data["overall_status"]

    status_badge = "🟢 PASS" if status == "PASS" else ("🟡 WARN" if status == "WARN" else "🔴 FAIL")

    lines = [
        f"# Layout Concordance & Quality Gate Audit: {job_name}",
        "",
        f"**Audit Status**: {status_badge}  ",
        f"**Original Pages**: {page_counts['orig']} | **Digital Pages**: {page_counts['digital']} ({'1:1 Match' if page_counts['concordant'] else 'Mismatch'})  ",
        f"**Mean Token Overlap**: {summary['mean_token_overlap']*100:.1f}%  ",
        f"**Audited Pages Summary**: {summary['pass_pages']} Pass, {summary['warn_pages']} Warn, {summary['fail_pages']} Fail  ",
        "",
        "## Key Discrepancies & Flagged Pages",
        "",
        "| Page | Status | Token Overlap | Vert. Fill (Orig / Dig) | Density CoM (Orig / Dig) | Sidehead Match | Warnings |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    flagged = [p for p in audit_data["pages"] if p["status"] in ("WARN", "FAIL")]
    display_pages = flagged[:35] if flagged else audit_data["pages"][:15]

    for p in display_pages:
        st_icon = "🟢" if p["status"] == "PASS" else ("🟡" if p["status"] == "WARN" else "🔴")
        v_fill = f"{p['vertical_fill']['orig']*100:.0f}% / {p['vertical_fill']['dig']*100:.0f}%"
        com = f"{p['center_of_mass_x']['orig']:.2f} / {p['center_of_mass_x']['dig']:.2f}"
        sh = "✓" if p["sideheads"]["concordance"] else "✗"
        warns = "; ".join(p["warnings"]) if p["warnings"] else "—"
        lines.append(f"| {p['page_index']} | {st_icon} {p['status']} | {p['token_overlap']*100:.1f}% | {v_fill} | {com} | {sh} | {warns} |")

    if len(flagged) > 35:
        lines.append(f"| ... | ... | ... | ... | ... | ... | *({len(flagged) - 35} more flagged pages omitted)* |")

    lines.append("")
    lines.append("---")
    lines.append("*Generated automatically by AlexandriaSandwich Layout Concordance Auditor.*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit layout concordance between original and digital PDF")
    parser.add_argument("--orig", required=True, type=Path, help="Path to original/reference PDF")
    parser.add_argument("--digital", required=True, type=Path, help="Path to digital vector PDF")
    parser.add_argument("--job", default="job", help="Job name")
    parser.add_argument("--json-out", type=Path, default=None, help="Output path for JSON audit")
    parser.add_argument("--md-out", type=Path, default=None, help="Output path for Markdown report")
    parser.add_argument("--threshold-x", type=float, default=175.0, help="Marginal sidehead X boundary in points")
    args = parser.parse_args()

    log(f"Auditing layout: {args.orig.name} vs. {args.digital.name}")
    audit_res = audit_layout_concordance(args.orig, args.digital, marginal_x_threshold=args.threshold_x)

    log(f"Overall status: {audit_res['overall_status']} (Pass: {audit_res['summary']['pass_pages']}, Warn: {audit_res['summary']['warn_pages']}, Fail: {audit_res['summary']['fail_pages']})")

    out_json = args.json_out or args.digital.parent / f"{args.job}.layout_audit.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_res, f, indent=2, ensure_ascii=False)
    log(f"Saved JSON audit to: {out_json}")

    out_md = args.md_out or args.digital.parent / f"{args.job}.layout_audit.md"
    md_content = generate_markdown_report(audit_res, job_name=args.job)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    log(f"Saved Markdown audit dashboard to: {out_md}")


if __name__ == "__main__":
    main()
