#!/usr/bin/env python3
"""
AlexandriaSandwich — Path A: Pre-PDF hOCR correction helpers

Path A corrects the OCR text layer before sandwich assembly:
  1) dump low-confidence / all words from hOCR (or TSV)
  2) edit a corrections JSON
  3) apply patches back into hOCR (preserves bboxes; optional conf bump)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TITLE_FIELDS_RE = re.compile(r"(\w+)\s+([^;]+)")
WORD_CLASSES = {"ocrx_word", "ocr_word"}


@dataclass
class WordToken:
    id: str
    text: str
    conf: Optional[float]
    bbox: Optional[Tuple[int, int, int, int]]
    title: str
    source: str
    index: int


def die(msg: str, code: int = 2) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_title(title: str) -> dict:
    out: dict = {}
    for key, raw in TITLE_FIELDS_RE.findall(title or ""):
        val = raw.strip()
        if key == "bbox":
            parts = val.split()
            if len(parts) == 4:
                try:
                    out["bbox"] = tuple(int(float(p)) for p in parts)
                except ValueError:
                    pass
        elif key == "x_wconf":
            try:
                out["conf"] = float(val)
            except ValueError:
                pass
        else:
            out[key] = val
    return out


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_word_elements(root: ET.Element) -> Iterable[ET.Element]:
    for el in root.iter():
        cls = el.attrib.get("class", "")
        classes = set(cls.split())
        title = el.attrib.get("title", "")
        if classes & WORD_CLASSES:
            yield el
        elif "x_wconf" in title and local(el.tag) == "span":
            yield el


def load_hocr_words(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        die(f"invalid hOCR XML in {path}: {exc}")
    tree = ET.ElementTree(root)
    pairs = []
    idx = 0
    for el in iter_word_elements(root):
        meta = parse_title(el.attrib.get("title", ""))
        word_text = "".join(el.itertext()).strip()
        token = WordToken(
            id=el.attrib.get("id") or f"w_{idx}",
            text=el.text if el.text is not None else word_text,
            conf=meta.get("conf"),
            bbox=meta.get("bbox"),
            title=el.attrib.get("title", ""),
            source=str(path),
            index=idx,
        )
        pairs.append((el, token))
        idx += 1
    return tree, pairs


def dump_tsv_words(path: Path, *, max_conf: Optional[float], all_words: bool) -> List[dict]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: List[dict] = []
    start = 1 if lines and lines[0].lower().startswith("level") else 0
    idx = 0
    for line in lines[start:]:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        try:
            conf = float(parts[10])
            left, top, width, height = map(int, parts[6:10])
        except ValueError:
            continue
        text = parts[-1]
        if conf < 0 or not text.strip():
            continue
        if not all_words and max_conf is not None and conf > max_conf:
            continue
        out.append(
            {
                "id": f"tsv_{idx}",
                "text": text,
                "conf": conf,
                "bbox": [left, top, left + width, top + height],
                "title": "",
                "source": str(path),
                "index": idx,
            }
        )
        idx += 1
    return out


def dump_words(path: Path, *, max_conf: Optional[float], all_words: bool) -> List[dict]:
    if path.suffix.lower() == ".tsv":
        return dump_tsv_words(path, max_conf=max_conf, all_words=all_words)
    _tree, pairs = load_hocr_words(path)
    out: List[dict] = []
    for _el, tok in pairs:
        conf = tok.conf
        if not all_words and max_conf is not None and conf is not None and conf > max_conf:
            continue
        if not all_words and max_conf is not None and conf is None:
            continue
        rec = asdict(tok)
        if rec.get("bbox") is not None:
            rec["bbox"] = list(rec["bbox"])
        out.append(rec)
    return out


def apply_hocr_corrections(path: Path, corrections: dict, *, out_path: Path, set_conf: Optional[float]) -> dict:
    tree, pairs = load_hocr_words(path)
    by_id = dict(corrections.get("by_id") or {})
    by_index = {int(k): v for k, v in (corrections.get("by_index") or {}).items()}
    replace_map: Dict[str, str] = dict(corrections.get("replace") or {})
    flat_ids = {
        k: v
        for k, v in corrections.items()
        if k not in {"by_id", "by_index", "replace", "meta", "count", "filter", "words"}
        and isinstance(v, str)
    }
    by_id.update(flat_ids)

    applied = 0
    for el, tok in pairs:
        new_text = None
        if tok.id in by_id and by_id[tok.id] != (tok.text or ""):
            new_text = by_id[tok.id]
        elif tok.index in by_index and by_index[tok.index] != (tok.text or ""):
            new_text = by_index[tok.index]
        elif (tok.text or "") in replace_map and replace_map[tok.text or ""] != (tok.text or ""):
            new_text = replace_map[tok.text or ""]
        if new_text is None or new_text == (tok.text or ""):
            continue
        for child in list(el):
            el.remove(child)
        el.text = new_text
        if set_conf is not None:
            title = el.attrib.get("title", "")
            if "x_wconf" in title:
                el.attrib["title"] = re.sub(
                    r"x_wconf\s+-?\d+(?:\.\d+)?",
                    f"x_wconf {int(set_conf)}",
                    title,
                )
            elif title:
                el.attrib["title"] = title.rstrip("; ") + f"; x_wconf {int(set_conf)}"
            else:
                el.attrib["title"] = f"x_wconf {int(set_conf)}"
        applied += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return {
        "source": str(path),
        "output": str(out_path),
        "words_total": len(pairs),
        "applied": applied,
    }


def export_plaintext(path: Path, out_path: Path) -> int:
    _tree, pairs = load_hocr_words(path)
    words = [(t.text or "") for _e, t in pairs]
    text = " ".join(w for w in words if w)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return len(words)


def cmd_dump(args: argparse.Namespace) -> int:
    all_recs: List[dict] = []
    for path in args.files:
        if not path.is_file():
            die(f"not found: {path}")
        all_recs.extend(dump_words(path, max_conf=args.max_conf, all_words=args.all))
    payload = {
        "count": len(all_recs),
        "filter": {"max_conf": args.max_conf, "all": args.all},
        "words": all_recs,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.output} ({payload['count']} words)", file=sys.stderr)
    else:
        print(text)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    if not args.hocr.is_file():
        die(f"not found: {args.hocr}")
    if not args.corrections.is_file():
        die(f"not found: {args.corrections}")
    corr = json.loads(args.corrections.read_text(encoding="utf-8"))
    # Accept dump format as corrections input: convert words list with edited "text" not supported;
    # only structured templates / maps.
    out = args.output or args.hocr.with_suffix(".corrected.hocr")
    summary = apply_hocr_corrections(
        args.hocr,
        corr,
        out_path=out,
        set_conf=None if args.keep_conf else args.set_conf,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Applied {summary['applied']}/{summary['words_total']} -> {summary['output']}",
            file=sys.stderr,
        )
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    if not args.hocr.is_file():
        die(f"not found: {args.hocr}")
    out = args.output or args.hocr.with_suffix(".txt")
    n = export_plaintext(args.hocr, out)
    print(f"Wrote plaintext ({n} tokens) -> {out}", file=sys.stderr)
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if not args.file.is_file():
        die(f"not found: {args.file}")
    words = dump_words(args.file, max_conf=args.max_conf, all_words=False)
    if args.all:
        words = dump_words(args.file, max_conf=None, all_words=True)
    template = {
        "meta": {
            "source": str(args.file),
            "max_conf": args.max_conf,
            "instructions": "Edit by_id values (or replace map), then run: hocr_correct.py apply",
        },
        "by_id": {w["id"]: w["text"] for w in words},
        "replace": {},
    }
    out = args.output or Path(str(args.file) + ".corrections.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote template {out} ({len(words)} entries)", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Path A hOCR correction tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dump", help="Dump words from hOCR/TSV as JSON")
    d.add_argument("files", nargs="+", type=Path)
    d.add_argument("-o", "--output", type=Path)
    d.add_argument("--all", action="store_true")
    d.add_argument("--max-conf", type=float, default=None)
    d.set_defaults(func=cmd_dump)

    a = sub.add_parser("apply", help="Apply corrections JSON to hOCR")
    a.add_argument("--hocr", type=Path, required=True)
    a.add_argument("--corrections", type=Path, required=True)
    a.add_argument("-o", "--output", type=Path)
    a.add_argument("--set-conf", type=float, default=99.0)
    a.add_argument("--keep-conf", action="store_true")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_apply)

    t = sub.add_parser("text", help="Export plaintext from hOCR")
    t.add_argument("hocr", type=Path)
    t.add_argument("-o", "--output", type=Path)
    t.set_defaults(func=cmd_text)

    i = sub.add_parser("init", help="Create corrections template")
    i.add_argument("file", type=Path)
    i.add_argument("-o", "--output", type=Path)
    i.add_argument("--max-conf", type=float, default=90.0)
    i.add_argument("--all", action="store_true")
    i.set_defaults(func=cmd_init)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
