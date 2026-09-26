# 📚 AlexandriaSandwich

> **Automatisierte Buch-Digitalisierung mit Hybrid-OCR (Tesseract + Mistral AI), GSD-Pipeline & Perfect Sandwich-PDF Output.**

![Build Status](https://img.shields.io/badge/docker-multi--arch-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12-yellow)

**AlexandriaSandwich** ist eine containergestützte Pipeline zur Archivierung und Digitalisierung von Büchern. Sie verwandelt rohe Buchscans in perfekte **1:1 Sandwich-PDFs** (visuelles Originalbild mit punktgenau hinterlegter, unsichtbarer Textebene) sowie strukturierte **Markdown-Dateien** für eReader und RAG-Systeme.

---

## ✨ Features

* 🪓 **Automatisches Pre-Processing:** Ausrichten (Deskewing) und Reinigen vergilbter Seiten via **ImageMagick + unpaper** (`scripts/preprocess.sh`).
* 🤖 **Hybrid Quality Loop:**
  * **Lokal & Schnell:** Erste OCR-Ebene mit Tesseract OCR auf der Proxmox Compute-Node.
  * **KI-Fallback:** Automatischer Wechsel auf **Mistral OCR (`mistral-ocr-latest`)** bei schlechten Scores (< 85% Confidence), Frakturschriften oder beschädigten Seiten.
* 📝 **eBook-Ready Export:** Erzeugt neben dem PDF automatisch sauberes Markdown für eReader oder Large Language Models.
* 🛠️ **Zwei Korrekturpfade:**
  * **Pfad A:** hOCR-Textkorrektur *vor* dem Zusammenbau des PDFs.
  * **Pfad B:** Direktes Editieren der unsichtbaren Textschicht *im* fertigen PDF.
* 🐳 **Multi-Architektur Support:** Native Unterstützung für `linux/amd64` (Intel Proxmox VM) und `linux/arm64` (Apple Silicon M2).

---

## 🏛️ Architektur-Übersicht

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Dev Node (Mac mini M2)                                      │
 │                                                             │
 │  • VS Code IDE (Workspace Isolation)                        │
 │  • Local AI Agents (Hermes via Remote / Claude 3.5 Sonnet)  │
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
 │    ├── Tesseract OCR (Lokale Primary Engine, hOCR Export)   │
 │    ├── Mistral OCR Client (API-Fallback & Layout Analysis)  │
 │    └── OCRmyPDF / img2pdf (PDF Sandwich Assembly)           │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📖 Dokumentation & Installation

- **Detaillierte Installationsanleitung:** [`INSTALLATION.md`](INSTALLATION.md) (Abhängigkeiten, Systempakete, Multi-Container-Setup, n8n-Aktivierung).
- **Die drei Primär-Artefakte:**
  1. **Generisches TEI-P5 XML** (`<job>.tei.xml`) für Langzeitarchivierung und Bibliothekskataloge.
  2. **1:1 Sandwich-PDF** (`<job>.sandwich.pdf`) mit unverändertem Scan und unsichtbarer Textebene.
  3. **Neusatz-PDF** (`<job>.digital.pdf`) via Typst-Vektorsatz mit modernen Schriften.
- **Web-UI & QA-Viewer:** [http://alex.local:8080/](http://alex.local:8080/)
- **n8n Orchestrator:** [http://alex.local:5678/](http://alex.local:5678/)