# 📚 AlexandriaSandwich

> **Automated book digitization with hybrid OCR (Tesseract + Mistral AI), GSD pipeline & 1:1 sandwich PDF output.**

![Build Status](https://img.shields.io/badge/docker-multi--arch-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12-yellow)

**AlexandriaSandwich** is a containerized pipeline designed for archiving and digitizing books. It converts raw scans into precise **1:1 sandwich PDFs** (visual scan preserved with an exact invisible searchable text layer underneath), generic **TEI-P5 XML**, and newly typeset **digital vector PDFs** via Typst.

---

## ✨ Key Features

* 🪓 **Headless Pre-Processing:** Automatic deskewing and edge cleaning for yellowed pages via **ImageMagick + unpaper** (`scripts/preprocess.sh`).
* 🤖 **Hybrid Quality Loop:**
  * **Local & Fast:** First-pass OCR using Tesseract on the compute node.
  * **AI Fallback:** Automatic switch to **Mistral OCR (`mistral-ocr-latest`)** for low confidence scores (< 85%), Fraktur typography, or degraded pages.
* 📦 **Three Core Artifacts:**
  1. **Generic TEI-P5 XML** (`<job>.tei.xml`) for long-term preservation and digital libraries.
  2. **1:1 Sandwich PDF** (`<job>.sandwich.pdf`) retaining the original scan 1:1 with an invisible text layer.
  3. **Digital Vector PDF** (`<job>.digital.pdf`) typeset from an AST via Typst with modern typography.
* 🛠️ **Dual Correction Paths:**
  * **Path A:** hOCR text editing *prior* to PDF compilation.
  * **Path B:** Direct editing of the invisible text layer *inside* the finished PDF.
* 🐳 **Multi-Architecture Support:** Built for `linux/amd64` (Intel Proxmox VM) and `linux/arm64` (Apple Silicon M2).

---

## 🏛️ System Architecture

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Dev Node (Mac mini M2)                                      │
 │                                                             │
 │  • VS Code IDE (Workspace Isolation)                        │
 │  • Local AI Agents / GSD Workflow Planner                   │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Git / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Control Node (NAS)                                          │
 │                                                             │
 │  • n8n Workflow Orchestrator (Docker Container)            │
 │  • Central Storage (NFS/SMB Share)                          │
 └──────────────────────────────┬──────────────────────────────┘
                                │ NFS Mount & REST / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Compute Node (Proxmox VM "alex" - 16GB RAM / 4 vCPUs)       │
 │                                                             │
 │  • Docker OCR Worker Container (`alexandria_worker`)        │
 │    ├── ImageMagick + unpaper (Deskew & Cleanup)             │
 │    ├── Tesseract OCR (Primary local engine, hOCR export)    │
 │    ├── Mistral OCR Client (API fallback & layout analysis)  │
 │    └── OCRmyPDF / Typst 0.11+ / TEI Exporter                │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📖 Navigation & Documentation

- [Installation Guide](INSTALLATION.md)
- [Pipeline Architecture](WIKI_VERFAHREN.md)
- [Correction Paths (Path A & B)](CORRECTION_PATHS.md)
- [Deployment Instructions](DEPLOY.md)
- [Storage Layout](STORAGE.md)
- [n8n Integration](N8N.md)
