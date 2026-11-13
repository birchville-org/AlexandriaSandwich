#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/extract_italics_pixtral.py

Uses Pixtral (pixtral-12b-2409) vision to inspect the original page scans
and extract every word, title, transliteration, and citation printed in italics (kurzíva).
Saves results to data/output/alexandros_czech/ocr/page_*.italics.json.
"""
from __future__ import annotations

import base64
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

from mistralai.client import Mistral

ocr_dir = Path("data/output/alexandros_czech/ocr")
img_dir = Path("data/input/alexandros_czech/pages")

api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    print("Error: MISTRAL_API_KEY environment variable not set", file=sys.stderr)
    sys.exit(1)

client = Mistral(api_key=api_key)


def process_page(pnum: int) -> tuple[int, list[str]]:
    out_json = ocr_dir / f"page_{pnum:03d}.italics.json"
    if out_json.exists():
        try:
            data = json.loads(out_json.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return pnum, data
        except Exception:
            pass

    img_path = img_dir / f"page_{pnum:03d}.png"
    ocr_path = ocr_dir / f"page_{pnum:03d}.mistral.md"
    
    if not img_path.exists() or not ocr_path.exists():
        print(f"Skipping page {pnum}: missing file")
        return pnum, []

    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    ocr_text = ocr_path.read_text(encoding="utf-8")

    prompt = f"""You are an expert scholarly typesetter and editor.
Here is an image of printed Czech academic book page {pnum} and here is its OCR text:

<OCR_TEXT>
{ocr_text}
</OCR_TEXT>

Carefully inspect the original image to identify EVERY word, title, term, phrase, or citation that is printed in ITALICS (kurzíva).
Academic books in this series italicize:
1. Foreign transliterated book/treatise titles (e.g. Kitāb al-amānāt, Sefer ha-egron, al-Radd, Sefer ha-galuj, Sefer ha-qabbalah, etc.)
2. Western book, journal, and article titles in footnotes (e.g. The Geonim of Babylonia, Saadia Gaon, etc.)
3. Arabic/Hebrew transliterated terms and names (e.g. amāna, i'tiqād, kalām, sidur, aluf, kátib, masoreti, etc.)
4. Latin terms (e.g. eximius monarcha medicinae, etc.)
5. Hebrew/Aramaic phrases or titles

Return a clean JSON list of the exact substring(s) as they appear in the OCR text that are italicized on this page.
Output ONLY a valid JSON array of strings, e.g. ["phrase 1", "phrase 2"]. Do not include markdown codeblocks or commentary.
"""

    for attempt in range(3):
        try:
            response = client.chat.complete(
                model="pixtral-12b-2409",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"}
                        ]
                    }
                ],
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            # Clean possible markdown fence
            if raw.startswith("```"):
                lines = raw.splitlines()
                if lines[0].startswith("```"):
                    lines.pop(0)
                if lines and lines[-1].startswith("```"):
                    lines.pop(-1)
                raw = "\n".join(lines).strip()
                
            data = json.loads(raw)
            if isinstance(data, list):
                out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"✓ Page {pnum}: extracted {len(data)} italic spans")
                return pnum, data
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
            
    print(f"✗ Page {pnum}: failed after 3 attempts")
    return pnum, []


def main():
    pages = list(range(11, 65))
    print(f"Extracting italic spans across {len(pages)} pages using Pixtral...")
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(process_page, p): p for p in pages}
        for future in concurrent.futures.as_completed(futures):
            pnum, data = future.result()
            results[pnum] = data
            
    total_spans = sum(len(v) for v in results.values())
    print(f"\nAll done! Extracted a total of {total_spans} italic spans across {len(pages)} pages.")


if __name__ == "__main__":
    main()
