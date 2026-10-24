#!/usr/bin/env bash
# AlexandriaSandwich — single job orchestrator (called from n8n / SSH / docker exec)
#
# Stages:
#   1) optional storage pull-input
#   2) preprocess (ImageMagick + unpaper)
#   3) Tesseract quality gate per page
#   4) Mistral OCR fallback on FAIL
#   5) optional push-output / push-processing
#
# Usage:
#   run_pipeline.sh [--job NAME] [--pull] [--push] [--lang deu+eng] [--threshold 85]
#                   [--no-mistral] [--limit N] [--input DIR] [--processing DIR] [--output DIR]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate local virtualenv if available on host
if [[ -x "${SCRIPT_DIR}/../.venv/bin/python3" && -z "${VIRTUAL_ENV:-}" ]]; then
  export PATH="${SCRIPT_DIR}/../.venv/bin:$PATH"
fi

# Fallback: MISTRAL_API_KEY aus .env laden falls im Container-Aufruf nicht übergeben
if [[ -z "${MISTRAL_API_KEY:-}" ]]; then
  for env_file in "/opt/alexandria/.env" "${SCRIPT_DIR}/../.env" "/data/.env"; do
    if [[ -f "$env_file" ]]; then
      set +u
      eval "$(grep -E '^(export )?MISTRAL_API_KEY=' "$env_file" | sed 's/^export //; s/^/export /')" 2>/dev/null || true
      set -u
      [[ -n "${MISTRAL_API_KEY:-}" ]] && break
    fi
  done
fi

JOB_NAME="${AS_JOB_NAME:-manual}"
DO_PULL=0
DO_PUSH=0
LANG_OCR="${OCR_LANG:-deu+eng}"
THRESHOLD="${OCR_CONFIDENCE_THRESHOLD:-100}"
USE_MISTRAL=1
USE_UNPAPER=1
SKIP_PREPROCESS=0
LIMIT=0
DEFAULT_DATA="/data"
if [[ ! -w "/data" && -d "${SCRIPT_DIR}/../data" ]]; then
  DEFAULT_DATA="$(cd "${SCRIPT_DIR}/../data" && pwd)"
fi
INPUT_DIR="${AS_INPUT_DIR:-${DEFAULT_DATA}/input}"
PROC_DIR="${AS_PROCESSING_DIR:-${DEFAULT_DATA}/processing}"
OUT_DIR="${AS_OUTPUT_DIR:-${DEFAULT_DATA}/output}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }
die() { log "ERROR: $*"; exit 2; }

LANG_EXPLICIT=0
THRESHOLD_EXPLICIT=0
MISTRAL_EXPLICIT=0
UNPAPER_EXPLICIT=0
SKIP_PREPROCESS_EXPLICIT=0
LIMIT_EXPLICIT=0
TYPESET_MODE=""
TYPESET_MODE_EXPLICIT=0

PDF_SRC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job|-j) JOB_NAME="$2"; shift 2 ;;
    --pdf) PDF_SRC="$2"; shift 2 ;;
    --pull) DO_PULL=1; shift ;;
    --push) DO_PUSH=1; shift ;;
    --lang) LANG_OCR="$2"; LANG_EXPLICIT=1; shift 2 ;;
    --threshold) THRESHOLD="$2"; THRESHOLD_EXPLICIT=1; shift 2 ;;
    --no-mistral) USE_MISTRAL=0; MISTRAL_EXPLICIT=1; shift ;;
    --no-unpaper) USE_UNPAPER=0; UNPAPER_EXPLICIT=1; shift ;;
    --skip-preprocess) SKIP_PREPROCESS=1; SKIP_PREPROCESS_EXPLICIT=1; shift ;;
    --typeset-mode) TYPESET_MODE="$2"; TYPESET_MODE_EXPLICIT=1; shift 2 ;;
    --limit) LIMIT="$2"; LIMIT_EXPLICIT=1; shift 2 ;;
    --input) INPUT_DIR="$2"; shift 2 ;;
    --processing) PROC_DIR="$2"; shift 2 ;;
    --output) OUT_DIR="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,25p' "$0"; exit 0 ;;
    *) die "unknown arg: $1" ;;
  esac
done

JOB_INPUT="${INPUT_DIR}/${JOB_NAME}"
JOB_CONFIG="${JOB_INPUT}/job.config.json"
if [[ -f "$JOB_CONFIG" ]]; then
  log "load job profile: $JOB_CONFIG"
  eval "$(python3 - "$JOB_CONFIG" <<'PY'
import json, sys, shlex, re
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        cfg = json.load(f)
    if "lang" in cfg:
        val = re.sub(r"[^a-zA-Z0-9_+.-]", "", str(cfg['lang']))
        print(f"CFG_LANG={shlex.quote(val)}")
    if "threshold" in cfg:
        print(f"CFG_THRESHOLD={int(cfg['threshold'])}")
    if "use_mistral" in cfg:
        print(f"CFG_MISTRAL={1 if cfg['use_mistral'] else 0}")
    if "use_unpaper" in cfg:
        print(f"CFG_UNPAPER={1 if cfg['use_unpaper'] else 0}")
    if "limit" in cfg:
        print(f"CFG_LIMIT={int(cfg['limit'])}")
    if "skip_preprocess" in cfg:
        print(f"CFG_SKIP_PREPROCESS={1 if cfg['skip_preprocess'] else 0}")
    t_mode = cfg.get("heuristics", {}).get("typeset_mode") or cfg.get("typeset_mode")
    if t_mode:
        val = re.sub(r"[^a-zA-Z0-9_.-]", "", str(t_mode))
        print(f"CFG_TYPESET_MODE={shlex.quote(val)}")
    s_pdf = cfg.get("heuristics", {}).get("source_pdf") or cfg.get("source_pdf")
    if s_pdf:
        print(f"CFG_SOURCE_PDF={shlex.quote(str(s_pdf))}")
except Exception:
    pass
PY
)"
  [[ -n "${CFG_LANG:-}" && "$LANG_EXPLICIT" -eq 0 ]] && LANG_OCR="$CFG_LANG"
  [[ -n "${CFG_THRESHOLD:-}" && "$THRESHOLD_EXPLICIT" -eq 0 ]] && THRESHOLD="$CFG_THRESHOLD"
  [[ -n "${CFG_MISTRAL:-}" && "$MISTRAL_EXPLICIT" -eq 0 ]] && USE_MISTRAL="$CFG_MISTRAL"
  [[ -n "${CFG_UNPAPER:-}" && "$UNPAPER_EXPLICIT" -eq 0 ]] && USE_UNPAPER="$CFG_UNPAPER"
  [[ -n "${CFG_LIMIT:-}" && "$LIMIT_EXPLICIT" -eq 0 ]] && LIMIT="$CFG_LIMIT"
  [[ -n "${CFG_SKIP_PREPROCESS:-}" && "$SKIP_PREPROCESS_EXPLICIT" -eq 0 ]] && SKIP_PREPROCESS="$CFG_SKIP_PREPROCESS"
  [[ -n "${CFG_TYPESET_MODE:-}" && "$TYPESET_MODE_EXPLICIT" -eq 0 ]] && TYPESET_MODE="$CFG_TYPESET_MODE"
  [[ -n "${CFG_SOURCE_PDF:-}" && -z "${PDF_SRC:-}" ]] && PDF_SRC="$CFG_SOURCE_PDF"
fi

JOB_OUT="${OUT_DIR}/${JOB_NAME}"
PRE_DIR="${PROC_DIR}/preprocessed/${JOB_NAME}"
QC_DIR="${PROC_DIR}/quality/${JOB_NAME}"
MD_DIR="${JOB_OUT}/markdown"
LOG_JSON="${JOB_OUT}/${JOB_NAME}.pipeline.json"
PAGES_JSONL="${QC_DIR}/pages.jsonl"
mkdir -p "$PRE_DIR" "$QC_DIR" "$JOB_OUT" "$MD_DIR"
: > "$PAGES_JSONL"

PREPROCESS="${SCRIPT_DIR}/preprocess.sh"
QUALITY="${SCRIPT_DIR}/quality_check.py"
MISTRAL="${SCRIPT_DIR}/mistral_ocr.py"
SYNC="${SCRIPT_DIR}/sync_storage.sh"
ASSEMBLE="${SCRIPT_DIR}/assemble_sandwich.py"

[[ -f "$PREPROCESS" ]] || die "missing $PREPROCESS"
[[ -f "$QUALITY" ]] || die "missing $QUALITY"

if [[ "$DO_PULL" -eq 1 ]]; then
  if [[ -f "$SYNC" ]]; then
    log "pull-input from NAS"
    AS_LOCAL_DATA="$(dirname "$INPUT_DIR")" bash "$SYNC" pull-input \
      || log "warn: pull-input failed (continuing with local data)"
  else
    log "warn: sync_storage.sh missing; skip pull"
  fi
fi

JOB_INPUT="${INPUT_DIR}/${JOB_NAME}"
if [[ ! -d "$JOB_INPUT" ]]; then
  if compgen -G "${INPUT_DIR}/${JOB_NAME}.*" >/dev/null; then
    JOB_INPUT="$INPUT_DIR"
  else
    die "Input directory for job '$JOB_NAME' not found: $JOB_INPUT"
  fi
fi

# Auto-detect or extract pages from source PDF if no images are present in JOB_INPUT
shopt -s nullglob
_input_imgs=( "$JOB_INPUT"/*.png "$JOB_INPUT"/*.jpg "$JOB_INPUT"/*.jpeg "$JOB_INPUT"/*.tif "$JOB_INPUT"/*.tiff )
_input_pdfs=( "$JOB_INPUT"/*.pdf )
shopt -u nullglob

_candidate_pdf=""
if [[ -n "${PDF_SRC:-}" && -f "$PDF_SRC" ]]; then
  _candidate_pdf="$PDF_SRC"
elif [[ ${#_input_imgs[@]} -eq 0 && ${#_input_pdfs[@]} -gt 0 ]]; then
  _candidate_pdf="${_input_pdfs[0]}"
elif [[ ${#_input_imgs[@]} -eq 0 && -f "${INPUT_DIR}/${JOB_NAME}.pdf" ]]; then
  _candidate_pdf="${INPUT_DIR}/${JOB_NAME}.pdf"
fi

if [[ -n "$_candidate_pdf" && ${#_input_imgs[@]} -eq 0 ]]; then
  log "extract pages from PDF: $_candidate_pdf -> $JOB_INPUT"
  mkdir -p "$JOB_INPUT"
  python3 - "$_candidate_pdf" "$JOB_INPUT" <<'PY'
import sys, os
from pathlib import Path
pdf_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
try:
    import pymupdf, concurrent.futures
    with pymupdf.open(pdf_path) as doc:
        total = len(doc)
    digits = max(3, len(str(total)))
    def _extract_page(pno):
        out_png = out_dir / f"page-{pno+1:0{digits}d}.png"
        if not (out_png.exists() and out_png.stat().st_size > 1000):
            with pymupdf.open(pdf_path) as d:
                pix = d[pno].get_pixmap(dpi=300)
                pix.save(str(out_png))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(_extract_page, range(total)))
    print(f"Extracted {total} pages via PyMuPDF (dpi=300)")
except Exception as e:
    import subprocess, shutil
    if shutil.which("pdftoppm"):
        cmd = ["pdftoppm", "-png", "-r", "300", str(pdf_path), str(out_dir / "page")]
        subprocess.run(cmd, check=True)
        print("Extracted pages via pdftoppm (dpi=300)")
    else:
        raise e
PY
fi

if [[ "$SKIP_PREPROCESS" -eq 1 ]]; then
  shopt -s nullglob
  existing_pre=( "$PRE_DIR"/*.png )
  shopt -u nullglob
  if [[ ${#existing_pre[@]} -gt 0 ]]; then
    log "skip preprocess: using ${#existing_pre[@]} existing preprocessed pages in $PRE_DIR"
  else
    log "skip preprocess: copy $JOB_INPUT/*.png -> $PRE_DIR"
    cp -a "$JOB_INPUT"/*.png "$PRE_DIR/"
  fi
else
  log "preprocess job=$JOB_NAME input=$JOB_INPUT -> $PRE_DIR"
  PRE_OPTS=()
  [[ "$USE_UNPAPER" -eq 0 ]] && PRE_OPTS+=("--no-unpaper")
  bash "$PREPROCESS" "${PRE_OPTS[@]}" --input "$JOB_INPUT" --output "$PRE_DIR" --overwrite
fi

shopt -s nullglob
PAGES=( "$PRE_DIR"/*.png )
if [[ ${#PAGES[@]} -eq 0 ]]; then
  die "no preprocessed pages in $PRE_DIR"
fi
if [[ "$LIMIT" -gt 0 && ${#PAGES[@]} -gt "$LIMIT" ]]; then
  PAGES=( "${PAGES[@]:0:$LIMIT}" )
fi

PASS_N=0
FAIL_N=0
MISTRAL_N=0

for page in "${PAGES[@]}"; do
  base="$(basename "$page" .png)"
  qc_json="${QC_DIR}/${base}.quality.json"

  if [[ -s "$qc_json" ]]; then
    passed="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(1 if d.get("mean_confidence",0) >= float(sys.argv[2]) and d.get("passed",False) else 0)' "$qc_json" "$THRESHOLD" 2>/dev/null || echo 0)"
    if [[ "$passed" -eq 1 ]]; then qc_rc=0; else qc_rc=1; fi
  else
    log "quality_check $base"
    set +e
    python3 "$QUALITY" -i "$page" -l "$LANG_OCR" -t "$THRESHOLD" --json --keep-ocr "$QC_DIR" >"$qc_json"
    qc_rc=$?
    set -e
  fi

  mean="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("mean_confidence",0))' "$qc_json" 2>/dev/null || echo 0)"
  decision="pass"
  mistral_md=""

  if [[ "$qc_rc" -eq 0 ]]; then
    PASS_N=$((PASS_N + 1))
    decision="pass"
  else
    FAIL_N=$((FAIL_N + 1))
    decision="fallback"
    if [[ -s "${MD_DIR}/${base}.mistral.md" ]]; then
      log "mistral cached $base"
      MISTRAL_N=$((MISTRAL_N + 1))
      mistral_md="${MD_DIR}/${base}.mistral.md"
    elif [[ "$USE_MISTRAL" -eq 1 ]]; then
      if [[ -z "${MISTRAL_API_KEY:-}" ]]; then
        log "warn: low confidence on $base but MISTRAL_API_KEY unset"
      elif [[ -f "$MISTRAL" ]]; then
        log "mistral fallback $base"
        set +e
        python3 "$MISTRAL" "$page" \
          -o "${MD_DIR}/${base}.mistral.md" \
          --json "${QC_DIR}/${base}.mistral.json"
        m_rc=$?
        set -e
        if [[ "$m_rc" -eq 0 ]]; then
          MISTRAL_N=$((MISTRAL_N + 1))
          mistral_md="${MD_DIR}/${base}.mistral.md"
        else
          log "warn: mistral failed for $base (rc=$m_rc)"
        fi
      fi
    fi
  fi

  python3 - "$PAGES_JSONL" "$base" "$mean" "$decision" "$qc_rc" "$mistral_md" <<'PY'
import json, sys
path, page, mean, decision, qc_rc, mistral_md = sys.argv[1:7]
rec = {
    "page": page,
    "mean_confidence": float(mean or 0),
    "decision": decision,
    "qc_exit": int(qc_rc),
    "mistral_md": mistral_md or None,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
done

# 5) Sandwich PDF assembly from preprocessed pages
PDF_OUT="${JOB_OUT}/${JOB_NAME}.sandwich.pdf"
SIDECAR_OUT="${JOB_OUT}/${JOB_NAME}.sidecar.txt"
if [[ -f "$ASSEMBLE" ]]; then
  if [[ -s "$PDF_OUT" ]]; then
    log "sandwich pdf cached: $PDF_OUT"
  else
    log "assemble sandwich pdf -> $PDF_OUT"
    set +e
    python3 "$ASSEMBLE" -i "$PRE_DIR" -o "$PDF_OUT" -l "$LANG_OCR" --sidecar "$SIDECAR_OUT" --json >"${QC_DIR}/assemble.json"
    assemble_rc=$?
    set -e
    if [[ "$assemble_rc" -ne 0 ]]; then
      log "warn: sandwich assembly failed (rc=$assemble_rc)"
      PDF_OUT=""
    else
      log "sandwich ok: $PDF_OUT"
    fi
  fi
else
  log "warn: assemble_sandwich.py missing; skip PDF"
  PDF_OUT=""
fi

# Multi-format outputs: TEI-P5 XML, Typst Digital PDF, Typeset Edition & EPUB 3
CONSOLIDATE="${SCRIPT_DIR}/consolidate_book.py"
ALIGN_SCRIPT="${SCRIPT_DIR}/align_mistral_pdf.py"
PERFECT_SANDWICH_SCRIPT="${SCRIPT_DIR}/build_perfect_sandwich.py"
PROFILE_LAYOUT_SCRIPT="${SCRIPT_DIR}/profile_source_layout.py"
RENDER_DIGITAL="${SCRIPT_DIR}/render_digital_pdf.py"
BUILD_TYPESET="${SCRIPT_DIR}/build_typeset_edition.py"
EXPORT_TEI="${SCRIPT_DIR}/export_tei.py"
EXPORT_EPUB="${SCRIPT_DIR}/export_epub.py"
INJECT_TOC="${SCRIPT_DIR}/inject_toc.py"
AUDIT_LAYOUT_SCRIPT="${SCRIPT_DIR}/audit_layout_concordance.py"
COMPARE_LAYOUT_SCRIPT="${SCRIPT_DIR}/compare_layout.py"

BOOK_DIR="${JOB_OUT}"
TEI_OUT="${JOB_OUT}/${JOB_NAME}.tei.xml"
ALIGNED_PDF="${JOB_OUT}/${JOB_NAME}.aligned.pdf"
PERFECT_SANDWICH_OUT="${JOB_OUT}/${JOB_NAME}.perfect_sandwich.pdf"
LAYOUT_PROFILE_OUT="${JOB_OUT}/layout.profile.json"
DIGITAL_PDF_OUT="${JOB_OUT}/${JOB_NAME}.digital.pdf"
TYPESET_PDF_OUT="${JOB_OUT}/${JOB_NAME}.typeset_edition.pdf"
EPUB_OUT="${JOB_OUT}/${JOB_NAME}.epub"
mkdir -p "$BOOK_DIR"

# 6) Consolidate book AST (book.json)
if [[ -f "$CONSOLIDATE" ]]; then
  log "consolidate book -> $BOOK_DIR"
  set +e
  python3 "$CONSOLIDATE" --job "$JOB_NAME" --input-dir "$QC_DIR" --markdown-dir "$MD_DIR" --output-dir "$BOOK_DIR" --lang "$LANG_OCR" ${JOB_CONFIG:+-c "$JOB_CONFIG"}
  con_rc=$?
  set -e
  if [[ "$con_rc" -ne 0 ]]; then
    log "warn: consolidate_book failed (rc=$con_rc)"
  fi
fi

# 7) Mistral Token Alignment into Facsimile PDF (.aligned.pdf)
if [[ -f "$ALIGN_SCRIPT" && -n "$PDF_OUT" && -f "$PDF_OUT" ]]; then
  log "align mistral text with sandwich pdf -> $ALIGNED_PDF"
  set +e
  python3 "$ALIGN_SCRIPT" \
    --pdf "$PDF_OUT" \
    --mistral-dir "$MD_DIR" \
    --book-json "${BOOK_DIR}/book.json" \
    --output "$ALIGNED_PDF" \
    --corrections "${QC_DIR}/mistral_align.json" \
    --json >"${QC_DIR}/align.json"
  align_rc=$?
  set -e
  if [[ "$align_rc" -eq 0 && -f "$ALIGNED_PDF" ]]; then
    log "aligned facsimile pdf ok: $ALIGNED_PDF"
  else
    log "warn: align_mistral_pdf failed (rc=$align_rc)"
    ALIGNED_PDF=""
  fi
else
  ALIGNED_PDF=""
fi

# 8) Publication-Grade Perfect Sandwich PDF (Content-aware margin masking, leveling, unsharp)
BASE_SANDWICH_SOURCE="${ALIGNED_PDF:-$PDF_OUT}"
if [[ -f "$PERFECT_SANDWICH_SCRIPT" && -n "$BASE_SANDWICH_SOURCE" && -f "$BASE_SANDWICH_SOURCE" ]]; then
  log "build perfect sandwich pdf (content-aware margin mask & leveling) -> $PERFECT_SANDWICH_OUT"
  set +e
  python3 "$PERFECT_SANDWICH_SCRIPT" \
    --input-pdf "$BASE_SANDWICH_SOURCE" \
    --output "$PERFECT_SANDWICH_OUT" \
    --markdown-dir "$MD_DIR" \
    --jobs 4
  perfect_rc=$?
  set -e
  if [[ "$perfect_rc" -eq 0 && -f "$PERFECT_SANDWICH_OUT" ]]; then
    log "perfect sandwich pdf ok: $PERFECT_SANDWICH_OUT"
  else
    log "warn: build_perfect_sandwich failed (rc=$perfect_rc)"
    PERFECT_SANDWICH_OUT=""
  fi
else
  PERFECT_SANDWICH_OUT=""
fi

# 9) Layout Profiling (Satzspiegel, Durchschuss, Paginierung)
PROFILE_SOURCE_PDF=""
for cand_pdf in "${PERFECT_SANDWICH_OUT:-}" "${ALIGNED_PDF:-}" "${PDF_OUT:-}" "${JOB_INPUT}/source.pdf" "${PDF_SRC:-}"; do
  if [[ -n "$cand_pdf" && -f "$cand_pdf" ]]; then
    PROFILE_SOURCE_PDF="$cand_pdf"
    break
  fi
done

if [[ -f "$PROFILE_LAYOUT_SCRIPT" && -n "$PROFILE_SOURCE_PDF" && -f "$PROFILE_SOURCE_PDF" ]]; then
  log "profile source layout ($PROFILE_SOURCE_PDF) -> $LAYOUT_PROFILE_OUT"
  set +e
  python3 "$PROFILE_LAYOUT_SCRIPT" --pdf "$PROFILE_SOURCE_PDF" --output "$LAYOUT_PROFILE_OUT"
  prof_rc=$?
  set -e
  if [[ "$prof_rc" -eq 0 && -f "$LAYOUT_PROFILE_OUT" ]]; then
    log "source layout profile ok: $LAYOUT_PROFILE_OUT"
  else
    log "warn: profile_source_layout failed (rc=$prof_rc)"
  fi
fi

# 10) Digital Vector Typeset PDF (calibrated against source layout profile)
if [[ -f "$RENDER_DIGITAL" && -f "${BOOK_DIR}/book.json" ]]; then
  log "render digital book pdf (calibrated from layout & facsimile) -> $DIGITAL_PDF_OUT"
  set +e
  PRESERVE_ARG=""
  if [[ "${TYPESET_MODE:-}" == "1to1" || "${TYPESET_MODE:-}" == "paginated" ]]; then
    PRESERVE_ARG="--preserve-pages"
  fi
  python3 "$RENDER_DIGITAL" --job "$JOB_NAME" --input "${BOOK_DIR}/book.json" --output "$DIGITAL_PDF_OUT" \
    $PRESERVE_ARG \
    ${TYPESET_MODE:+--typeset-mode "$TYPESET_MODE"}
  render_rc=$?
  set -e
  if [[ "$render_rc" -ne 0 ]]; then
    log "warn: render_digital_pdf failed (rc=$render_rc)"
    DIGITAL_PDF_OUT=""
  fi
else
  DIGITAL_PDF_OUT=""
fi

# 11) Semantic Typeset Edition (optional Boethlingk model)
if [[ -f "$BUILD_TYPESET" ]]; then
  COMPLETE_JSON=""
  if [[ -f "${JOB_INPUT}/${JOB_NAME}_complete.json" ]]; then
    COMPLETE_JSON="${JOB_INPUT}/${JOB_NAME}_complete.json"
  elif [[ -f "${JOB_INPUT}/dhatupatha_complete.json" && "$JOB_NAME" == *"dhatu"* ]]; then
    COMPLETE_JSON="${JOB_INPUT}/dhatupatha_complete.json"
  elif [[ "$JOB_NAME" == *"dhatu"* && -f "${SCRIPT_DIR}/../data/dhatupatha_complete.json" ]]; then
    COMPLETE_JSON="${SCRIPT_DIR}/../data/dhatupatha_complete.json"
  fi

  if [[ -n "$COMPLETE_JSON" && -f "$COMPLETE_JSON" ]]; then
    TYPESET_SOURCE_REF="${PERFECT_SANDWICH_OUT:-${ALIGNED_PDF:-$PDF_OUT}}"
    log "build semantic typeset edition (Boethlingk model) -> $TYPESET_PDF_OUT"
    set +e
    python3 "$BUILD_TYPESET" --job "$JOB_NAME" --complete-json "$COMPLETE_JSON" --output "$TYPESET_PDF_OUT" ${TYPESET_SOURCE_REF:+--source-pdf "$TYPESET_SOURCE_REF"}
    typeset_rc=$?
    set -e
    if [[ "$typeset_rc" -ne 0 ]]; then
      log "warn: build_typeset_edition failed (rc=$typeset_rc)"
      TYPESET_PDF_OUT=""
    fi
  else
    log "skip typeset_edition: no job-specific canonical ground truth for $JOB_NAME"
    TYPESET_PDF_OUT=""
  fi
else
  TYPESET_PDF_OUT=""
fi

# 12) Multi-format structured exports: TEI-P5 XML & EPUB 3
IIIF_PAGES_CAND="${JOB_INPUT}/iiif_pages.json"

if [[ -f "$EXPORT_TEI" && -f "${BOOK_DIR}/book.json" ]]; then
  log "export tei-p5 -> $TEI_OUT"
  set +e
  python3 "$EXPORT_TEI" --job "$JOB_NAME" --input "${BOOK_DIR}/book.json" --output "$TEI_OUT" \
    ${JOB_CONFIG:+-c "$JOB_CONFIG"} \
    ${IIIF_PAGES_CAND:+--iiif-pages "$IIIF_PAGES_CAND"}
  tei_rc=$?
  set -e
  if [[ "$tei_rc" -ne 0 ]]; then
    log "warn: export_tei failed (rc=$tei_rc)"
    TEI_OUT=""
  fi
else
  TEI_OUT=""
fi

if [[ -f "$EXPORT_EPUB" && -f "${BOOK_DIR}/book.json" ]]; then
  log "export epub 3 -> $EPUB_OUT"
  set +e
  python3 "$EXPORT_EPUB" --job "$JOB_NAME" --input "${BOOK_DIR}/book.json" --output "$EPUB_OUT"
  epub_rc=$?
  set -e
  if [[ "$epub_rc" -ne 0 ]]; then
    log "warn: export_epub failed (rc=$epub_rc)"
    EPUB_OUT=""
  fi
else
  EPUB_OUT=""
fi

# 13) Hierarchical Outline (TOC) & Metadata Injection into PDF artifacts
TOC_FILE=""
for cand in \
  "${JOB_INPUT}/toc.txt" \
  "${JOB_INPUT}/${JOB_NAME}.toc.txt" \
  "${JOB_INPUT}/toc.json" \
  "${JOB_INPUT}/${JOB_NAME}.toc.json" \
  "${INPUT_DIR}/${JOB_NAME}.toc.txt" \
  "${INPUT_DIR}/${JOB_NAME}.toc.json" \
  "${INPUT_DIR}/toc.txt" \
  "${INPUT_DIR}/toc.json" \
  "${JOB_OUT}/toc.txt" \
  "${JOB_OUT}/${JOB_NAME}.toc.txt" \
  "${JOB_OUT}/toc.json" \
  "${QC_DIR}/toc.json" \
  "${BOOK_DIR}/toc.json"; do
  if [[ -f "$cand" ]]; then
    TOC_FILE="$cand"
    break
  fi
done

if [[ -f "$INJECT_TOC" ]]; then
  for pdf in "$PDF_OUT" "$ALIGNED_PDF" "$PERFECT_SANDWICH_OUT" "$DIGITAL_PDF_OUT" "$TYPESET_PDF_OUT"; do
    if [[ -n "$pdf" && -f "$pdf" ]]; then
      log "inject toc / metadata into $pdf"
      set +e
      python3 "$INJECT_TOC" \
        --input "$pdf" \
        ${TOC_FILE:+--toc "$TOC_FILE"} \
        --book-json "${BOOK_DIR}/book.json"
      set -e
    fi
  done
fi

# 14) Layout Concordance Audit (Geometric & Structural Quality Gate)
LAYOUT_AUDIT_OUT="${JOB_OUT}/${JOB_NAME}.layout_audit.json"
LAYOUT_AUDIT_MD="${JOB_OUT}/${JOB_NAME}.layout_audit.md"
AUDIT_REF_PDF=""
for cand in "${PERFECT_SANDWICH_OUT:-}" "${ALIGNED_PDF:-}" "${PDF_OUT:-}"; do
  if [[ -n "$cand" && -f "$cand" ]]; then
    AUDIT_REF_PDF="$cand"
    break
  fi
done

if [[ -f "$AUDIT_LAYOUT_SCRIPT" && -n "$DIGITAL_PDF_OUT" && -f "$DIGITAL_PDF_OUT" && -n "$AUDIT_REF_PDF" && -f "$AUDIT_REF_PDF" ]]; then
  log "audit layout concordance -> $LAYOUT_AUDIT_OUT"
  set +e
  python3 "$AUDIT_LAYOUT_SCRIPT" \
    --orig "$AUDIT_REF_PDF" \
    --digital "$DIGITAL_PDF_OUT" \
    --job "$JOB_NAME" \
    --json-out "$LAYOUT_AUDIT_OUT" \
    --md-out "$LAYOUT_AUDIT_MD"
  audit_rc=$?
  set -e
  if [[ "$audit_rc" -eq 0 && -f "$LAYOUT_AUDIT_OUT" ]]; then
    log "layout concordance audit ok: $LAYOUT_AUDIT_OUT"
  else
    log "warn: audit_layout_concordance failed (rc=$audit_rc)"
  fi
fi

# 15) Visual Side-by-Side Comparison Diffs
COMPARE_IMG_DIR="${JOB_OUT}/comparison_samples"
if [[ -f "$COMPARE_LAYOUT_SCRIPT" && -n "$DIGITAL_PDF_OUT" && -f "$DIGITAL_PDF_OUT" && -n "$AUDIT_REF_PDF" && -f "$AUDIT_REF_PDF" ]]; then
  log "render side-by-side layout comparisons -> $COMPARE_IMG_DIR"
  set +e
  python3 "$COMPARE_LAYOUT_SCRIPT" \
    --orig "$AUDIT_REF_PDF" \
    --digital "$DIGITAL_PDF_OUT" \
    --job "$JOB_NAME" \
    --book-json "${BOOK_DIR}/book.json" \
    --img-dir "$COMPARE_IMG_DIR"
  set -e
fi

REPORT="$(JOB_NAME="$JOB_NAME" INPUT_DIR="$INPUT_DIR" PRE_DIR="$PRE_DIR" \
THRESHOLD="$THRESHOLD" LANG_OCR="$LANG_OCR" PASS_N="$PASS_N" FAIL_N="$FAIL_N" \
MISTRAL_N="$MISTRAL_N" TOTAL="${#PAGES[@]}" PAGES_JSONL="$PAGES_JSONL" \
PDF_OUT="${PDF_OUT:-}" ALIGNED_PDF="${ALIGNED_PDF:-}" SIDECAR_OUT="${SIDECAR_OUT:-}" \
PERFECT_SANDWICH_OUT="${PERFECT_SANDWICH_OUT:-}" TYPESET_PDF_OUT="${TYPESET_PDF_OUT:-}" \
TEI_OUT="${TEI_OUT:-}" DIGITAL_PDF_OUT="${DIGITAL_PDF_OUT:-}" EPUB_OUT="${EPUB_OUT:-}" \
JOB_OUT="$JOB_OUT" \
python3 - <<'PY'
import json, os
pages = []
with open(os.environ["PAGES_JSONL"], encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            pages.append(json.loads(line))
aligned_pdf = os.environ.get("ALIGNED_PDF") or None
report = {
    "job": os.environ["JOB_NAME"],
    "input": os.environ["INPUT_DIR"],
    "job_output_dir": os.environ.get("JOB_OUT"),
    "preprocessed": os.environ["PRE_DIR"],
    "threshold": float(os.environ["THRESHOLD"]),
    "lang": os.environ["LANG_OCR"],
    "pages_total": int(os.environ["TOTAL"]),
    "pass": int(os.environ["PASS_N"]),
    "fail": int(os.environ["FAIL_N"]),
    "mistral_ok": int(os.environ["MISTRAL_N"]),
    "sandwich_pdf": os.environ.get("PDF_OUT") or None,
    "perfect_sandwich_pdf": os.environ.get("PERFECT_SANDWICH_OUT") or None,
    "aligned_pdf": aligned_pdf,
    "pathb_pdf": aligned_pdf,
    "sidecar_txt": os.environ.get("SIDECAR_OUT") or None,
    "tei_xml": os.environ.get("TEI_OUT") or None,
    "digital_pdf": os.environ.get("DIGITAL_PDF_OUT") or None,
    "typeset_edition_pdf": os.environ.get("TYPESET_PDF_OUT") or None,
    "epub": os.environ.get("EPUB_OUT") or None,
    "pages": pages,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
)"

printf '%s\n' "$REPORT" | tee "$LOG_JSON" >/dev/null
printf '%s\n' "$REPORT"

# Build comprehensive closing report (<job>.report.md)
GENERATE_REPORT="${SCRIPT_DIR}/generate_job_report.py"
if [[ -f "$GENERATE_REPORT" ]]; then
  log "generate closing audit report -> ${JOB_OUT}/${JOB_NAME}.report.md"
  set +e
  python3 "$GENERATE_REPORT" --job "$JOB_NAME" --data-dir "$(dirname "$OUT_DIR")" --output-dir "$JOB_OUT" ${JOB_CONFIG:+-c "$JOB_CONFIG"}
  set -e
fi

if [[ "$DO_PUSH" -eq 1 && -f "$SYNC" ]]; then
  log "push processing+output to NAS"
  AS_LOCAL_DATA="$(dirname "$OUT_DIR")" bash "$SYNC" push-processing || true
  AS_LOCAL_DATA="$(dirname "$OUT_DIR")" bash "$SYNC" push-output || true
fi

log "pipeline done job=$JOB_NAME pass=$PASS_N fail=$FAIL_N mistral=$MISTRAL_N report=$LOG_JSON"
exit 0
