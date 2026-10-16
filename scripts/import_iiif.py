#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/import_iiif.py

Universal IIIF Presentation & Image API Ingest Engine (v2 & v3).
Imports high-resolution page scans and metadata directly from library digital manifests
(e.g. UB Heidelberg, British Library, BnF Gallica, BSB München, Internet Archive).

Features:
- Dual-mode support for IIIF Presentation API v2 and v3
- Concurrent image downloading with retry and exponential backoff
- Automatic metadata extraction (title, author, year, publisher, IIIF URLs)
- Generates data/input/<job>/job.config.json and iiif_pages.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def log(msg: str):
    print(f"[{time.strftime('%X')}] [import_iiif] {msg}", file=sys.stderr)


def extract_iiif_string(val: Any) -> str:
    """Extract string from IIIF v2 string or v3 multi-language dictionary."""
    if not val:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        items = [extract_iiif_string(x) for x in val]
        return " / ".join(filter(None, items))
    if isinstance(val, dict):
        # IIIF v3: {"none": ["Title"], "en": ["Title"]}
        res = []
        for _, v in val.items():
            if isinstance(v, list):
                res.extend([str(x) for x in v])
            elif isinstance(v, str):
                res.append(v)
        return " / ".join(res).strip()
    return str(val).strip()


def parse_manifest(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parse IIIF Presentation Manifest (v2 or v3) into unified metadata and canvas list.
    """
    # 1. Metadata
    title = extract_iiif_string(data.get("label", ""))
    meta_dict: Dict[str, Any] = {
        "title": title,
        "author": "",
        "editor": "",
        "year": None,
        "publisher": "",
        "attribution": extract_iiif_string(data.get("attribution") or data.get("requiredStatement", {}).get("value")),
    }

    raw_metadata = data.get("metadata", [])
    if isinstance(raw_metadata, list):
        for item in raw_metadata:
            lbl = extract_iiif_string(item.get("label", "")).lower()
            val = extract_iiif_string(item.get("value", ""))
            if not val:
                continue
            if any(k in lbl for k in ("author", "autor", "creator", "verfasser")):
                if not meta_dict["author"]:
                    meta_dict["author"] = val
            elif any(k in lbl for k in ("editor", "herausgeber", "bearbeiter")):
                if not meta_dict["editor"]:
                    meta_dict["editor"] = val
            elif any(k in lbl for k in ("date", "datum", "jahr", "year", "erscheinungsjahr")):
                m_yr = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", val)
                if m_yr and not meta_dict["year"]:
                    meta_dict["year"] = int(m_yr.group(1))
            elif any(k in lbl for k in ("publisher", "verlag", "drucker")):
                if not meta_dict["publisher"]:
                    meta_dict["publisher"] = val

    # 2. Extract Canvases & Image URLs
    canvases: List[Dict[str, Any]] = []

    # Check IIIF v2 sequences
    seqs = data.get("sequences", [])
    if seqs and isinstance(seqs, list):
        for seq in seqs:
            for c in seq.get("canvases", []):
                c_id = c.get("@id", "")
                label = extract_iiif_string(c.get("label", ""))
                width = c.get("width")
                height = c.get("height")
                img_url = ""
                images = c.get("images", [])
                if images:
                    res = images[0].get("resource", {})
                    service = res.get("service", {})
                    svc_id = service.get("@id") or service.get("id") or ""
                    if svc_id:
                        svc_id = svc_id.rstrip("/")
                        img_url = f"{svc_id}/full/max/0/default.jpg"
                    else:
                        img_url = res.get("@id") or res.get("id") or ""
                canvases.append({
                    "canvas_id": c_id,
                    "label": label,
                    "width": width,
                    "height": height,
                    "image_url": img_url
                })

    # Check IIIF v3 items
    items = data.get("items", [])
    if not canvases and items and isinstance(items, list):
        for c in items:
            c_id = c.get("id", "")
            label = extract_iiif_string(c.get("label", ""))
            width = c.get("width")
            height = c.get("height")
            img_url = ""
            c_items = c.get("items", [])
            if c_items and isinstance(c_items, list):
                anno_page = c_items[0]
                annos = anno_page.get("items", [])
                if annos and isinstance(annos, list):
                    body = annos[0].get("body", {})
                    service = body.get("service", [])
                    svc_id = ""
                    if isinstance(service, list) and service:
                        svc_id = service[0].get("id") or service[0].get("@id") or ""
                    elif isinstance(service, dict):
                        svc_id = service.get("id") or service.get("@id") or ""
                    if svc_id:
                        svc_id = svc_id.rstrip("/")
                        img_url = f"{svc_id}/full/max/0/default.jpg"
                    else:
                        img_url = body.get("id") or ""
            canvases.append({
                "canvas_id": c_id,
                "label": label,
                "width": width,
                "height": height,
                "image_url": img_url
            })

    return meta_dict, canvases


def download_image(url: str, dest_path: Path, max_retries: int = 3, timeout: int = 30) -> bool:
    """Download single IIIF image with exponential backoff retry."""
    if dest_path.is_file() and dest_path.stat().st_size > 1000:
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    headers = {"User-Agent": "AlexandriaSandwich-IIIF/1.5 (Academic Digital Humanities Ingestion)"}
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if len(data) < 200:
                    raise ValueError(f"Downloaded image payload too small ({len(data)} bytes)")
                temp_path.write_bytes(data)
                temp_path.replace(dest_path)
                return True
        except Exception as e:
            delay = 1.5 * (2 ** attempt)
            if attempt == max_retries - 1:
                # If /full/max/ fails, attempt fallback to /full/full/
                if "/full/max/" in url:
                    fallback_url = url.replace("/full/max/", "/full/full/")
                    try:
                        req_fallback = urllib.request.Request(fallback_url, headers=headers)
                        with urllib.request.urlopen(req_fallback, timeout=timeout) as resp:
                            data = resp.read()
                            temp_path.write_bytes(data)
                            temp_path.replace(dest_path)
                            return True
                    except Exception:
                        pass
                log(f"Failed to download {url}: {e} (attempt {attempt+1}/{max_retries})")
            time.sleep(delay)
    return False


def import_iiif_manifest(
    manifest_uri: str,
    job_name: str,
    output_dir: Path,
    limit: Optional[int] = None,
    workers: int = 4,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Import IIIF manifest into AlexandriaSandwich job directory.
    """
    log(f"Fetching IIIF manifest: {manifest_uri}")
    manifest_data: Dict[str, Any] = {}

    if manifest_uri.startswith("http://") or manifest_uri.startswith("https://"):
        req = urllib.request.Request(manifest_uri, headers={"User-Agent": "AlexandriaSandwich/1.5"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            manifest_data = json.loads(resp.read().decode("utf-8"))
    else:
        manifest_path = Path(manifest_uri)
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Local manifest not found: {manifest_path}")
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    meta, canvases = parse_manifest(manifest_data)
    log(f"Parsed manifest: '{meta['title']}', Total Canvases: {len(canvases)}")

    job_input_dir = output_dir / job_name
    job_input_dir.mkdir(parents=True, exist_ok=True)

    # Cache original manifest
    (job_input_dir / "iiif_manifest.json").write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate job.config.json
    job_config: Dict[str, Any] = {
        "$schema": "../../schemas/job.config.schema.json",
        "title": meta.get("title") or job_name,
        "author": meta.get("author") or "",
        "editor": meta.get("editor") or "",
        "year": meta.get("year"),
        "publisher": meta.get("publisher") or "",
        "iiif_manifest": manifest_uri,
        "lang": "deu+eng",
        "threshold": 50.0,
        "use_mistral": True,
        "use_unpaper": True,
        "skip_preprocess": False,
        "limit": limit or 0,
        "heuristics": {
            "script": "Latin",
            "two_column": False,
            "strip_running_headers": True,
            "strip_page_numbers": True,
            "strip_library_boilerplates": True,
            "strip_rogue_scripts": True
        }
    }

    config_file = job_input_dir / "job.config.json"
    if not config_file.exists():
        config_file.write_text(json.dumps(job_config, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"Generated job configuration: {config_file}")

    target_canvases = canvases[:limit] if limit and limit > 0 else canvases

    pages_meta: List[Dict[str, Any]] = []
    download_tasks: List[Tuple[str, Path]] = []

    for idx, c in enumerate(target_canvases):
        p_num = idx + 1
        img_name = f"page_{p_num:04d}.jpg"
        dest_img = job_input_dir / img_name
        img_url = c.get("image_url", "")
        pages_meta.append({
            "page_num": p_num,
            "label": c.get("label", str(p_num)),
            "canvas_id": c.get("canvas_id"),
            "width": c.get("width"),
            "height": c.get("height"),
            "image_url": img_url,
            "filename": img_name
        })
        if img_url and not dry_run:
            download_tasks.append((img_url, dest_img))

    # Save iiif_pages.json mapping
    (job_input_dir / "iiif_pages.json").write_text(json.dumps(pages_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if dry_run:
        log(f"[dry-run] Manifest imported, mapped {len(pages_meta)} pages without download.")
        return {"job": job_name, "title": meta["title"], "pages": len(pages_meta), "downloaded": 0}

    log(f"Downloading {len(download_tasks)} page scans using {workers} worker threads...")
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(download_image, url, path): path for url, path in download_tasks}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                completed += 1
            if completed % 10 == 0 or completed == len(download_tasks):
                print(f"[{time.strftime('%X')}] [import_iiif] Progress: {completed}/{len(download_tasks)} scans downloaded...", file=sys.stderr)

    log(f"Import complete: {completed}/{len(download_tasks)} page scans ready in {job_input_dir}")
    return {
        "job": job_name,
        "title": meta["title"],
        "pages": len(pages_meta),
        "downloaded": completed,
        "input_dir": str(job_input_dir)
    }


def main():
    parser = argparse.ArgumentParser(description="Import book scans and metadata from a IIIF Presentation Manifest (v2/v3)")
    parser.add_argument("-m", "--manifest", required=True, help="URL or local path to IIIF Presentation Manifest (manifest.json)")
    parser.add_argument("-j", "--job", required=True, help="Target job identifier (e.g. boethlingk_heidelberg)")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("data/input"), help="Base input directory (default: data/input)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of pages to download (e.g. 10 for smoke test)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent image download workers (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and generate metadata without downloading image scans")

    args = parser.parse_args()

    try:
        res = import_iiif_manifest(
            manifest_uri=args.manifest,
            job_name=args.job,
            output_dir=args.output_dir,
            limit=args.limit,
            workers=args.workers,
            dry_run=args.dry_run
        )
        print(json.dumps(res, indent=2))
        return 0
    except Exception as e:
        log(f"Error importing IIIF manifest: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
