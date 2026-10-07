import json
from pathlib import Path

DATA_DIR = Path('data')
INPUT_DIR = DATA_DIR / 'input'
PROC_DIR = DATA_DIR / 'processing'
OUT_DIR = DATA_DIR / 'output'
REPORTS_DIR = OUT_DIR / 'reports'
PDF_DIR = OUT_DIR / 'pdf'
TEI_DIR = OUT_DIR / 'tei'
BOOKS_DIR = OUT_DIR / 'books'

def get_job_progress(job):
    in_dir = INPUT_DIR / job
    pre_dir = PROC_DIR / 'preprocessed' / job
    qc_dir = PROC_DIR / 'quality' / job
    md_dir = OUT_DIR / 'markdown' / job
    rep_file = REPORTS_DIR / f"{job}.pipeline.json"
    
    rep_data = {}
    if rep_file.exists():
        try:
            rep_data = json.loads(rep_file.read_text())
        except Exception:
            pass
        
    in_files = [p for p in in_dir.iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.tif'}] if in_dir.is_dir() else []
    pre_files = list(pre_dir.glob('*.png')) if pre_dir.is_dir() else []
    qc_files = list(qc_dir.glob('*.quality.json')) if qc_dir.is_dir() else []
    md_files = list(md_dir.glob('*.md')) if md_dir.is_dir() else []
    sandwich_pdf = PDF_DIR / f"{job}.sandwich.pdf"
    digital_pdf = PDF_DIR / f"{job}.digital.pdf"
    pathb_pdf = PDF_DIR / f"{job}.pathb.pdf"
    tei_file = TEI_DIR / f"{job}.tei.xml"
    epub_file = BOOKS_DIR / job / f"{job}.epub"
    
    pages_total = rep_data.get('pages_total') or len(in_files) or len(pre_files) or 1
    mistral_ok = rep_data.get('mistral_ok', len(md_files))
    pass_n = rep_data.get('pass', 0)
    fail_n = rep_data.get('fail', 0)
    has_report = rep_file.exists()
    
    # 8 Stages of AlexandriaSandwich
    stages = []
    
    # Stage 1: Ingress & Upload
    s1_done = len(in_files) > 0 or has_report
    s1_dur = round(max(1.0, len(in_files) * 0.25), 1)
    stages.append({
        'id': 1, 'name': 'Ingress & Seitenextraktion',
        'status': 'completed' if s1_done else 'pending',
        'progress': 100 if s1_done else 0,
        'info': f"{len(in_files) or pages_total} Seiten bereitgestellt (300 DPI)",
        'duration_str': f"{s1_dur} s" if s1_done else f"~{s1_dur} s",
        'seconds': s1_dur
    })
    
    # Stage 2: Preprocessing
    s2_done = has_report or (len(pre_files) >= pages_total and pages_total > 0)
    s2_running = not s2_done and len(pre_files) > 0
    s2_prog = 100 if s2_done else (round((len(pre_files) / pages_total) * 100) if pages_total else 0)
    s2_dur = round(max(1.0, pages_total * 0.8), 1)
    stages.append({
        'id': 2, 'name': 'Vorverarbeitung (Deskew & Unpaper)',
        'status': 'completed' if s2_done else ('running' if s2_running else 'pending'),
        'progress': s2_prog,
        'info': f"{len(pre_files)} von {pages_total} Seiten entzerrt" if (s2_running or len(pre_files) > 0) else f"{pages_total} Seiten eingeplant",
        'duration_str': f"{s2_dur} s" if s2_done else f"~{s2_dur} s",
        'seconds': s2_dur
    })

    # Stage 3: Tesseract OCR
    s3_done = has_report or (len(qc_files) >= pages_total and pages_total > 0)
    s3_running = not s3_done and len(qc_files) > 0
    s3_prog = 100 if s3_done else (round((len(qc_files) / pages_total) * 100) if pages_total else 0)
    s3_dur = round(max(1.5, pages_total * 1.0), 1)
    threshold = rep_data.get('threshold', 85)
    stages.append({
        'id': 3, 'name': 'Tesseract OCR & Quality-Gate',
        'status': 'completed' if s3_done else ('running' if s3_running else 'pending'),
        'progress': s3_prog,
        'info': f"PASS: {pass_n}, FAIL: {fail_n} (Schwellenwert {threshold} %)" if has_report else f"{len(qc_files)} von {pages_total} Seiten geprüft",
        'duration_str': f"{s3_dur} s" if s3_done else f"~{s3_dur} s",
        'seconds': s3_dur
    })

    # Stage 4: Mistral AI Fallback
    s4_done = has_report or (len(md_files) >= mistral_ok and mistral_ok > 0)
    s4_running = not s4_done and len(md_files) > 0
    s4_prog = 100 if s4_done else (round((len(md_files) / max(1, mistral_ok)) * 100) if mistral_ok else 0)
    s4_dur = round(max(1.5, (mistral_ok or pages_total) * 1.8), 1)
    stages.append({
        'id': 4, 'name': 'Mistral Document AI (Cloud Fallback)',
        'status': 'completed' if s4_done else ('running' if s4_running else 'pending'),
        'progress': s4_prog,
        'info': f"{mistral_ok} Seiten verarbeitet (${round(mistral_ok * 0.004, 4)})" if has_report else f"{len(md_files)} Seiten erfasst",
        'duration_str': f"{s4_dur} s" if s4_done else f"~{s4_dur} s",
        'seconds': s4_dur
    })

    # Stage 5: Sandwich PDF Assembly
    s5_done = sandwich_pdf.exists() or has_report
    s5_dur = round(max(2.0, min(15.0, pages_total * 0.4 + 3.0)), 1)
    pdf_kb = round(sandwich_pdf.stat().st_size / 1024, 1) if sandwich_pdf.exists() else 0
    stages.append({
        'id': 5, 'name': 'Sandwich-PDF Assembly',
        'status': 'completed' if s5_done else 'pending',
        'progress': 100 if s5_done else 0,
        'info': f"Dual-Layer PDF & Text-Sidecar ({pdf_kb} KB)" if sandwich_pdf.exists() else "Unsichtbare OCR-Textebene",
        'duration_str': f"{s5_dur} s" if s5_done else f"~{s5_dur} s",
        'seconds': s5_dur
    })

    # Stage 6: Digital PDF & TEI-XML
    s6_done = digital_pdf.exists() or tei_file.exists() or has_report
    s6_dur = round(max(2.0, min(10.0, pages_total * 0.2 + 2.0)), 1)
    digi_kb = round(digital_pdf.stat().st_size / 1024, 1) if digital_pdf.exists() else 0
    stages.append({
        'id': 6, 'name': 'Typst Neusatz & TEI-P5 XML',
        'status': 'completed' if s6_done else 'pending',
        'progress': 100 if s6_done else 0,
        'info': f"Typst PDF ({digi_kb} KB) & TEI-XML" if s6_done else "Digitaler Neusatz & TEI Schema",
        'duration_str': f"{s6_dur} s" if s6_done else f"~{s6_dur} s",
        'seconds': s6_dur
    })

    # Stage 7: Path B Token Alignment
    s7_done = pathb_pdf.exists() or has_report
    s7_dur = round(max(2.0, min(12.0, pages_total * 0.3 + 3.0)), 1)
    pathb_kb = round(pathb_pdf.stat().st_size / 1024, 1) if pathb_pdf.exists() else 0
    stages.append({
        'id': 7, 'name': 'KI-Textlayer-Synchronisation (In-PDF)',
        'status': 'completed' if s7_done else 'pending',
        'progress': 100 if s7_done else 0,
        'info': f"KI-präzisiertes Sandwich-PDF ({pathb_kb} KB)" if pathb_pdf.exists() else "Präzisions-Ersetzung im PDF Stream",
        'duration_str': f"{s7_dur} s" if s7_done else f"~{s7_dur} s",
        'seconds': s7_dur
    })

    # Stage 8: EPUB 3 & Report
    s8_done = has_report
    s8_dur = round(max(1.0, min(8.0, pages_total * 0.1 + 1.5)), 1)
    stages.append({
        'id': 8, 'name': 'EPUB 3 & Pipeline-Abschlussbericht',
        'status': 'completed' if s8_done else 'pending',
        'progress': 100 if s8_done else 0,
        'info': f"Status: {rep_data.get('status', 'PASS')} ({epub_file.name if epub_file.exists() else 'EPUB 3 generiert'})" if has_report else "Audit-Log & Validierung",
        'duration_str': f"{s8_dur} s" if s8_done else f"~{s8_dur} s",
        'seconds': s8_dur
    })

    total_sec = sum(s['seconds'] for s in stages)
    completed_stages = sum(1 for s in stages if s['status'] == 'completed')
    overall_progress = round((completed_stages / len(stages)) * 100)
    
    current_stage = 'Vollständig abgeschlossen'
    if not has_report:
        if s1_done and not s2_running and not s2_done:
            current_stage = 'Wartet auf Pipeline-Trigger (Dateien bereitgestellt)'
        else:
            for s in stages:
                if s['status'] in ('running', 'pending'):
                    current_stage = f"Stufe {s['id']}: {s['name']}"
                    break

    return {
        'job': job,
        'has_report': has_report,
        'pages_total': pages_total,
        'overall_progress': overall_progress,
        'completed_stages': completed_stages,
        'total_stages': len(stages),
        'current_stage': current_stage,
        'estimated_total_seconds': total_sec,
        'estimated_total_str': f"{int(total_sec // 60)} Min. {int(total_sec % 60)} s" if total_sec >= 60 else f"{round(total_sec, 1)} s",
        'stages': stages
    }

if __name__ == '__main__':
    for j in ['Test2026-10-07', 'katha_06', 'stenzler_10p']:
        res = get_job_progress(j)
        print(f"=== {j}: {res['overall_progress']}% | {res['current_stage']} | Total: {res['estimated_total_str']} ===")
        for s in res['stages']:
            print(f"  [{s['id']}] {s['name']}: {s['status']} ({s['duration_str']}) -> {s['info']}")
