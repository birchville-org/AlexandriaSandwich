#!/usr/bin/env bash
# AlexandriaSandwich — mount NAS NFS exports on compute/dev host
#
# Usage:
#   mount_nfs.sh mount|umount|status|fstab-snippet
#
# Env:
#   AS_NAS_HOST AS_NAS_NFS_BASE AS_LOCAL_DATA AS_NFS_OPTS
#
set -euo pipefail

NAS_HOST="${AS_NAS_HOST:-nas.local}"
# NFS export base on NAS (may equal AS_NAS_BASE or differ, e.g. /export/alexandria)
NAS_NFS_BASE="${AS_NAS_NFS_BASE:-${AS_NAS_BASE:-/volume1/alexandria}}"
LOCAL_DATA="${AS_LOCAL_DATA:-/data}"
NFS_OPTS="${AS_NFS_OPTS:-rw,soft,intr,timeo=50,_netdev,nofail}"

log() { printf '%s\n' "$*" >&2; }
die() { log "Error: $*"; exit 2; }
have() { command -v "$1" >/dev/null 2>&1; }

SUBS=(input processing output)
ACTION="${1:-status}"

mount_one() {
  local sub="$1"
  local src="${NAS_HOST}:${NAS_NFS_BASE}/${sub}"
  local dst="${LOCAL_DATA}/${sub}"
  mkdir -p "$dst"
  if mountpoint -q "$dst" 2>/dev/null; then
    log "already mounted: $dst"
    return 0
  fi
  log "mount $src → $dst"
  sudo mount -t nfs -o "$NFS_OPTS" "$src" "$dst"
}

umount_one() {
  local sub="$1"
  local dst="${LOCAL_DATA}/${sub}"
  if mountpoint -q "$dst" 2>/dev/null; then
    log "umount $dst"
    sudo umount "$dst" || sudo umount -l "$dst"
  else
    log "not mounted: $dst"
  fi
}

case "$ACTION" in
  mount)
    have mount || die "mount not found"
    for s in "${SUBS[@]}"; do mount_one "$s"; done
    ;;
  umount|unmount)
    for s in "${SUBS[@]}"; do umount_one "$s"; done
    ;;
  status)
    for s in "${SUBS[@]}"; do
      dst="${LOCAL_DATA}/${s}"
      if mountpoint -q "$dst" 2>/dev/null; then
        findmnt -n -o SOURCE,TARGET,FSTYPE,OPTIONS "$dst" || ls -ld "$dst"
      else
        log "UNMOUNTED $dst"
      fi
    done
    ;;
  fstab-snippet)
    for s in "${SUBS[@]}"; do
      printf '%s:%s/%s  %s/%s  nfs  %s  0  0\n' \
        "$NAS_HOST" "$NAS_NFS_BASE" "$s" "$LOCAL_DATA" "$s" "$NFS_OPTS"
    done
    ;;
  *)
    die "usage: $0 mount|umount|status|fstab-snippet"
    ;;
esac
