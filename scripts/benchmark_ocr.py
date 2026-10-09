#!/usr/bin/env python3
"""
AlexandriaSandwich — OCR Engine Benchmark
Compares Mistral Document AI (mistral-ocr-latest) against local Qwen2.5-VL (nyx.local:8088).

Generates comparative metrics:
- Latency (sec/page)
- Character, word & line counts
- Diacritic & Non-Latin (Devanāgarī) script preservation
- Text similarity & difference analysis
- Visual side-by-side comparison report (Markdown & HTML)
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import qwen_ocr
import mistral_ocr


DEFAULT_TEST_IMAGE = ROOT / "data/input/stenzler/page-108.png"
DEFAULT_OUT_DIR = ROOT / "benchmark_results"


def log(msg: str) -> None:
    print(f"[benchmark] {msg}", file=sys.stderr)


def analyze_text(text: str) -> Dict[str, Any]:
    lines = text.splitlines()
    words = text.split()
    chars = len(text)
    
    # Count Devanagari Unicode block (U+0900 - U+097F)
    devanagari_chars = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    # Count Latin Extended diacritics
    diacritic_chars = sum(1 for c in text if 0x0100 <= ord(c) <= 0x024F or 0x1E00 <= ord(c) <= 0x1EFF)

    return {
        "chars": chars,
        "words": len(words),
        "lines": len(lines),
        "devanagari_chars": devanagari_chars,
        "diacritic_chars": diacritic_chars,
    }


def compute_similarity(text_a: str, text_b: str) -> float:
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    return round(matcher.ratio() * 100.0, 2)


def generate_html_report(
    image_path: Path,
    mistral_res: Dict[str, Any],
    qwen_res: Dict[str, Any],
    out_html: Path,
) -> None:
    m_text = mistral_res.get("markdown", "")
    q_text = qwen_res.get("markdown", "")
    m_meta = mistral_res.get("analysis", {})
    q_meta = qwen_res.get("analysis", {})

    sim = compute_similarity(m_text, q_text)
    diff = list(difflib.unified_diff(
        m_text.splitlines(),
        q_text.splitlines(),
        fromfile="Mistral OCR",
        tofile="Qwen2.5-VL",
        lineterm="",
    ))
    diff_text = "\n".join(diff[:150])

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>OCR Benchmark: Mistral vs Qwen2.5-VL — {image_path.name}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0b0f17;
      color: #f8fafc;
      margin: 0;
      padding: 1.5rem;
    }}
    h1, h2, h3 {{ color: #fbbf24; margin-top: 0; }}
    .header-box {{
      background: rgba(17, 24, 39, 0.85);
      border: 1px solid rgba(255,255,255,0.1);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
    }}
    .grid-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }}
    .stat-card {{
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 6px;
      padding: 1rem;
    }}
    .stat-title {{ font-size: 0.8rem; text-transform: uppercase; color: #94a3b8; font-weight: 600; }}
    .stat-num {{ font-size: 1.6rem; font-weight: bold; margin-top: 0.2rem; }}
    .split-view {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .pane {{
      background: #111827;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 8px;
      padding: 1.2rem;
      overflow-x: auto;
    }}
    pre {{
      font-family: ui-monospace, Menlo, Monaco, monospace;
      font-size: 0.88rem;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
      color: #e2e8f0;
    }}
    .badge {{
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-mistral {{ background: #1e3a8a; color: #93c5fd; }}
    .badge-qwen {{ background: #064e3b; color: #6ee7b7; }}
    .diff-box {{
      background: #030712;
      border: 1px solid #374151;
      border-radius: 6px;
      padding: 1rem;
      color: #9ca3af;
    }}
  </style>
</head>
<body>

  <div class="header-box">
    <h1>⚔️ OCR Benchmark: Mistral Document AI vs. Qwen2.5-VL</h1>
    <p style="color:#94a3b8; margin:0;">
      Test-Vorlage: <code>{image_path.name}</code> &middot; 
      Ähnlichkeit (Similarity): <strong style="color:#fbbf24;">{sim} %</strong>
    </p>
  </div>

  <div class="grid-stats">
    <div class="stat-card">
      <div class="stat-title">Mistral Latenz</div>
      <div class="stat-num" style="color:#60a5fa;">{mistral_res.get('elapsed_seconds', 0)} s</div>
      <small style="color:#94a3b8;">Modell: {mistral_res.get('model', 'mistral-ocr-latest')}</small>
    </div>
    <div class="stat-card">
      <div class="stat-title">Qwen Latenz</div>
      <div class="stat-num" style="color:#34d399;">{qwen_res.get('elapsed_seconds', 0)} s</div>
      <small style="color:#94a3b8;">Modell: {qwen_res.get('model', 'qwen2.5-vl')}</small>
    </div>
    <div class="stat-card">
      <div class="stat-title">Wort-Anzahl</div>
      <div class="stat-num" style="color:#f8fafc;">M: {m_meta.get('words', 0)} / Q: {q_meta.get('words', 0)}</div>
      <small style="color:#94a3b8;">Zeichen: {m_meta.get('chars', 0)} vs {q_meta.get('chars', 0)}</small>
    </div>
    <div class="stat-card">
      <div class="stat-title">Devanāgarī-Zeichen</div>
      <div class="stat-num" style="color:#fbbf24;">M: {m_meta.get('devanagari_chars', 0)} / Q: {q_meta.get('devanagari_chars', 0)}</div>
      <small style="color:#94a3b8;">Diakritika: {m_meta.get('diacritic_chars', 0)} vs {q_meta.get('diacritic_chars', 0)}</small>
    </div>
  </div>

  <h2>Dual-Pane Textvergleich</h2>
  <div class="split-view">
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
        <h3 style="margin:0;">Mistral Document AI</h3>
        <span class="badge badge-mistral">Cloud API (0,004 $)</span>
      </div>
      <pre>{m_text}</pre>
    </div>
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
        <h3 style="margin:0;">Qwen2.5-VL</h3>
        <span class="badge badge-qwen">Lokal / nyx.local (0,00 $)</span>
      </div>
      <pre>{q_text}</pre>
    </div>
  </div>

  <h2>Unified Diff (Auszug)</h2>
  <div class="diff-box">
    <pre>{diff_text if diff_text else "Keine signifikanten Unterschiede in den ersten 150 Zeilen."}</pre>
  </div>

</body>
</html>
"""
    out_html.write_text(html, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Mistral OCR against local Qwen2.5-VL")
    parser.add_argument(
        "-i", "--image",
        type=Path,
        default=DEFAULT_TEST_IMAGE,
        help=f"Image to benchmark (default: {DEFAULT_TEST_IMAGE})",
    )
    parser.add_argument(
        "-e", "--endpoint",
        default=qwen_ocr.DEFAULT_ENDPOINT,
        help=f"Qwen VLM endpoint URL (default: {qwen_ocr.DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "-m", "--model",
        default="",
        help="Qwen model name (default: auto-detected)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for benchmark reports (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check connectivity and API readiness without calling models",
    )

    parser.add_argument(
        "--force-mistral",
        action="store_true",
        help="Re-run Mistral OCR even if cached result exists in output directory",
    )

    args = parser.parse_args(argv)

    if not args.image.is_file():
        log(f"Test-Bild nicht gefunden: {args.image}")
        die("Bitte ein gültiges Bild mit --image angeben.")

    print("=" * 60)
    print("AlexandriaSandwich — OCR Engine Benchmark Readiness Check")
    print("=" * 60)

    # 1. Check Mistral
    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    mistral_ready = bool(mistral_key)
    print(f"1. Mistral OCR Cloud API: {'✅ Bereit (API-Key konfiguriert)' if mistral_ready else '❌ MISTRAL_API_KEY nicht gesetzt'}")

    # 2. Check Qwen VLM
    qwen_ok, qwen_models, qwen_loaded, qwen_note = qwen_ocr.check_health(args.endpoint)
    print(f"2. Qwen2.5-VL Lokal ({args.endpoint}):")
    if qwen_ok:
        print(f"   ✅ Server online! Aktiv geladen: {qwen_loaded or 'Kein Modell als loaded markiert'}")
        print(f"      Verfügbare Modelle: {', '.join(qwen_models)}")
    else:
        print(f"   ⏳ Wartet auf Server: {qwen_note}")
        print(f"      (Sobald nyx.local:8088 online ist, kann der Test ausgeführt werden)")

    if args.check_only:
        return 0 if (mistral_ready and qwen_ok) else 1

    if not qwen_ok:
        print("\n" + "=" * 60)
        print("Hinweis: Der lokale Server auf nyx.local:8088 steht noch nicht bereit.")
        print("Client-Schnittstelle ist einsatzbereit konfiguriert.")
        print(f"Start-Befehl für den Test, sobald der Server läuft:")
        print(f"  python3 scripts/benchmark_ocr.py --image {args.image}")
        print("=" * 60)
        return 2

    if not mistral_ready:
        die("MISTRAL_API_KEY ist erforderlich, um den Vergleich durchzuführen.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_name = args.image.stem
    m_md_path = args.output_dir / f"{base_name}_mistral.md"
    m_json_path = args.output_dir / f"{base_name}_mistral.json"

    # Run / Load Mistral
    if m_md_path.is_file() and not args.force_mistral:
        print(f"\n[1/2] Verwende gecachte Mistral-Ergebnisse: {m_md_path.name}")
        m_text = m_md_path.read_text(encoding="utf-8")
        elapsed_m = 0.0
        if m_json_path.is_file():
            try:
                raw = json.loads(m_json_path.read_text(encoding="utf-8"))
                elapsed_m = raw.get("elapsed_seconds", 0.0)
            except Exception:
                pass
        mistral_res = {
            "source": str(args.image),
            "markdown": m_text,
            "elapsed_seconds": elapsed_m,
            "analysis": analyze_text(m_text),
            "model": "mistral-ocr-latest",
        }
    else:
        print(f"\n[1/2] Führe Mistral OCR aus auf: {args.image.name} ...")
        t0_m = time.time()
        mistral_res = mistral_ocr.process_with_mistral(args.image)
        mistral_res["elapsed_seconds"] = round(time.time() - t0_m, 2)
        mistral_res["analysis"] = analyze_text(mistral_res.get("markdown", ""))
        m_md_path.write_text(mistral_res["markdown"], encoding="utf-8")
        m_json_path.write_text(json.dumps(mistral_res, ensure_ascii=False, indent=2), encoding="utf-8")

    # Run Qwen
    print(f"[2/2] Führe Qwen2.5-VL OCR aus auf: {args.image.name} ...")
    qwen_res = qwen_ocr.ocr_image(args.image, endpoint=args.endpoint, model=args.model)
    qwen_res["analysis"] = analyze_text(qwen_res.get("markdown", ""))

    # Compare
    sim = compute_similarity(mistral_res["markdown"], qwen_res["markdown"])

    # Save artifacts
    base_name = args.image.stem
    m_md_path = args.output_dir / f"{base_name}_mistral.md"
    q_md_path = args.output_dir / f"{base_name}_qwen.md"
    html_path = args.output_dir / f"{base_name}_benchmark.html"
    report_md_path = args.output_dir / f"{base_name}_benchmark.md"

    m_md_path.write_text(mistral_res["markdown"], encoding="utf-8")
    q_md_path.write_text(qwen_res["markdown"], encoding="utf-8")
    generate_html_report(args.image, mistral_res, qwen_res, html_path)

    # Markdown Summary Report
    md_report = f"""# OCR Benchmark Report: Mistral Document AI vs. Qwen2.5-VL

- **Testdatei:** `{args.image.name}`
- **Datum:** {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Ähnlichkeit (Similarity):** **{sim} %**

## Metriken-Vergleich

| Metrik | Mistral Document AI | Qwen2.5-VL (Lokal) | Differenz |
| :--- | :--- | :--- | :--- |
| **Laufzeit (Latenz)** | {mistral_res['elapsed_seconds']} s | {qwen_res['elapsed_seconds']} s | {round(qwen_res['elapsed_seconds'] - mistral_res['elapsed_seconds'], 2)} s |
| **Fremdkosten** | 0,004 $ | **0,00 $ (Lokal)** | -100 % |
| **Zeichenanzahl** | {mistral_res['analysis']['chars']} | {qwen_res['analysis']['chars']} | {qwen_res['analysis']['chars'] - mistral_res['analysis']['chars']} |
| **Wortanzahl** | {mistral_res['analysis']['words']} | {qwen_res['analysis']['words']} | {qwen_res['analysis']['words'] - mistral_res['analysis']['words']} |
| **Zeilenanzahl** | {mistral_res['analysis']['lines']} | {qwen_res['analysis']['lines']} | {qwen_res['analysis']['lines'] - mistral_res['analysis']['lines']} |
| **Devanāgarī-Zeichen** | {mistral_res['analysis']['devanagari_chars']} | {qwen_res['analysis']['devanagari_chars']} | {qwen_res['analysis']['devanagari_chars'] - mistral_res['analysis']['devanagari_chars']} |
| **Diakritika-Zeichen** | {mistral_res['analysis']['diacritic_chars']} | {qwen_res['analysis']['diacritic_chars']} | {qwen_res['analysis']['diacritic_chars'] - mistral_res['analysis']['diacritic_chars']} |

## Generierte Artefakte
- Mistral Markdown: [{m_md_path.name}](file://{m_md_path})
- Qwen2.5-VL Markdown: [{q_md_path.name}](file://{q_md_path})
- Interaktiver Side-by-Side HTML-Bericht: [{html_path.name}](file://{html_path})
"""
    report_md_path.write_text(md_report, encoding="utf-8")

    print("\n" + "=" * 60)
    print("BENCHMARK-ERGEBNIS")
    print("=" * 60)
    print(f"Ähnlichkeit (Similarity): {sim} %")
    print(f"Mistral: {mistral_res['elapsed_seconds']} s ({mistral_res['analysis']['words']} Wörter, {mistral_res['analysis']['devanagari_chars']} Devanāgarī-Zeichen)")
    print(f"Qwen2.5: {qwen_res['elapsed_seconds']} s ({qwen_res['analysis']['words']} Wörter, {qwen_res['analysis']['devanagari_chars']} Devanāgarī-Zeichen)")
    print(f"\nBerichte gespeichert in:")
    print(f"  Markdown: {report_md_path}")
    print(f"  HTML:     {html_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
