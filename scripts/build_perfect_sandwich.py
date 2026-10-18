#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_perfect_sandwich.py

Builds a publication-grade Perfect Sandwich PDF:
1. Restores scanned page images:
   - Preserves full-color covers and color illustrations in native RGB without destructive clipping.
   - Restores text pages via adaptive histogram leveling to achieve pure #FFFFFF paper background
     and deep, crisp black ink without haloing or erasing subtle Sanskrit ligatures/diacritics.
2. Accurately extracts images from the base sandwich PDF via pikepdf.PdfImage (avoiding raw byte distortion).
3. Preserves the entire invisible vector text layer (PDF Render Mode 3).
4. Re-encodes grayscale streams with zlib FlateDecode (and color with DCTDecode), producing
   ultra-clean visual fidelity and compact publication file size.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import io
import os
import sys
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pikepdf
from PIL import Image, ImageFilter, ImageStat


def log(msg: str):
    print(f"[{time.strftime('%X')}] [perfect_sandwich] {msg}", file=sys.stderr)


def is_color_image(im: Image.Image) -> bool:
    """Detect whether an image contains significant color (e.g. cover or color plate)."""
    if im.mode in ("L", "1"):
        return False
    rgb = im.convert("RGB")
    stat = ImageStat.Stat(rgb)
    r, g, b = stat.mean[:3]
    var_r, var_g, var_b = stat.var[:3]
    diff = abs(r - g) + abs(g - b) + abs(r - b)
    return diff > 8.0 or abs(var_r - var_g) > 25.0


def restore_text_image(
    im: Image.Image,
    apply_unsharp: bool = True,
) -> Image.Image:
    """
    Restore a grayscale text image to pure white background and deep dark ink.
    Uses adaptive background peak detection to avoid crushing thin strokes.
    """
    if im.mode != "L":
        im = im.convert("L")

    hist = im.histogram()
    total = sum(hist)
    if total == 0:
        return im

    # Find paper background level from the top 5% of the histogram
    cum = 0
    p95 = 255
    for val in range(255, -1, -1):
        cum += hist[val]
        if cum / total >= 0.05:
            p95 = val
            break

    in_white = max(215, min(255, p95))
    in_black = 20

    lut = []
    scale = 255.0 / max(1, in_white - in_black)
    for i in range(256):
        if i <= in_black:
            lut.append(0)
        elif i >= in_white:
            lut.append(255)
        else:
            lut.append(int((i - in_black) * scale))
    im = im.point(lut)

    if apply_unsharp:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=60, threshold=3))

    return im


def process_image(
    page_idx: int,
    img_name: str,
    im: Image.Image,
) -> Tuple[int, str, bytes, int, int, str, str]:
    """
    Process image: preserve color or restore text.
    Returns (page_idx, img_name, comp_bytes, width, height, colorspace, filter_name).
    """
    w, h = im.size
    if is_color_image(im):
        # Full-color cover or illustration: preserve RGB with high quality JPEG
        rgb_im = im.convert("RGB")
        buf = io.BytesIO()
        rgb_im.save(buf, format="JPEG", quality=92, optimize=True)
        comp_bytes = buf.getvalue()
        return page_idx, img_name, comp_bytes, w, h, "DeviceRGB", "DCTDecode"
    else:
        # Grayscale text page: adaptive white leveling + zlib compression
        rest_im = restore_text_image(im)
        rw, rh = rest_im.size
        comp_bytes = zlib.compress(rest_im.tobytes(), level=6)
        return page_idx, img_name, comp_bytes, rw, rh, "DeviceGray", "FlateDecode"


def enhance_sandwich_pdf(
    input_pdf_path: Path,
    output_pdf_path: Path,
    max_pages: Optional[int] = None,
    page_indices: Optional[List[int]] = None,
    jobs: int = 4,
) -> None:
    """
    Directly enhances an existing Sandwich PDF by restoring background images
    while preserving the entire searchable vector text layer and bookmarks.
    """
    log(f"Opening base sandwich PDF: {input_pdf_path}")
    pdf = pikepdf.open(input_pdf_path)
    total_pages = len(pdf.pages)
    if page_indices is not None:
        pages_to_process = [i for i in page_indices if 0 <= i < total_pages]
    elif max_pages and max_pages < total_pages:
        pages_to_process = list(range(max_pages))
    else:
        pages_to_process = list(range(total_pages))

    batch_size = max(8, jobs * 4)
    total_extracted = 0
    done_count = 0

    log(f"Processing up to {len(pages_to_process)} pages in batches of {batch_size} with {jobs} worker threads...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        for b_start in range(0, len(pages_to_process), batch_size):
            b_indices = pages_to_process[b_start : b_start + batch_size]
            batch_items: List[Tuple[int, str, Image.Image]] = []
            for idx in b_indices:
                p = pdf.pages[idx]
                res = p.get("/Resources")
                if not res or "/XObject" not in res:
                    continue
                xobj = res["/XObject"]
                img_name = None
                for k in xobj.keys():
                    val = xobj[k]
                    if isinstance(val, pikepdf.Stream) and val.get("/Subtype") == pikepdf.Name("/Image"):
                        img_name = k
                        break
                if not img_name:
                    continue

                try:
                    pdf_img = pikepdf.PdfImage(xobj[img_name])
                    pil_img = pdf_img.as_pil_image()
                    batch_items.append((idx, img_name, pil_img))
                except Exception as exc:
                    log(f"Warning: could not extract image from page {idx + 1}: {exc}")

            if not batch_items:
                continue

            total_extracted += len(batch_items)
            futures = [executor.submit(process_image, item[0], item[1], item[2]) for item in batch_items]
            for f in concurrent.futures.as_completed(futures):
                try:
                    p_idx, i_name, comp_bytes, rw, rh, cs_name, filter_name = f.result()
                    p = pdf.pages[p_idx]
                    xobj = p.Resources.XObject
                    new_img = pikepdf.Stream(
                        pdf,
                        comp_bytes,
                        Type=pikepdf.Name.XObject,
                        Subtype=pikepdf.Name.Image,
                        Width=rw,
                        Height=rh,
                        ColorSpace=pikepdf.Name(f"/{cs_name}"),
                        BitsPerComponent=8,
                        Filter=pikepdf.Name(f"/{filter_name}"),
                    )
                    xobj[i_name] = new_img
                    done_count += 1
                    if done_count % 50 == 0 or done_count == total_extracted:
                        log(f"Processed {done_count} page images...")
                except Exception as e:
                    log(f"Error processing page image: {e}")

            del batch_items

    if page_indices is not None:
        new_pdf = pikepdf.new()
        for idx in page_indices:
            if idx < len(pdf.pages):
                new_pdf.pages.append(pdf.pages[idx])
        pdf = new_pdf
    elif max_pages and len(pdf.pages) > max_pages:
        del pdf.pages[max_pages:]

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(output_pdf_path)
    file_size_mb = output_pdf_path.stat().st_size / (1024 * 1024)
    log(f"Successfully saved Perfect Sandwich PDF: {output_pdf_path} ({len(pdf.pages)} pages, {file_size_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description="AlexandriaSandwich Perfect Sandwich PDF Builder")
    parser.add_argument("--input-pdf", "-i", type=Path, help="Input base sandwich PDF")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output target PDF path")
    parser.add_argument("--max-pages", "-n", type=int, default=None, help="Process first N pages (for test)")
    parser.add_argument("--pages", "-p", type=str, default=None, help="Specific pages (e.g. '27,73' or '1-50')")
    parser.add_argument("--jobs", "-j", type=int, default=4, help="Parallel worker processes")
    args = parser.parse_args()

    t0 = time.time()
    if not args.input_pdf or not args.input_pdf.exists():
        log(f"Error: input PDF not found: {args.input_pdf}")
        sys.exit(1)

    page_indices = None
    if args.pages:
        indices = []
        for part in args.pages.split(","):
            part = part.strip()
            if "-" in part:
                start_p, end_p = part.split("-", 1)
                indices.extend(range(int(start_p) - 1, int(end_p)))
            elif part.isdigit():
                indices.append(int(part) - 1)
        page_indices = sorted(set(indices))

    enhance_sandwich_pdf(args.input_pdf, args.output, max_pages=args.max_pages, page_indices=page_indices, jobs=args.jobs)
    log(f"Total time: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
