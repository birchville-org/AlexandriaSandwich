#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/clean_alexandros.py

High-precision scanner shadow and border glare restoration for Alexandros_Tschechisch.pdf:
- Splits each landscape double-page spread (3661 x 2822 px) into Verso (Left) and Recto (Right).
- Automatically detects empty flyleaves and renders them pure #FFFFFF.
- Detects the authentic text bounding box (including top running headers, body text,
  footnotes, and bottom page numbers) using adaptive projection profiles.
- Wipes all pixels outside the authentic content area to pure #FFFFFF:
  * Eliminates outer top, bottom, and side scanner edge shadows.
  * Eliminates the dark vertical binding gutter shadow between the pages.
- Applies gentle background leveling inside the text area to ensure pristine white paper
  while strictly preserving all Czech diacritical marks (háčky, čárky, kroužek).
- Reassembles the cleaned halves into full 3661 x 2822 double spreads.
- Generates a pristine output PDF matching the original dimensions (878.64 x 677.28 pt).
"""
import io
import os
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image
import pymupdf


def clean_half_page(half: np.ndarray, side: str, pad: int = 25) -> np.ndarray:
    """
    Cleans one half (Verso or Recto) of a double spread:
    - side: 'L' for Verso (left), 'R' for Recto (right)
    - pad: safety margin padding around detected content box (in pixels)
    """
    h, w = half.shape
    
    # Typography candidate window (avoids capturing scanner edge artifacts)
    # Verso: page number on left (x >= 200), text ends at inner gutter (x <= 1750)
    # Recto: text starts at inner gutter (x >= 110), page number on right (x <= 1660)
    win = (90, 2630, 200, 1750) if side == "L" else (90, 2630, 110, 1660)
    ymin, ymax, xmin, xmax = win
    
    sub = half[ymin:ymax, xmin:xmax]
    ink = (sub < 180).astype(np.uint8)
    
    # Check if page is blank (e.g. Spread 0 Left)
    if np.mean(ink) < 0.003:
        return np.full_like(half, 255)
    
    # Locate text boundaries via row and column projection profiles
    rows = np.where(np.sum(ink, axis=1) > 5)[0]
    cols = np.where(np.sum(ink, axis=0) > 5)[0]
    
    if len(rows) == 0 or len(cols) == 0:
        return np.full_like(half, 255)
    
    y0, y1 = rows[0] + ymin, rows[-1] + ymin
    x0, x1 = cols[0] + xmin, cols[-1] + xmin
    
    top = max(0, y0 - pad)
    bot = min(h, y1 + pad)
    left = max(0, x0 - pad)
    right = min(w, x1 + pad)
    
    cleaned = half.copy()
    
    # Hard wipe margins outside detected content area (removes shadows, gutter, borders)
    cleaned[:top, :] = 255
    cleaned[bot:, :] = 255
    cleaned[:, :left] = 255
    cleaned[:, right:] = 255
    
    # Background leveling inside text content box:
    # Gentle linear stretch: map paper background (>= 210) to 255, keep ink (<= 70) deep black
    box = cleaned[top:bot, left:right]
    box_f = box.astype(np.float32)
    leveled = np.clip((box_f - 70.0) / (210.0 - 70.0) * 255.0, 0, 255).astype(np.uint8)
    cleaned[top:bot, left:right] = leveled
    
    return cleaned


def clean_pdf(input_path: Path, output_path: Path) -> None:
    doc_in = pymupdf.open(str(input_path))
    doc_out = pymupdf.open()
    total_pages = len(doc_in)
    
    print(f"Opening '{input_path.name}' ({total_pages} pages)...")
    t0 = time.time()
    
    for pno in range(total_pages):
        page = doc_in[pno]
        rect = page.rect
        img_info = page.get_images()[0]
        base_img = doc_in.extract_image(img_info[0])
        
        orig_im = Image.open(io.BytesIO(base_img["image"])).convert("L")
        arr = np.array(orig_im)
        h, w = arr.shape
        mid = w // 2
        
        # Clean left and right halves independently
        cleaned_l = clean_half_page(arr[:, :mid], "L")
        cleaned_r = clean_half_page(arr[:, mid:], "R")
        
        # Reassemble double spread
        cleaned_spread = np.hstack([cleaned_l, cleaned_r])
        out_im = Image.fromarray(cleaned_spread)
        
        # Encode as JPEG with high quality to preserve file balance and fast rendering
        buf = io.BytesIO()
        out_im.save(buf, format="JPEG", quality=95, optimize=True)
        
        new_page = doc_out.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, stream=buf.getvalue())
        
        print(f"  Spread {pno + 1:02d}/{total_pages:02d} processed.")
        
    doc_out.save(str(output_path), garbage=4, deflate=True)
    doc_out.close()
    doc_in.close()
    
    elapsed = time.time() - t0
    out_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Saved cleaned PDF: '{output_path}' in {elapsed:.1f}s ({out_size_mb:.2f} MB)")


def main():
    pcloud_dir = Path(os.environ.get("ALEXANDRIA_PCLOUD_DIR", str(Path.home() / "pCloud Drive" / "70_AlexandriaSandwich")))
    input_file = pcloud_dir / "Alexandros_Tschechisch.pdf"
    output_file = pcloud_dir / "Alexandros_Tschechisch_bereinigt.pdf"
    
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
        
    clean_pdf(input_file, output_file)


if __name__ == "__main__":
    main()
