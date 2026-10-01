#!/usr/bin/env python3
"""AlexandriaSandwich Web UI (FastAPI)"""
from __future__ import annotations
import asyncio
import html, json, logging, os, re, shutil, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/alexandria/ocr")
N8N_WEBHOOK_TIMEOUT = float(os.getenv("N8N_WEBHOOK_TIMEOUT", "180"))
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="AlexandriaSandwich UI")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _list_jobs():
    jobs = {}
    if INPUT_DIR.is_dir():
        for d in sorted(INPUT_DIR.iterdir()):
            if d.is_dir():
                jobs.setdefault(d.name, {"name": d.name, "input_pages": len(list(d.glob("*.png"))) + len(list(d.glob("*.jpg"))) + len(list(d.glob("*.tif"))), "status": "-", "has_report": False, "has_pdf": False})
    if REPORTS_DIR.is_dir():
        for f in sorted(REPORTS_DIR.glob("*.pipeline.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            name = f.stem.replace(".pipeline", "")
            try: report = json.loads(f.read_text())
            except: report = {}
            entry = jobs.get(name, {"name": name, "input_pages": 0, "status": "-", "has_report": False, "has_pdf": False})
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
    return sorted(jobs.values(), key=lambda j: j.get("modified", ""), reverse=True)


def _trigger_n8n(job, lang="deu+eng", threshold=85, limit=0, no_mistral=False):
    payload = {"job": job, "pull": False, "push": False, "lang": lang, "threshold": threshold, "limit": limit, "no_mistral": no_mistral}
    try:
        resp = httpx.post(N8N_WEBHOOK_URL, json=payload, timeout=N8N_WEBHOOK_TIMEOUT)
        try: return resp.json()
        except: return {"ok": False, "error": f"n8n returned HTTP {resp.status_code}: {resp.text[:500]}"}
    except Exception as e: return {"ok": False, "error": str(e)}


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


@app.api_route("/portal", methods=["GET", "HEAD"])
async def portal_redirect():
    return RedirectResponse(url="/dashboard", status_code=302)


@app.api_route("/login", methods=["GET", "HEAD"])
async def login_redirect():
    return RedirectResponse(url="https://auth.birchville.cc/?rd=https://alex.birchville.cc/upload", status_code=302)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "service": "AlexandriaSandwich", "timestamp": datetime.now(timezone.utc).isoformat()}


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
async def trigger_job(request: Request, job: str, lang: str = "deu+eng", threshold: int = 85, limit: int = 0, no_mistral: bool = False):
    resp = _trigger_n8n(job, lang=lang, threshold=threshold, limit=limit, no_mistral=no_mistral)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url=f"/jobs/{job}", status_code=303)
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
    return templates.TemplateResponse(request, "job_detail.html", {"job": job, "info": info})


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


# ── Path B Editor: text extraction, preview, correction ────────────────
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
            "job": job, "error": f"Path B Modul nicht verfügbar: {_PATHB_ERR}", "pages": [], "corrections_template": {}, "info": None
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
        return JSONResponse({"ok": False, "error": f"Path B module not available: {_PATHB_ERR}"}, status_code=500)

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
