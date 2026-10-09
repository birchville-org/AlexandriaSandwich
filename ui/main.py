#!/usr/bin/env python3
"""AlexandriaSandwich Web UI (FastAPI)"""
from __future__ import annotations
import asyncio
import io
import html, json, logging, os, platform, re, shutil, subprocess, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
_default_data = "/data" if Path("/data").exists() else str(BASE_DIR.parent / "data")
DATA_DIR = Path(os.getenv("DATA_DIR", _default_data))
INPUT_DIR = DATA_DIR / "input"
PROC_DIR = DATA_DIR / "processing"
OUT_DIR = DATA_DIR / "output"
REPORTS_DIR = OUT_DIR / "reports"
PDF_DIR = OUT_DIR / "pdf"
TEI_DIR = OUT_DIR / "tei"
BOOKS_DIR = OUT_DIR / "books"
RUNS_DIR = OUT_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
VALID_IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pnm", ".ppm"}

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/alexandria/ocr")
FALLBACK_N8N_URL = os.getenv("FALLBACK_N8N_URL", "http://192.168.1.250:5678/webhook/alexandria/ocr")
N8N_WEBHOOK_TIMEOUT = float(os.getenv("N8N_WEBHOOK_TIMEOUT", "180"))
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="AlexandriaSandwich UI")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_job_artifacts(job: str, run_id: str | None = None) -> dict[str, Any]:
    """Sammelt alle erzeugten Artefakte eines Jobs (oder eines archivierten Vorlaufs)."""
    items = []
    if run_id:
        target_dir = RUNS_DIR / job / run_id
        if target_dir.is_dir():
            for p in sorted(target_dir.iterdir()):
                if p.is_file() and p.name != "meta.json":
                    size_kb = round(p.stat().st_size / 1024, 1)
                    ext = p.suffix.lower()
                    kind = "pdf" if ext == ".pdf" else ("tei" if ".tei" in p.name else ("books" if ext in {".epub", ".json", ".md"} else "reports"))
                    title = p.name
                    desc = "Archiviertes Artefakt"
                    if "sandwich" in p.name:
                        title = "1:1 Sandwich-PDF"
                        desc = "Originalscan + native OCR-Textebene"
                    elif "pathb" in p.name:
                        title = "KI-synchronisiertes Sandwich-PDF"
                        desc = "Mistral-bereinigter Textlayer (Path B)"
                    elif "digital" in p.name:
                        title = "Digitales Neusatz-PDF"
                        desc = "Typst wissenschaftlicher Buchsatz"
                    elif p.name.endswith(".epub"):
                        title = "Reflowable EPUB 3 E-Book"
                        desc = "E-Reader & Mobilgeräte"
                    elif "tei" in p.name:
                        title = "Generisches TEI-P5 XML"
                        desc = "Langzeitarchivierungs-Standard"
                    elif p.name == "book.json":
                        title = "Buch-AST (JSON)"
                        desc = "Strukturierte Objektrepräsentation"
                    elif p.name == "book.md":
                        title = "Konsolidiertes Markdown"
                        desc = "Bereinigter Fließtext"
                    elif "sidecar" in p.name:
                        title = "OCR-Textstrom (Sidecar)"
                        desc = "Unformatierter Text"
                    elif "pipeline.json" in p.name:
                        title = "Pipeline-Auditbericht"
                        desc = "Qualitätsmetriken & Kostenaufstellung"

                    items.append({
                        "name": p.name,
                        "title": title,
                        "desc": desc,
                        "path": str(p),
                        "size_kb": size_kb,
                        "size_mb": round(size_kb / 1024, 2),
                        "ext": ext,
                        "kind": kind,
                        "download_url": f"/jobs/{job}/runs/{run_id}/download/{p.name}",
                        "browse_url": f"/jobs/{job}/runs/{run_id}/browse/{p.name}",
                    })
    else:
        # Aktueller Lauf
        candidates = [
            (PDF_DIR / f"{job}.sandwich.pdf", "pdf", "1:1 Sandwich-PDF", "Originalscan + native OCR-Textebene"),
            (PDF_DIR / f"{job}.pathb.pdf", "pdf", "KI-synchronisiertes Sandwich-PDF", "Mistral-abgeglichene Textebene (Path B)"),
            (PDF_DIR / f"{job}.digital.pdf", "pdf", "Digitales Neusatz-PDF", "Moderner Typst Vektorsatz"),
            (TEI_DIR / f"{job}.tei.xml", "tei", "Generisches TEI-P5 XML", "Bibliotheksstandard zur Langzeitarchivierung"),
            (BOOKS_DIR / job / f"{job}.epub", "books", "Reflowable EPUB 3 E-Book", "Mobilgeräte & E-Reader mit eingebetteten Schriften"),
            (BOOKS_DIR / job / "book.json", "books", "Hierarchischer AST (book.json)", "Single Source of Truth mit Bounding Boxes"),
            (BOOKS_DIR / job / "book.md", "books", "Konsolidiertes Markdown (book.md)", "Bereinigter UTF-8 Fließtext"),
            (PDF_DIR / f"{job}.sidecar.txt", "pdf", "OCR-Textstrom (Sidecar)", "Unformatierter Volltext"),
            (REPORTS_DIR / f"{job}.pipeline.json", "reports", "Pipeline-Auditbericht", "Qualitätsmetriken & Kostenaufstellung"),
        ]
        # Fallback EPUB Check
        if not (BOOKS_DIR / job / f"{job}.epub").exists() and (OUT_DIR / "books" / f"{job}.epub").exists():
            candidates[4] = (OUT_DIR / "books" / f"{job}.epub", "books", "Reflowable EPUB 3 E-Book", "Mobilgeräte & E-Reader mit eingebetteten Schriften")

        for path, kind, title, desc in candidates:
            if path.exists() and path.stat().st_size > 0:
                size_kb = round(path.stat().st_size / 1024, 1)
                items.append({
                    "name": path.name,
                    "title": title,
                    "desc": desc,
                    "path": str(path),
                    "size_kb": size_kb,
                    "size_mb": round(size_kb / 1024, 2),
                    "ext": path.suffix.lower(),
                    "kind": kind,
                    "download_url": f"/download/{kind}/{job}/{path.name}",
                    "browse_url": f"/browse/{kind}/{job}/{path.name}",
                })

    total_kb = sum(it["size_kb"] for it in items)
    total_mb = round(total_kb / 1024, 2)
    zip_url = f"/jobs/{job}/runs/{run_id}/download-zip" if run_id else f"/jobs/{job}/download-zip"

    return {
        "job": job,
        "run_id": run_id,
        "files": items,
        "items": items,
        "count": len(items),
        "has_any": len(items) > 0,
        "total_size_kb": round(total_kb, 1),
        "total_size_mb": total_mb,
        "zip_download_url": zip_url,
    }


def _archive_current_run(job: str, note: str = "") -> str | None:
    """Archiviert die aktuellen Ziel-Artefakte und den Report eines Jobs als separaten Vorlauf."""
    current_art = _get_job_artifacts(job)
    if not current_art["has_any"]:
        return None

    now = datetime.now()
    run_id = f"run_{now.strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / job / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for item in current_art["items"]:
        src = Path(item["path"])
        dst = run_dir / src.name
        try:
            shutil.copy2(src, dst)
            copied.append({
                "name": src.name,
                "title": item["title"],
                "kind": item["kind"],
                "size_kb": round(dst.stat().st_size / 1024, 1),
                "ext": item["ext"],
            })
        except Exception as e:
            logging.warning(f"Could not copy {src} to {dst}: {e}")

    rep_file = REPORTS_DIR / f"{job}.pipeline.json"
    rep_data = {}
    if rep_file.exists():
        try:
            rep_data = json.loads(rep_file.read_text())
        except Exception:
            pass

    meta = {
        "run_id": run_id,
        "job": job,
        "archived_at": now.isoformat(),
        "archived_str": now.strftime("%d.%m.%Y, %H:%M:%S"),
        "note": note or "Vorangegangener Lauf",
        "status": "PASS" if rep_data.get("fail", 1) == 0 or rep_data.get("pass", 0) > 0 else (rep_data.get("status") or "COMPLETED"),
        "threshold": rep_data.get("threshold", 100),
        "lang": rep_data.get("lang", "deu+eng"),
        "pages_total": rep_data.get("pages_total", len(copied)),
        "pass": rep_data.get("pass", 0),
        "fail": rep_data.get("fail", 0),
        "mistral_ok": rep_data.get("mistral_ok", 0),
        "mistral_cost_usd": round(rep_data.get("mistral_ok", 0) * 0.004, 4),
        "artifacts_count": len(copied),
        "total_size_kb": round(sum(c["size_kb"] for c in copied), 1),
        "artifacts": copied
    }

    meta_file = run_dir / "meta.json"
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return run_id


def _list_job_runs(job: str) -> list[dict[str, Any]]:
    """Listet alle archivierten Vorläufe eines Jobs chronologisch sortiert auf (neueste zuerst)."""
    runs = []
    job_runs_dir = RUNS_DIR / job
    if not job_runs_dir.is_dir():
        return []

    for d in sorted(job_runs_dir.iterdir(), reverse=True):
        if d.is_dir() and d.name.startswith("run_"):
            meta_file = d / "meta.json"
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                except Exception:
                    pass

            artifacts_info = _get_job_artifacts(job, run_id=d.name)
            run_entry = {
                "run_id": d.name,
                "job": job,
                "archived_at": meta.get("archived_at", datetime.fromtimestamp(d.stat().st_mtime).isoformat()),
                "archived_str": meta.get("archived_str", datetime.fromtimestamp(d.stat().st_mtime).strftime("%d.%m.%Y, %H:%M:%S")),
                "note": meta.get("note", "Archivierter Vorlauf"),
                "status": meta.get("status", "PASS"),
                "threshold": meta.get("threshold", 100),
                "lang": meta.get("lang", "deu+eng"),
                "pages_total": meta.get("pages_total", artifacts_info["count"]),
                "pass": meta.get("pass", 0),
                "fail": meta.get("fail", 0),
                "mistral_ok": meta.get("mistral_ok", 0),
                "mistral_cost_usd": meta.get("mistral_cost_usd", 0.0),
                "artifacts": artifacts_info["items"],
                "artifacts_count": artifacts_info["count"],
                "total_size_mb": artifacts_info["total_size_mb"],
                "zip_download_url": artifacts_info["zip_download_url"],
            }
            runs.append(run_entry)

    return runs


def _delete_job_run(job: str, run_id: str) -> bool:
    """Löscht einen spezifischen Vorlauf sicher."""
    job_runs_dir = RUNS_DIR / job
    run_dir = job_runs_dir / run_id
    try:
        resolved = run_dir.resolve()
        if not str(resolved).startswith(str(job_runs_dir.resolve())):
            raise ValueError("Path traversal blocked")
        if run_dir.is_dir():
            shutil.rmtree(run_dir)
            return True
    except Exception as e:
        logging.error(f"Error deleting run {run_id} for job {job}: {e}")
    return False


def _clear_all_runs(job: str) -> int:
    """Löscht alle archivierten Vorläufe eines Jobs."""
    job_runs_dir = RUNS_DIR / job
    count = 0
    if job_runs_dir.is_dir():
        for d in list(job_runs_dir.iterdir()):
            if d.is_dir() and d.name.startswith("run_"):
                try:
                    shutil.rmtree(d)
                    count += 1
                except Exception as e:
                    logging.error(f"Error removing {d}: {e}")
    return count


def _delete_entire_job(job: str) -> bool:
    """Löscht alle Daten eines Jobs (Input, Preprocessing, Quality, Markdown, Books, PDFs, TEI, Reports, Runs)."""
    in_dir = INPUT_DIR / job
    if in_dir.is_dir():
        shutil.rmtree(in_dir, ignore_errors=True)
    pre_dir = PROC_DIR / "preprocessed" / job
    if pre_dir.is_dir():
        shutil.rmtree(pre_dir, ignore_errors=True)
    qc_dir = PROC_DIR / "quality" / job
    if qc_dir.is_dir():
        shutil.rmtree(qc_dir, ignore_errors=True)
    md_dir = OUT_DIR / "markdown" / job
    if md_dir.is_dir():
        shutil.rmtree(md_dir, ignore_errors=True)
    bk_dir = BOOKS_DIR / job
    if bk_dir.is_dir():
        shutil.rmtree(bk_dir, ignore_errors=True)
    for p in PDF_DIR.glob(f"{job}.*"):
        p.unlink(missing_ok=True)
    for p in TEI_DIR.glob(f"{job}.*"):
        p.unlink(missing_ok=True)
    for p in REPORTS_DIR.glob(f"{job}.*"):
        p.unlink(missing_ok=True)
    runs_dir = RUNS_DIR / job
    if runs_dir.is_dir():
        shutil.rmtree(runs_dir, ignore_errors=True)
    return True


def _build_zip_response(job: str, run_id: str | None = None) -> StreamingResponse | JSONResponse:
    art = _get_job_artifacts(job, run_id=run_id)
    if not art["items"]:
        return JSONResponse({"error": "Keine Artefakte zum Download vorhanden"}, status_code=404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        summary = {
            "job": job,
            "run_id": run_id or "aktuell",
            "exported_at": datetime.now().isoformat(),
            "artifacts_count": len(art["items"]),
            "artifacts": [{"name": it["name"], "title": it["title"], "size_kb": it["size_kb"]} for it in art["items"]],
        }
        zf.writestr("MANIFEST.json", json.dumps(summary, indent=2, ensure_ascii=False))

        for item in art["items"]:
            file_path = Path(item["path"])
            if file_path.exists() and file_path.is_file():
                zf.write(file_path, arcname=file_path.name)

    buf.seek(0)
    suffix = f"_{run_id}" if run_id else ""
    filename = f"{job}{suffix}_artefakte.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _list_jobs():
    jobs = {}
    if INPUT_DIR.is_dir():
        for d in sorted(INPUT_DIR.iterdir()):
            if d.is_dir():
                jobs.setdefault(d.name, {
                    "name": d.name,
                    "input_pages": len([p for p in d.iterdir() if p.suffix.lower() in VALID_IMG_EXTS]),
                    "status": "-",
                    "has_report": False,
                    "has_pdf": False,
                    "runs_count": 0,
                    "has_artifacts": False
                })
    if REPORTS_DIR.is_dir():
        for f in sorted(REPORTS_DIR.glob("*.pipeline.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            name = f.stem.replace(".pipeline", "")
            try: report = json.loads(f.read_text())
            except: report = {}
            entry = jobs.get(name, {
                "name": name,
                "input_pages": 0,
                "status": "-",
                "has_report": False,
                "has_pdf": False,
                "runs_count": 0,
                "has_artifacts": False
            })
            entry["status"] = "PASS" if report.get("fail", 1) == 0 or report.get("pass", 0) > 0 else "FAIL"
            entry["has_report"] = True
            entry["pass"] = report.get("pass", 0)
            entry["fail"] = report.get("fail", 0)
            mistral_pages = report.get("mistral_ok", 0)
            entry["mistral_ok"] = mistral_pages
            entry["mistral_cost_usd"] = round(mistral_pages * 0.004, 4)
            entry["pages_total"] = report.get("pages_total", 0)
            entry["threshold"] = report.get("threshold", 0)
            entry["lang"] = report.get("lang", "")
            entry["modified"] = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            jobs[name] = entry
    if PDF_DIR.is_dir():
        for f in PDF_DIR.glob("*.pdf"):
            name = f.stem.replace(".sandwich", "").replace(".pathb", "").replace(".digital", "")
            if name in jobs: jobs[name]["has_pdf"] = True
    if TEI_DIR.is_dir():
        for f in TEI_DIR.glob("*.tei.xml"):
            name = f.name.replace(".tei.xml", "")
            if name in jobs: jobs[name]["has_tei"] = True

    # Ergänze Vorläufe und Artefakt-Status für jeden Job
    for name, entry in jobs.items():
        entry["runs_count"] = len(_list_job_runs(name))
        entry["has_artifacts"] = _get_job_artifacts(name)["has_any"]

    return sorted(jobs.values(), key=lambda j: j.get("modified", ""), reverse=True)


def _trigger_n8n(job, lang="deu+eng", threshold=100, limit=0, no_mistral=False, skip_preprocess=False):
    payload = {"job": job, "pull": False, "push": False, "lang": lang, "threshold": threshold, "limit": limit, "no_mistral": no_mistral, "skip_preprocess": skip_preprocess}
    urls_to_try = [N8N_WEBHOOK_URL]
    if FALLBACK_N8N_URL and FALLBACK_N8N_URL != N8N_WEBHOOK_URL:
        urls_to_try.append(FALLBACK_N8N_URL)

    last_err = ""
    for target_url in urls_to_try:
        try:
            resp = httpx.post(target_url, json=payload, timeout=N8N_WEBHOOK_TIMEOUT)
            try:
                data = resp.json()
                if target_url != N8N_WEBHOOK_URL:
                    data["via_fallback"] = target_url
                return data
            except Exception:
                last_err = f"n8n returned HTTP {resp.status_code}: {resp.text[:500]}"
        except Exception as e:
            last_err = str(e)
            continue
    return {"ok": False, "error": last_err}


def _probe_system_status() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. UI Host
    ui_status = {
        "id": "ui",
        "name": "Alexandria Web Portal (FastAPI)",
        "role": "Upload-Ingress, Job-Verwaltung & Status-Dashboard",
        "status": "healthy",
        "badge": "ONLINE",
        "port": 8080,
        "runtime": f"Python {platform.python_version()}",
        "os": f"{platform.system()} {platform.release()}",
        "hostname": platform.node(),
        "pid": os.getpid(),
        "ingress": "Traefik v3 + Authelia 2FA (alex.birchville.cc)",
    }

    # 2. n8n Engine Probe
    def _check_n8n_endpoint(url: str):
        if not url:
            return False, None, "Keine URL konfiguriert"
        try:
            p = urlparse(url)
            health_url = f"{p.scheme}://{p.netloc}/healthz"
            t0 = time.time()
            resp = httpx.get(health_url, timeout=2.0)
            lat = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200:
                return True, lat, f"HTTP 200 ({lat} ms)"
            return False, lat, f"HTTP {resp.status_code}"
        except Exception as exc:
            err_str = str(exc)
            if "Name or service not known" in err_str or "Errno -2" in err_str:
                return False, None, "DNS-Fehler: Hostname nicht auflösbar"
            elif "Connection refused" in err_str or "Errno 61" in err_str or "Errno 111" in err_str:
                return False, None, "Verbindung abgelehnt (Port 5678 nicht erreichbar)"
            return False, None, f"Fehler: {err_str[:60]}"

    n8n_ok, n8n_lat, n8n_msg = _check_n8n_endpoint(N8N_WEBHOOK_URL)
    fallback_ok, fallback_lat, fallback_msg = _check_n8n_endpoint(FALLBACK_N8N_URL) if not n8n_ok else (None, None, None)

    n8n_state = "healthy" if n8n_ok else ("warning" if fallback_ok else "error")
    n8n_badge = "ONLINE" if n8n_ok else ("FALLBACK BEREIT" if fallback_ok else "OFFLINE")
    remedy = None
    if not n8n_ok:
        if fallback_ok:
            remedy = f"Primäre URL '{N8N_WEBHOOK_URL}' schlägt fehl, Fallback '{FALLBACK_N8N_URL}' antwortet ({fallback_lat} ms). N8N_WEBHOOK_URL in Docker anpassen."
        else:
            remedy = f"n8n unter weder '{N8N_WEBHOOK_URL}' noch '{FALLBACK_N8N_URL}' erreichbar. Prüfe, ob n8n auf alex.local läuft."

    n8n_status = {
        "id": "n8n",
        "name": "Workflow-Engine (n8n Orchestrator)",
        "role": "Asynchrone Pipeline-Steuerung & Worker-Ausführung",
        "status": n8n_state,
        "badge": n8n_badge,
        "primary_url": N8N_WEBHOOK_URL,
        "primary_ok": n8n_ok,
        "primary_latency_ms": n8n_lat,
        "primary_message": n8n_msg,
        "fallback_url": FALLBACK_N8N_URL,
        "fallback_ok": fallback_ok,
        "fallback_latency_ms": fallback_lat,
        "fallback_message": fallback_msg,
        "workflow_id": "alexandria-pipeline",
        "remedy": remedy
    }

    # 3. Compute Worker (alexandria_worker)
    worker_script = (BASE_DIR / "scripts" / "run_pipeline.sh") if (BASE_DIR / "scripts" / "run_pipeline.sh").exists() else Path("/opt/alexandria/scripts/run_pipeline.sh")
    worker_status = {
        "id": "worker",
        "name": "OCR Compute Worker (alexandria_worker)",
        "role": "Bildvorverarbeitung, OCR-Durchführung, Typst-Neusatz & TEI/EPUB Assembly",
        "status": "healthy" if (n8n_ok or fallback_ok) else "warning",
        "badge": "BEREIT" if (n8n_ok or fallback_ok) else "STANDBY",
        "target": "alex.local (Proxmox Compute Node)",
        "pipeline_script": str(worker_script) if worker_script.exists() else "/opt/alexandria/scripts/run_pipeline.sh",
        "trigger_mechanism": "docker exec via n8n (n8n_run_job.sh)",
        "mode": "On-Demand Container Execution"
    }

    # 4. Storage Subsystem (/data)
    total_b, used_b, free_b = (0, 0, 0)
    try:
        total_b, used_b, free_b = shutil.disk_usage(DATA_DIR)
    except Exception:
        pass

    total_gb = round(total_b / (1024**3), 1)
    used_gb = round(used_b / (1024**3), 1)
    free_gb = round(free_b / (1024**3), 1)
    used_pct = round((used_b / total_b * 100), 1) if total_b > 0 else 0.0

    in_jobs_count = len([d for d in INPUT_DIR.iterdir() if d.is_dir()]) if INPUT_DIR.is_dir() else 0
    in_files_count = len([p for p in INPUT_DIR.glob("*/*.*") if p.suffix.lower() in VALID_IMG_EXTS]) if INPUT_DIR.is_dir() else 0
    proc_prep_count = len(list(PROC_DIR.glob("preprocessed/*/*.png"))) if PROC_DIR.is_dir() else 0
    proc_qc_count = len(list(PROC_DIR.glob("quality/*/*.json"))) if PROC_DIR.is_dir() else 0
    out_rep_count = len(list(REPORTS_DIR.glob("*.pipeline.json"))) if REPORTS_DIR.is_dir() else 0
    out_pdf_count = len(list(PDF_DIR.glob("*.pdf"))) if PDF_DIR.is_dir() else 0
    out_tei_count = len(list(TEI_DIR.glob("*.tei.xml"))) if TEI_DIR.is_dir() else 0
    out_epub_count = len(list(BOOKS_DIR.glob("**/*.epub"))) if BOOKS_DIR.is_dir() else 0
    out_runs_count = sum(len([p for p in d.iterdir() if p.is_dir() and p.name.startswith("run_")]) for d in RUNS_DIR.iterdir() if d.is_dir()) if RUNS_DIR.is_dir() else 0

    storage_status = {
        "id": "storage",
        "name": "Speicher-Subsystem (/data)",
        "role": "Eingangsdaten, Vorverarbeitung, Berichte & Zielformate",
        "status": "healthy" if free_gb > 2.0 else "warning",
        "badge": "ONLINE",
        "base_path": str(DATA_DIR),
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "used_pct": used_pct,
        "counts": {
            "input_jobs": in_jobs_count,
            "input_pages": in_files_count,
            "preprocessed_pages": proc_prep_count,
            "quality_files": proc_qc_count,
            "reports": out_rep_count,
            "pdfs": out_pdf_count,
            "tei_xmls": out_tei_count,
            "epubs": out_epub_count,
            "archived_runs": out_runs_count
        }
    }

    # 5. Tools (Poppler, Typst, Tesseract)
    poppler_which = shutil.which("pdftoppm")
    typst_which = shutil.which("typst")
    tess_which = shutil.which("tesseract")
    tools_status = {
        "id": "tools",
        "name": "Lokale Hilfswerkzeuge & Renderer",
        "role": "PDF-Seitenextraktion, Lokales OCR & Typst-Kompilierung",
        "poppler": {
            "present": bool(poppler_which),
            "path": poppler_which or "poppler-utils im UI-Container",
            "status": "healthy" if poppler_which else "warning"
        },
        "typst": {
            "present": bool(typst_which),
            "path": typst_which or "Im Worker-Container integriert",
            "status": "healthy"
        },
        "tesseract": {
            "present": bool(tess_which),
            "path": tess_which or "Im Worker-Container integriert",
            "status": "healthy"
        }
    }

    # 6. Mistral AI Document OCR
    mistral_key = os.getenv("MISTRAL_API_KEY", "")
    mistral_configured = bool(mistral_key and len(mistral_key) > 5)
    mistral_masked = f"{mistral_key[:4]}...{mistral_key[-4:]}" if mistral_configured else "Nicht konfiguriert"
    mistral_ok = False
    mistral_lat = None
    mistral_msg = "Nicht konfiguriert"
    if mistral_configured:
        try:
            t0 = time.time()
            m_resp = httpx.get("https://api.mistral.ai/v1/models", headers={"Authorization": f"Bearer {mistral_key}"}, timeout=2.5)
            mistral_lat = round((time.time() - t0) * 1000, 1)
            if m_resp.status_code == 200:
                mistral_ok = True
                mistral_msg = f"API autorisiert & erreichbar ({mistral_lat} ms)"
            else:
                mistral_msg = f"HTTP {m_resp.status_code}"
        except Exception as exc:
            mistral_msg = f"Verbindungsfehler: {str(exc)[:60]}"
    mistral_status = {
        "id": "mistral",
        "name": "Cloud Vision AI (Mistral Document AI)",
        "role": "Multimodale Layout-Analyse & Hochpräzisions-OCR (Devanāgarī, Fraktur)",
        "status": "healthy" if mistral_ok else ("warning" if mistral_configured else "offline"),
        "badge": "ONLINE" if mistral_ok else ("KONFIGURIERT" if mistral_configured else "FEHLT"),
        "key_present": mistral_configured,
        "key_masked": mistral_masked,
        "latency_ms": mistral_lat,
        "message": mistral_msg,
        "cost_rate": "0,004 $ pro Seite",
        "model": "mistral-ocr-latest"
    }

    # 7. Qwen2.5-VL Vision
    qwen_endpoint = os.getenv("QWEN_OCR_ENDPOINT", "http://nyx.local:8088/v1").rstrip("/")
    qwen_ok = False
    qwen_lat = None
    qwen_msg = "Standby (nyx.local:8088 offline)"
    try:
        t0 = time.time()
        q_resp = httpx.get(f"{qwen_endpoint}/models", timeout=1.5)
        qwen_lat = round((time.time() - t0) * 1000, 1)
        if q_resp.status_code == 200:
            qwen_ok = True
            m_count = len(q_resp.json().get("data", []))
            qwen_msg = f"Online ({m_count} Modelle, {qwen_lat} ms)"
        else:
            qwen_msg = f"HTTP {q_resp.status_code}"
    except Exception:
        pass
    qwen_status = {
        "id": "qwen",
        "name": "Lokales Vision-LLM (Qwen2.5-VL)",
        "role": "Lokale Vision-Language OCR via nyx.local:8088 (OpenAI-kompatibel)",
        "status": "healthy" if qwen_ok else "standby",
        "badge": "ONLINE" if qwen_ok else "STANDBY",
        "endpoint": qwen_endpoint,
        "latency_ms": qwen_lat,
        "message": qwen_msg,
        "cost_rate": "0,00 $ (Lokale GPU)",
    }

    # 8. Stalled Jobs Detection
    stalled_jobs = []
    if INPUT_DIR.is_dir():
        for d in sorted(INPUT_DIR.iterdir()):
            if not d.is_dir():
                continue
            rep = REPORTS_DIR / f"{d.name}.pipeline.json"
            if not rep.exists():
                img_count = len([p for p in d.iterdir() if p.suffix.lower() in VALID_IMG_EXTS])
                if img_count > 0:
                    stalled_jobs.append({
                        "name": d.name,
                        "pages": img_count,
                        "folder": str(d),
                        "modified": datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })

    # Overall Status Calculation
    if not n8n_ok and not fallback_ok:
        overall_status = "critical"
        overall_text = "Kritische Störung: Orchestrator nicht erreichbar"
    elif not n8n_ok and fallback_ok:
        overall_status = "warning"
        overall_text = "Beeinträchtigt: n8n nur über Fallback-IP erreichbar"
    elif not mistral_configured:
        overall_status = "warning"
        overall_text = "Warnung: Mistral API Key fehlt"
    elif len(stalled_jobs) > 0:
        overall_status = "warning"
        overall_text = f"Achtung: {len(stalled_jobs)} Job(s) mit ausstehendem Trigger"
    else:
        overall_status = "healthy"
        overall_text = "Alle Systeme betriebsbereit"

    recent_jobs = _list_jobs()[:6]
    featured_job = None
    if stalled_jobs:
        featured_job = stalled_jobs[0]["name"]
    elif recent_jobs:
        featured_job = recent_jobs[0]["name"]

    featured_progress = _get_job_progress(featured_job) if featured_job else None
    all_jobs_progress = {j["name"]: _get_job_progress(j["name"]) for j in recent_jobs}
    if stalled_jobs and stalled_jobs[0]["name"] not in all_jobs_progress:
        all_jobs_progress[stalled_jobs[0]["name"]] = _get_job_progress(stalled_jobs[0]["name"])

    return {
        "timestamp_utc": now.isoformat(),
        "timestamp_local": now_local,
        "overall_status": overall_status,
        "overall_text": overall_text,
        "host": ui_status,
        "n8n": n8n_status,
        "worker": worker_status,
        "storage": storage_status,
        "tools": tools_status,
        "mistral": mistral_status,
        "qwen": qwen_status,
        "stalled_jobs": stalled_jobs,
        "recent_jobs": recent_jobs,
        "featured_job": featured_job,
        "featured_progress": featured_progress,
        "all_jobs_progress": all_jobs_progress
    }


def _get_job_progress(job: str) -> dict[str, Any]:
    in_dir = INPUT_DIR / job
    pre_dir = PROC_DIR / "preprocessed" / job
    qc_dir = PROC_DIR / "quality" / job
    md_dir = OUT_DIR / "markdown" / job
    rep_file = REPORTS_DIR / f"{job}.pipeline.json"

    rep_data = {}
    if rep_file.exists():
        try:
            rep_data = json.loads(rep_file.read_text())
        except Exception:
            pass

    in_files = [p for p in in_dir.iterdir() if p.suffix.lower() in VALID_IMG_EXTS] if in_dir.is_dir() else []
    pre_files = list(pre_dir.glob("*.png")) if pre_dir.is_dir() else []
    qc_files = list(qc_dir.glob("*.quality.json")) if qc_dir.is_dir() else []
    md_files = list(md_dir.glob("*.md")) if md_dir.is_dir() else []
    sandwich_pdf = PDF_DIR / f"{job}.sandwich.pdf"
    digital_pdf = PDF_DIR / f"{job}.digital.pdf"
    pathb_pdf = PDF_DIR / f"{job}.pathb.pdf"
    tei_file = TEI_DIR / f"{job}.tei.xml"
    epub_file = BOOKS_DIR / job / f"{job}.epub"
    if not epub_file.exists():
        epub_alt = OUT_DIR / "books" / f"{job}.epub"
        if epub_alt.exists():
            epub_file = epub_alt

    pages_total = rep_data.get("pages_total") or len(in_files) or len(pre_files) or 1
    mistral_ok = rep_data.get("mistral_ok", len(md_files))
    pass_n = rep_data.get("pass", 0)
    fail_n = rep_data.get("fail", 0)
    has_report = rep_file.exists()

    stages = []

    # 1. Ingress & Seitenbereitstellung
    s1_done = len(in_files) > 0 or has_report
    s1_dur = round(max(1.0, len(in_files) * 0.25), 1)
    stages.append({
        "id": 1,
        "name": "Ingress & Seitenextraktion",
        "tool": "pdftoppm (Poppler)",
        "status": "completed" if s1_done else "pending",
        "progress": 100 if s1_done else 0,
        "info": f"{len(in_files) or pages_total} Einzelseite(n) bereitgestellt (300 DPI)",
        "duration_str": f"{s1_dur} s" if s1_done else f"~{s1_dur} s",
        "seconds": s1_dur
    })

    # 2. Bildvorverarbeitung
    s2_done = has_report or (len(pre_files) >= pages_total and pages_total > 0)
    s2_running = not s2_done and len(pre_files) > 0
    s2_prog = 100 if s2_done else (round((len(pre_files) / pages_total) * 100) if pages_total else 0)
    s2_dur = round(max(1.0, pages_total * 0.8), 1)
    stages.append({
        "id": 2,
        "name": "Bildvorverarbeitung (Entzerrung)",
        "tool": "ImageMagick & Unpaper",
        "status": "completed" if s2_done else ("running" if s2_running else "pending"),
        "progress": s2_prog,
        "info": f"{len(pre_files)} von {pages_total} Seiten entzerrt" if (s2_running or len(pre_files) > 0) else f"{pages_total} Seiten eingeplant (Deskew/Binarisierung)",
        "duration_str": f"{s2_dur} s" if s2_done else f"~{s2_dur} s",
        "seconds": s2_dur
    })

    # 3. Tesseract OCR & Quality-Gate
    s3_done = has_report or (len(qc_files) >= pages_total and pages_total > 0)
    s3_running = not s3_done and len(qc_files) > 0
    s3_prog = 100 if s3_done else (round((len(qc_files) / pages_total) * 100) if pages_total else 0)
    s3_dur = round(max(1.5, pages_total * 1.0), 1)
    threshold = rep_data.get("threshold", 100)
    stages.append({
        "id": 3,
        "name": "Tesseract OCR & Konfidenz-Gate",
        "tool": "Tesseract 5 (deu+eng+san)",
        "status": "completed" if s3_done else ("running" if s3_running else "pending"),
        "progress": s3_prog,
        "info": f"PASS: {pass_n}, FAIL: {fail_n} (Schwellenwert {threshold} %)" if has_report else f"{len(qc_files)} von {pages_total} Seiten ausgewertet",
        "duration_str": f"{s3_dur} s" if s3_done else f"~{s3_dur} s",
        "seconds": s3_dur
    })

    # 4. Mistral Document AI Cloud Fallback
    s4_done = has_report or (len(md_files) >= mistral_ok and mistral_ok > 0)
    s4_running = not s4_done and len(md_files) > 0
    s4_prog = 100 if s4_done else (round((len(md_files) / max(1, mistral_ok)) * 100) if mistral_ok else 0)
    s4_dur = round(max(1.5, (mistral_ok or pages_total) * 1.8), 1)
    cost_usd = round((mistral_ok or 0) * 0.004, 4)
    stages.append({
        "id": 4,
        "name": "Cloud Vision AI (Mistral OCR)",
        "tool": "mistral-ocr-latest",
        "status": "completed" if s4_done else ("running" if s4_running else "pending"),
        "progress": s4_prog,
        "info": f"{mistral_ok} Seiten erfasst (Fremdkosten: ${cost_usd})" if has_report else f"{len(md_files)} Seiten hochauflösend analysiert",
        "duration_str": f"{s4_dur} s" if s4_done else f"~{s4_dur} s",
        "seconds": s4_dur
    })

    # 5. Sandwich-PDF Assembly
    s5_done = sandwich_pdf.exists() or has_report
    s5_dur = round(max(2.0, min(15.0, pages_total * 0.4 + 3.0)), 1)
    pdf_kb = round(sandwich_pdf.stat().st_size / 1024, 1) if sandwich_pdf.exists() else 0
    stages.append({
        "id": 5,
        "name": "Sandwich-PDF & Sidecar Assembly",
        "tool": "PyMuPDF / assemble_sandwich.py",
        "status": "completed" if s5_done else "pending",
        "progress": 100 if s5_done else 0,
        "info": f"Doppellagiges PDF ({pdf_kb} KB) & Text-Sidecar" if sandwich_pdf.exists() else "Unsichtbare OCR-Textebene über Faksimile",
        "duration_str": f"{s5_dur} s" if s5_done else f"~{s5_dur} s",
        "seconds": s5_dur
    })

    # 6. Typst Digital-Neusatz & TEI-P5
    s6_done = digital_pdf.exists() or tei_file.exists() or has_report
    s6_dur = round(max(2.0, min(10.0, pages_total * 0.2 + 2.0)), 1)
    digi_kb = round(digital_pdf.stat().st_size / 1024, 1) if digital_pdf.exists() else 0
    stages.append({
        "id": 6,
        "name": "Typst Neusatz & TEI-P5 XML",
        "tool": "Typst CLI & TEI-P5 Generator",
        "status": "completed" if s6_done else "pending",
        "progress": 100 if s6_done else 0,
        "info": f"Typst PDF ({digi_kb} KB) & TEI-XML Schema" if s6_done else "Semantischer Neusatz mit Garamond & Devanāgarī",
        "duration_str": f"{s6_dur} s" if s6_done else f"~{s6_dur} s",
        "seconds": s6_dur
    })

    # 7. KI-Textlayer-Synchronisation (In-PDF)
    s7_done = pathb_pdf.exists() or has_report
    s7_dur = round(max(2.0, min(12.0, pages_total * 0.3 + 3.0)), 1)
    pathb_kb = round(pathb_pdf.stat().st_size / 1024, 1) if pathb_pdf.exists() else 0
    stages.append({
        "id": 7,
        "name": "KI-Textlayer-Synchronisation (In-PDF)",
        "tool": "align_mistral_pdf.py",
        "status": "completed" if s7_done else "pending",
        "progress": 100 if s7_done else 0,
        "info": f"KI-präzisiertes Sandwich-PDF ({pathb_kb} KB)" if pathb_pdf.exists() else "Präzisions-Token-Austausch im PDF Content-Stream",
        "duration_str": f"{s7_dur} s" if s7_done else f"~{s7_dur} s",
        "seconds": s7_dur
    })

    # 8. EPUB 3 & Report
    s8_done = has_report
    s8_dur = round(max(1.0, min(8.0, pages_total * 0.1 + 1.5)), 1)
    epub_name = epub_file.name if epub_file.exists() else f"{job}.epub"
    stages.append({
        "id": 8,
        "name": "EPUB 3 & Pipeline-Auditbericht",
        "tool": "export_epub.py & Pipeline Logger",
        "status": "completed" if s8_done else "pending",
        "progress": 100 if s8_done else 0,
        "info": f"Erfolgreich abgeschlossen ({epub_name})" if has_report else "Archiv-E-Book & JSON-Qualitätsaudit",
        "duration_str": f"{s8_dur} s" if s8_done else f"~{s8_dur} s",
        "seconds": s8_dur
    })

    total_sec = sum(s["seconds"] for s in stages)
    completed_stages = sum(1 for s in stages if s["status"] == "completed")
    overall_progress = round((completed_stages / len(stages)) * 100)

    current_stage = "Vollständig abgeschlossen"
    status_type = "completed"
    if not has_report:
        if s1_done and not s2_running and not s2_done:
            current_stage = "Wartet auf Pipeline-Trigger (Bereitgestellt)"
            status_type = "waiting"
        else:
            status_type = "running"
            for s in stages:
                if s["status"] in ("running", "pending"):
                    current_stage = f"Stufe {s['id']}: {s['name']}"
                    break

    art = _get_job_artifacts(job)
    runs = _list_job_runs(job)

    return {
        "job": job,
        "status_type": status_type,
        "has_report": has_report,
        "pages_total": pages_total,
        "overall_progress": overall_progress,
        "completed_stages": completed_stages,
        "total_stages": len(stages),
        "current_stage": current_stage,
        "current_threshold": rep_data.get("threshold", 100),
        "current_lang": rep_data.get("lang", "deu+eng"),
        "current_pass": pass_n,
        "current_fail": fail_n,
        "current_mistral_ok": mistral_ok,
        "estimated_total_seconds": total_sec,
        "estimated_total_str": f"{int(total_sec // 60)} Min. {int(total_sec % 60)} s" if total_sec >= 60 else f"{round(total_sec, 1)} s",
        "stages": stages,
        "artifacts": art,
        "runs": runs,
        "runs_count": len(runs),
        "zip_download_url": f"/jobs/{job}/download-zip"
    }


def _safe_path(base, user_path):
    resolved = (base / user_path).resolve()
    if not str(resolved).startswith(str(base.resolve())): raise ValueError("path traversal blocked")
    return resolved


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def landing(request: Request):
    jobs = _list_jobs()
    total_pages = sum(j.get("pages_total", j.get("input_pages", 0)) for j in jobs)
    total_mistral = sum(j.get("mistral_ok", 0) for j in jobs)
    return templates.TemplateResponse(request, "landing.html", {
        "jobs": jobs[:6],
        "total_jobs": len(jobs),
        "total_pages": total_pages,
        "total_mistral": total_mistral
    })


@app.api_route("/dashboard", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def dashboard(request: Request):
    jobs = _list_jobs()
    return templates.TemplateResponse(request, "dashboard.html", {"jobs": jobs})


@app.api_route("/status", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def status_page(request: Request):
    data = await asyncio.to_thread(_probe_system_status)
    requested_job = request.query_params.get("job")
    if requested_job and requested_job in data.get("all_jobs_progress", {}):
        data["featured_job"] = requested_job
        data["featured_progress"] = data["all_jobs_progress"][requested_job]
    return templates.TemplateResponse(request, "status.html", {
        "status_data": data
    })


@app.api_route("/api/system/status", methods=["GET", "HEAD"])
async def api_system_status():
    data = await asyncio.to_thread(_probe_system_status)
    return JSONResponse(data)


@app.api_route("/api/jobs/{job}/progress", methods=["GET", "HEAD"])
async def api_job_progress(job: str):
    prog = await asyncio.to_thread(_get_job_progress, job)
    return JSONResponse(prog)


@app.api_route("/portal", methods=["GET", "HEAD"])
async def portal_redirect():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.api_route("/login", methods=["GET", "HEAD"])
async def login_redirect():
    return RedirectResponse(url="https://auth.birchville.cc/?rd=https://alex.birchville.cc/upload", status_code=302)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    data = await asyncio.to_thread(_probe_system_status)
    return {
        "status": data["overall_status"],
        "service": "AlexandriaSandwich",
        "timestamp": data["timestamp_utc"],
        "n8n": data["n8n"]["badge"],
        "storage_free_gb": data["storage"]["free_gb"],
        "stalled_jobs": len(data["stalled_jobs"])
    }


logger = logging.getLogger("alexandria_ui")
VALID_IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pnm", ".ppm"}


def _extract_pdf(pdf_path: Path, target_dir: Path, stem: str, dpi: int = 300) -> list[str]:
    """Extrahiert Seiten eines Multi-Page PDFs als PNG via pdftoppm."""
    target_dir.mkdir(parents=True, exist_ok=True)
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem).strip("_") or "page"
    prefix = target_dir / clean_stem
    cmd = ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip()
        logger.error(f"pdftoppm fehlgeschlagen: {err}")
        raise RuntimeError(f"pdftoppm Fehler: {err}")
    pages = sorted([p.name for p in target_dir.glob(f"{clean_stem}-*.png")])
    return pages


def _extract_zip(zip_path: Path, target_dir: Path, dpi: int = 300) -> list[str]:
    """Entpackt Bilddateien und PDFs aus einem ZIP-Archiv."""
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            fname = Path(member.filename).name
            if not fname or fname.startswith(".") or fname.startswith("__MACOSX"):
                continue
            ext = Path(fname).suffix.lower()
            if ext in VALID_IMG_EXTS:
                dest = target_dir / fname
                with zf.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(dest.name)
            elif ext == ".pdf":
                temp_pdf = target_dir / f"_temp_{fname}"
                with zf.open(member) as src, open(temp_pdf, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                try:
                    pdf_pages = _extract_pdf(temp_pdf, target_dir, stem=Path(fname).stem, dpi=dpi)
                    extracted.extend(pdf_pages)
                finally:
                    temp_pdf.unlink(missing_ok=True)
    return sorted(extracted)


@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    jobs = _list_jobs()
    total_cost = sum(j.get("mistral_cost_usd", 0.0) for j in jobs)
    return templates.TemplateResponse(request, "upload.html", {
        "result": None,
        "recent_jobs": jobs[:6],
        "total_mistral_cost": round(total_cost, 4),
    })


@app.post("/upload")
async def upload_submit(
    request: Request,
    job: str = Form(...),
    lang: str = Form("deu+eng"),
    threshold: int = Form(100),
    limit: int = Form(0),
    dpi: int = Form(300),
    no_mistral: bool = Form(False),
    trigger: bool = Form(False),
    files: list[UploadFile] = File(...),
):
    job_dir = INPUT_DIR / job
    job_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    notes = []

    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext == ".pdf":
            # Originales PDF als Quelle sichern
            pdf_path = job_dir / f"source_{Path(f.filename).name}"
            with open(pdf_path, "wb") as out:
                out.write(await f.read())
            try:
                pages = await asyncio.to_thread(_extract_pdf, pdf_path, job_dir, Path(f.filename).stem, dpi)
                saved.extend(pages)
                notes.append(f"PDF '{f.filename}' zerlegt in {len(pages)} Einzelseite(n) ({dpi} DPI)")
            except Exception as e:
                notes.append(f"Fehler bei PDF-Extraktion von '{f.filename}': {e}")
        elif ext == ".zip":
            zip_path = job_dir / f"_temp_{Path(f.filename).name}"
            with open(zip_path, "wb") as out:
                out.write(await f.read())
            try:
                items = await asyncio.to_thread(_extract_zip, zip_path, job_dir, dpi)
                saved.extend(items)
                notes.append(f"ZIP-Archiv '{f.filename}' entpackt: {len(items)} Seite(n) bereitgestellt")
            except Exception as e:
                notes.append(f"Fehler bei ZIP-Entpacken von '{f.filename}': {e}")
            finally:
                zip_path.unlink(missing_ok=True)
        elif ext in VALID_IMG_EXTS:
            dest = job_dir / Path(f.filename).name
            with open(dest, "wb") as out:
                out.write(await f.read())
            saved.append(dest.name)
        else:
            notes.append(f"Format nicht unterstützt und übersprungen: '{f.filename}'")

    result = {
        "saved": saved,
        "notes": notes,
        "job": job,
        "triggered": False,
        "has_report": False,
        "mistral_pages": 0,
        "mistral_cost_usd": 0.0,
        "cost_per_page_usd": 0.004,
        "tesseract_pass": 0,
        "tesseract_fail": 0,
        "pages_total": len(saved),
    }

    if trigger and len(saved) > 0:
        n8n_resp = _trigger_n8n(job, lang=lang, threshold=threshold, limit=limit, no_mistral=no_mistral)
        result["triggered"] = True
        result["n8n_response"] = n8n_resp

        # Check ob Report unmittelbar vorliegt (z. B. synchrone Pipeline)
        report_path = REPORTS_DIR / f"{job}.pipeline.json"
        if report_path.exists():
            try:
                rep = json.loads(report_path.read_text())
                result["has_report"] = True
                result["pages_total"] = rep.get("pages_total", len(saved))
                result["tesseract_pass"] = rep.get("pass", 0)
                result["tesseract_fail"] = rep.get("fail", 0)
                m_ok = rep.get("mistral_ok", 0)
                result["mistral_pages"] = m_ok
                result["mistral_cost_usd"] = round(m_ok * 0.004, 4)
            except Exception:
                pass

    jobs = _list_jobs()
    total_cost = sum(j.get("mistral_cost_usd", 0.0) for j in jobs)
    return templates.TemplateResponse(request, "upload.html", {
        "result": result,
        "recent_jobs": jobs[:6],
        "total_mistral_cost": round(total_cost, 4),
    })


@app.get("/api/jobs/{job}/status")
async def job_status_api(job: str):
    report_path = REPORTS_DIR / f"{job}.pipeline.json"
    in_dir = INPUT_DIR / job
    input_pages = len([p for p in in_dir.iterdir() if p.suffix.lower() in VALID_IMG_EXTS]) if in_dir.is_dir() else 0
    if not report_path.exists():
        return {
            "job": job,
            "status": "PROCESSING",
            "has_report": False,
            "input_pages": input_pages,
            "tesseract_pass": 0,
            "tesseract_fail": 0,
            "mistral_pages": 0,
            "mistral_cost_usd": 0.0,
            "cost_per_page_usd": 0.004,
        }
    try:
        report = json.loads(report_path.read_text())
    except Exception as e:
        return {"job": job, "status": "ERROR", "error": str(e)}

    mistral_pages = report.get("mistral_ok", 0)
    cost_usd = round(mistral_pages * 0.004, 4)
    pages_total = report.get("pages_total", input_pages)
    pass_pages = report.get("pass", 0)
    fail_pages = report.get("fail", 0)

    return {
        "job": job,
        "status": "COMPLETED",
        "has_report": True,
        "pages_total": pages_total,
        "tesseract_pass": pass_pages,
        "tesseract_fail": fail_pages,
        "mistral_pages": mistral_pages,
        "mistral_cost_usd": cost_usd,
        "cost_per_page_usd": 0.004,
        "modified": datetime.fromtimestamp(report_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/jobs/{job}/trigger")
async def trigger_job(request: Request, job: str):
    lang = "deu+eng"
    threshold = 100
    limit = 0
    no_mistral = False

    skip_preprocess = False

    # 1. Query Params
    qp = request.query_params
    if "lang" in qp: lang = qp["lang"]
    if "threshold" in qp: threshold = int(qp["threshold"])
    if "limit" in qp: limit = int(qp["limit"])
    if "no_mistral" in qp: no_mistral = qp["no_mistral"].lower() in ("1", "true", "yes", "on")
    if "skip_preprocess" in qp: skip_preprocess = qp["skip_preprocess"].lower() in ("1", "true", "yes", "on")

    # 2. Form or JSON Body
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            body = await request.json()
            lang = body.get("lang", lang)
            threshold = int(body.get("threshold", threshold))
            limit = int(body.get("limit", limit))
            no_mistral = bool(body.get("no_mistral", no_mistral))
            skip_preprocess = bool(body.get("skip_preprocess", skip_preprocess))
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
        try:
            form = await request.form()
            if "lang" in form: lang = str(form["lang"])
            if "threshold" in form: threshold = int(form["threshold"])
            if "limit" in form: limit = int(form["limit"])
            if "no_mistral" in form: no_mistral = str(form["no_mistral"]).lower() in ("1", "true", "yes", "on")
            if "skip_preprocess" in form: skip_preprocess = str(form["skip_preprocess"]).lower() in ("1", "true", "yes", "on")
        except Exception:
            pass

    # 3. Vor Re-Run: bisherigen Lauf automatisch archivieren, falls Artefakte vorhanden sind
    current_art = _get_job_artifacts(job)
    if current_art.get("has_any"):
        archived_id = _archive_current_run(
            job,
            note=f"Snapshot vor Re-Run (Threshold {threshold}%, {lang})"
        )
        logging.info(f"Job '{job}': Aktueller Stand archiviert als '{archived_id}'")

    resp = await asyncio.to_thread(
        _trigger_n8n,
        job,
        lang=lang,
        threshold=threshold,
        limit=limit,
        no_mistral=no_mistral,
        skip_preprocess=skip_preprocess
    )

    redirect_target = request.query_params.get("redirect", "")
    if not redirect_target:
        ref = request.headers.get("referer", "")
        if "/status" in ref:
            redirect_target = f"/status?job={job}"
        else:
            redirect_target = f"/jobs/{job}"

    accept = request.headers.get("accept", "")
    if "text/html" in accept or redirect_target:
        return RedirectResponse(url=redirect_target, status_code=303)
    return JSONResponse(resp)


@app.get("/jobs/{job}", response_class=HTMLResponse)
async def job_detail(job: str, request: Request):
    info = {"name": job}
    report_path = REPORTS_DIR / f"{job}.pipeline.json"
    info["report"] = json.loads(report_path.read_text()) if report_path.exists() else None
    in_dir = INPUT_DIR / job
    info["input_pages"] = sorted([p.name for p in in_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".tif", ".jpeg"}]) if in_dir.is_dir() else []
    pre_dir = PROC_DIR / "preprocessed" / job
    info["preprocessed_pages"] = sorted([p.name for p in pre_dir.iterdir() if p.suffix.lower() == ".png"]) if pre_dir.is_dir() else []
    qc_dir = PROC_DIR / "quality" / job
    info["quality_files"] = sorted([p.name for p in qc_dir.glob("*.quality.json")]) if qc_dir.is_dir() else []
    md_dir = OUT_DIR / "markdown" / job
    info["markdown_files"] = sorted([p.name for p in md_dir.glob("*.md")]) if md_dir.is_dir() else []
    info["pdfs"] = []
    if PDF_DIR.is_dir():
        for pattern in [f"{job}.sandwich.pdf", f"{job}.digital.pdf", f"{job}.pathb.pdf"]:
            p = PDF_DIR / pattern
            if p.exists(): info["pdfs"].append({"name": p.name, "size_kb": round(p.stat().st_size / 1024, 1), "kind": "digital" if "digital" in p.name else ("sandwich" if "sandwich" in p.name else "pathb")})
    
    tei_file = TEI_DIR / f"{job}.tei.xml"
    info["tei_xml"] = {"name": tei_file.name, "size_kb": round(tei_file.stat().st_size / 1024, 1)} if tei_file.exists() else None

    book_dir = BOOKS_DIR / job
    epub_file = book_dir / f"{job}.epub"
    if not epub_file.exists():
        epub_alt = OUT_DIR / "books" / f"{job}.epub"
        if epub_alt.exists():
            epub_file = epub_alt
    info["epub"] = {"name": epub_file.name, "size_kb": round(epub_file.stat().st_size / 1024, 1)} if epub_file.exists() else None

    b_json = book_dir / "book.json"
    info["book_json"] = {"name": b_json.name, "size_kb": round(b_json.stat().st_size / 1024, 1)} if b_json.exists() else None

    b_md = book_dir / "book.md"
    info["book_md"] = {"name": b_md.name, "size_kb": round(b_md.stat().st_size / 1024, 1)} if b_md.exists() else None

    info["book_files"] = sorted([p.name for p in book_dir.iterdir()]) if book_dir.is_dir() else []

    sidecar = PDF_DIR / f"{job}.sidecar.txt"
    info["sidecar"] = sidecar.name if sidecar.exists() else None
    e2e_path = REPORTS_DIR / f"{job}.e2e.json"
    info["e2e_report"] = json.loads(e2e_path.read_text()) if e2e_path.exists() else None

    # Artefakte und vorangegangene Läufe
    info["artifacts"] = _get_job_artifacts(job)
    info["runs"] = _list_job_runs(job)

    return templates.TemplateResponse(request, "job_detail.html", {"job": job, "info": info})


@app.get("/jobs/{job}/download-zip")
@app.get("/download/zip/{job}")
async def job_download_zip(job: str):
    return _build_zip_response(job)


@app.get("/jobs/{job}/runs/{run_id}/download-zip")
async def run_download_zip(job: str, run_id: str):
    return _build_zip_response(job, run_id=run_id)


@app.get("/jobs/{job}/runs/{run_id}/download/{filename}")
async def run_download_file(job: str, run_id: str, filename: str):
    try:
        run_dir = _safe_path(RUNS_DIR / job, run_id)
        path = _safe_path(run_dir, filename)
    except ValueError:
        return JSONResponse({"error": "path traversal blocked"}, status_code=403)
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return StreamingResponse(open(path, "rb"), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{path.name}"'})


@app.get("/jobs/{job}/runs/{run_id}/browse/{filename}")
async def run_browse_file(job: str, run_id: str, filename: str):
    try:
        run_dir = _safe_path(RUNS_DIR / job, run_id)
        path = _safe_path(run_dir, filename)
    except ValueError:
        return JSONResponse({"error": "path traversal blocked"}, status_code=403)
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)

    ext = path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg"}:
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        return StreamingResponse(open(path, "rb"), media_type=media_type)
    elif ext == ".json":
        return JSONResponse(json.loads(path.read_text()))
    elif ext in {".xml", ".tei.xml"}:
        return HTMLResponse(f"<pre style='white-space:pre-wrap;word-break:break-all;'>{html.escape(path.read_text(errors='replace'))}</pre>")
    elif ext in {".txt", ".md", ".hocr", ".tsv", ".typ"}:
        return HTMLResponse(f"<pre style='white-space:pre-wrap;word-break:break-all;'>{html.escape(path.read_text(errors='replace'))}</pre>")
    elif ext == ".pdf":
        return StreamingResponse(open(path, "rb"), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{path.name}"'})
    elif ext == ".epub":
        return StreamingResponse(open(path, "rb"), media_type="application/epub+zip", headers={"Content-Disposition": f'attachment; filename="{path.name}"'})
    return JSONResponse({"error": "unsupported"}, status_code=400)


@app.post("/jobs/{job}/runs/archive")
async def run_archive_current(job: str, request: Request):
    note = "Manuell archivierter Vorlauf"
    ct = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
        try:
            form = await request.form()
            if "note" in form and str(form["note"]).strip():
                note = str(form["note"]).strip()
        except Exception:
            pass
    elif "application/json" in ct:
        try:
            body = await request.json()
            if "note" in body and str(body["note"]).strip():
                note = str(body["note"]).strip()
        except Exception:
            pass

    run_id = _archive_current_run(job, note=note)
    ref = request.headers.get("referer", f"/jobs/{job}")
    accept = request.headers.get("accept", "")
    if "text/html" in accept or ref:
        return RedirectResponse(url=ref, status_code=303)
    return JSONResponse({"ok": bool(run_id), "run_id": run_id})


@app.post("/jobs/{job}/runs/{run_id}/delete")
async def run_delete_single(job: str, run_id: str, request: Request):
    ok = _delete_job_run(job, run_id)
    ref = request.headers.get("referer", f"/jobs/{job}")
    accept = request.headers.get("accept", "")
    if "text/html" in accept or ref:
        return RedirectResponse(url=ref, status_code=303)
    return JSONResponse({"ok": ok, "job": job, "run_id": run_id})


@app.post("/jobs/{job}/runs/clear")
async def run_clear_all(job: str, request: Request):
    deleted_count = _clear_all_runs(job)
    ref = request.headers.get("referer", f"/jobs/{job}")
    accept = request.headers.get("accept", "")
    if "text/html" in accept or ref:
        return RedirectResponse(url=ref, status_code=303)
    return JSONResponse({"ok": True, "job": job, "deleted_runs": deleted_count})


@app.post("/jobs/{job}/delete")
async def job_delete_entire(job: str, request: Request):
    ok = _delete_entire_job(job)
    accept = request.headers.get("accept", "")
    if "text/html" in accept or request.headers.get("referer"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return JSONResponse({"ok": ok, "job": job})


@app.get("/api/jobs/{job}/artifacts")
async def api_job_artifacts(job: str):
    return JSONResponse(_get_job_artifacts(job))


@app.get("/api/jobs/{job}/runs")
async def api_job_runs(job: str):
    return JSONResponse(_list_job_runs(job))


@app.get("/browse/{kind}/{job}/{filename}")
async def browse_file(kind: str, job: str, filename: str):
    base_map = {
        "input": INPUT_DIR, "preprocessed": PROC_DIR / "preprocessed",
        "quality": PROC_DIR / "quality", "markdown": OUT_DIR / "markdown",
        "pdf": PDF_DIR, "reports": REPORTS_DIR, "tei": TEI_DIR, "books": BOOKS_DIR, "epub": BOOKS_DIR
    }
    base = base_map.get(kind)
    if base is None: return JSONResponse({"error": "invalid kind"}, status_code=400)
    try:
        if (base / filename).exists():
            path = _safe_path(base, filename)
        elif (base / job / filename).exists():
            path = _safe_path(base / job, filename)
        else:
            path = _safe_path(base, filename)
    except ValueError: return JSONResponse({"error": "path traversal blocked"}, status_code=403)
    if not path.exists(): return JSONResponse({"error": "not found"}, status_code=404)
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        media_type = "image/png" if path.suffix == ".png" else "image/jpeg"
        return StreamingResponse(open(path, "rb"), media_type=media_type)
    elif path.suffix == ".json": return JSONResponse(json.loads(path.read_text()))
    elif path.suffix in {".xml", ".tei.xml"}:
        return HTMLResponse(f"<pre style='white-space:pre-wrap;word-break:break-all;'>{html.escape(path.read_text(errors='replace'))}</pre>")
    elif path.suffix in {".txt", ".md", ".hocr", ".tsv", ".typ"}:
        return HTMLResponse(f"<pre style='white-space:pre-wrap;word-break:break-all;'>{html.escape(path.read_text(errors='replace'))}</pre>")
    elif path.suffix == ".pdf": return StreamingResponse(open(path, "rb"), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={path.name}"})
    elif path.suffix == ".epub": return StreamingResponse(open(path, "rb"), media_type="application/epub+zip", headers={"Content-Disposition": f"attachment; filename={path.name}"})
    return JSONResponse({"error": "unsupported"}, status_code=400)


@app.get("/download/{kind}/{job}/{filename}")
async def download_file(kind: str, job: str, filename: str):
    base_map = {
        "pdf": PDF_DIR, "reports": REPORTS_DIR, "markdown": OUT_DIR / "markdown",
        "preprocessed": PROC_DIR / "preprocessed", "quality": PROC_DIR / "quality",
        "input": INPUT_DIR, "tei": TEI_DIR, "books": BOOKS_DIR
    }
    base = base_map.get(kind)
    if base is None: return JSONResponse({"error": "invalid kind"}, status_code=400)
    try:
        if (base / filename).exists():
            path = _safe_path(base, filename)
        elif (base / job / filename).exists():
            path = _safe_path(base / job, filename)
        else:
            path = _safe_path(base, filename)
    except ValueError: return JSONResponse({"error": "path traversal blocked"}, status_code=403)
    if not path.exists(): return JSONResponse({"error": "not found"}, status_code=404)
    return StreamingResponse(open(path, "rb"), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={path.name}"})


@app.get("/health")
async def health(): return {"status": "ok", "data_dir": str(DATA_DIR), "n8n_url": N8N_WEBHOOK_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


# ── PDF Textlayer-Editor: text extraction, preview, correction ────────────────
import subprocess
import sys as _sys
import tempfile

# Add scripts/ to path so we can import pdf_text_correct directly
_scripts_dir = BASE_DIR / "scripts"
if str(_scripts_dir) not in _sys.path:
    _sys.path.insert(0, str(_scripts_dir))

try:
    from pdf_text_correct import replace_in_pdf as _replace_in_pdf, pdftotext as _pdftotext
    _HAS_PATHB = True
except Exception as _e:
    _HAS_PATHB = False
    _PATHB_ERR = str(_e)


def _get_sandwich_pdf(job: str) -> Path | None:
    pdf = PDF_DIR / f"{job}.sandwich.pdf"
    return pdf if pdf.exists() else None


@app.get("/jobs/{job}/edit", response_class=HTMLResponse)
async def job_edit(job: str, request: Request):
    pdf = _get_sandwich_pdf(job)
    if pdf is None:
        return templates.TemplateResponse(request, "editor.html", {
            "job": job, "error": "Kein Sandwich-PDF gefunden. Starte zuerst die Pipeline.", "pages": [], "corrections_template": {}, "info": None
        })
    if not _HAS_PATHB:
        return templates.TemplateResponse(request, "editor.html", {
            "job": job, "error": f"PDF-Textlayer-Modul nicht verfügbar: {_PATHB_ERR}", "pages": [], "corrections_template": {}, "info": None
        })
    try:
        text = _pdftotext(pdf)
    except Exception as e:
        return templates.TemplateResponse(request, "editor.html", {
            "job": job, "error": f"Text-Extraktion fehlgeschlagen: {e}", "pages": [], "corrections_template": {}, "info": None
        })

    # Split into pages by form-feed
    raw_pages = text.split("\f")
    pages = []
    for i, page_text in enumerate(raw_pages):
        tokens = page_text.split()
        pages.append({"page_num": i + 1, "tokens": tokens, "raw": page_text})

    # Build corrections template (token -> same token, ready for user edits)
    all_tokens = set()
    for p in pages:
        for t in p["tokens"]:
            if len(t) >= 3:
                all_tokens.add(t)
    corrections_template = {t: t for t in sorted(all_tokens)[:100]}

    return templates.TemplateResponse(request, "editor.html", {
        "job": job, "pages": pages, "corrections_template": corrections_template,
        "error": None, "info": {"sandwich_pdf": str(pdf), "total_pages": len(pages)}
    })


@app.get("/jobs/{job}/preview/{page}")
async def job_preview_page(job: str, page: int):
    pdf = _get_sandwich_pdf(job)
    if pdf is None:
        return JSONResponse({"error": "no sandwich PDF"}, status_code=404)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        proc = subprocess.run(
            ["pdftoppm", "-png", "-f", str(page), "-l", str(page), "-r", "150", str(pdf), tmp_path],
            capture_output=True, timeout=30,
        )
        if proc.returncode != 0:
            return JSONResponse({"error": f"pdftoppm failed: {proc.stderr.decode()[:200]}"}, status_code=500)
        # pdftoppm appends -N to filename
        result_path = Path(tmp_path + f"-{page}.png") if page < 10 else Path(tmp_path.replace(".png", f"-{page}.png"))
        if not result_path.exists():
            # try alternate naming
            candidates = list(Path(tmp_path).parent.glob(Path(tmp_path).stem + "-*.png"))
            if candidates:
                result_path = candidates[0]
            else:
                return JSONResponse({"error": "pdftoppm produced no output"}, status_code=500)
        img_bytes = result_path.read_bytes()
        result_path.unlink(missing_ok=True)
        Path(tmp_path).unlink(missing_ok=True)
        return StreamingResponse(
            iter([img_bytes]),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/jobs/{job}/correct")
async def job_correct(job: str, body: dict = None):
    pdf = _get_sandwich_pdf(job)
    if pdf is None:
        return JSONResponse({"ok": False, "error": "no sandwich PDF"}, status_code=404)
    if not _HAS_PATHB:
        return JSONResponse({"ok": False, "error": f"PDF-Textlayer-Modul nicht verfügbar: {_PATHB_ERR}"}, status_code=500)

    corrections = (body or {}).get("corrections", {})
    if not isinstance(corrections, dict):
        return JSONResponse({"ok": False, "error": "corrections must be an object"}, status_code=400)

    # Filter to non-identity mappings
    mapping = {str(k): str(v) for k, v in corrections.items() if k and str(k) != str(v)}
    if not mapping:
        return JSONResponse({"ok": False, "error": "no non-identity corrections provided"}, status_code=400)

    # Save corrections for audit trail
    qc_dir = PROC_DIR / "quality" / job
    qc_dir.mkdir(parents=True, exist_ok=True)
    corr_file = qc_dir / "pathb_corrections.json"
    corr_file.write_text(json.dumps({"corrections": mapping}, ensure_ascii=False, indent=2))

    # Apply corrections
    out_pdf = PDF_DIR / f"{job}.pathb.pdf"
    try:
        summary = _replace_in_pdf(pdf, out_pdf, mapping)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # Extract text after correction for verification
    try:
        text_after = _pdftotext(out_pdf)
    except Exception:
        text_after = ""

    return JSONResponse({
        "ok": True,
        "hits": summary.get("replacement_hits", 0),
        "streams_touched": len(summary.get("streams_touched", [])),
        "output": str(out_pdf),
        "text_after": text_after[:2000],
    })
