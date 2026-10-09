#!/usr/bin/env python3
"""
AlexandriaSandwich — Post-Assembly Textlayer-Korrektur (In-PDF invisible text-layer correction)

OCRmyPDF sandwich PDFs store invisible text in Form XObjects using
GlyphLessFont + Identity-H. Operators look like:

  [ <0041006C00650078...> ] TJ

where hex pairs are UTF-16BE code units. This tool rewrites those hex
strings (and plain literal strings) while leaving the image layer intact.

Commands:
  dump      Extract text via pdftotext
  init      Build a corrections template from extracted tokens
  replace   Apply OLD→NEW replacements into the PDF text layer
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    import pikepdf
    from pikepdf import Name, Object, Pdf
except ImportError as exc:  # pragma: no cover
    print(f"Error: pikepdf required: {exc}", file=sys.stderr)
    raise SystemExit(2)


HEX_TOKEN_RE = re.compile(rb"<([0-9A-Fa-f\s]+)>")
# Only attempt UTF-16BE decode/replace on reasonably long hex bodies


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def pdftotext(path: Path, *, layout: bool = True) -> str:
    bin_path = shutil.which("pdftotext")
    if not bin_path:
        die("pdftotext not found (poppler-utils)")
    cmd = [bin_path]
    if layout:
        cmd.append("-layout")
    cmd.extend([str(path), "-"])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"pdftotext failed: {proc.stderr.strip()}")
    return proc.stdout


def load_corrections(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "replace" in data and isinstance(data["replace"], dict):
        mapping = data["replace"]
    elif isinstance(data, dict):
        mapping = {
            k: v
            for k, v in data.items()
            if k not in {"meta", "pages", "notes", "count", "filter", "words"}
            and isinstance(v, str)
        }
    else:
        die("corrections JSON must be an object or {replace:{...}}")
    out = {str(k): str(v) for k, v in mapping.items() if str(k) and str(k) != str(v)}
    # keep identities only if explicitly intended — for apply we skip no-ops later
    if not {str(k): str(v) for k, v in mapping.items() if str(k)}:
        die("no replacements found in corrections file")
    # Prefer non-identity mappings; if user left template as identity, still allow subst CLI
    cleaned = {k: v for k, v in out.items()}
    if not cleaned:
        # Restore raw map if only identities (CLI may still work via -s)
        cleaned = {str(k): str(v) for k, v in mapping.items() if str(k)}
    return dict(sorted(cleaned.items(), key=lambda kv: len(kv[0]), reverse=True))


def apply_mapping_to_text(text: str, mapping: Dict[str, str]) -> Tuple[str, int]:
    if not mapping or not text:
        return text, 0

    stripped = text.strip()
    has_trailing_space = text.endswith(" ")
    has_leading_space = text.startswith(" ")

    # 1. Exact full-token match (safest and most common for OCR token streams)
    if stripped in mapping:
        new_val = mapping[stripped]
        if new_val == "":
            return "", 1
        res = (" " if has_leading_space else "") + new_val + (" " if has_trailing_space else "")
        return res, 1

    # 2. Exact match with original text (including spaces/punctuation)
    if text in mapping:
        new_val = mapping[text]
        return new_val, 1

    # 3. Sub-token matching for compound expressions or literal strings
    current = text
    total = 0
    for old, new in mapping.items():
        if not old or old == new:
            continue
        # Word boundary replacement for alphanumeric words
        if re.match(r"^\w+$", old):
            pattern = re.compile(r"(?<!\w)" + re.escape(old) + r"(?!\w)")
            new_current, n = pattern.subn(new, current)
            if n:
                current = new_current
                total += n
        else:
            # If old contains punctuation / dots / noise:
            # Only match substring if len(old) >= 3 to avoid short punctuation collateral damage
            if len(old) >= 3 and old in current:
                current = current.replace(old, new)
                total += 1

    return current, total


def decode_pdf_literal(data: bytes) -> str:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b != 0x5C:
            out.append(b)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        esc = data[i]
        i += 1
        if esc == 0x6E:
            out.append(0x0A)
        elif esc == 0x72:
            out.append(0x0D)
        elif esc == 0x74:
            out.append(0x09)
        elif esc == 0x62:
            out.append(0x08)
        elif esc == 0x66:
            out.append(0x0C)
        elif esc in (0x28, 0x29, 0x5C):
            out.append(esc)
        elif 0x30 <= esc <= 0x37:
            oct_digits = bytes([esc])
            for _ in range(2):
                if i < n and 0x30 <= data[i] <= 0x37:
                    oct_digits += bytes([data[i]])
                    i += 1
                else:
                    break
            out.append(int(oct_digits, 8) & 0xFF)
        else:
            out.append(esc)
    return out.decode("latin-1", errors="replace")


def encode_pdf_literal(text: str) -> bytes:
    raw = text.encode("latin-1", errors="replace")
    out = bytearray()
    for b in raw:
        if b in (0x28, 0x29, 0x5C):
            out.append(0x5C)
            out.append(b)
        elif b == 0x0A:
            out.extend(b"\\n")
        elif b == 0x0D:
            out.extend(b"\\r")
        elif b == 0x09:
            out.extend(b"\\t")
        else:
            out.append(b)
    return bytes(out)


def utf16be_hex_encode(text: str) -> bytes:
    """Encode text to PDF hex string body (no angle brackets), UTF-16BE code units."""
    return text.encode("utf-16-be").hex().upper().encode("ascii")


def utf16be_hex_decode(hex_body: bytes) -> Optional[str]:
    cleaned = re.sub(rb"\s+", b"", hex_body)
    if len(cleaned) < 4 or len(cleaned) % 2 != 0:
        return None
    # Prefer even number of bytes; UTF-16BE needs even byte length
    try:
        raw = bytes.fromhex(cleaned.decode("ascii"))
    except ValueError:
        return None
    if len(raw) % 2 != 0:
        return None
    try:
        return raw.decode("utf-16-be")
    except UnicodeDecodeError:
        return None


def transform_hex_token(hex_body: bytes, mapping: Dict[str, str]) -> Tuple[bytes, int]:
    text = utf16be_hex_decode(hex_body)
    if text is None:
        return hex_body, 0
    new_text, hits = apply_mapping_to_text(text, mapping)
    if not hits:
        return hex_body, 0
    return utf16be_hex_encode(new_text), hits


def transform_content_stream(data: bytes, mapping: Dict[str, str]) -> Tuple[bytes, int]:
    """Rewrite UTF-16BE hex strings and plain literal strings in a content stream."""
    applied = 0
    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        b = data[i]

        # Hex string <...>
        if b == 0x3C:  # '<'
            # Avoid messing with dict marks like <<
            if i + 1 < n and data[i + 1] == 0x3C:
                out.append(b)
                i += 1
                continue
            j = i + 1
            body = bytearray()
            while j < n and data[j] != 0x3E:
                body.append(data[j])
                j += 1
            if j >= n:
                out.append(b)
                i += 1
                continue
            # body should be hex-ish
            new_body, hits = transform_hex_token(bytes(body), mapping)
            applied += hits
            out.append(0x3C)
            out.extend(new_body)
            out.append(0x3E)
            i = j + 1
            continue

        # Literal string (...)
        if b == 0x28:  # '('
            i += 1
            body = bytearray()
            depth = 1
            while i < n and depth:
                c = data[i]
                if c == 0x5C and i + 1 < n:
                    body.append(c)
                    body.append(data[i + 1])
                    i += 2
                    continue
                if c == 0x28:
                    depth += 1
                    body.append(c)
                    i += 1
                    continue
                if c == 0x29:
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                    body.append(c)
                    i += 1
                    continue
                body.append(c)
                i += 1
            text = decode_pdf_literal(bytes(body))
            new_text, hits = apply_mapping_to_text(text, mapping)
            applied += hits
            out.append(0x28)
            out.extend(encode_pdf_literal(new_text))
            out.append(0x29)
            continue

        out.append(b)
        i += 1

    return bytes(out), applied


def iter_stream_objects(pdf: Pdf) -> Iterable[Tuple[str, Object]]:
    seen = set()
    found: List[Tuple[str, Object]] = []

    def add(label: str, obj: Object) -> None:
        try:
            if not hasattr(obj, "read_bytes"):
                return
            key = getattr(obj, "objgen", None) or id(obj)
            if key in seen:
                return
            seen.add(key)
            found.append((label, obj))
        except Exception:
            return

    def walk_xobjects(prefix: str, xobjects) -> None:
        if xobjects is None:
            return
        for name, xobj in xobjects.items():
            try:
                subtype = xobj.get("/Subtype")
            except Exception:
                subtype = None
            is_form = subtype == Name("/Form") or (
                subtype is None and hasattr(xobj, "read_bytes") and subtype != Name("/Image")
            )
            if subtype == Name("/Image"):
                continue
            if is_form or hasattr(xobj, "read_bytes"):
                # Only Form streams carry text for post-assembly textlayer correction
                if subtype == Name("/Form") or (hasattr(xobj, "read_bytes") and subtype != Name("/Image")):
                    if subtype == Name("/Form"):
                        add(f"{prefix}.xobject{name}", xobj)
                        try:
                            nested = xobj.get("/Resources")
                            if nested is not None:
                                walk_xobjects(f"{prefix}.xobject{name}", nested.get("/XObject"))
                        except Exception:
                            pass
                    elif subtype is None:
                        # unknown stream; skip binary images by size heuristic elsewhere
                        pass

    for page_idx, page in enumerate(pdf.pages):
        contents = page.get("/Contents")
        if contents is not None:
            if isinstance(contents, pikepdf.Array):
                for j, part in enumerate(contents):
                    add(f"page{page_idx}.contents[{j}]", part)
            else:
                add(f"page{page_idx}.contents", contents)
        resources = page.get("/Resources")
        if resources is not None:
            walk_xobjects(f"page{page_idx}", resources.get("/XObject"))

    for item in found:
        yield item


def replace_in_pdf(src: Path, dst: Path, mapping: Union[Dict[str, str], List[Dict[str, str]]]) -> dict:
    pdf = Pdf.open(src)
    total = 0
    touched = []
    is_list = isinstance(mapping, list)

    for label, obj in iter_stream_objects(pdf):
        try:
            data = obj.read_bytes()
        except Exception:
            continue
        # skip huge binary-like streams
        if len(data) > 2_000_000:
            continue

        if is_list:
            m_p = re.search(r"page(\d+)", label)
            pidx = int(m_p.group(1)) if m_p else -1
            cur_map = mapping[pidx] if 0 <= pidx < len(mapping) else {}
        else:
            cur_map = mapping

        if not cur_map:
            continue

        new_data, hits = transform_content_stream(data, cur_map)
        if hits:
            obj.write(new_data)
            total += hits
            touched.append({"stream": label, "replacements": hits})

    pdf.save(dst)
    pdf.close()
    return {
        "source": str(src),
        "output": str(dst),
        "replacement_hits": total,
        "streams_touched": touched,
        "mapping": mapping if not is_list else {"pages_mapped": len(mapping)},
    }


def cmd_dump(args: argparse.Namespace) -> int:
    if not args.pdf.is_file():
        die(f"not found: {args.pdf}")
    text = pdftotext(args.pdf)
    payload = {
        "source": str(args.pdf),
        "text": text,
        "pages": text.count("\f") + (1 if text.strip() else 0),
    }
    if args.json:
        out = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out + "\n", encoding="utf-8")
        else:
            print(out)
    else:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Wrote text -> {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def cmd_replace(args: argparse.Namespace) -> int:
    if not args.pdf.is_file():
        die(f"not found: {args.pdf}")
    mapping: Dict[str, str] = {}
    if args.corrections:
        mapping.update(load_corrections(args.corrections))
    for item in args.subst or []:
        if "=" not in item:
            die(f"--subst expects OLD=NEW, got: {item}")
        old, new = item.split("=", 1)
        mapping[old] = new
    mapping = {k: v for k, v in mapping.items() if k and k != v}
    if not mapping:
        die("provide --corrections and/or --subst OLD=NEW with actual changes")

    out = args.output or args.pdf.with_name(args.pdf.stem.replace(".sandwich", "") + ".aligned.pdf")
    with tempfile.TemporaryDirectory(prefix="as-aligned-") as tmp:
        tmp_out = Path(tmp) / "out.pdf"
        summary = replace_in_pdf(args.pdf, tmp_out, mapping)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp_out, out)
        summary["output"] = str(out)
        summary["text_after"] = pdftotext(out)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Post-Assembly Textlayer: hits={summary['replacement_hits']} "
            f"streams={len(summary['streams_touched'])} -> {out}",
            file=sys.stderr,
        )
        sys.stdout.write(summary["text_after"])
        if not summary["text_after"].endswith("\n"):
            sys.stdout.write("\n")
    if summary["replacement_hits"] == 0:
        print("Warning: no replacements applied (encoding/key mismatch?)", file=sys.stderr)
        return 1
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if not args.pdf.is_file():
        die(f"not found: {args.pdf}")
    text = pdftotext(args.pdf)
    tokens = sorted(set(re.findall(r"[A-Za-zÄÖÜäöüß]{3,}|\d{3,}", text)))
    template = {
        "meta": {
            "source": str(args.pdf),
            "instructions": (
                "Edit replace values (OLD identity placeholders). "
                "Then: pdf_text_correct.py replace PDF -c THIS.json -o OUT.pdf"
            ),
            "extracted_preview": text[:500],
        },
        "replace": {tok: tok for tok in tokens[:50]},
    }
    out = args.output or Path(str(args.pdf) + ".aligned.corrections.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Post-Assembly In-PDF text-layer correction (aligned PDF)")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dump", help="Extract text from sandwich PDF")
    d.add_argument("pdf", type=Path)
    d.add_argument("-o", "--output", type=Path)
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_dump)

    r = sub.add_parser("replace", help="Replace strings in invisible text layer")
    r.add_argument("pdf", type=Path)
    r.add_argument("-o", "--output", type=Path)
    r.add_argument("-c", "--corrections", type=Path)
    r.add_argument("-s", "--subst", action="append", default=[])
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_replace)

    i = sub.add_parser("init", help="Create aligned corrections template")
    i.add_argument("pdf", type=Path)
    i.add_argument("-o", "--output", type=Path)
    i.set_defaults(func=cmd_init)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
