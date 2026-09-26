# 🏛️ Systemarchitektur: AlexandriaSandwich

Diese Dokumentation beschreibt die technische Architektur, den Datenfluss und die Schnittstellen von **AlexandriaSandwich**.

---

## 1. Systemübersicht & Topologie

Das System ist in eine **Control Node** (NAS), eine **Compute Node** (Proxmox Hypervisor) und eine **Dev Node** (Mac mini M2) unterteilt.

```text
 ┌─────────────────────────────────────────────────────────────┐
 │ Dev Node (Mac mini M2)                                      │
 │                                                             │
 │  • VS Code IDE (Workspace Isolation)                        │
 │  • Local AI Agents (Hermes via Remote / Claude 3.5 Sonnet)  │
 │  • Docker Buildx (ARM64 & AMD64 Cross-Compilation)          │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Git / SSH
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Control Node (NAS)                                          │
 │                                                             │
 │  • n8n Workflow Orchestrator (Docker Container)            │
 │  • Central Storage (NFS/SMB Share)                          │
 │    ├── /data/input       (Unverarbeitete Scans)             │
 │    ├── /data/processing  (Temp-Cache auf NVMe)              │
 │    └── /data/output      (Fertige Sandwich-PDFs + MD)       │
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

## 2. Storage

Siehe **[docs/STORAGE.md](docs/STORAGE.md)** für NFS-Mounts (`mount_nfs.sh`), rsync-Fallback (`sync_storage.sh`) und Ansible-Variablen.
