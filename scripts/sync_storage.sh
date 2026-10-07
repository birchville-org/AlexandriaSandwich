#!/usr/bin/env bash
# AlexandriaSandwich — rsync storage helper (NAS ↔ compute/dev)
#
# Usage:
#   sync_storage.sh pull-input|push-output|pull-all|push-processing|push-output-delete-extra [extra rsync args]
#
# Env:
#   AS_NAS_HOST AS_NAS_USER AS_NAS_BASE AS_LOCAL_DATA AS_RSH
#
set -euo pipefail

NAS_HOST="${AS_NAS_HOST:-192.168.1.8}"
NAS_USER="${AS_NAS_USER:-marco}"
NAS_BASE="${AS_NAS_BASE:-/volume1/docker/alexandria/data}"
LOCAL_DATA="${AS_LOCAL_DATA:-/data}"
RSH="${AS_RSH:-ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new}"
RSYNC_OPTS=( -aH --info=stats2,progress2 --human-readable --rsync-path=/usr/bin/rsync )

log() { printf '%s\n' "$*" >&2; }
die() { log "Error: $*"; exit 2; }

MODE="${1:-}"
shift || true
[[ -n "$MODE" ]] || die "usage: $0 pull-input|push-output|pull-all|push-processing|push-output-delete-extra|dry-pull-input"

remote() { printf '%s@%s:%s' "$NAS_USER" "$NAS_HOST" "$1"; }

ensure_local_dirs() {
  mkdir -p "$LOCAL_DATA"/{input,processing,output}
}

run_rsync() {
  local src="$1" dst="$2"; shift 2
  log "rsync: $src  →  $dst"
  rsync "${RSYNC_OPTS[@]}" "$@" -e "$RSH" "$src" "$dst"
}

ensure_local_dirs

case "$MODE" in
  dry-pull-input)
    RSYNC_OPTS+=( -n )
    ;&
  pull-input)
    # trailing slash = contents of input/
    run_rsync "$(remote "$NAS_BASE/input/")" "$LOCAL_DATA/input/" "$@"
    ;;
  push-output)
    run_rsync "$LOCAL_DATA/output/" "$(remote "$NAS_BASE/output/")" "$@"
    ;;
  push-output-delete-extra)
    # only when output/ is worker-authoritative
    run_rsync "$LOCAL_DATA/output/" "$(remote "$NAS_BASE/output/")" --delete "$@"
    ;;
  push-processing)
    run_rsync "$LOCAL_DATA/processing/" "$(remote "$NAS_BASE/processing/")" "$@"
    ;;
  pull-all)
    for sub in input processing output; do
      run_rsync "$(remote "$NAS_BASE/$sub/")" "$LOCAL_DATA/$sub/" "$@"
    done
    ;;
  push-all-safe)
    # never --delete; never wipe NAS input
    run_rsync "$LOCAL_DATA/processing/" "$(remote "$NAS_BASE/processing/")" "$@"
    run_rsync "$LOCAL_DATA/output/" "$(remote "$NAS_BASE/output/")" "$@"
    ;;
  *)
    die "unknown mode: $MODE"
    ;;
esac

log "done: mode=$MODE local=$LOCAL_DATA nas=$NAS_USER@$NAS_HOST:$NAS_BASE"
