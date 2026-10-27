#!/usr/bin/env python3
"""
AlexandriaSandwich - Adaptive Typeset Solver
Iteratively optimizes font sizes and leading per page to guarantee 100% 1:1 page parity
without overflows, while maximizing typographic visual comfort.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


# Standard 6-tier typographic ladder
DEFAULT_LEVELS = [
    # Level 5: Maximum comfort (sparse pages, minimal text)
    {"level": 5, "deva_size": "11.8pt", "body_size": "9.6pt", "body_leading": "0.45em", "comm_size": "8.4pt", "comm_leading": "0.42em", "sutra_spacing": "0.95em", "tier": 5},
    # Level 4: Generous comfort (medium-low text density, e.g. 3-6 items)
    {"level": 4, "deva_size": "11.4pt", "body_size": "9.3pt", "body_leading": "0.42em", "comm_size": "8.1pt", "comm_leading": "0.38em", "sutra_spacing": "0.70em", "tier": 4},
    # Level 3: Relaxed standard (average text density, e.g. 6-8 items)
    {"level": 3, "deva_size": "10.8pt", "body_size": "8.9pt", "body_leading": "0.37em", "comm_size": "7.7pt", "comm_leading": "0.32em", "sutra_spacing": "0.38em", "tier": 3},
    # Level 2: Compact standard (text-heavy pages)
    {"level": 2, "deva_size": "10.4pt", "body_size": "8.6pt", "body_leading": "0.33em", "comm_size": "7.4pt", "comm_leading": "0.27em", "sutra_spacing": "0.20em", "tier": 2},
    # Level 1: Dense safety (very dense pages, 10-12 items)
    {"level": 1, "deva_size": "10.0pt", "body_size": "8.4pt", "body_leading": "0.30em", "comm_size": "7.2pt", "comm_leading": "0.25em", "sutra_spacing": "0.12em", "tier": 1},
    # Level 0: Extreme safety (highest historical density)
    {"level": 0, "deva_size": "9.6pt", "body_size": "8.1pt", "body_leading": "0.26em", "comm_size": "6.9pt", "comm_leading": "0.23em", "sutra_spacing": "0.06em", "tier": 0},
]


class AdaptiveTypesetSolver:
    """Solver that finds the maximum comfortable font size/leading per page with 0 overflows."""

    def __init__(
        self,
        pages_data: List[Dict[str, Any]],
        typst_file: Path,
        output_pdf: Path,
        levels: Optional[List[Dict[str, Any]]] = None,
        front_matter_pages: int = 5,
        page_num_key: str = "page_num",
        items_key: str = "sutras",
        ref_checker: Optional[Callable[[Dict[str, Any], str], bool]] = None,
    ):
        self.pages_data = pages_data
        self.typst_file = Path(typst_file)
        self.output_pdf = Path(output_pdf)
        self.levels = levels or DEFAULT_LEVELS
        self.front_matter_pages = front_matter_pages
        self.page_num_key = page_num_key
        self.items_key = items_key
        self.ref_checker = ref_checker or self._default_ref_checker

    @staticmethod
    def _default_ref_checker(item: Dict[str, Any], page_text: str) -> bool:
        # Check standard ref pattern e.g. "1, 1, 1." or "ref" string
        if "adhyaya" in item and "pada" in item and "sutra_num" in item:
            ref_str = f"{item['adhyaya']}, {item['pada']}, {item['sutra_num']}."
            return ref_str in page_text
        ref = item.get("ref", "")
        return ref in page_text if ref else True

    def find_first_overflow(self) -> Optional[int]:
        doc = pymupdf.open(str(self.output_pdf))
        total_pages = len(doc)

        for p_info in self.pages_data:
            orig_p = p_info[self.page_num_key]
            pdf_idx = self.front_matter_pages + (orig_p - 1)
            if pdf_idx >= total_pages:
                doc.close()
                return orig_p

            page_text = doc[pdf_idx].get_text()
            for item in p_info.get(self.items_key, []):
                if not self.ref_checker(item, page_text):
                    doc.close()
                    return orig_p

        doc.close()
        return None

    def solve(self, data_json_path: Path, max_iterations: int = 50) -> Dict[str, Dict[str, Any]]:
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"--- Iteration {iteration} ---")

            with open(data_json_path, "w", encoding="utf-8") as f:
                json.dump(self.pages_data, f, ensure_ascii=False, indent=2)

            res = subprocess.run(
                ["typst", "compile", "--root", ".", str(self.typst_file), str(self.output_pdf)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                print(f"Typst compile error: {res.stderr}", file=sys.stderr)
                sys.exit(res.returncode)

            overflow_page = self.find_first_overflow()
            if overflow_page is None:
                print("✓ 100% 1:1 Page Parity achieved! All pages fit with 0 overflows.")
                break

            print(f"Overflow found on original page {overflow_page}. Stepping down...")
            p_obj = next(p for p in self.pages_data if p[self.page_num_key] == overflow_page)
            curr_idx = p_obj.get("level_idx", 0)
            if curr_idx < len(self.levels) - 1:
                p_obj["level_idx"] = curr_idx + 1
                cfg = dict(self.levels[p_obj["level_idx"]])
                p_obj["profile"] = cfg
                print(f"Page {overflow_page} stepped down to Level {cfg['level']} (body={cfg['body_size']}, comm={cfg['comm_size']})")
            else:
                print(f"Fatal: Page {overflow_page} already at lowest level 0 and still overflows!", file=sys.stderr)
                sys.exit(1)

        calibrated = {str(p[self.page_num_key]): p["profile"] for p in self.pages_data}
        return calibrated


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Typeset Solver for AlexandriaSandwich")
    parser.add_argument("--data", type=Path, required=True, help="Path to page data JSON")
    parser.add_argument("--typst", type=Path, required=True, help="Path to Typst source file")
    parser.add_argument("--output", type=Path, required=True, help="Target PDF path")
    parser.add_argument("--profile-out", type=Path, default=Path("data/calibrated_profiles.json"), help="Output calibrated profile JSON")
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as f:
        pages = json.load(f)

    solver = AdaptiveTypesetSolver(pages, args.typst, args.output)
    calibrated = solver.solve(args.data)

    args.profile_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.profile_out, "w", encoding="utf-8") as f:
        json.dump(calibrated, f, indent=2)
    print(f"Calibrated profiles saved to {args.profile_out}")


if __name__ == "__main__":
    main()
