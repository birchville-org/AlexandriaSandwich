#!/usr/bin/env bash
# AlexandriaSandwich - Headless page preprocessing
# Deskew (ImageMagick) + page cleanup (unpaper) for OCR readiness.
#
# Usage:
#   preprocess.sh [--input DIR] [--output DIR] [--dpi N] [--no-unpaper] [--dry-run] [FILES...]
#
# Defaults (container paths):
#   input  = /data/input
#   output = /data/processing/preprocessed
#
set -euo pipefail

INPUT_DIR="${AS_INPUT_DIR:-/data/input}"
OUTPUT_DIR="${AS_OUTPUT_DIR:-/data/processing/preprocessed}"
DPI="${AS_DPI:-300}"
USE_UNPAPER=1
DRY_RUN=0
OVERWRITE=0
EXTENSIONS_DEFAULT="png,jpg,jpeg,tif,tiff,bmp,pnm,pgm,ppm"

log()  { printf '%s\n' "$*" >&2; }
die()  { log "Error: $*"; exit 2; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat >&2 <<'EOF'
AlexandriaSandwich preprocess.sh — deskew + unpaper cleanup

Options:
  -i, --input DIR      Input directory (default: /data/input or $AS_INPUT_DIR)
  -o, --output DIR     Output directory (default: /data/processing/preprocessed)
  -d, --dpi N          Target density metadata (default: 300)
      --no-unpaper     Skip unpaper post-processing
      --overwrite      Overwrite existing outputs
      --dry-run        List actions only
  -h, --help           Show help

Positional FILE args process only those files (absolute or relative).
EOF
}

FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input) INPUT_DIR="$2"; shift 2 ;;
    -o|--output) OUTPUT_DIR="$2"; shift 2 ;;
    -d|--dpi) DPI="$2"; shift 2 ;;
    --no-unpaper) USE_UNPAPER=0; shift ;;
    --overwrite) OVERWRITE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; FILES+=("$@"); break ;;
    -*) die "unknown option: $1" ;;
    *) FILES+=("$1"); shift ;;
  esac
done

have convert || die "ImageMagick 'convert' not found"
have identify || die "ImageMagick 'identify' not found"
if [[ "$USE_UNPAPER" -eq 1 ]]; then
  have unpaper || die "unpaper not found (use --no-unpaper to skip)"
fi

mkdir -p "$OUTPUT_DIR"
shopt -s nullglob nocaseglob

collect_from_dir() {
  local dir="$1"
  local ext
  IFS=',' read -r -a exts <<< "$EXTENSIONS_DEFAULT"
  local found=()
  for ext in "${exts[@]}"; do
    found+=("$dir"/*."$ext")
    found+=("$dir"/*/*."$ext")
  done
  # shellcheck disable=SC2068
  for f in ${found[@]+"${found[@]}"}; do
    [[ -f "$f" ]] && printf '%s\n' "$f"
  done | sort -u
}

if [[ ${#FILES[@]} -eq 0 ]]; then
  [[ -d "$INPUT_DIR" ]] || die "input directory not found: $INPUT_DIR"
  if command -v mapfile >/dev/null 2>&1; then
    mapfile -t FILES < <(collect_from_dir "$INPUT_DIR")
  else
    while IFS= read -r line; do
      [[ -n "$line" ]] && FILES+=("$line")
    done < <(collect_from_dir "$INPUT_DIR")
  fi
fi

TMP=()
for f in "${FILES[@]:-}"; do
  [[ -n "${f:-}" && -f "$f" ]] || continue
  TMP+=("$f")
done
FILES=("${TMP[@]:-}")

if [[ ${#FILES[@]} -eq 0 ]]; then
  die "no input images found (input=$INPUT_DIR)"
fi

log "preprocess: ${#FILES[@]} file(s) → $OUTPUT_DIR (dpi=$DPI unpaper=$USE_UNPAPER)"

ok=0
fail=0
skipped=0

process_one() {
  local src="$1"
  local base stem out_png work
  base="$(basename "$src")"
  stem="${base%.*}"
  out_png="$OUTPUT_DIR/${stem}.png"

  if [[ -f "$out_png" && "$OVERWRITE" -eq 0 ]]; then
    log "skip (exists): $out_png"
    skipped=$((skipped + 1))
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "dry-run: $src → $out_png"
    ok=$((ok + 1))
    return 0
  fi

  work="$(mktemp -d "${TMPDIR:-/tmp}/as-pre.XXXXXX")"
  # shellcheck disable=SC2064
  trap 'rm -rf "$work"' RETURN

  # ImageMagick -deskew threshold is percent, not degrees.
  # Force 8-bit gray PGM (P5) — unpaper rejects 16-bit/PNM variants.
  if ! convert "$src" \
      -colorspace Gray -depth 8 \
      -density "$DPI" \
      -deskew 40% \
      -background white -flatten \
      -alpha off \
      -strip \
      "pgm:$work/deskew.pgm"; then
    convert "$src" -colorspace Gray -depth 8 -density "$DPI" \
      -background white -flatten -alpha off -strip \
      "pgm:$work/deskew.pgm"
  fi

  if [[ ! -s "$work/deskew.pgm" ]]; then
    log "failed: deskew produced empty file for $src"
    fail=$((fail + 1))
    return 1
  fi

  if [[ "$USE_UNPAPER" -eq 1 ]]; then
    if ! unpaper --layout single --dpi "$DPI" \
        --no-mask-scan --no-border-align \
        --overwrite \
        "$work/deskew.pgm" "$work/clean.pgm" >/dev/null; then
      log "warn: unpaper failed for $src — using deskew-only output"
      convert "$work/deskew.pgm" -density "$DPI" -alpha off -strip "PNG:$out_png"
    else
      convert "$work/clean.pgm" -density "$DPI" -alpha off -strip "PNG:$out_png"
    fi
  else
    convert "$work/deskew.pgm" -density "$DPI" -alpha off -strip "PNG:$out_png"
  fi

  if [[ ! -s "$out_png" ]]; then
    log "failed: empty output for $src"
    fail=$((fail + 1))
    return 1
  fi

  local dims
  dims="$(identify -format '%wx%h' "$out_png" 2>/dev/null || echo '?')"
  log "ok: $base → $(basename "$out_png") ($dims)"
  ok=$((ok + 1))
}

for src in "${FILES[@]}"; do
  process_one "$src" || true
done

log "done: ok=$ok fail=$fail skipped=$skipped out=$OUTPUT_DIR"
[[ "$fail" -eq 0 ]] || exit 1
exit 0
