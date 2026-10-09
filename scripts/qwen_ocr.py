#!/usr/bin/env python3
"""
AlexandriaSandwich — Qwen2.5-VL Local OCR Client
High-precision OCR client targeting local Vision-Language Models (e.g. Qwen2.5-VL)
running on OpenAI-compatible inference servers (Ollama, vLLM, llama-server, LM Studio).

Default endpoint: http://nyx.local:8088/v1
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ENDPOINT = os.environ.get("QWEN_OCR_ENDPOINT", "http://nyx.local:8088/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("QWEN_OCR_MODEL", "")  # Empty = auto-detect from /v1/models
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}

DEFAULT_OCR_PROMPT = (
    "Perform complete, high-precision OCR on this document page. "
    "Transcribe all text accurately, preserving original headings, paragraph breaks, lists, and tables as clean Markdown. "
    "Maintain exact diacritics, transliteration, and non-Latin scripts (e.g. Devanāgarī, Sanskrit ligatures, Fraktur). "
    "Do not hallucinate, summarize, translate, comment, or omit any text. "
    "Output ONLY the transcribed Markdown text without surrounding backticks or preamble."
)


def log(msg: str) -> None:
    print(f"[qwen_ocr] {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
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
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


def check_health(endpoint: str, timeout: float = 3.0) -> Tuple[bool, List[str], Optional[str], str]:
    """Check connectivity to endpoint and return list of available models and currently loaded model."""
    url = f"{endpoint}/models"
    req = urllib.request.Request(url, headers={"User-Agent": "AlexandriaSandwich-QwenOCR/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            loaded_model = None
            raw_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for item in raw_list:
                if isinstance(item, dict):
                    mid = item.get("id", "")
                    if mid:
                        models.append(mid)
                    if item.get("loaded") is True and not loaded_model:
                        loaded_model = mid
            return True, [m for m in models if m], loaded_model, "ok"
    except urllib.error.HTTPError as exc:
        return False, [], None, f"HTTP {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:
        return False, [], None, f"Connection failed: {exc.reason}"
    except Exception as exc:
        return False, [], None, str(exc)


def auto_detect_model(endpoint: str, preferred: str = "") -> str:
    """Detect available models from server and pick preferred, loaded, or matching Qwen/VL model."""
    if preferred:
        return preferred
    ok, models, loaded, err = check_health(endpoint)
    # If the server reports a model that is already loaded in memory (e.g. mlx_vlm.server), use it directly
    if loaded:
        return loaded
    if not ok or not models:
        return "mlx-community/Qwen2.5-VL-7B-Instruct-bf16"

    # Look for Qwen2.5-VL variants
    for m in models:
        m_lower = m.lower()
        if "qwen2.5-vl" in m_lower or "qwen2_5_vl" in m_lower or "qwen2.5vl" in m_lower:
            return m
    # Look for any Qwen VL
    for m in models:
        m_lower = m.lower()
        if "qwen" in m_lower and "vl" in m_lower:
            return m
    # Look for any vision model
    for m in models:
        m_lower = m.lower()
        if "vl" in m_lower or "vision" in m_lower or "ocr" in m_lower:
            return m

    # Default to first model
    return models[0]


def clean_markdown_fences(text: str) -> str:
    """Strip redundant markdown code fences if model enclosed entire response in ```markdown."""
    text = text.strip()
    match = re.match(r"^```(?:markdown|md)?\s*\n([\s\S]*?)\n```$", text, re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    return text + ("\n" if text and not text.endswith("\n") else "")


def ocr_image(
    image_path: Path,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = "",
    prompt: str = DEFAULT_OCR_PROMPT,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    timeout: float = 600.0,
) -> Dict[str, Any]:
    """Execute high-precision OCR on image via OpenAI-compatible vision endpoint."""
    if not image_path.is_file():
        die(f"image not found: {image_path}")

    resolved_model = auto_detect_model(endpoint, model)
    mime = guess_mime(image_path)
    b64_img = base64.b64encode(image_path.read_bytes()).decode("ascii")
    data_url = f"data:{mime};base64,{b64_img}"

    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0 if temperature == 0.0 else temperature,
        "max_tokens": max_tokens,
    }

    url = f"{endpoint}/chat/completions"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AlexandriaSandwich-QwenOCR/1.0",
        },
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - t0
            resp_body = resp.read().decode("utf-8")
            resp_data = json.loads(resp_body)
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        die(f"HTTP {exc.code} from {url}: {err_msg}")
    except urllib.error.URLError as exc:
        die(f"failed to connect to {url}: {exc.reason} (Is the local VLM server running on {endpoint}?)")
    except Exception as exc:
        die(f"unexpected request error: {exc}")

    choices = resp_data.get("choices") or []
    if not choices:
        die(f"empty response from model on {image_path.name}: {resp_data}")

    raw_text = choices[0].get("message", {}).get("content", "")
    clean_text = clean_markdown_fences(raw_text)

    usage = resp_data.get("usage", {})
    return {
        "source": str(image_path),
        "engine": "qwen_vlm",
        "model": resolved_model,
        "endpoint": endpoint,
        "elapsed_seconds": round(elapsed, 3),
        "markdown": clean_text,
        "usage": usage,
        "raw_response": resp_data,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Qwen2.5-VL Local OCR Client for AlexandriaSandwich")
    parser.add_argument("input", nargs="?", type=Path, help="Image file or directory to OCR")
    parser.add_argument("-o", "--output", type=Path, help="Path for output markdown file")
    parser.add_argument("--json", type=Path, help="Optional path for raw response JSON")
    parser.add_argument(
        "-e", "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"OpenAI-compatible VLM base URL (default: {DEFAULT_ENDPOINT} or $QWEN_OCR_ENDPOINT)",
    )
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help="Model ID (default: auto-detected from /v1/models or $QWEN_OCR_MODEL)",
    )
    parser.add_argument("--prompt", default=DEFAULT_OCR_PROMPT, help="Custom OCR system/user prompt")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (default: 0.0)")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max generated tokens (default: 4096)")
    parser.add_argument("--timeout", type=float, default=600.0, help="HTTP request timeout in seconds (default: 600)")
    parser.add_argument("--health", action="store_true", help="Check health and available models at endpoint, then exit")
    parser.add_argument("--input-dir", type=Path, help="Batch directory of image pages")
    parser.add_argument("--output-dir", type=Path, help="Batch output directory for *.qwen.md")
    parser.add_argument("--jobs", "-j", type=int, default=2, help="Concurrency for batch processing")

    args = parser.parse_args(argv)

    if args.health:
        print(f"Checking VLM endpoint: {args.endpoint} ...")
        ok, models, loaded, note = check_health(args.endpoint)
        if ok:
            print(f"✅ Connection successful! Status: {note}")
            print(f"Available models ({len(models)}):")
            for m in models:
                tag = " (currently loaded)" if m == loaded else ""
                print(f"  - {m}{tag}")
            selected = auto_detect_model(args.endpoint, args.model)
            print(f"Selected OCR model: {selected}")
            return 0
        else:
            print(f"❌ Connection failed: {note}")
            print("Hinweis: Starten Sie den lokalen VLM-Server auf nyx.local:8088.")
            return 1

    # Batch mode
    if args.input_dir:
        out_dir = args.output_dir or args.input_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        images = [p for p in args.input_dir.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES]
        images.sort()
        if not images:
            die(f"no supported images found in {args.input_dir}")

        log(f"processing {len(images)} pages in batch (jobs={args.jobs}) against {args.endpoint}...")
        resolved_model = auto_detect_model(args.endpoint, args.model)

        def worker(img_p: Path) -> Tuple[str, bool, float]:
            target_md = out_dir / f"{img_p.stem}.qwen.md"
            target_json = out_dir / f"{img_p.stem}.qwen.json"
            if target_md.is_file() and target_md.stat().st_size > 0:
                return img_p.name, True, 0.0
            try:
                res = ocr_image(
                    img_p,
                    endpoint=args.endpoint,
                    model=resolved_model,
                    prompt=args.prompt,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
                target_md.write_text(res["markdown"], encoding="utf-8")
                target_json.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
                return img_p.name, True, res["elapsed_seconds"]
            except Exception as exc:
                log(f"error on {img_p.name}: {exc}")
                return img_p.name, False, 0.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(worker, images))

        success = sum(1 for _, ok, _ in results if ok)
        log(f"batch completed: {success}/{len(images)} pages successful.")
        return 0 if success == len(images) else 1

    # Single image mode
    if not args.input:
        die("please specify an input image or use --health / --input-dir")

    log(f"running local VLM OCR on {args.input} (endpoint={args.endpoint})...")
    res = ocr_image(
        args.input,
        endpoint=args.endpoint,
        model=args.model,
        prompt=args.prompt,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(res["markdown"], encoding="utf-8")
        log(f"saved markdown -> {args.output} ({len(res['markdown'])} chars, {res['elapsed_seconds']}s)")
    else:
        print(res["markdown"])

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"saved raw JSON -> {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
