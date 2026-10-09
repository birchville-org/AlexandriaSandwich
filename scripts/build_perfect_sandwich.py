#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_perfect_sandwich.py

Builds a publication-grade Perfect Sandwich PDF:
1. Restores scanned page images (contrast leveling 15%..82%, unsharp masking,
   margin and thumb cleanup) to achieve pure #FFFFFF paper background and crisp dark ink.
2. Injects or preserves the invisible OCR text layer (PDF Render Mode 3).
3. Re-encodes image streams with zlib FlateDecode, drastically improving visual quality
   and reducing file size (e.g. 278 MB -> ~60 MB).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import os
import re
import sys
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pikepdf
from PIL import Image, ImageDraw, ImageFilter


def log(msg: str):
    print(f"[{time.strftime('%X')}] [perfect_sandwich] {msg}", file=sys.stderr)


def restore_pil_image(
    im: Image.Image,
    level_low: float = 0.15,
    level_high: float = 0.82,
    apply_unsharp: bool = True,
    mask_margins: bool = True,
) -> Image.Image:
    """
    Restore a grayscale PIL image to pure white background and deep dark ink.
    """
    if im.mode != "L":
        im = im.convert("L")
    w, h = im.size

    # 1. Leveling (Contrast adjustment)
    in_black = int(level_low * 255)
    in_white = int(level_high * 255)
    
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

    # 2. Border & thumb cleanup (masking)
    if mask_margins:
        draw = ImageDraw.Draw(im)
        mx = max(3, int(w * 0.015))
        my = max(3, int(h * 0.015))
        draw.rectangle([0, 0, w, my], fill=255)
        draw.rectangle([0, h - my, w, h], fill=255)
        draw.rectangle([0, 0, mx, h], fill=255)
        draw.rectangle([w - mx, 0, w, h], fill=255)

        # Bottom-left corner thumb / scanner clamp
        bl_w = int(w * 0.08)
        bl_h = int(h * 0.08)
        crop_bl = im.crop((0, h - bl_h, bl_w, h))
        hist_bl = crop_bl.histogram()
        dark_bl = sum(hist_bl[:140])
        if dark_bl > (bl_w * bl_h * 0.04):
            draw.rectangle([0, h - bl_h, bl_w, h], fill=255)

        # Bottom-right corner thumb
        crop_br = im.crop((w - bl_w, h - bl_h, w, h))
        hist_br = crop_br.histogram()
        dark_br = sum(hist_br[:140])
        if dark_br > (bl_w * bl_h * 0.04):
            draw.rectangle([w - bl_w, h - bl_h, w, h], fill=255)

    # 3. Unsharp Mask for crisp type edges
    if apply_unsharp:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))

    return im


def process_page_image(
    page_idx: int,
    raw_bytes: bytes,
    w: int,
    h: int,
    cs: str,
    bpc: int,
) -> Tuple[int, bytes, int, int]:
    """Worker function for multiprocessing."""
    if cs == "/DeviceGray" and bpc == 8:
        im = Image.frombytes("L", (w, h), raw_bytes)
    else:
        # Fallback via io
        try:
            im = Image.open(io.BytesIO(raw_bytes))
        except Exception:
            im = Image.frombytes("L", (w, h), raw_bytes)
    
    rest_im = restore_pil_image(im)
    rest_w, rest_h = rest_im.size
    comp_bytes = zlib.compress(rest_im.tobytes(), level=9)
    return page_idx, comp_bytes, rest_w, rest_h


def enhance_sandwich_pdf(
    input_pdf_path: Path,
    output_pdf_path: Path,
    max_pages: Optional[int] = None,
    page_indices: Optional[List[int]] = None,
    jobs: int = 4,
) -> None:
    """
    Directly enhances an existing Sandwich PDF by restoring its background images
    in-place while preserving the entire searchable vector text layer.
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

    log(f"Processing {len(pages_to_process)} pages with {jobs} worker threads...")

    # Extract images metadata for workers
    work_items = []
    for idx in pages_to_process:
        p = pdf.pages[idx]
        res = p.get("/Resources")
        if not res or "/XObject" not in res:
            continue
        xobj = res["/XObject"]
        # Find image object (typically /Im0 or first /Subtype /Image)
        img_name = None
        for k in xobj.keys():
            val = xobj[k]
            if isinstance(val, pikepdf.Stream) and val.get("/Subtype") == pikepdf.Name("/Image"):
                img_name = k
                break
        if not img_name:
            continue
        
        img_stream = xobj[img_name]
        w = int(img_stream.get("/Width", 0))
        h = int(img_stream.get("/Height", 0))
        cs = str(img_stream.get("/ColorSpace", "/DeviceGray"))
        bpc = int(img_stream.get("/BitsPerComponent", 8))
        raw_bytes = img_stream.read_bytes()
        work_items.append((idx, img_name, raw_bytes, w, h, cs, bpc))

    log(f"Found {len(work_items)} page images to restore.")

    # Process in parallel
    restored_map: Dict[int, Tuple[str, bytes, int, int]] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(process_page_image, item[0], item[2], item[3], item[4], item[5], item[6]): (item[0], item[1])
            for item in work_items
        }
        done_count = 0
        for f in concurrent.futures.as_completed(futures):
            p_idx, img_name = futures[f]
            try:
                res_idx, comp_bytes, rw, rh = f.result()
                restored_map[res_idx] = (img_name, comp_bytes, rw, rh)
                done_count += 1
                if done_count % 50 == 0 or done_count == len(work_items):
                    log(f"Restored {done_count}/{len(work_items)} pages...")
            except Exception as e:
                log(f"Error on page {p_idx}: {e}")

    # Inject restored images back into PDF
    log("Injecting restored images into PDF...")
    for idx, (img_name, comp_bytes, rw, rh) in restored_map.items():
        p = pdf.pages[idx]
        xobj = p.Resources.XObject
        old_img = xobj[img_name]
        new_img = pikepdf.Stream(
            pdf,
            comp_bytes,
            Type=pikepdf.Name.XObject,
            Subtype=pikepdf.Name.Image,
            Width=rw,
            Height=rh,
            ColorSpace=pikepdf.Name.DeviceGray,
            BitsPerComponent=8,
            Filter=pikepdf.Name.FlateDecode,
        )
        xobj[img_name] = new_img

    # If page_indices or max_pages was specified, construct clean output pages
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
    parser.add_argument("--input-pdf", "-i", type=Path, help="Input base sandwich PDF (e.g. Dhatu-patha.sandwich.pdf)")
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
