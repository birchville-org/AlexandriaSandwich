# 🤖 Project Context: AlexandriaSandwich

## Overview
Automated book digitization pipeline producing 1:1 Sandwich PDFs with a local-first Quality Loop (Tesseract) and high-precision AI fallback (Mistral OCR).

## Stack & Infrastructure
- **Dev Workstation:** Mac mini M2 (VS Code + Hermes / Claude)
- **Control Node (NAS):** Hosts n8n, storage volumes (/data/input, processing, output) via NFS
- **Compute Node (Proxmox):** Intel i7 (32GB RAM), hosts heavy OCR Worker (Docker)
- **Worker Tools:** ScanTailor CLI, ImageMagick, Tesseract (hOCR), OCRmyPDF, img2pdf
- **AI/Fallback:** Mistral OCR API (`mistral-ocr-latest`) for low confidence scores and Markdown export.

## Core Rules for Agents
1. Always build multi-arch docker images (linux/amd64 + linux/arm64).
2. Follow the GSD framework steps in .gsd/
3. Support both Correction Paths: Path A (Pre-PDF hOCR) & Path B (Post-PDF Editor).

