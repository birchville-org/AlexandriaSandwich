#!/usr/bin/env python3
"""
AlexandriaSandwich - Mistral OCR Helper

High-precision OCR fallback when Tesseract confidence < threshold.
Uses official mistralai SDK (mistral-ocr-latest).
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence


DEFAULT_MODEL = os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff", ".tif", ".pdf", ".bmp"}


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")


def build_document(path: Path) -> dict:
    """Build SDK document payload: image base64 data-URL or PDF as document_url data-URL."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = guess_mime(path)
    data_url = f"data:{mime};base64,{b64}"
    if path.suffix.lower() == ".pdf" or mime == "application/pdf":
        return {
            "type": "document_url",
            "document_url": data_url,
        }
    return {
        "type": "image_url",
        "image_url": data_url,
    }


def get_client(api_key: str):
    # mistralai 1.x exported Mistral at top-level; 2.x nests under mistralai.client
    try:
        from mistralai.client import Mistral  # type: ignore
    except ImportError:
        try:
            from mistralai import Mistral  # type: ignore
        except ImportError as exc:
            die(f"mistralai SDK not installed: {exc}")
    return Mistral(api_key=api_key)


def response_to_dict(resp: Any) -> dict:
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    if hasattr(resp, "dict"):
        return resp.dict()
    if isinstance(resp, dict):
        return resp
    return {"raw": str(resp)}


def extract_markdown(payload: dict) -> str:
    pages = payload.get("pages") or []
    parts = []
    for i, page in enumerate(pages):
        md = page.get("markdown") if isinstance(page, dict) else getattr(page, "markdown", None)
        if md:
            parts.append(md if isinstance(md, str) else str(md))
        elif isinstance(page, dict) and page.get("text"):
            parts.append(str(page["text"]))
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def process_with_mistral(
    image_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    include_image_base64: bool = False,
    pages: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    key = api_key or os.environ.get("MISTRAL_API_KEY")
    if not key:
        die("MISTRAL_API_KEY environment variable not set", code=2)
    if not image_path.is_file():
        die(f"file not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        die(f"unsupported file type: {image_path.suffix} (supported: {sorted(SUPPORTED_SUFFIXES)})")

    client = get_client(key)
    document = build_document(image_path)

    kwargs: dict[str, Any] = {
        "model": model,
        "document": document,
        "include_image_base64": include_image_base64,
    }
    if pages:
        kwargs["pages"] = pages

    print(f"Sende {image_path} an Mistral OCR ({model})...", file=sys.stderr)
    try:
        resp = client.ocr.process(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surface API errors cleanly
        die(f"Mistral OCR request failed: {exc}", code=1)

    payload = response_to_dict(resp)
    markdown = extract_markdown(payload)
    return {
        "source": str(image_path),
        "model": model,
        "markdown": markdown,
        "pages": payload.get("pages"),
        "usage_info": payload.get("usage_info") or payload.get("usage"),
        "raw": payload,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AlexandriaSandwich Mistral OCR fallback")
    parser.add_argument("path", type=Path, help="Image or PDF path")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"OCR model (default {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write markdown to this file (default: <stem>.mistral.md beside input)",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        type=Path,
        help="Also write full JSON response to this path",
    )
    parser.add_argument(
        "--pages",
        help="Optional page selection (from 0), e.g. '0-2' or '0,2-4'",
    )
    parser.add_argument(
        "--include-image-base64",
        action="store_true",
        help="Ask API to include extracted image base64 (larger response)",
    )
    parser.add_argument(
        "--stdout-md",
        action="store_true",
        help="Print markdown to stdout instead of only writing a file",
    )
    args = parser.parse_args(argv)

    result = process_with_mistral(
        args.path,
        model=args.model,
        include_image_base64=args.include_image_base64,
        pages=args.pages,
    )

    out_md = args.output or args.path.with_suffix(args.path.suffix + ".mistral.md")
    # nicer default for many inputs: stem.mistral.md
    if args.output is None:
        out_md = args.path.with_name(args.path.stem + ".mistral.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(result["markdown"] or "", encoding="utf-8")
    print(f"Wrote markdown: {out_md}", file=sys.stderr)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        # avoid dumping huge base64 unless requested
        dump = {
            "source": result["source"],
            "model": result["model"],
            "markdown": result["markdown"],
            "usage_info": result["usage_info"],
            "pages": result["pages"],
        }
        args.json_out.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote JSON: {args.json_out}", file=sys.stderr)

    if args.stdout_md:
        sys.stdout.write(result["markdown"] or "")
        if result["markdown"] and not result["markdown"].endswith("\n"):
            sys.stdout.write("\n")

    if not result["markdown"]:
        print("Warning: empty markdown from Mistral OCR", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
