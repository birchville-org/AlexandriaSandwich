#!/usr/bin/env bash
# Baut das Worker-Image sowohl für ARM64 (M2 Mac) als auch für AMD64 (Proxmox Intel i7)
echo "🏗️ Starte Multi-Architektur Docker Build..."
docker buildx build --platform linux/amd64,linux/arm64 -t alexandria-worker:latest ./docker/worker --load
