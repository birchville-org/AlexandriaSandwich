#!/usr/bin/env python3
"""
AlexandriaSandwich - Quality Check
Compute Tesseract OCR confidence and gate the hybrid quality loop.

Default threshold: 85 (per .gsd/SPEC.md).
Exit codes:
  0 = pass (score >= threshold)
  1 = fail / low confidence (trigger Mistral / HITL)
  2 = usage / input / dependency error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

DEFAULT_THRESHOLD = 85.0
TITLE_CONF_RE = re.compile(r"\bx_wconf\s+(-?\d+(?:\.\d+)?)")


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_tsv_confidences(text: str) -> List[float]:
    """Parse Tesseract TSV output; conf is last column, -1 means non-word/separator."""
    confs: List[float] = []
    lines = text.splitlines()
    if not lines:
        return confs
    # Skip header if present
    start = 1 if lines[0].lower().startswith("level\t") or "conf" in lines[0].lower().split("\t") else 0
    for line in lines[start:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        try:
            conf = float(parts[10] if len(parts) == 12 else parts[-2])
        except ValueError:
            # classic TSV: level page_num block_num par_num line_num word_num left top width height conf text
            try:
                conf = float(parts[10])
            except (ValueError, IndexError):
                continue
        text_val = parts[-1].strip() if parts else ""
        # Drop separators and empty tokens
        if conf < 0 or not text_val:
            continue
        confs.append(conf)
    return confs


def parse_hocr_confidences(text: str) -> List[float]:
    """Extract x_wconf values from hOCR title attributes."""
    confs: List[float] = []
    # Robust to namespaces
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        # fallback: regex over raw text
        return [float(m.group(1)) for m in TITLE_CONF_RE.finditer(text)]

    for el in root.iter():
        title = el.attrib.get("title") or ""
        cls = el.attrib.get("class") or ""
        if "ocrx_word" not in cls and "ocr_word" not in cls and "x_wconf" not in title:
            # still allow any title with x_wconf
            if "x_wconf" not in title:
                continue
        m = TITLE_CONF_RE.search(title)
        if not m:
            continue
        conf = float(m.group(1))
        word = (el.text or "").strip()
        if conf < 0:
            continue
        # keep word conf even if text empty (some engines still score boxes)
        confs.append(conf)
    if confs:
        return confs
    return [float(m.group(1)) for m in TITLE_CONF_RE.finditer(text)]


def mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def run_tesseract(
    image: Path,
    lang: str,
    psm: Optional[int],
    out_base: Path,
) -> Tuple[str, str]:
    """Run tesseract producing .tsv and .hocr next to out_base."""
    bin_path = shutil.which("tesseract")
    if not bin_path:
        die("tesseract not found on PATH")

    cmd = [bin_path, str(image), str(out_base), "-l", lang]
    if psm is not None:
        cmd.extend(["--psm", str(psm)])
    # TSV + hOCR
    cmd.extend(["tsv", "hocr"])
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        die(f"failed to execute tesseract: {exc}")

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        die(f"tesseract failed ({proc.returncode}): {err}")

    tsv_path = Path(str(out_base) + ".tsv")
    hocr_path = Path(str(out_base) + ".hocr")
    # some builds use .html for hocr
    if not hocr_path.exists():
        alt = Path(str(out_base) + ".html")
        if alt.exists():
            hocr_path = alt
    tsv = tsv_path.read_text(encoding="utf-8", errors="replace") if tsv_path.exists() else ""
    hocr = hocr_path.read_text(encoding="utf-8", errors="replace") if hocr_path.exists() else ""
    if not tsv and not hocr:
        die("tesseract produced neither TSV nor hOCR output")
    return tsv, hocr


def collect_from_file(path: Path) -> List[float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return parse_tsv_confidences(text)
    if suffix in {".hocr", ".html", ".xml"}:
        return parse_hocr_confidences(text)
    # sniff
    if "ocrx_word" in text or "x_wconf" in text or "<html" in text.lower():
        return parse_hocr_confidences(text)
    if "\t" in text and "conf" in text.splitlines()[0].lower():
        return parse_tsv_confidences(text)
    # default try both
    confs = parse_tsv_confidences(text)
    return confs or parse_hocr_confidences(text)


def build_result(
    confs: List[float],
    threshold: float,
    source: str,
    lang: Optional[str] = None,
) -> dict:
    avg = mean(confs)
    count = len(confs)
    if avg is None:
        score = 0.0
        passed = False
        note = "no_word_confidences"
    else:
        score = round(avg, 3)
        passed = score >= threshold
        note = "ok"
    low = sorted(confs)[:5] if confs else []
    return {
        "source": source,
        "lang": lang,
        "word_count": count,
        "mean_confidence": score,
        "min_confidence": round(min(confs), 3) if confs else None,
        "max_confidence": round(max(confs), 3) if confs else None,
        "threshold": threshold,
        "passed": passed,
        "decision": "pass" if passed else "fallback",
        "low_samples": [round(x, 3) for x in low],
        "note": note,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AlexandriaSandwich Tesseract quality/confidence gate"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("-i", "--image", type=Path, help="Image to OCR with Tesseract")
    src.add_argument("-f", "--file", type=Path, help="Existing Tesseract TSV or hOCR file")
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=float(os.environ.get("OCR_CONFIDENCE_THRESHOLD", DEFAULT_THRESHOLD)),
        help=f"Pass threshold (default {DEFAULT_THRESHOLD} or $OCR_CONFIDENCE_THRESHOLD)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default=os.environ.get("OCR_LANG", "deu+eng"),
        help="Tesseract languages (default deu+eng or $OCR_LANG)",
    )
    parser.add_argument("--psm", type=int, default=None, help="Tesseract page segmentation mode")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout",
    )
    parser.add_argument(
        "--keep-ocr",
        type=Path,
        default=None,
        help="Optional directory to keep generated .tsv/.hocr when using --image",
    )
    args = parser.parse_args(argv)

    if args.threshold < 0 or args.threshold > 100:
        die("threshold must be between 0 and 100")

    confs: List[float] = []
    source = ""

    if args.file:
        if not args.file.is_file():
            die(f"file not found: {args.file}")
        confs = collect_from_file(args.file)
        source = str(args.file)
    else:
        image = args.image
        if image is None or not image.is_file():
            die(f"image not found: {image}")
        if args.keep_ocr:
            args.keep_ocr.mkdir(parents=True, exist_ok=True)
            out_base = args.keep_ocr / image.stem
            tsv, hocr = run_tesseract(image, args.lang, args.psm, out_base)
        else:
            with tempfile.TemporaryDirectory(prefix="as-qc-") as tmp:
                out_base = Path(tmp) / image.stem
                tsv, hocr = run_tesseract(image, args.lang, args.psm, out_base)
        confs = parse_tsv_confidences(tsv)
        if not confs:
            confs = parse_hocr_confidences(hocr)
        source = str(image)

    result = build_result(confs, args.threshold, source=source, lang=args.lang if args.image else None)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result["passed"] else "FALLBACK"
        print(f"[{status}] mean_confidence={result['mean_confidence']} "
              f"threshold={result['threshold']} words={result['word_count']} "
              f"source={result['source']}")
        if result["note"] != "ok":
            print(f"note: {result['note']}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
