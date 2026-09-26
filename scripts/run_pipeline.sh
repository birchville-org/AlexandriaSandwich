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

JOB_NAME="${AS_JOB_NAME:-manual}"
DO_PULL=0
DO_PUSH=0
LANG_OCR="${OCR_LANG:-deu+eng}"
THRESHOLD="${OCR_CONFIDENCE_THRESHOLD:-85}"
USE_MISTRAL=1
LIMIT=0
INPUT_DIR="${AS_INPUT_DIR:-/data/input}"
PROC_DIR="${AS_PROCESSING_DIR:-/data/processing}"
OUT_DIR="${AS_OUTPUT_DIR:-/data/output}"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }
die() { log "ERROR: $*"; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job|-j) JOB_NAME="$2"; shift 2 ;;
    --pull) DO_PULL=1; shift ;;
    --push) DO_PUSH=1; shift ;;
    --lang) LANG_OCR="$2"; shift 2 ;;
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --no-mistral) USE_MISTRAL=0; shift ;;
    --limit) LIMIT="$2"; shift 2 ;;
    --input) INPUT_DIR="$2"; shift 2 ;;
    --processing) PROC_DIR="$2"; shift 2 ;;
    --output) OUT_DIR="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,25p' "$0"; exit 0 ;;
    *) die "unknown arg: $1" ;;
  esac
done

PRE_DIR="${PROC_DIR}/preprocessed/${JOB_NAME}"
QC_DIR="${PROC_DIR}/quality/${JOB_NAME}"
MD_DIR="${OUT_DIR}/markdown/${JOB_NAME}"
LOG_JSON="${OUT_DIR}/reports/${JOB_NAME}.pipeline.json"
PAGES_JSONL="${QC_DIR}/pages.jsonl"
mkdir -p "$PRE_DIR" "$QC_DIR" "$MD_DIR" "$(dirname "$LOG_JSON")" "$OUT_DIR"
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
  JOB_INPUT="$INPUT_DIR"
fi

log "preprocess job=$JOB_NAME input=$JOB_INPUT -> $PRE_DIR"
bash "$PREPROCESS" --input "$JOB_INPUT" --output "$PRE_DIR" --overwrite

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
  log "quality_check $base"
  set +e
  python3 "$QUALITY" -i "$page" -l "$LANG_OCR" -t "$THRESHOLD" --json --keep-ocr "$QC_DIR" >"$qc_json"
  qc_rc=$?
  set -e

  mean="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("mean_confidence",0))' "$qc_json" 2>/dev/null || echo 0)"
  decision="pass"
  mistral_md=""

  if [[ "$qc_rc" -eq 0 ]]; then
    PASS_N=$((PASS_N + 1))
    decision="pass"
  else
    FAIL_N=$((FAIL_N + 1))
    decision="fallback"
    if [[ "$USE_MISTRAL" -eq 1 ]]; then
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
PDF_OUT="${OUT_DIR}/pdf/${JOB_NAME}.sandwich.pdf"
SIDECAR_OUT="${OUT_DIR}/pdf/${JOB_NAME}.sidecar.txt"
mkdir -p "$(dirname "$PDF_OUT")"
if [[ -f "$ASSEMBLE" ]]; then
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
else
  log "warn: assemble_sandwich.py missing; skip PDF"
  PDF_OUT=""
fi

# Multi-format outputs: TEI-P5 XML & Typst Digital PDF
CONSOLIDATE="${SCRIPT_DIR}/consolidate_book.py"
EXPORT_TEI="${SCRIPT_DIR}/export_tei.py"
RENDER_DIGITAL="${SCRIPT_DIR}/render_digital_pdf.py"

BOOK_DIR="${OUT_DIR}/books/${JOB_NAME}"
TEI_OUT="${OUT_DIR}/tei/${JOB_NAME}.tei.xml"
DIGITAL_PDF_OUT="${OUT_DIR}/pdf/${JOB_NAME}.digital.pdf"
mkdir -p "$BOOK_DIR" "$(dirname "$TEI_OUT")"

if [[ -f "$CONSOLIDATE" ]]; then
  log "consolidate book -> $BOOK_DIR"
  set +e
  python3 "$CONSOLIDATE" --job "$JOB_NAME" --input-dir "$QC_DIR" --output-dir "$BOOK_DIR" --lang "$LANG_OCR"
  con_rc=$?
  set -e
  if [[ "$con_rc" -ne 0 ]]; then
    log "warn: consolidate_book failed (rc=$con_rc)"
  fi
fi

if [[ -f "$EXPORT_TEI" && -f "${BOOK_DIR}/book.json" ]]; then
  log "export tei-p5 -> $TEI_OUT"
  set +e
  python3 "$EXPORT_TEI" --job "$JOB_NAME" --input "${BOOK_DIR}/book.json" --output "$TEI_OUT"
  tei_rc=$?
  set -e
  if [[ "$tei_rc" -ne 0 ]]; then
    log "warn: export_tei failed (rc=$tei_rc)"
    TEI_OUT=""
  fi
else
  TEI_OUT=""
fi

if [[ -f "$RENDER_DIGITAL" && -f "${BOOK_DIR}/book.json" ]]; then
  log "render digital book pdf -> $DIGITAL_PDF_OUT"
  set +e
  python3 "$RENDER_DIGITAL" --job "$JOB_NAME" --input "${BOOK_DIR}/book.json" --output "$DIGITAL_PDF_OUT"
  render_rc=$?
  set -e
  if [[ "$render_rc" -ne 0 ]]; then
    log "warn: render_digital_pdf failed (rc=$render_rc)"
    DIGITAL_PDF_OUT=""
  fi
else
  DIGITAL_PDF_OUT=""
fi

REPORT="$(JOB_NAME="$JOB_NAME" INPUT_DIR="$INPUT_DIR" PRE_DIR="$PRE_DIR" \
THRESHOLD="$THRESHOLD" LANG_OCR="$LANG_OCR" PASS_N="$PASS_N" FAIL_N="$FAIL_N" \
MISTRAL_N="$MISTRAL_N" TOTAL="${#PAGES[@]}" PAGES_JSONL="$PAGES_JSONL" \
PDF_OUT="${PDF_OUT:-}" SIDECAR_OUT="${SIDECAR_OUT:-}" TEI_OUT="${TEI_OUT:-}" DIGITAL_PDF_OUT="${DIGITAL_PDF_OUT:-}" \
python3 - <<'PY'
import json, os
pages = []
with open(os.environ["PAGES_JSONL"], encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            pages.append(json.loads(line))
report = {
    "job": os.environ["JOB_NAME"],
    "input": os.environ["INPUT_DIR"],
    "preprocessed": os.environ["PRE_DIR"],
    "threshold": float(os.environ["THRESHOLD"]),
    "lang": os.environ["LANG_OCR"],
    "pages_total": int(os.environ["TOTAL"]),
    "pass": int(os.environ["PASS_N"]),
    "fail": int(os.environ["FAIL_N"]),
    "mistral_ok": int(os.environ["MISTRAL_N"]),
    "sandwich_pdf": os.environ.get("PDF_OUT") or None,
    "sidecar_txt": os.environ.get("SIDECAR_OUT") or None,
    "tei_xml": os.environ.get("TEI_OUT") or None,
    "digital_pdf": os.environ.get("DIGITAL_PDF_OUT") or None,
    "pages": pages,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
)"

printf '%s\n' "$REPORT" | tee "$LOG_JSON" >/dev/null
printf '%s\n' "$REPORT"

if [[ "$DO_PUSH" -eq 1 && -f "$SYNC" ]]; then
  log "push processing+output to NAS"
  AS_LOCAL_DATA="$(dirname "$OUT_DIR")" bash "$SYNC" push-processing || true
  AS_LOCAL_DATA="$(dirname "$OUT_DIR")" bash "$SYNC" push-output || true
fi

log "pipeline done job=$JOB_NAME pass=$PASS_N fail=$FAIL_N mistral=$MISTRAL_N report=$LOG_JSON"
exit 0
