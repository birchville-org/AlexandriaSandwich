#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_perfect_sandwich.py

Builds a publication-grade Perfect Sandwich PDF:
1. Restores scanned page images:
   - Preserves full-color covers and color illustrations in native RGB without destructive clipping.
   - Restores text pages via adaptive illumination modeling to achieve pure #FFFFFF paper background
     and deep, crisp black ink without haloing or erasing subtle Sanskrit ligatures/diacritics.
   - High-precision rotational deskewing via projection profile variance optimization.
   - Asymmetric, page-aware Bundsteg/gutter masking (Verso vs. Recto) to completely eliminate binding shadows.
2. Accurately extracts images from the base sandwich PDF via pikepdf.PdfImage (avoiding raw byte distortion).
3. Preserves the entire invisible vector text layer (PDF Render Mode 3).
4. Re-encodes grayscale streams with zlib FlateDecode (and color with DCTDecode), producing
   ultra-clean visual fidelity and compact publication file size.
5. Automated post-build Quality Gate auditing margins for 100% zero-dark-pixel purity.
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

import numpy as np
import pikepdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat


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


def find_skew_projection(im_gray: Image.Image, search_range: float = 2.5, step: float = 0.02) -> float:
    """Measure deskew angle using horizontal projection profile variance optimization."""
    w, h = im_gray.size
    crop = im_gray.crop((int(w * 0.1), int(h * 0.08), int(w * 0.9), int(h * 0.92)))
    sw, sh = crop.size[0] // 2, crop.size[1] // 2
    small = crop.resize((sw, sh), Image.Resampling.BILINEAR)
    arr_small = 255.0 - np.array(small, dtype=np.float32)
    ink_small = Image.fromarray(np.where(arr_small > 50, arr_small, 0.0))

    # Coarse sweep
    angles_coarse = np.arange(-search_range, search_range + 0.1, 0.2)
    best_var = -1.0
    best_angle = 0.0
    for a in angles_coarse:
        rot = ink_small.rotate(a, resample=Image.Resampling.BILINEAR)
        prof = np.sum(np.array(rot), axis=1)
        v = np.var(prof)
        if v > best_var:
            best_var = v
            best_angle = a

    # Fine sweep
    fine_range = 0.25
    angles_fine = np.arange(best_angle - fine_range, best_angle + fine_range + step / 2, step)
    best_fine_var = -1.0
    best_fine_angle = best_angle
    for a in angles_fine:
        rot = ink_small.rotate(a, resample=Image.Resampling.BILINEAR)
        prof = np.sum(np.array(rot), axis=1)
        v = np.var(prof)
        if v > best_fine_var:
            best_fine_var = v
            best_fine_angle = a

    return round(float(best_fine_angle), 3)


def get_page_text_bboxes(pdf_path: Path, mistral_dir: Optional[Path] = None) -> Dict[int, Tuple[float, float, float, float, float, float]]:
    """Extract content bounding box (x0, y0, x1, y1, width, height) per page from Mistral JSON or PDF words."""
    bboxes = {}
    job_dir = pdf_path.parent
    mistral_files = []
    if mistral_dir and mistral_dir.exists():
        mistral_files = sorted(mistral_dir.glob("page-*.mistral.json"))
    if not mistral_files:
        mistral_files = sorted(job_dir.glob("markdown/page-*.mistral.json"))
    if not mistral_files:
        mistral_files = sorted((job_dir.parent / "markdown").glob("page-*.mistral.json"))
    if not mistral_files:
        mistral_files = sorted(job_dir.glob("page-*.mistral.json"))

    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        total_p = len(doc)
    except Exception:
        total_p = 0
        doc = None

    if mistral_files and (total_p == 0 or len(mistral_files) == total_p):
        for idx, mf in enumerate(mistral_files):
            try:
                import json
                with open(mf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                mp = d["pages"][0]
                w = float(mp["dimensions"]["width"])
                h = float(mp["dimensions"]["height"])
                blocks = mp.get("blocks", [])
                if blocks:
                    x0 = float(min(b["top_left_x"] for b in blocks))
                    y0 = float(min(b["top_left_y"] for b in blocks))
                    x1 = float(max(b["bottom_right_x"] for b in blocks))
                    y1 = float(max(b["bottom_right_y"] for b in blocks))
                    bboxes[idx] = (x0, y0, x1, y1, w, h)
            except Exception:
                pass
        if doc:
            doc.close()
        return bboxes

    if doc:
        for idx, p in enumerate(doc):
            rect = p.rect
            words = p.get_text("words")
            # Filter out extreme border noise and edge specks
            clean_words = [
                w for w in words
                if w[1] >= rect.height * 0.03
                and w[3] <= rect.height * 0.97
                and w[0] >= rect.width * 0.02
                and w[2] <= rect.width * 0.98
            ]
            if clean_words:
                wx0 = min(w[0] for w in clean_words)
                wy0 = min(w[1] for w in clean_words)
                wx1 = max(w[2] for w in clean_words)
                wy1 = max(w[3] for w in clean_words)
                bboxes[idx] = (wx0, wy0, wx1, wy1, rect.width, rect.height)
        doc.close()

    return bboxes


def restore_text_image(
    im: Image.Image,
    text_bbox: Optional[Tuple[float, float, float, float, float, float]] = None,
    apply_unsharp: bool = True,
    is_even_page: Optional[bool] = None,
    in_white: int = 225,
    in_black: int = 65,
) -> Image.Image:
    """
    Restore a grayscale text image to pure #FFFFFF white background and deep dark ink.
    Uses multi-scale morphological background subtraction and asymmetric content-aware margin masking
    to completely eliminate gutter shadows, binding stripes, scanner edge artifacts, and paper bleed-through
    without damaging thin Sanskrit ligatures or diacritics.
    """
    if im.mode != "L":
        im = im.convert("L")

    w, h = im.size

    # 1. Multi-scale background illumination modeling
    scale_factor = 4
    sw, sh = max(1, w // scale_factor), max(1, h // scale_factor)
    small = im.resize((sw, sh), Image.Resampling.BILINEAR)

    # Filter size proportional to image resolution
    filter_size = max(11, int(sw * 0.03) | 1)
    blur_radius = max(5, int(filter_size // 2))
    bg_small = small.filter(ImageFilter.MaxFilter(size=filter_size)).filter(ImageFilter.GaussianBlur(radius=blur_radius))
    bg = bg_small.resize((w, h), Image.Resampling.BILINEAR)

    # 2. Local background subtraction (removes shadows, gradients, and paper discoloration)
    diff = ImageChops.subtract(bg, im)
    inv = ImageChops.invert(diff)

    # 3. Dynamic contrast leveling: snap paper to #FFFFFF and deepen ink to rich black
    scale = 255.0 / max(1, in_white - in_black)
    lut = [255 if i >= in_white else (0 if i <= in_black else int((i - in_black) * scale)) for i in range(256)]
    out = inv.point(lut)

    # 4. Content-aware margin masking (asymmetric Verso/Recto gutter removal)
    draw = ImageDraw.Draw(out)
    if text_bbox:
        bx0, by0, bx1, by1, ref_w, ref_h = text_bbox
        scale_x = w / ref_w
        scale_y = h / ref_h

        # Asymmetric padding: tight at the binding gutter (15-20 px) to cut off gutter shadows,
        # wider on outer margins (35-40 px)
        if is_even_page is True:
            # Verso: outer margin is left, inner gutter is right
            pad_left = max(35, int(w * 0.020))
            pad_right = max(15, int(w * 0.010))
        elif is_even_page is False:
            # Recto: inner gutter is left, outer margin is right
            pad_left = max(15, int(w * 0.010))
            pad_right = max(35, int(w * 0.020))
        else:
            pad_left = max(25, int(w * 0.015))
            pad_right = max(25, int(w * 0.015))

        pad_top = max(25, int(h * 0.010))
        pad_bot = max(25, int(h * 0.010))

        safe_x0 = max(0, int(bx0 * scale_x - pad_left))
        safe_y0 = max(0, int(by0 * scale_y - pad_top))
        safe_x1 = min(w, int(bx1 * scale_x + pad_right))
        safe_y1 = min(h, int(by1 * scale_y + pad_bot))

        if safe_x0 > 0:
            draw.rectangle([0, 0, safe_x0, h], fill=255)
        if safe_x1 < w:
            draw.rectangle([safe_x1, 0, w, h], fill=255)
        if safe_y0 > 0:
            draw.rectangle([0, 0, w, safe_y0], fill=255)
        if safe_y1 < h:
            draw.rectangle([0, safe_y1, w, h], fill=255)
    else:
        # Fallback based on image geometry and Verso/Recto
        m_top = int(h * 0.03)
        m_bot = int(h * 0.03)
        draw.rectangle([0, 0, w, m_top], fill=255)
        draw.rectangle([0, h - m_bot, w, h], fill=255)

        if is_even_page is True:
            # Verso: inner gutter right (6%), outer left (4%)
            draw.rectangle([0, 0, int(w * 0.04), h], fill=255)
            draw.rectangle([int(w * 0.94), 0, w, h], fill=255)
        elif is_even_page is False:
            # Recto: inner gutter left (6%), outer right (4%)
            draw.rectangle([0, 0, int(w * 0.06), h], fill=255)
            draw.rectangle([int(w * 0.96), 0, w, h], fill=255)
        else:
            draw.rectangle([0, 0, int(w * 0.03), h], fill=255)
            draw.rectangle([int(w * 0.97), 0, w, h], fill=255)

    # 5. Crisp stroke unsharp mask
    if apply_unsharp:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=3))

    return out


def process_image(
    page_idx: int,
    img_name: str,
    im: Image.Image,
    text_bbox: Optional[Tuple[float, float, float, float, float, float]] = None,
    deskew: bool = False,
    in_white: int = 225,
    in_black: int = 65,
) -> Tuple[int, str, bytes, int, int, str, str, float]:
    """
    Process image: preserve color or restore text.
    Returns (page_idx, img_name, comp_bytes, width, height, colorspace, filter_name, skew_angle).
    """
    w, h = im.size
    is_even = (page_idx % 2 == 0 and page_idx > 0)
    skew_angle = 0.0

    if is_color_image(im):
        # Full-color cover or illustration: preserve RGB with high quality JPEG
        rgb_im = im.convert("RGB")
        buf = io.BytesIO()
        rgb_im.save(buf, format="JPEG", quality=92, optimize=True)
        comp_bytes = buf.getvalue()
        return page_idx, img_name, comp_bytes, w, h, "DeviceRGB", "DCTDecode", 0.0
    else:
        im_gray = im.convert("L")
        if deskew:
            skew_angle = find_skew_projection(im_gray)
            if abs(skew_angle) >= 0.02:
                im_gray = im_gray.rotate(skew_angle, resample=Image.Resampling.BICUBIC, fillcolor=255)

        # Grayscale text page: adaptive white leveling + zlib compression
        rest_im = restore_text_image(
            im_gray,
            text_bbox=text_bbox,
            is_even_page=is_even,
            in_white=in_white,
            in_black=in_black,
        )
        rw, rh = rest_im.size
        comp_bytes = zlib.compress(rest_im.tobytes(), level=6)
        return page_idx, img_name, comp_bytes, rw, rh, "DeviceGray", "FlateDecode", skew_angle


def enhance_sandwich_pdf(
    input_pdf_path: Path,
    output_pdf_path: Path,
    max_pages: Optional[int] = None,
    page_indices: Optional[List[int]] = None,
    jobs: int = 4,
    mistral_dir: Optional[Path] = None,
    deskew: bool = False,
    in_white: int = 225,
    in_black: int = 65,
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

    page_text_bboxes = get_page_text_bboxes(input_pdf_path, mistral_dir=mistral_dir)
    log(f"Extracted content bounding boxes for {len(page_text_bboxes)} pages.")

    log(f"Processing up to {len(pages_to_process)} pages in batches of {batch_size} with {jobs} worker threads (deskew={deskew}, in_white={in_white})...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        for b_start in range(0, len(pages_to_process), batch_size):
            b_indices = pages_to_process[b_start : b_start + batch_size]
            batch_items: List[Tuple[int, str, Image.Image, Any]] = []
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
                    batch_items.append((idx, img_name, pil_img, page_text_bboxes.get(idx)))
                except Exception as exc:
                    log(f"Warning: could not extract image from page {idx + 1}: {exc}")

            if not batch_items:
                continue

            total_extracted += len(batch_items)
            futures = [
                executor.submit(process_image, item[0], item[1], item[2], item[3], deskew, in_white, in_black)
                for item in batch_items
            ]
            for f in concurrent.futures.as_completed(futures):
                try:
                    p_idx, i_name, comp_bytes, rw, rh, cs_name, filter_name, ang = f.result()
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
                        log(f"Processed {done_count} page images (sample deskew: {ang:+.3f}°)...")
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

    # Post-build Quality Gate: verify outer margin purity
    try:
        import pymupdf
        doc_audit = pymupdf.open(output_pdf_path)
        dirty_margins = []
        for pno in range(len(doc_audit)):
            pix = doc_audit[pno].get_pixmap(dpi=150)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))[:, :, 0]
            h, w = arr.shape
            m_left = arr[:, :int(w * 0.05)]
            m_right = arr[:, int(w * 0.95):]
            m_top = arr[:int(h * 0.03), :]
            m_bot = arr[int(h * 0.97):, :]
            dl = int(np.sum(m_left < 200))
            dr = int(np.sum(m_right < 200))
            dt = int(np.sum(m_top < 200))
            db = int(np.sum(m_bot < 200))
            if dl > 0 or dr > 0 or dt > 0 or db > 0:
                dirty_margins.append((pno + 1, dl, dr, dt, db))
        doc_audit.close()
        if dirty_margins:
            log(f"Quality Gate Warning: {len(dirty_margins)} page(s) have dark margin artifacts: {dirty_margins[:5]}")
        else:
            log("Quality Gate Passed: 100% of pages verified with pure #FFFFFF margins (0 dark margin pixels).")
    except Exception as exc:
        log(f"Quality Gate check skipped: {exc}")


def main():
    parser = argparse.ArgumentParser(description="AlexandriaSandwich Perfect Sandwich PDF Builder")
    parser.add_argument("--input-pdf", "-i", type=Path, help="Input base sandwich PDF")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output target PDF path")
    parser.add_argument("--max-pages", "-n", type=int, default=None, help="Process first N pages (for test)")
    parser.add_argument("--pages", "-p", type=str, default=None, help="Specific pages (e.g. '27,73' or '1-50')")
    parser.add_argument("--jobs", "-j", type=int, default=4, help="Parallel worker processes")
    parser.add_argument("--markdown-dir", "--mistral-dir", "-m", type=Path, default=None, help="Directory containing page-*.mistral.json")
    parser.add_argument("--deskew", action="store_true", help="Enable projection profile deskewing")
    parser.add_argument("--in-white", type=int, default=225, help="White point clipping threshold (default: 225)")
    parser.add_argument("--in-black", type=int, default=65, help="Black point clipping threshold (default: 65)")
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

    enhance_sandwich_pdf(
        args.input_pdf,
        args.output,
        max_pages=args.max_pages,
        page_indices=page_indices,
        jobs=args.jobs,
        mistral_dir=args.markdown_dir,
        deskew=args.deskew,
        in_white=args.in_white,
        in_black=args.in_black,
    )
    log(f"Total time: {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
