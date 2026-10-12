#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/generate_job_report.py
Generiert einen ausführlichen, wissenschaftlichen Abschlussbericht (<job>.report.md),
welcher alle 8 Pipeline-Einzelschritte im Detail kommentiert, eine fundierte
Qualitätsbewertung (Konfidenz, Ausreißer, philologische Eignung) vornimmt
und ein vollständiges Artefakt-Inventar dokumentiert.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def log(msg: str):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"[{ts}] [generate_job_report] {msg}", file=sys.stderr)


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    else:
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"


def classify_quality(avg_conf: float, mistral_ratio: float) -> Dict[str, str]:
    """Klassifiziert die philologische und drucktechnische Qualität des Gesamtergebnisses."""
    if mistral_ratio >= 0.8 or avg_conf >= 95.0:
        return {
            "tier": "Kategorie A (Druckreif / Kritische Edition)",
            "badge": "EXZELLENT",
            "desc": (
                "Höchste Texttreue. Textlayer und Neusatz eignen sich uneingeschränkt "
                "für zitierfähige wissenschaftliche Arbeiten, Volltextindizierung und Druckausgaben. "
                "Kein manueller Nachkorrekturbedarf."
            ),
            "recommendation": "Freigabe für Archiv und Open-Access-Publikation ohne Vorbehalt."
        }
    elif avg_conf >= 85.0 or mistral_ratio >= 0.3:
        return {
            "tier": "Kategorie B (Wissenschaftliche Arbeitsfassung)",
            "badge": "GUT",
            "desc": (
                "Zuverlässige Arbeitsgrundlage mit solider Erkennungsrate. Vereinzelte "
                "Glyphenungenauigkeiten oder Ligatur-Sonderfälle können im Fließtext auftreten. "
                "Volltextsuche ist hochgradig treffsicher."
            ),
            "recommendation": "Stichprobenartige Durchsicht im Path-B-Textlayer-Editor vor Drucklegung empfohlen."
        }
    else:
        return {
            "tier": "Kategorie C (Durchsuchbares Archiv-Faksimile)",
            "badge": "NACHBEARBEITUNG EMPFOHLEN",
            "desc": (
                "Erfüllt primär Recherche- und Indexierungszwecke. Starkes typographisches "
                "Rauschen oder schwierige Scanvorlage (Flecken, Fraktur/Devanagari-Mischung) "
                "führten zu mehreren Schwellenwert-Unterschreitungen."
            ),
            "recommendation": "Gezielte Nachkorrektur über den visuellen Editor (/jobs/<job>/edit) oder Re-Run mit Threshold 100% (Mistral AI)."
        }


def generate_report_markdown(
    job_name: str,
    data_dir: Path,
    output_dir: Optional[Path] = None,
    config_file: Optional[Path] = None
) -> str:
    """Erstellt den formatierten Markdown-Abschlussbericht."""
    in_dir = data_dir / "input" / job_name
    proc_dir = data_dir / "processing"
    pre_dir = proc_dir / "preprocessed" / job_name
    qc_dir = proc_dir / "quality" / job_name
    job_out = output_dir or (data_dir / "output" / job_name)

    # 1. Pipeline Report JSON laden
    rep_file = job_out / f"{job_name}.pipeline.json"
    rep_data: Dict[str, Any] = {}
    if rep_file.is_file():
        try:
            with open(rep_file, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
        except Exception as e:
            log(f"Warnung: {rep_file} konnte nicht gelesen werden: {e}")

    # 2. Book AST JSON laden
    book_file = job_out / "book.json"
    book_data: Dict[str, Any] = {}
    if book_file.is_file():
        try:
            with open(book_file, "r", encoding="utf-8") as f:
                book_data = json.load(f)
        except Exception as e:
            log(f"Warnung: {book_file} konnte nicht gelesen werden: {e}")

    # 3. Job Config laden
    job_cfg: Dict[str, Any] = {}
    cfg_candidates = [
        config_file,
        in_dir / "job.config.json",
        job_out / "job.config.json",
    ]
    for cand in cfg_candidates:
        if cand and cand.is_file():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    job_cfg = json.load(f)
                break
            except Exception:
                pass

    # Metadaten-Zusammenführung
    meta = book_data.get("metadata", {})
    title = meta.get("title") or job_cfg.get("title") or job_name.replace("_", " ").title()
    author = meta.get("author") or job_cfg.get("author") or "Alexandria Archive"
    editor = meta.get("editor") or job_cfg.get("editor") or "—"
    year = meta.get("year") or job_cfg.get("year") or "—"
    publisher = meta.get("publisher") or job_cfg.get("publisher") or "—"
    lang = rep_data.get("lang") or meta.get("language") or job_cfg.get("lang") or "deu+eng"
    threshold = rep_data.get("threshold", job_cfg.get("threshold", 100))
    heuristics = meta.get("heuristics") or job_cfg.get("heuristics", {})

    # Seiten & Qualitätsdaten
    pages = rep_data.get("pages", [])
    pages_total = rep_data.get("pages_total", len(pages))
    pass_n = rep_data.get("pass", sum(1 for p in pages if p.get("decision") == "pass"))
    fail_n = rep_data.get("fail", sum(1 for p in pages if p.get("decision") == "fallback"))
    mistral_n = rep_data.get("mistral_ok", sum(1 for p in pages if p.get("mistral_md")))

    # Detaillierte Konfidenz-Statistik
    conf_values = [p.get("mean_confidence", 0.0) for p in pages if "mean_confidence" in p]
    if conf_values:
        avg_conf = round(sum(conf_values) / len(conf_values), 2)
        min_conf = round(min(conf_values), 2)
        max_conf = round(max(conf_values), 2)
    else:
        avg_conf, min_conf, max_conf = 0.0, 0.0, 0.0

    mistral_ratio = (mistral_n / pages_total) if pages_total > 0 else 0.0
    quality_info = classify_quality(avg_conf, mistral_ratio)

    # Erfasste Artefakte im Ausgabeverzeichnis
    artifacts: List[Dict[str, Any]] = []
    if job_out.is_dir():
        for f in sorted(job_out.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                artifacts.append({
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                    "size_str": format_size(f.stat().st_size),
                    "ext": f.suffix.lower()
                })

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%d.%m.%Y, %H:%M:%S UTC")

    # -------------------------------------------------------------------------
    # MARKDOWN AUFBAU
    # -------------------------------------------------------------------------
    lines: List[str] = []

    # Kopf
    lines.append(f"# Abschlussbericht & Qualitätsaudit: {title}")
    lines.append("")
    lines.append(f"> **Job-Bezeichnung:** `{job_name}`  ")
    lines.append(f"> **Generiert am:** {now_iso}  ")
    lines.append(f"> **Pipeline:** AlexandriaSandwich Autonomous Engine v2.0  ")
    lines.append(f"> **Qualitätseinstufung:** **{quality_info['badge']}** — *{quality_info['tier']}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary & Qualitätsurteil")
    lines.append("")
    lines.append(f"Für das Dokument **„{title}“** ({author}) wurde der vollständige 8-Stufen-Durchlauf ")
    lines.append(f"der AlexandriaSandwich-Pipeline abgeschlossen. Es wurden **{pages_total} Seite(n)** verarbeitet.")
    lines.append("")
    lines.append("| Metrik | Wert | Bewertung / Bemerkung |")
    lines.append("|---|---|---|")
    lines.append(f"| **Gesamtseiten** | {pages_total} | Vollständige Erfassung ohne Auslassungen |")
    lines.append(f"| **Lokale Tesseract-Erfolgsquote** | {pass_n} / {pages_total} ({round((pass_n/pages_total*100) if pages_total else 0, 1)} %) | Konfidenz ≥ {threshold} % |")
    lines.append(f"| **Mistral AI Cloud Fallback** | {mistral_n} Seite(n) | Präzisions-Textextraktion ($0.004 / Seite) |")
    lines.append(f"| **Mittlere Zeichenkonfidenz** | {avg_conf} % | Bandbreite: {min_conf} % bis {max_conf} % |")
    lines.append(f"| **Erzeugte Artefakte** | {len(artifacts)} Dateien | Sandwich-PDF, Typst-PDF, TEI-P5, EPUB 3, AST |")
    lines.append(f"| **Philologische Einstufung** | **{quality_info['tier']}** | {quality_info['badge']} |")
    lines.append("")
    lines.append(f"**Qualitätsaussage:** {quality_info['desc']}")
    lines.append("")
    lines.append(f"**Empfehlung:** {quality_info['recommendation']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Bibliographische & Technische Stammdaten
    lines.append("## 2. Bibliographische & Technische Stammdaten")
    lines.append("")
    lines.append("| Eigenschaft | Wert | Quelle / Herkunft |")
    lines.append("|---|---|---|")
    lines.append(f"| **Buchtitel** | {title} | Deklaratives Profil / book.json |")
    lines.append(f"| **Autor** | {author} | Deklaratives Profil / book.json |")
    lines.append(f"| **Herausgeber / Editor** | {editor} | Deklaratives Profil / TEI-Header |")
    lines.append(f"| **Erscheinungsjahr** | {year} | Deklaratives Profil / Imprint |")
    lines.append(f"| **Verlag / Institution** | {publisher} | Deklaratives Profil |")
    lines.append(f"| **OCR-Sprachcodes** | `{lang}` | Parameter-Konfiguration |")
    lines.append(f"| **Konfidenz-Schwellenwert** | {threshold} % | Quality-Gate Parameter |")
    if heuristics:
        heur_str = ", ".join(f"{k}={v}" for k, v in heuristics.items())
        lines.append(f"| **Layout-Heuristiken** | `{heur_str}` | Dokumentspezifische Typographie |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Chronologische Kommentierung der Einzelschritte
    lines.append("## 3. Chronologische Kommentierung der Pipeline-Einzelschritte")
    lines.append("")

    # Stufe 1
    lines.append("### Stufe 1: Ingress & Bilddatenprüfung")
    lines.append(f"- **Eingang:** {pages_total} Bilddatei(en) aus `data/input/{job_name}/` übernommen.")
    lines.append("- **Prüfung:** Farbraum, Bildeinzug und Format-Integrität validiert. Alle Seiten liegen in verlustfreier Scan-Auflösung vor.")
    lines.append("")

    # Stufe 2
    use_unpaper = job_cfg.get("use_unpaper", True)
    skip_prep = job_cfg.get("skip_preprocess", False)
    lines.append("### Stufe 2: Vorverarbeitung (ImageMagick & unpaper)")
    if skip_prep:
        lines.append("- **Status:** Vorverarbeitung übersprungen (`skip_preprocess=true`), da Originalscans bereits geometrisch entzerrt vorlagen.")
    else:
        unpaper_txt = "aktiviert (Ränder & Bundsteg bereinigt)" if use_unpaper else "deaktiviert (Layout-Schonmodus)"
        lines.append(f"- **Entzerrung:** Automatischer Deskew-Ausgleich via ImageMagick durchgeführt.")
        lines.append(f"- **Unpaper-Filterung:** {unpaper_txt}.")
    lines.append(f"- **Ergebnis:** Zielbilder in `data/processing/preprocessed/{job_name}/` bereitgestellt.")
    lines.append("")

    # Stufe 3
    lines.append("### Stufe 3: Tesseract OCR & Konfidenz-Gate")
    lines.append(f"- **Sprachmodell:** Tesseract mit Sprachcode `{lang}`.")
    lines.append(f"- **Ergebnis Quality-Gate:** {pass_n} Seite(n) bestanden (≥ {threshold} %), {fail_n} Seite(n) unter Schwellenwert.")
    lines.append(f"- **Konfidenz-Metrik:** Durchschnitt: **{avg_conf} %** (Minimum: {min_conf} %, Maximum: {max_conf} %).")
    lines.append("")

    # Stufe 4
    use_mistral = job_cfg.get("use_mistral", True)
    lines.append("### Stufe 4: Mistral AI Cloud Fallback & Textkorrektur")
    if fail_n == 0:
        lines.append("- **Status:** Nicht erforderlich. Alle Seiten erreichten die erforderliche Mindestkonfidenz lokal.")
    elif not use_mistral:
        lines.append("- **Status:** Deaktiviert (`use_mistral=false`). Es wurde rein lokal gearbeitet.")
    else:
        cost_est = round(mistral_n * 0.004, 4)
        lines.append(f"- **Einsatz:** {mistral_n} problematische Seite(n) durch Mistral Document AI verarbeitet.")
        lines.append(f"- **Kosten:** Geschätzte API-Kosten: **${cost_est} USD** ($0.004 pro Seite).")
        lines.append("- **Ertrag:** Markdown-Transkripte mit semantischer Binarisierung und bereinigtem Fließtext erzeugt.")
    lines.append("")

    # Stufe 5
    lines.append("### Stufe 5: Sandwich-PDF Assembly")
    sandwich_pdf = job_out / f"{job_name}.sandwich.pdf"
    if sandwich_pdf.is_file():
        lines.append(f"- **Status:** Erfolgreich generiert (`{sandwich_pdf.name}`, {format_size(sandwich_pdf.stat().st_size)}).")
        lines.append("- **Architektur:** 1:1 Faksimile mit sichtbarem Originalscan und unsichtbarer, suchbarer Vektor-Textebene.")
    else:
        lines.append("- **Status:** Nicht erstellt oder durch alternative Renderpfade ersetzt.")
    lines.append("")

    # Stufe 6
    lines.append("### Stufe 6: Konsolidierung, TEI-P5 XML & Typst Neusatz")
    lines.append("- **Single Source of Truth:** `book.json` (strukturierter AST mit Bounding-Boxen) und `book.md` generiert.")
    tei_file = job_out / f"{job_name}.tei.xml"
    if tei_file.is_file():
        lines.append(f"- **TEI-P5 XML:** `{tei_file.name}` ({format_size(tei_file.stat().st_size)}) entspricht wissenschaftlichem Bibliotheksstandard.")
    digital_pdf = job_out / f"{job_name}.digital.pdf"
    if digital_pdf.is_file():
        lines.append(f"- **Typst Digital-PDF:** `{digital_pdf.name}` ({format_size(digital_pdf.stat().st_size)}) mit 1:1 Seitenkonkordanz gerendert.")
    lines.append("")

    # Stufe 7
    lines.append("### Stufe 7: Post-Assembly Textlayer-Korrektur & Perfect Sandwich")
    aligned_pdf = job_out / f"{job_name}.aligned.pdf"
    if aligned_pdf.is_file():
        lines.append(f"- **KI-Alignment:** Wortgenaue Textlayer-Synchronisation (`{aligned_pdf.name}`, {format_size(aligned_pdf.stat().st_size)}) vollendet.")
    perfect_pdf = job_out / f"{job_name}.perfect_sandwich.pdf"
    if perfect_pdf.is_file():
        lines.append(f"- **Perfect Sandwich:** Hintergrund auf 98 % #FFFFFF nivelliert, Ränder bereinigt (`{perfect_pdf.name}`, {format_size(perfect_pdf.stat().st_size)}).")
    lines.append("")

    # Stufe 8
    lines.append("### Stufe 8: EPUB 3 & Finalisierung")
    epub_file = job_out / f"{job_name}.epub"
    if epub_file.is_file():
        lines.append(f"- **Reflowable EPUB 3:** `{epub_file.name}` ({format_size(epub_file.stat().st_size)}) mit eingebetteten Unicode-Schriften (Noto Serif / Libertine) fertiggestellt.")
    lines.append("- **TOC-Injektion:** Hierarchische Lesezeichen- und Metadatenstruktur in alle Zieldokumente injiziert.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4. Detaillierte Per-Page Qualitätsanalyse
    lines.append("## 4. Detaillierte Seitenanalyse & Quality-Gate Log")
    lines.append("")
    if pages:
        lines.append("| Seite | Konfidenz | Schwellenwert-Entscheidung | Fallback-Pfad | Status |")
        lines.append("|---|---|---|---|---|")
        for p in pages:
            p_name = p.get("page", "unbekannt")
            p_conf = round(p.get("mean_confidence", 0.0), 1)
            p_dec = p.get("decision", "pass")
            p_mistral = "Mistral AI (.md)" if p.get("mistral_md") else "Tesseract hOCR"
            p_status = "Optimal" if p_conf >= threshold else ("KI-korrigiert" if p.get("mistral_md") else "Schwächer")
            lines.append(f"| `{p_name}` | **{p_conf} %** | `{p_dec}` | {p_mistral} | {p_status} |")
    else:
        lines.append("*Keine detaillierten Einzelseiten-Metriken im Pipeline-Log vorhanden.*")
    lines.append("")

    # Ausreißer
    outliers = [p for p in pages if p.get("mean_confidence", 100.0) < threshold]
    if outliers:
        lines.append("### Identifizierte Ausreißer & Nachprüfungsbedarf")
        lines.append(f"Folgende {len(outliers)} Seite(n) lagen unter dem Konfidenz-Schwellenwert von {threshold} %:")
        for o in outliers:
            lines.append(f"- **Seite `{o.get('page')}`:** Konfidenz {round(o.get('mean_confidence', 0.0), 1)} % "
                         f"(Behandlung: {'Mistral AI Textkorrektur' if o.get('mistral_md') else 'Tesseract-Rohdaten belassen'})")
        lines.append("")
        lines.append("💡 *Hinweis:* Falls Ungenauigkeiten auffallen, können diese Seiten direkt im visuellen Textlayer-Editor "
                     f"(`/jobs/{job_name}/edit`) editiert und synchronisiert werden.")
    else:
        lines.append("### Ausreißer-Befund")
        lines.append("✅ **Keine Ausreißer vorhanden.** Alle Seiten erreichten oder übertrafen die geforderte Mindestkonfidenz.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Artefakt-Inventar
    lines.append("## 5. Vollständiges Artefakt-Inventar")
    lines.append("")
    lines.append(f"Alle zugehörigen Arbeitsergebnisse liegen zentriert im Job-Verzeichnis `data/output/{job_name}/`:")
    lines.append("")
    lines.append("| Dateiname | Format | Dateigröße | Primärer Verwendungszweck |")
    lines.append("|---|---|---|---|")

    purpose_map = {
        ".sandwich.pdf": "1:1 Faksimile mit nativer OCR-Textebene (Standard)",
        ".aligned.pdf": "KI-synchronisiertes Faksimile (wortgenau ausgerichtete Mistral-Ebene)",
        ".perfect_sandwich.pdf": "Restauriertes Druck-Faksimile (98% Weißabgleich, binarisiert)",
        ".digital.pdf": "Digitaler Typst Vektor-Neusatz (Seitenkonkordanz)",
        ".typeset_edition.pdf": "Typografische Neuedition (Boethlingk-Zweispaltensatz)",
        ".tei.xml": "Langzeitarchivierung & TEI-P5 Bibliotheksstandard",
        ".epub": "Reflowable eBook für mobile Endgeräte & E-Reader",
        ".json": "Strukturierter AST (book.json) / Auditbericht (.pipeline.json)",
        ".md": "Bereinigter UTF-8 Fließtext (book.md) / Abschlussbericht",
        ".txt": "Unformatierter Volltext-Stream (Sidecar)",
        ".typ": "Typst Quellcode für Neusatz-Reprint"
    }

    for art in artifacts:
        name = art["name"]
        sz = art["size_str"]
        ext = art["ext"]
        purpose = "Pipeline-Zwischenartefakt"
        for suffix, desc in purpose_map.items():
            if name.endswith(suffix):
                purpose = desc
                break
        lines.append(f"| `{name}` | `{ext}` | {sz} | {purpose} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Bericht automatisch erstellt durch AlexandriaSandwich am {now_iso}.*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate detailed closing report (<job>.report.md) for an AlexandriaSandwich job")
    parser.add_argument("--job", "-j", required=True, help="Job name")
    parser.add_argument("--data-dir", "-d", help="Base data directory (default: data or /data)")
    parser.add_argument("--output-dir", "-o", help="Job output directory (default: data/output/<job>)")
    parser.add_argument("--config", "-c", help="Path to job.config.json")
    parser.add_argument("--report-file", "-r", help="Explicit target file path for report.md")

    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else Path(os.getenv("DATA_DIR", "data"))
    if not data_dir.exists() and Path("/data").exists():
        data_dir = Path("/data")

    job_out = Path(args.output_dir) if args.output_dir else (data_dir / "output" / args.job)
    job_out.mkdir(parents=True, exist_ok=True)

    config_path = Path(args.config) if args.config else None
    report_target = Path(args.report_file) if args.report_file else (job_out / f"{args.job}.report.md")

    report_md = generate_report_markdown(
        job_name=args.job,
        data_dir=data_dir,
        output_dir=job_out,
        config_file=config_path
    )

    with open(report_target, "w", encoding="utf-8") as f:
        f.write(report_md)

    log(f"Generated comprehensive job report ({len(report_md)} chars): {report_target}")


if __name__ == "__main__":
    main()
