#!/usr/bin/env bash
# Baut das Worker-Image für AMD64 (alex.local / Proxmox) und ARM64 (M2).
# Hinweis: docker buildx --load unterstützt nur EINE Zielplattform.
# Deshalb: Multi-Arch in den Build-Cache, Host-Arch lokal laden.
set -euo pipefail

IMAGE="${IMAGE:-alexandria-worker:latest}"
CONTEXT="${CONTEXT:-./docker/worker}"
BUILDER="${BUILDER:-alexandria_builder}"

HOST_ARCH="$(uname -m)"
case "$HOST_ARCH" in
  x86_64|amd64) HOST_PLATFORM="linux/amd64" ;;
  aarch64|arm64) HOST_PLATFORM="linux/arm64" ;;
  *) echo "Unsupported host arch: $HOST_ARCH"; exit 1 ;;
esac

echo "🏗️  Multi-Arch Docker Build → ${IMAGE}"
echo "    Platforms: linux/amd64,linux/arm64 | Host load: ${HOST_PLATFORM}"

# Ensure buildx builder exists (docker-container driver for multi-arch)
if ! docker buildx inspect "$BUILDER" >/dev/null 2>&1; then
  docker buildx create --name "$BUILDER" --driver docker-container \
    --platform linux/amd64,linux/arm64 --use
  docker buildx inspect --bootstrap
else
  docker buildx use "$BUILDER"
fi

# 1) Multi-arch into build cache (no --load)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t "$IMAGE" \
  "$CONTEXT"

# 2) Load host architecture image into local docker for immediate use
docker buildx build \
  --platform "$HOST_PLATFORM" \
  -t "$IMAGE" \
  --load \
  "$CONTEXT"

echo "✅ Fertig: ${IMAGE} (multi-arch cached, ${HOST_PLATFORM} loaded locally)"
