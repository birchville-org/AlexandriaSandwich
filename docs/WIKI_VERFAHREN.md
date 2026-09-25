# Verfahrensdokumentation: AlexandriaSandwich

## 1. Zielsetzung & Kernkonzept

Das Verfahren von **AlexandriaSandwich** dient der vollautomatischen, qualitätsgesicherten Digitalisierung von Büchern und Dokumenten zu archivfesten **1:1 Sandwich-PDFs**. 

Ein Sandwich-PDF besteht aus zwei exakt deckungsgleichen Ebenen:
1. **Visuelle Bildebene (oben):** Das originale, bereinigte Scanbild bleibt 1:1 und pixelgenau erhalten. Es findet kein Neusatz und keine visuelle Textersetzung statt.
2. **Unsichtbare Textebene (unten):** Eine unsichtbare Vektorschrift-Ebene (GlyphLessFont) mit präzisen Positionskoordinaten ermöglicht Volltextsuche, Textmarkierung sowie Copy & Paste.

Zur Optimierung von Betriebskosten, Datenschutz und Verarbeitungsgeschwindigkeit folgt das System einem **Local-First-Ansatz mit KI-Fallback**: Standardseiten werden lokal und ressourceneffizient verarbeitet; nur bei schlechter Erkennungsqualität wird eine externe KI-Schnittstelle hinzugezogen.

---

## 2. Systemarchitektur & Topologie

Der Prozess ist auf drei Knoten verteilt:

```text
┌─────────────────────────────────────────────────────────────┐
│ Dev Node (Mac mini M2)                                      │
│ • Entwicklung & Multi-Arch Docker Builds (ARM64 / AMD64)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Git / Docker Registry
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Control Node (NAS)                                          │
│ • n8n Workflow-Orchestrierung                               │
│ • Zentraler NFS-Speicher:                                    │
│   ├── /data/input       (Eingehende Rohscans)               │
│   ├── /data/processing  (Zwischenstufen auf NVMe-Cache)     │
│   └── /data/output      (Fertige PDFs, Berichte, Markdown)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ NFS Mount & Webhooks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Compute Node (Proxmox VM: alex.local)                       │
│ • alexandria_worker  (ImageMagick, unpaper, Tesseract, OCR) │
│ • alexandria_ui      (FastAPI Dashboard & Path B Editor)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Der Verarbeitungsablauf (Pipeline)

Der Gesamtprozess gliedert sich in sechs aufeinanderfolgende Schritte:

```text
[Rohscan] 
   │
   ▼
[1. Preprocessing] ──────► Deskew & Randbereinigung (ImageMagick + unpaper)
   │
   ▼
[2. Lokale OCR] ────────► Tesseract erzeugt hOCR mit Wortkoordinaten & Konfidenz
   │
   ▼
[3. Quality Gate] ──────► quality_check.py: Mittlere Konfidenz >= 85%?
   │            │
   │ (Ja)       │ (Nein)
   │            ▼
   │      [4. KI-Fallback] ──► Mistral OCR API (mistral-ocr-latest)
   │            │
   ▼            ▼
[5. Sandwich-Assembly] ──► OCRmyPDF / img2pdf fügt Bild + unsichtbaren Text zusammen
   │
   ▼
[6. Korrekturpfade] ────► Pfad A (Pre-PDF / hOCR) ODER Pfad B (Post-PDF / TJ-Layer)
   │
   ▼
[Fertiges Sandwich-PDF]
```

---

### Schritt 1: Headless Preprocessing (`scripts/preprocess.sh`)
- **Werkzeuge:** ImageMagick und `unpaper`.
- **Aufgaben:**
  - Automatisches Entzerren / Geraderichten (Deskew).
  - Entfernen schwarzer Scanränder und Falzschatten.
  - Kontrastoptimierung und Bereinigung von Hintergrundrauschen.
- **Entwurfsentscheidung:** Das früher evaluierte Werkzeug *ScanTailor* wurde bewusst verworfen, da es zwingend eine grafische Benutzeroberfläche erfordert und sich nicht deterministisch und headless in automatisierte Server-Pipelines einbinden lässt.

---

### Schritt 2 & 3: Lokale OCR & Quality Gate (`scripts/quality_check.py`)
- **Primäre Engine:** Tesseract OCR führt die Erkennung lokal auf der Compute-Node aus und gibt standardisiertes `hOCR` (HTML-basiertes OCR-Format mit Bounding Boxes) sowie TSV-Daten aus.
- **Qualitätsprüfung:** Das Skript `quality_check.py` parst die Konfidenzwerte der einzelnen Wörter (0 bis 100 %).
- **Regel:**
  - Mittlere Konfidenz >= 85 %: Seite gilt als erfolgreich erkannt.
  - Mittlere Konfidenz < 85 %: Quality Gate schlägt an; die Seite wird für den KI-Fallback markiert.

---

### Schritt 4: Bedingter KI-Fallback (`scripts/mistral_ocr.py`)
- **Engine:** Mistral OCR API (`mistral-ocr-latest`).
- **Einsatz:** Greift bei komplexen Layouts, vergilbten Vorlagen, Frakturschriften oder schlechter Druckqualität, an denen die klassische lokale OCR scheitert.
- **Funktion:** Liefert hochpräzise Transkriptionen und strukturiertes Markdown zur Ergänzung oder Korrektur.

---

### Schritt 5: Sandwich-Assembly (`scripts/assemble_sandwich.py`)
- **Werkzeuge:** OCRmyPDF und `img2pdf`.
- **Generierung:** 
  - Die bereinigte Scan-Bilddatei wird als verlustfreie/optimierte Bildebene eingebettet.
  - Die erkannten Zeichen werden als unsichtbare Vektor-Textebene exakt an den geometrischen Koordinaten der Scan-Wörter hinterlegt.
- **Ergebnis:** Standardkonformes PDF/A, durchsuchbar in jedem PDF-Viewer.

---

## 4. Die Korrekturverfahren (Double Correction Paths)

AlexandriaSandwich implementiert zwei getrennte Korrekturmechanismen für unterschiedliche Szenarien:

| Kriterium | Pfad A (Pre-PDF) | Pfad B (Post-PDF) |
|---|---|---|
| **Eingriffspunkt** | Vor der PDF-Erstellung (auf hOCR-Ebene) | Direkt im fertigen Sandwich-PDF |
| **Werkzeug** | `scripts/hocr_correct.py` | `scripts/pdf_text_correct.py` |
| **Mechanismus** | Patching von XML/hOCR-Tokens anhand von Wort-IDs | Modifikation von PDF-Content-Streams (`TJ`-Operatoren, UTF-16BE) |
| **Bildintegrität** | Unberührt | 100 % unberührt (kein Re-Encoding des Bildes) |
| **Anwendungsfall** | Batch-Korrekturen vor Endmontage; automatisierte Textbereinigung | Nachträgliche redaktionelle Korrektur einzelner Wörter im Archiv |

### Pfad A: Pre-PDF Korrektur
1. Wörter mit Konfidenz unterhalb eines Schwellenwerts werden per CLI extrahiert:
   `python3 scripts/hocr_correct.py dump seite.hocr --max-conf 90 -o words.json`
2. Eine Korrekturdatei (`corrections.json`) definiert Ersetzungen per Wort-ID oder Volltext-Muster.
3. Die Korrekturen werden in eine neue `seite.corrected.hocr` eingebacken.

### Pfad B: Post-PDF Textebenen-Korrektur
1. Im fertigen Sandwich-PDF liegt der Text in Form-XObjects unter Verwendung von `GlyphLessFont` / `Identity-H` als UTF-16BE hex-kodierte Strings vor:
   Beispiel: `[ <0041006C...> ] TJ`
2. `pdf_text_correct.py` parst diese Ströme und ersetzt gezielt fehlerhafte Zeichenketten direkt im Binärstrom, ohne die Geometrie oder das darunterliegende Bild anzutasten.
3. Die Originaldatei bleibt als unverändertes Master-Exemplar erhalten; die Korrektur erzeugt eine neue `.pathb.pdf`.

---

## 5. Benutzeroberfläche & Visuelle Verifikation (`alexandria_ui`)

Zur Steuerung und manuellen Qualitätskontrolle dient die Weboberfläche auf `alex.local:8080`:
- **Dashboard:** Anzeige aller aktiven und abgeschlossenen Verarbeitungsjobs.
- **Upload & Trigger:** Direkter Datei-Upload und Anstoßen der n8n-Pipeline.
- **Visueller Pfad-B-Editor:** Direkte Nebeneinander-Darstellung von Originalscan und editierbarer OCR-Textebene im Browser. Änderungen werden serverseitig über Pfad B direkt in die PDF-Textebene geschrieben.

---

## 6. Zusammenfassung der Kernvorteile

- **100 % Bildtreue:** Das Originaldokument wird visuell niemals verändert oder degradiert.
- **Kostenkontrolle:** Lokale OCR übernimmt das Gros der Seiten; externe API-Aufrufe erfolgen ausschließlich bei Bedarf.
- **Chirurgische Korrigierbarkeit:** Durch Pfad B können typische OCR-Fehler korrigiert werden, ohne dass die gesamte Pipeline oder das PDF neu gerechnet werden müssen.
