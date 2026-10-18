#!/usr/bin/env bash
# AlexandriaSandwich — Automated Golden Master Regression Suite (M4 / Plan 06-03)
#
# Validates end-to-end pipeline execution, declarative job profile resolution (job.config.json),
# digital multi-format artifact generation, and enforces the job-centric directory layout.
#
# Usage:
#   bash scripts/test_golden_regression.sh [--keep]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Activate virtualenv if present
if [[ -x "${ROOT_DIR}/.venv-ui/bin/python3" && -z "${VIRTUAL_ENV:-}" ]]; then
  export PATH="${ROOT_DIR}/.venv-ui/bin:$PATH"
elif [[ -x "${ROOT_DIR}/.venv/bin/python3" && -z "${VIRTUAL_ENV:-}" ]]; then
  export PATH="${ROOT_DIR}/.venv/bin:$PATH"
fi

DATA_DIR="${ROOT_DIR}/data"
INPUT_DIR="${DATA_DIR}/input"
PROC_DIR="${DATA_DIR}/processing"
OUT_DIR="${DATA_DIR}/output"

JOB_NAME="golden_smoke"
KEEP_OUTPUT=0

for arg in "$@"; do
  case "$arg" in
    --keep) KEEP_OUTPUT=1 ;;
    -h|--help)
      echo "Usage: $0 [--keep]"
      exit 0
      ;;
  esac
done

# Colors & Logging
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
NC="\033[0m"

log_info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
log_ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
log_warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
log_fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

ERRORS=0
record_fail() {
  log_fail "$*"
  ERRORS=$((ERRORS + 1))
}

echo "======================================================================"
echo " AlexandriaSandwich Golden Master Regression Guard (Milestone 4)"
echo "======================================================================"
log_info "Workspace:   $ROOT_DIR"
log_info "Data Root:   $DATA_DIR"
log_info "Target Job:  $JOB_NAME"

# --------------------------------------------------------------------
# STEP 1: Verify Environment & Tools
# --------------------------------------------------------------------
log_info "Step 1: Checking host environment and CLI dependencies..."

if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 --version 2>&1)"
  log_ok "Python: $PY_VER"
else
  record_fail "python3 not found in PATH"
fi

if command -v tesseract >/dev/null 2>&1; then
  TESS_VER="$(tesseract --version 2>&1 | head -n 1)"
  log_ok "Tesseract: $TESS_VER"
else
  record_fail "tesseract not found in PATH"
fi

if command -v typst >/dev/null 2>&1; then
  TYPST_VER="$(typst --version 2>&1 | head -n 1)"
  log_ok "Typst: $TYPST_VER"
else
  log_warn "typst not found in PATH (digital vector PDF step will be skipped)"
fi

# Check Python environment dependencies
PYTHON_DEPS_OK=1
python3 -c "
import json, sys
mods = ['PIL', 'pymupdf']
missing = []
for m in mods:
    try:
        __import__(m)
    except ImportError:
        missing.append(m)
if missing:
    print('Missing Python modules:', ', '.join(missing))
    sys.exit(1)
" || PYTHON_DEPS_OK=0

if [[ "$PYTHON_DEPS_OK" -eq 1 ]]; then
  log_ok "Python modules (PIL, PyMuPDF) verified"
else
  record_fail "Missing critical Python modules"
fi

if [[ -f "${ROOT_DIR}/tests/test_ui_safety.py" ]]; then
  if python3 -c "import fastapi" >/dev/null 2>&1; then
    python3 -m unittest "${ROOT_DIR}/tests/test_ui_safety.py"
    log_ok "UI Safety & Validation unit tests passed (17 tests)"
  fi
fi

# --------------------------------------------------------------------
# STEP 2: Setup Test Harness & Declarative Job Profile
# --------------------------------------------------------------------
log_info "Step 2: Preparing test payload in ${INPUT_DIR}/${JOB_NAME}..."

JOB_IN="${INPUT_DIR}/${JOB_NAME}"
JOB_OUT="${OUT_DIR}/${JOB_NAME}"
JOB_PROC="${PROC_DIR}/preprocessed/${JOB_NAME}"
JOB_QC="${PROC_DIR}/quality/${JOB_NAME}"

mkdir -p "$JOB_IN"

# Populate test images from e2e_m1 if available, otherwise synthetic
if [[ -d "${INPUT_DIR}/e2e_m1" && -f "${INPUT_DIR}/e2e_m1/e2e_01.png" ]]; then
  cp -a "${INPUT_DIR}/e2e_m1"/e2e_*.png "$JOB_IN/"
  log_ok "Copied reference scan pages from e2e_m1"
else
  # Generate minimal PNG pages via Python
  python3 -c "
from PIL import Image, ImageDraw
for i in (1, 2):
    img = Image.new('RGB', (1200, 1600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((100, 100), f'AlexandriaSandwich Golden Test Page {i}', fill=(0, 0, 0))
    d.text((100, 200), 'Dies ist ein automatischer Regressionstest fuer die Pipeline.', fill=(0, 0, 0))
    img.save('${JOB_IN}/page-0' + str(i) + '.png')
"
  log_ok "Created synthetic test pages"
fi

# Write declarative job.config.json
cat > "${JOB_IN}/job.config.json" <<'JSON'
{
  "$schema": "../../schemas/job.config.schema.json",
  "title": "AlexandriaSandwich Golden Master Reference",
  "author": "Birchville Scholar Collective",
  "editor": "Automated Quality Gate",
  "year": 2026,
  "lang": "deu+eng",
  "threshold": 50,
  "use_mistral": false,
  "use_unpaper": false,
  "skip_preprocess": true,
  "heuristics": {
    "script": "Latin",
    "two_column": false,
    "strip_running_headers": true
  }
}
JSON
log_ok "Created declarative profile: ${JOB_IN}/job.config.json"

# Clean any existing output / processing for isolated test run
rm -rf "$JOB_OUT" "$JOB_PROC" "$JOB_QC"

# --------------------------------------------------------------------
# STEP 3: Execute Pipeline Orchestrator
# --------------------------------------------------------------------
log_info "Step 3: Running pipeline orchestrator (scripts/run_pipeline.sh)..."

PIPELINE_SCRIPT="${SCRIPT_DIR}/run_pipeline.sh"
[[ -x "$PIPELINE_SCRIPT" ]] || chmod +x "$PIPELINE_SCRIPT"

set +e
bash "$PIPELINE_SCRIPT" \
  --job "$JOB_NAME" \
  --input "$INPUT_DIR" \
  --processing "$PROC_DIR" \
  --output "$OUT_DIR" \
  --no-mistral \
  --skip-preprocess
PIPE_RC=$?
set -e

if [[ "$PIPE_RC" -eq 0 ]]; then
  log_ok "Pipeline execution finished with exit code 0"
else
  record_fail "Pipeline execution failed with exit code $PIPE_RC"
fi

# --------------------------------------------------------------------
# STEP 4: Validate Artifact Integrity & Declarative Metadata
# --------------------------------------------------------------------
log_info "Step 4: Validating artifact integrity in ${JOB_OUT}..."

check_file() {
  local fpath="$1"
  local desc="$2"
  local min_size="${3:-10}"
  if [[ -f "$fpath" ]]; then
    local sz
    sz="$(wc -c < "$fpath" | tr -d ' ')"
    if [[ "$sz" -ge "$min_size" ]]; then
      log_ok "$desc: $(basename "$fpath") ($sz bytes)"
    else
      record_fail "$desc: $fpath is too small ($sz bytes < $min_size)"
    fi
  else
    record_fail "$desc: missing $fpath"
  fi
}

check_file "${JOB_OUT}/${JOB_NAME}.sandwich.pdf" "Sandwich PDF facsimile" 1000
check_file "${JOB_OUT}/${JOB_NAME}.pipeline.json" "Pipeline JSON report" 100
check_file "${JOB_OUT}/${JOB_NAME}.report.md" "Closing audit report (report.md)" 500
check_file "${JOB_OUT}/book.json" "Consolidated AST (book.json)" 100
check_file "${JOB_OUT}/book.md" "Consolidated Markdown (book.md)" 50
check_file "${JOB_OUT}/${JOB_NAME}.tei.xml" "TEI-P5 XML Edition" 100
check_file "${JOB_OUT}/${JOB_NAME}.epub" "Reflowable EPUB 3 eBook" 500

if command -v typst >/dev/null 2>&1; then
  check_file "${JOB_OUT}/${JOB_NAME}.digital.pdf" "Digital Typst PDF" 1000
fi

# Verify report.md content structure
python3 - "${JOB_OUT}/${JOB_NAME}.report.md" <<'PY'
import sys
content = open(sys.argv[1], encoding='utf-8').read()
assert "Abschlussbericht & Qualitätsaudit" in content, "Report header missing"
assert "Executive Summary & Qualitätsurteil" in content, "Report summary missing"
assert "Chronologische Kommentierung der Pipeline-Einzelschritte" in content, "Stages breakdown missing"
assert "Stufe 1: Ingress" in content, "Stage 1 missing"
assert "Stufe 8: EPUB 3" in content, "Stage 8 missing"
assert "Vollständiges Artefakt-Inventar" in content, "Inventory missing"
print("Report.md structure and quality comments verified.")
PY

# Verify profile metadata propagation into book.json and TEI-P5
log_info "Validating metadata propagation from job.config.json..."
python3 - "${JOB_OUT}/book.json" "${JOB_OUT}/${JOB_NAME}.tei.xml" <<'PY'
import json, sys
import xml.etree.ElementTree as ET

book_json_path, tei_xml_path = sys.argv[1:3]

with open(book_json_path, encoding='utf-8') as f:
    book = json.load(f)
meta = book.get("metadata", {})

assert meta.get("title") == "AlexandriaSandwich Golden Master Reference", f"Title mismatch: {meta.get('title')}"
assert meta.get("author") == "Birchville Scholar Collective", f"Author mismatch: {meta.get('author')}"
assert meta.get("editor") == "Automated Quality Gate", f"Editor mismatch: {meta.get('editor')}"
assert meta.get("year") == 2026, f"Year mismatch: {meta.get('year')}"
assert meta.get("heuristics", {}).get("script") == "Latin", "Heuristics missing in AST"

tree = ET.parse(tei_xml_path)
root = tree.getroot()
ns = {"tei": "http://www.tei-c.org/ns/1.0"}
title_elem = root.find(".//tei:titleStmt/tei:title", ns)
editor_elem = root.find(".//tei:titleStmt/tei:editor", ns)
assert title_elem is not None and "AlexandriaSandwich" in title_elem.text, "TEI title missing"
assert editor_elem is not None and "Automated Quality Gate" in editor_elem.text, "TEI editor missing"

print("Metadata assertions passed: title, author, editor, year, heuristics verified.")
PY
if [[ $? -eq 0 ]]; then
  log_ok "Metadata inheritance into book.json and TEI-P5 verified"
else
  record_fail "Metadata inheritance verification failed"
fi

# --------------------------------------------------------------------
# STEP 5: Enforce Output Directory Layout Guard (No Loose Files)
# --------------------------------------------------------------------
log_info "Step 5: Enforcing job-centric output directory layout..."

# Check for loose files in root output directory
LOOSE_FILES=()
while IFS= read -r f; do
  [[ -n "$f" ]] && LOOSE_FILES+=("$f")
done < <(find "$OUT_DIR" -maxdepth 1 -type f ! -name ".gitkeep" ! -name ".DS_Store")

if [[ ${#LOOSE_FILES[@]} -eq 0 ]]; then
  log_ok "Zero loose files in ${OUT_DIR}/"
else
  record_fail "Found ${#LOOSE_FILES[@]} loose file(s) in root output dir: ${LOOSE_FILES[*]}"
fi

# Check for obsolete legacy subdirectories
LEGACY_DIRS=("pdf" "reports" "tei" "books" "markdown" "runs" "images")
FOUND_LEGACY=()
for ldir in "${LEGACY_DIRS[@]}"; do
  if [[ -d "${OUT_DIR}/${ldir}" ]]; then
    FOUND_LEGACY+=("$ldir")
  fi
done

if [[ ${#FOUND_LEGACY[@]} -eq 0 ]]; then
  log_ok "Zero legacy type-split directories in ${OUT_DIR}/"
else
  record_fail "Legacy directories present in output dir: ${FOUND_LEGACY[*]}"
fi

# --------------------------------------------------------------------
# STEP 6: Validate Downstream Python Components (job_progress & ui)
# --------------------------------------------------------------------
log_info "Step 6: Testing job_progress.py & UI artifact resolution..."

# Test job_progress.py
PROGRESS_OUT="$(python3 "${SCRIPT_DIR}/job_progress.py" --job "$JOB_NAME" --json)"
python3 -c "
import json, sys
data = json.loads('''$PROGRESS_OUT''')
assert data.get('job') == '$JOB_NAME', 'job_progress wrong job'
assert 'stages' in data, 'job_progress missing stages'
print('job_progress.py OK: current_stage =', data.get('current_stage'))
"
if [[ $? -eq 0 ]]; then
  log_ok "scripts/job_progress.py resolves job-centric artifacts successfully"
else
  record_fail "scripts/job_progress.py failed to resolve artifacts"
fi

# Test UI discovery logic
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '${ROOT_DIR}')
from ui.main import _list_jobs, _get_job_artifacts

jobs = _list_jobs()
target = next((j for j in jobs if j.get('name') == '$JOB_NAME'), None)
assert target is not None, 'UI did not find $JOB_NAME in _list_jobs'

artifacts_res = _get_job_artifacts('$JOB_NAME')
items = artifacts_res.get('items', [])
assert any('sandwich.pdf' in a.get('name', '') for a in items), 'Sandwich PDF missing in UI artifacts'
assert any('tei.xml' in a.get('name', '') for a in items), 'TEI XML missing in UI artifacts'
print(f'UI discovery OK: found {len(items)} artifacts for $JOB_NAME')
"
if [[ $? -eq 0 ]]; then
  log_ok "ui/main.py successfully indexes and serves ${JOB_NAME} artifacts"
else
  record_fail "ui/main.py failed to discover ${JOB_NAME} artifacts"
fi

# --------------------------------------------------------------------
# Cleanup or Preserve
# --------------------------------------------------------------------
if [[ "$KEEP_OUTPUT" -eq 0 ]]; then
  log_info "Cleaning up temporary test artifacts (${JOB_NAME})..."
  rm -rf "$JOB_IN" "$JOB_OUT" "$JOB_PROC" "$JOB_QC"
  log_ok "Cleanup complete"
else
  log_info "Preserving test artifacts in ${JOB_OUT} (--keep specified)"
fi

echo "======================================================================"
if [[ "$ERRORS" -eq 0 ]]; then
  printf "${GREEN}>>> GOLDEN MASTER REGRESSION SUITE: ALL CHECKS PASSED <<<${NC}\n"
  exit 0
else
  printf "${RED}>>> GOLDEN MASTER REGRESSION SUITE: %d ERROR(S) DETECTED <<<${NC}\n" "$ERRORS"
  exit 1
fi
