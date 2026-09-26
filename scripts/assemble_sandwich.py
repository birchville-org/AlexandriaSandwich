#!/usr/bin/env python3
"""
AlexandriaSandwich — assemble 1:1 Sandwich PDF

Builds a searchable PDF: original page images as the visible layer +
invisible OCR text (via OCRmyPDF sandwich renderer).

Typical flow:
  preprocessed/*.png  →  img2pdf (exact pixels)  →  ocrmypdf sandwich  →  out.pdf
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence


IMAGE_GLOBS = ("*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.webp", "*.bmp")


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def list_images(directory: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in IMAGE_GLOBS:
        files.extend(directory.glob(pattern))
        files.extend(directory.glob(pattern.upper()))
    # unique + natural-ish sort
    uniq = sorted(set(files), key=lambda p: p.name.lower())
    return [p for p in uniq if p.is_file()]


def run(cmd: Sequence[str], *, quiet: bool = False) -> None:
    if not quiet:
        print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        die(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{err}", code=1)


def build_base_pdf(images: Sequence[Path], base_pdf: Path, dpi: int) -> None:
    """Lossless image→PDF via img2pdf (1:1 pixel layout)."""
    try:
        import img2pdf
    except ImportError as exc:
        die(f"img2pdf not installed: {exc}")

    layout = img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))
    # img2pdf accepts path strings / bytes
    with open(base_pdf, "wb") as fh:
        fh.write(img2pdf.convert([str(p) for p in images], layout_fun=layout))


def run_ocrmypdf(
    src_pdf: Path,
    out_pdf: Path,
    *,
    lang: str,
    jobs: int,
    optimize: int,
    force_ocr: bool,
    sidecar: Optional[Path],
    title: Optional[str],
    author: Optional[str],
) -> None:
    bin_path = shutil.which("ocrmypdf")
    if not bin_path:
        die("ocrmypdf not found on PATH")

    cmd: List[str] = [
        bin_path,
        "--language",
        lang,
        "--output-type",
        "pdf",
        "--pdf-renderer",
        "sandwich",
        "--optimize",
        str(optimize),
        "--jobs",
        str(jobs),
        "--skip-big",
        "100",
    ]
    if force_ocr:
        cmd.append("--force-ocr")
    else:
        # Input is our fresh img2pdf → no text expected; default errors on text.
        # Using force-ocr is safer for re-runs. Prefer --force-ocr always for sandwich from images.
        cmd.append("--force-ocr")

    if sidecar is not None:
        cmd.extend(["--sidecar", str(sidecar)])
    if title:
        cmd.extend(["--title", title])
    if author:
        cmd.extend(["--author", author])

    cmd.extend([str(src_pdf), str(out_pdf)])
    run(cmd)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble 1:1 Sandwich PDF from page images")
    parser.add_argument(
        "-i",
        "--images-dir",
        type=Path,
        help="Directory of preprocessed page images (png/jpg/tiff)",
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        type=Path,
        help="Explicit image files (ordered)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output sandwich PDF path",
    )
    parser.add_argument(
        "-l",
        "--lang",
        default=os.environ.get("OCR_LANG", "deu+eng"),
        help="Tesseract languages for OCRmyPDF (default deu+eng)",
    )
    parser.add_argument("--dpi", type=int, default=int(os.environ.get("AS_DPI", "300")))
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--optimize", type=int, choices=[0, 1, 2, 3], default=1)
    parser.add_argument("--title", default=None)
    parser.add_argument("--author", default="AlexandriaSandwich")
    parser.add_argument(
        "--sidecar",
        type=Path,
        default=None,
        help="Optional plain-text sidecar from OCR",
    )
    parser.add_argument(
        "--keep-base-pdf",
        type=Path,
        default=None,
        help="Keep intermediate img2pdf base PDF at this path",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary on stdout")
    args = parser.parse_args(argv)

    images: List[Path] = []
    if args.files:
        images = [p for p in args.files if p.is_file()]
        missing = [str(p) for p in args.files if not p.is_file()]
        if missing:
            die(f"missing files: {', '.join(missing)}")
    elif args.images_dir:
        if not args.images_dir.is_dir():
            die(f"images dir not found: {args.images_dir}")
        images = list_images(args.images_dir)
    else:
        die("provide --images-dir or --files")

    if not images:
        die("no images found")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.sidecar:
        args.sidecar.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="as-sandwich-") as tmp:
        tmp_path = Path(tmp)
        base_pdf = args.keep_base_pdf or (tmp_path / "base.pdf")
        if args.keep_base_pdf:
            base_pdf.parent.mkdir(parents=True, exist_ok=True)

        print(f"img2pdf: {len(images)} page(s) @ {args.dpi} dpi → {base_pdf}", file=sys.stderr)
        build_base_pdf(images, base_pdf, args.dpi)
        if not base_pdf.is_file() or base_pdf.stat().st_size == 0:
            die("base PDF missing/empty after img2pdf")

        print(f"ocrmypdf sandwich: {base_pdf} → {args.output}", file=sys.stderr)
        run_ocrmypdf(
            base_pdf,
            args.output,
            lang=args.lang,
            jobs=args.jobs,
            optimize=args.optimize,
            force_ocr=True,
            sidecar=args.sidecar,
            title=args.title or args.output.stem,
            author=args.author,
        )

    if not args.output.is_file() or args.output.stat().st_size == 0:
        die("output PDF missing/empty", code=1)

    summary = {
        "output": str(args.output),
        "pages": len(images),
        "lang": args.lang,
        "dpi": args.dpi,
        "bytes": args.output.stat().st_size,
        "images": [p.name for p in images],
        "sidecar": str(args.sidecar) if args.sidecar else None,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"OK sandwich pages={summary['pages']} bytes={summary['bytes']} → {summary['output']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
