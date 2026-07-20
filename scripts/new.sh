#!/usr/bin/env bash

# ==============================================================================
# AlexandriaSandwich - Idempotentes Setup-Skript
# Kann beliebig oft ausgeführt werden, ohne bestehende Dateien zu überschreiben.
# ==============================================================================

set -e # Skript abbrechen, falls ein kritischer Systemfehler auftritt

PROJECT_NAME="AlexandriaSandwich"

echo "🚀 Prüfe / Erstelle Projektstruktur für: $PROJECT_NAME..."

# Falls wir nicht im Projektordner sind, erstelle ihn oder wechsele hinein
if [ "$(basename "$PWD")" != "$PROJECT_NAME" ]; then
    mkdir -p "$PROJECT_NAME"
    cd "$PROJECT_NAME"
fi

# Helper-Funktion: Datei nur erstellen, wenn sie noch NICHT existiert (Idempotenz)
create_file_if_missing() {
    local file_path="$1"
    local content="$2"

    if [ -f "$file_path" ]; then
        echo "  ℹ️  Datei existiert bereits (übersprungen): $file_path"
    else
        echo "  📝 Erstelle Datei: $file_path"
        # Ordner für Datei sicherstellen
        mkdir -p "$(dirname "$file_path")"
        echo "$content" > "$file_path"
    fi
}

# 1. Ordnerstruktur anlegen (mkdir -p ist von Haus aus idempotent)
echo "📁 Stelle Verzeichnisstruktur sicher..."
mkdir -p .agent
mkdir -p .gsd/TASKS
mkdir -p .vscode
mkdir -p ansible/roles
mkdir -p docker/n8n
mkdir -p docker/worker
mkdir -p workflows
mkdir -p scripts
mkdir -p data/input
mkdir -p data/processing
mkdir -p data/output

# 2. .gitkeep in Datenordnern sicherstellen
touch data/input/.gitkeep
touch data/processing/.gitkeep
touch data/output/.gitkeep

# 3. .gitignore
create_file_if_missing ".gitignore" \
"# System & OS
.DS_Store
Thumbs.db

# Daten- und Arbeitsverzeichnisse ausschließen
/data/input/*
!/data/input/.gitkeep
/data/processing/*
!/data/processing/.gitkeep
/data/output/*
!/data/output/.gitkeep

# n8n Daten, Keys & Secrets
docker/n8n/data/
*.env

# Ansible Vault & Temporary Files
*.retry
.ansible/
"

# 4. Agenten Context für Hermes / Antigravity (.agent/CONTEXT.md)
create_file_if_missing ".agent/CONTEXT.md" \
"# 🤖 Project Context: AlexandriaSandwich

## Overview
Automated book digitization pipeline producing 1:1 Sandwich PDFs with a local-first Quality Loop (Tesseract) and high-precision AI fallback (Mistral OCR).

## Stack & Infrastructure
- **Dev Workstation:** Mac mini M2 (VS Code + Hermes / Claude)
- **Control Node (NAS):** Hosts n8n, storage volumes (/data/input, processing, output) via NFS
- **Compute Node (Proxmox):** Intel i7 (32GB RAM), hosts heavy OCR Worker (Docker)
- **Worker Tools:** ScanTailor CLI, ImageMagick, Tesseract (hOCR), OCRmyPDF, img2pdf
- **AI/Fallback:** Mistral OCR API (\`mistral-ocr-latest\`) for low confidence scores and Markdown export.

## Core Rules for Agents
1. Always build multi-arch docker images (linux/amd64 + linux/arm64).
2. Follow the GSD framework steps in .gsd/
3. Support both Correction Paths: Path A (Pre-PDF hOCR) & Path B (Post-PDF Editor).
"

# 5. GSD Specification (.gsd/SPEC.md)
create_file_if_missing ".gsd/SPEC.md" \
"# AlexandriaSandwich - GSD Specification

## Core Goal
Automated book digitization producing 1:1 Sandwich PDFs with a local-first Quality Loop (Tesseract) and high-precision AI fallback (Mistral OCR).

## Execution Strategy
1. Local Image Processing via ScanTailor CLI on Proxmox Compute Worker.
2. OCR via Tesseract (hOCR output).
3. Confidence score check: If < 85%, trigger Mistral OCR fallback / Human-in-the-loop.
4. Assembly into Sandwich PDF via OCRmyPDF.
"

# 6. VS Code Workspace Settings (.vscode/settings.json)
create_file_if_missing ".vscode/settings.json" \
"{
  \"files.associations\": {
    \"*.yml\": \"dockercompose\",
    \"Dockerfile*\": \"dockerfile\"
  },
  \"editor.formatOnSave\": true,
  \"files.exclude\": {
    \"**/.git\": true,
    \"**/.DS_Store\": true
  }
}"

# 7. Root docker-compose.yml
create_file_if_missing "docker-compose.yml" \
"version: '3.8'

services:
  ocr_worker:
    build:
      context: ./docker/worker
    container_name: alexandria_worker
    restart: unless-stopped
    environment:
      - MISTRAL_API_KEY=\${MISTRAL_API_KEY:-}
    volumes:
      - ./data/input:/data/input
      - ./data/processing:/data/processing
      - ./data/output:/data/output
"

# 8. Worker Dockerfile (Multi-Arch + Mistral AI)
create_file_if_missing "docker/worker/Dockerfile" \
"FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    scantailor \\
    unpaper \\
    imagemagick \\
    ghostscript \\
    tesseract-ocr \\
    tesseract-ocr-deu \\
    tesseract-ocr-eng \\
    pngquant \\
    jbig2enc \\
    poppler-utils \\
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ocrmypdf img2pdf mistralai

RUN sed -i 's/rights=\"none\" pattern=\"PDF\"/rights=\"read|write\" pattern=\"PDF\"/' /etc/ImageMagick-6/policy.xml

WORKDIR /data

CMD [\"tail\", \"-f\", \"/dev/null\"]
"

# 9. Helper Skripte
create_file_if_missing "scripts/quality_check.py" \
"#!/usr/bin/env python3
"""
AlexandriaSandwich - Quality Check Script
"""
import sys

def main():
    print(\"Starte Qualitätsprüfung...\")
    sys.exit(0)

if __name__ == \"__main__\":
    main()
"

create_file_if_missing "scripts/mistral_ocr.py" \
"#!/usr/bin/env python3
"""
AlexandriaSandwich - Mistral OCR Helper
"""
import os
import sys

def process_with_mistral(image_path):
    api_key = os.environ.get(\"MISTRAL_API_KEY\")
    if not api_key:
        print(\"Error: MISTRAL_API_KEY environment variable not set.\")
        sys.exit(1)
    
    print(f\"Sende {image_path} an Mistral OCR...\")

if __name__ == \"__main__\":
    if len(sys.argv) < 2:
        print(\"Usage: python mistral_ocr.py <path_to_image>\")
        sys.exit(1)
    process_with_mistral(sys.argv[1])
"

create_file_if_missing "scripts/build_multiarch.sh" \
"#!/usr/bin/env bash
echo \"🏗️ Starte Multi-Architektur Docker Build...\"
docker buildx build --platform linux/amd64,linux/arm64 -t alexandria-worker:latest ./docker/worker --load
"

# Skripte ausführbar machen
chmod +x scripts/*.py 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# 10. Git-Repository initialisieren (falls noch nicht geschehen)
if [ ! -d ".git" ]; then
    echo "📦 Initialisiere Git-Repository..."
    git init > /dev/null
fi

echo ""
echo "✅ Fertig! Die Projektstruktur ist vollständig & auf aktuellem Stand."
