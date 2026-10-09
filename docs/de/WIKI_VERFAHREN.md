# Verfahrensdokumentation: AlexandriaSandwich

## 1. Zielsetzung & Kernkonzept

Das Verfahren von **AlexandriaSandwich** dient der vollautomatischen, qualitätsgesicherten Digitalisierung von Büchern und Dokumenten zu archivfesten **1:1 Sandwich-PDFs**. 

Ein Sandwich-PDF besteht aus zwei exakt deckungsgleichen Ebenen:
1. **Visuelle Bildebene (oben):** Das originale, bereinigte Scanbild bleibt 1:1 und pixelgenau erhalten. Es findet kein Neusatz und keine visuelle Textersetzung statt.
2. **Unsichtbare Textebene (unten):** Eine unsichtbare Vektorschrift-Ebene (GlyphLessFont) mit präzisen Positionskoordinaten ermöglicht Volltextsuche, Textmarkierung sowie Copy & Paste.

Zur Optimierung von Betriebskosten, Datenschutz und Verarbeitungsgeschwindigkeit folgt das System einem **Local-First-Ansatz mit KI-Fallback**: Standardseiten werden lokal und ressourceneffizient verarbeitet; nur bei schlechter Erkennungsqualität wird eine externe KI-Schnittstelle hinzugezogen.

---

## 2. Systemarchitektur & Topologie

Der Prozess ist auf spezialisierte Knoten im Birchville-Netzwerk verteilt:

```text
┌─────────────────────────────────────────────────────────────┐
│ Dev Node (Mac mini M2: hermes.local)                        │
│ • Entwicklung & Multi-Arch Docker Builds (ARM64 / AMD64)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Git / Rsync
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage & Web Portal (Synology NAS: synology.local)          │
│ • alexandria_ui      (FastAPI Dashboard, Textlayer-Editor)  │
│ • Traefik Reverse-Proxy + Authelia 2FA SSO (alex.birchville)│
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
│ • alexandria_n8n     (Workflow-Orchestrierung & Webhooks)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Optionale lokale Vision-Inferenz
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ GPU Node (Lokaler VLM-Server: nyx.local:8088)               │
│ • Qwen2.5-VL Vision-Language OCR (100% lokal, 0,00 $ Cloud) │
└─────────────────────────────────────────────────────────────┘
```

### Rollen & API-Key-Zuständigkeit

| Host | Dienste | Mistral API Key? | Rolle / Begründung |
| :--- | :--- | :---: | :--- |
| **`alex.local`** | `alexandria_worker`, `n8n` | **Ja (Pflicht)** | Führt die Pipeline und Cloud-OCR-Aufrufe aus (`MISTRAL_API_KEY` in `/opt/alexandria/.env`). |
| **`synology.local`** | `alexandria_ui`, Traefik, Authelia | **Ja (Monitoring)**| Prüft die API-Erreichbarkeit gegen `api.mistral.ai` und aggregiert Job-Kosten. |
| **`nyx.local`** | `nyx.local:8088` (Qwen2.5-VL) | **Nein** | 100 % lokale GPU-Inferenz ohne Cloud-Abhängigkeiten. |

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
  - Mittlere Konfidenz >= Schwelle: Seite gilt als `PASS` (kostenfreie lokale Tesseract-Verarbeitung).
  - Mittlere Konfidenz < Schwelle: Quality Gate schlägt an (`FAIL`); die Seite wird an Mistral Document AI übergeben.
- **Entscheidungshilfe zur Schwellwert-Wahl:**
  - **100 % (Empfohlen für wissenschaftliche Editionen):** Maximale semantische Wiedergabetreue für Typst-Neusatz & EPUB 3. Eliminiert Tesseract-Fehlerfragmente vollständig (Kosten: 0,004 $ pro Seite, ca. 1,00 $ pro 250 Seiten).
  - **85 % (Standard für moderne Drucke ab 1950):** Tesseract verarbeitet saubere Seiten lokal und kostenlos; Mistral wird nur für Ausreißer oder Tabellen gerufen (spart bis zu 90 % der API-Kosten).
  - **85 % oder tiefer (Massendigitalisierung 100.000+ Seiten):** Signifikanter Kostenhebel (400 $ statt 4.000 $ pro 100k Seiten) und Vermeidung von Cloud-Rate-Limits.
  - **`--no-mistral` (Sensible Akten & Air-Gap):** 100 % offline, volle Datenhoheit und DSGVO-Konformität auf dem lokalen Server.

#### Sprachprofile & Bounding-Box-Geometrie

AlexandriaSandwich trennt strikt zwischen **Geometrie** (visuelle Positionierung im Faksimile) und **Semantik** (Zeichenbedeutung im Volltext):

| Profil (`--lang`) | Sprachkombination | Typischer Anwendungsbereich |
| :--- | :--- | :--- |
| **`eng+san`** | Englisch + Sanskrit Devanagari | Englische Indologie, Lexika, Grammatiken (z. B. George Cardona 1976 *Panini*) |
| **`deu+san`** | Deutsch + Sanskrit Devanagari | Historische deutsche Indologie (z. B. Otto Böhtlingk 1887 *Sanskrit-Chrestomathie*) |
| **`deu+eng+san`** | Trilingual | Kritische Editionen mit englischen Texten, deutschen Scholien & Devanagari |
| **`deu+eng`** | Deutsch + Englisch | Standard für westliche Antiqua- und Frakturbestände |
| **`san`** | Reines Sanskrit Devanagari | Reine Sanskrit-Originale, Manuskripte, Anthologien |

> **Warum die Sprachwahl auch bei 100 % Mistral AI entscheidend ist:**  
> Mistral AI ist für den Volltext (Typst-Neusatz, EPUB 3, TEI XML) sprachagnostisch. Das 1:1 Sandwich-PDF & KI-synchronisierte Faksimile benötigen jedoch pixelgenaue Wort-Bounding-Boxes von Tesseract (`ocrmypdf`). Fehlt `san`, kann Tesseract Devanagari nicht segmentieren: Im Sandwich-PDF sind die Sanskrit-Zitate dann weder durchsuchbar noch markierbar.

---

### Schritt 4: Bedingter KI-Fallback & Vision-Language-Modelle (`scripts/mistral_ocr.py`, `scripts/qwen_ocr.py`)
- **Engine A (Cloud-API):** Mistral OCR API (`mistral-ocr-latest`) greift bei komplexen Layouts, vergilbten Vorlagen, Frakturschriften oder polyglotten Drucken (z. B. historische indische Schriften) mit minimaler Latenz und höchster Ligatur-Treue.
- **Engine B (Offline / Air-Gap):** Qwen2.5-VL ([scripts/qwen_ocr.py](file:///Volumes/SanDisk1TB/proj/AlexandriaSandwich/scripts/qwen_ocr.py)) ermöglicht die vollständige lokale Verarbeitung auf eigener Hardware (z. B. MLX auf Apple Silicon) ohne Datenabfluss oder API-Kosten (99,96 % Textübereinstimmung bei lateinischen Schriftsätzen).
- **Benchmark & Modellvergleich:** Über [scripts/benchmark_ocr.py](file:///Volumes/SanDisk1TB/proj/AlexandriaSandwich/scripts/benchmark_ocr.py) können beide Engines direkt auf Testseiten verglichen und Side-by-Side-HTML-Diffs erzeugt werden. Detaillierte Kennzahlen siehe [Fallstudie Böhtlingk 1887](case-study.md#schritt-21-lokale-vlm-alternative-modell-benchmark-mistral-ocr-vs-qwen25-vl).

---

### Schritt 5: Sandwich-Assembly (`scripts/assemble_sandwich.py`)
- **Werkzeuge:** OCRmyPDF und `img2pdf`.
- **Generierung:** 
  - Die bereinigte Scan-Bilddatei wird als verlustfreie/optimierte Bildebene eingebettet.
  - Die erkannten Zeichen werden als unsichtbare Vektor-Textebene exakt an den geometrischen Koordinaten der Scan-Wörter hinterlegt.
- **Ergebnis:** Standardkonformes PDF/A, durchsuchbar in jedem PDF-Viewer.

---

## 4. Die Korrekturverfahren (Pre-Assembly vs. Post-Assembly)

AlexandriaSandwich implementiert zwei getrennte Korrekturmechanismen für unterschiedliche Szenarien:

| Kriterium | Pre-Assembly hOCR-Korrektur | Post-Assembly Textlayer-Korrektur |
|---|---|---|
| **Eingriffspunkt** | Vor der PDF-Erstellung (auf hOCR-Ebene) | Direkt im fertigen Sandwich-PDF |
| **Werkzeug** | `scripts/hocr_correct.py` | `scripts/pdf_text_correct.py`, `align_mistral_pdf.py` |
| **Mechanismus** | Patching von XML/hOCR-Tokens anhand von Wort-IDs | Modifikation von PDF-Content-Streams (`TJ`-Operatoren, UTF-16BE) |
| **Bildintegrität** | Unberührt | 100 % unberührt (kein Re-Encoding des Bildes) |
| **Anwendungsfall** | Batch-Korrekturen vor Endmontage; automatisierte Textbereinigung | Nachträgliche redaktionelle Korrektur oder KI-Synchronisation (`.aligned.pdf`) |

### Pre-Assembly hOCR-Korrektur
1. Wörter mit Konfidenz unterhalb eines Schwellenwerts werden per CLI extrahiert:
   `python3 scripts/hocr_correct.py dump seite.hocr --max-conf 90 -o words.json`
2. Eine Korrekturdatei (`corrections.json`) definiert Ersetzungen per Wort-ID oder Volltext-Muster.
3. Die Korrekturen werden in eine neue `seite.corrected.hocr` eingebacken.

### Post-Assembly Textlayer-Korrektur
1. Im fertigen Sandwich-PDF liegt der Text in Form-XObjects unter Verwendung von `GlyphLessFont` / `Identity-H` als UTF-16BE hex-kodierte Strings vor:
   Beispiel: `[ <0041006C...> ] TJ`
2. `pdf_text_correct.py` parst diese Ströme und ersetzt gezielt fehlerhafte Zeichenketten direkt im Binärstrom, ohne die Geometrie oder das darunterliegende Bild anzutasten.
3. Die Originaldatei bleibt als unverändertes Master-Exemplar erhalten; die Korrektur erzeugt eine neue `.aligned.pdf`.

---

## 5. Benutzeroberfläche & Visuelle Verifikation (`alexandria_ui`)

Zur Steuerung und manuellen Qualitätskontrolle dient die Weboberfläche auf `alex.local:8080`:
- **Dashboard:** Anzeige aller aktiven und abgeschlossenen Verarbeitungsjobs.
- **Upload & Trigger:** Direkter Datei-Upload und Anstoßen der n8n-Pipeline.
- **Visueller Textlayer-Editor:** Direkte Nebeneinander-Darstellung von Originalscan und editierbarer OCR-Textebene im Browser. Änderungen werden serverseitig direkt in die PDF-Textebene geschrieben (`.aligned.pdf`).

---

## 6. Zusammenfassung der Kernvorteile

- **100 % Bildtreue:** Das Originaldokument wird visuell niemals verändert oder degradiert.
- **Kostenkontrolle:** Lokale OCR übernimmt das Gros der Seiten; externe API-Aufrufe erfolgen ausschließlich bei Bedarf.
- **Chirurgische Korrigierbarkeit:** Durch Pfad B können typische OCR-Fehler korrigiert werden, ohne dass die gesamte Pipeline oder das PDF neu gerechnet werden müssen.

---

## 7. Referenzprojekte & Fallstudien

* **[Pāṇinis Grammatik (Otto von Böhtlingk, 1887)](case-study.md):**
  Vollständige Digitalisierung und kanonische Textschichtung von 3.997 Sūtras auf 478 Buchseiten historischer Mehrschriftigkeit (Devanāgarī, Fraktur/Antiqua, IAST) mit autarkem QA-Viewer.

