# Fallstudie & Architektur: Dhātu-Pāṭha (Böhtlingk-Standard)

> **Kanonische Ground-Truth, bilinguale Facing-Page-Alignment-Pipeline und hybride Typst-Vektorneuedition für 2.259 Verbalwurzeln auf 410 Buchseiten.**
> 🔗 **Projekt-Repository:** [github.com/birchville-org/dhatupatha](https://github.com/birchville-org/dhatupatha)  
> 🌐 **Live QA-Viewer:** [birchville-org.github.io/dhatupatha](https://birchville-org.github.io/dhatupatha/)

---

## 1. Ausgangslage & Die Kernfrage

### 1.1 Das Phänomen: „Digitalisiert aber ohne Layout“ vs. „Digitalisiert UND Original-Layout“
Bei der initialen Digitalisierung des *Dhātu-Pāṭha* (Pāṇinīya-Wurzelverzeichnis) trat eine fundamentale Diskrepanz zutage:
* Das Referenzprojekt **Otto von Böhtlingk (1887)** erzeugte ein Ergebnis mit voller Layouttreue und gestochen scharfem Satzbild („digitalisiert UND Original-Layout“).
* Der *Dhātu-Pāṭha* erschien nach einem rein OCR-gestützten Neusatzversuch unstrukturiert: Tabellarische Wurzelspalten brachen auseinander, Bedeutungen flossen in Absätze zusammen („digitalisiert, aber ohne Layout“).

Die Klärung der Ursachen und die Übertragung des *Böhtlingk-Standards* auf den *Dhātu-Pāṭha* führten zu zentralen architektonischen Erkenntnissen für die gesamte AlexandriaSandwich-Pipeline.

### 1.2 Die Struktur des historischen Ausgangswerkes
Das 410-seitige Werk weist eine komplexe zweifache Binnenstruktur auf:
1. **Sektionsstruktur:**
   * **Front Matter (S. 1–25):** Rein einspaltiger Fließtext (Vorwort, grammatische Einführung, Lautgesetze) in zusammenhängenden Absätzen.
   * **Hauptteil (S. 26–285):** Streng zweispaltiges Wörterbuch- und Tabellenlayout der 10 Gaṇas (Wurzelklassen von Bhvādi bis Curādi).
   * **Back Matter (S. 286–410):** Register, Indizes und Anhangstabellen.
2. **Bilinguale Gegenüberstellung (Facing Pages):**
   * **Ungerade Seiten (rechts):** Primärer Sanskrit-Text in Devanāgarī mit traditionellen Aupadeśika-Markern und Lokativ-Bedeutungen (*arthas*).
   * **Gerade Seiten (links):** Gegenüberliegende wissenschaftliche Transliteration (IAST) mit englischer Übersetzung und grammatischen Attributen.

---

## 2. Ursachenanalyse: Warum blindes „Reverse-Layout“ scheitert

Der Versuch, aus rohem OCR-Volltext das Original-Layout mathematisch oder rein regelbasiert Seite für Seite zu rekonstruieren, scheitert an zwei strukturellen Hürden:

```text
[Roher OCR-Datenstrom] ──► Sequentielles Auslesen (1D)
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[Problem 1: Serialisierungsverlust]              [Problem 2: Layout-Zwang]
Zweispaltige Wurzel/Bedeutung-Flucht             Ein globales 2-Spalten-Layout
wird zu flachem 1D-Fließtext reduziert.          zerstört das 1-spaltige Vorwort;
Typst muss Spaltenbrüche raten.                  1-Spalten-Layout zerstört das Lexikon.
```

1. **Serialisierungsverlust:** OCR-Engines (sowohl Tesseract als auch VLM-Modelle) lesen Textblöcke sequentiell aus. Bei mehrspaltigen Wörterbüchern werden Wurzeln und ihre zugehörigen Übersetzungen zeilenweise vermischt oder in falscher Reihenfolge serialisiert.
2. **Globaler Layout-Zwang:** Wird dem Satzgenerator (Typst) ein starres Spaltenmodell verordnet, entsteht entweder im Vorwort unleserlicher Schmalspaltensatz oder im Hauptteil ein unübersichtlicher Fließtext ohne Spaltentrennung.

---

## 3. Die Lösung: Der 4-Säulen-Böhtlingk-Standard

Um maximale visuelle und philologische Treue zu erzielen, trennt AlexandriaSandwich strikt zwischen dem Faksimile-Erhalt und der semantisch geführten Neuedition:

```text
                              ┌──────────────────────┐
                              │  Rohscans / Quelle   │
                              └──────────┬───────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   [ SÄULE 1: FAKSIMILE-GARANTIE ]                [ SÄULE 2: KANONISCHES ALIGNMENT ]
   • 1:1 unveränderte Scan-Pixel                  • Abgleich gegen dhatupatha_canonical.json
   • Unsichtbarer Bbox-Textlayer                  • Bilinguale 10-Gaṇa-Statusmaschine
   • Dhatu-patha.perfect_sandwich.pdf             • 100 % lückenloses dhatupatha_complete.json
                                                                 │
                                                                 ▼
   [ SÄULE 4: HERMETISCHES FONT-DEPLOY ]          [ SÄULE 3: TYPST-VEKTORNEUEDITION ]
   • data/fonts/ (Noto + Libertine)               • S. 1–25:  1-Spalten Fließtext
   • APT fonts-noto-extra auf Linux               • S. 26–285: 2-Spalten-Gitter mit grid.vline
   • Null Tofu-Zeichen (?)                        • Marginal-Konkordanz: [S. 26]
```

### Säule 1: Die Faksimile-Garantie (`*.perfect_sandwich.pdf`)
* Die 410 Originalscans bleiben unverändert und pixelgenau als Bildschicht erhalten.
* Der bereinigte Volltext liegt unsichtbar (PDF Text Rendering Mode 3) exakt auf den Bounding-Boxen der historischen Druckzeilen.
* **Garantie:** 100 % historische Beweiskraft, 0 % Layout-Risiko, vollständige Volltext-Durchsuchbarkeit.

### Säule 2: Kanonische Ground-Truth & Bilinguales Facing-Page-Alignment
Anstatt den unvollkommenen OCR-Text blind zu setzen, wird er über eine zweistufige Pipeline semantisch kuratiert:
1. **Kanonische Referenzdatenbank (`scripts/build_dhatupatha_groundtruth.py`):**
   * Erzeugt `data/dhatupatha_canonical.json` (2.259 Wurzeln über alle 10 Gaṇas).
   * Enthält kanonische Devanāgarī, IAST, Aupadeśika-It-Marker (z. B. `टु`, `डु`, `इर्`), Sanskrit-Bedeutungen im Lokativ (`भू सत्तायाम्`), englische Übersetzungen und Pāṇinīya-Klassifikationen (Svarita-Anudātta, Sakarmaka/Akarmaka, Seṭ/Aniṭ).
2. **Bilinguale Alignment-Engine (`scripts/align_dhatupatha.py`):**
   * Da der Druck gegenüberliegende Seiten nutzt (ungerade Devanāgarī, gerade IAST), gleicht die Statusmaschine die OCR-Erkennung gegen **beide** Schriftsysteme parallel ab.
   * Unleserliche Devanāgarī-Ligaturen werden durch die lateinische Transliteration der Gegenseite verifiziert und umgekehrt.
   * **Ergebnis:** `data/dhatupatha_complete.json` (100 % lückenloser Masterkatalog, vollständig mit den Original-Seitenzahlen verknüpft).

### Säule 3: Sektionsspezifische Layouttreue in Typst (`scripts/build_typeset_edition.py`)
Die Vektorneuedition passt ihr Layout dynamisch an die logischen Abschnitte des Werkes an:
* **Front Matter (S. 1–25):**
  * Einspaltiger, eleganter Fließtext in Standardbreite.
  * Erhalt der originalen Absätze, Paragraphen und Gliederungspunkte.
  * Randnotizen mit Scan-Konkordanz (`[S. 6]`, `[S. 11]`).
* **Hauptteil / Wörterbuch (S. 26–285):**
  * Zweispaltiges Tabellengitter mit vertikaler Trennlinie (`grid.vline`).
  * Zentrierte Gaṇa-Kopfzeilen (z. B. *1. Bhvādigaṇaḥ* / *भ्वादिगणः*).
  * Fette Devanāgarī-Wurzel mit Akzenten, daneben kursive IAST-Umschrift, Lokativ-Bedeutung und englische Übersetzung.
  * Marginalien zur schnellen Orientierung (`[S. 26]`).
* **Lebende Kolumnentitel (Running Headers):**
  * Dynamischer Typst-Header im Code-Modus: Gerade Seiten tragen den Buchtitel; ungerade Seiten zeigen den aktuellen Gaṇa-Namen und die Seitenzahl.

### Säule 4: Cross-Platform Font-Vendoring & Linux-Tofu-Fix
Ein kritischer Befund bei der Portierung von macOS auf Linux-Produktionsserver (`alex.local`, Docker):
* **Das Problem:** Unter macOS renderte Typst fehlerfrei, da macOS Systemschriften für indische Schriften vorhält (`Devanagari MT`, `Kohinoor Devanagari`, `Baskerville`). Im Linux-Worker-Container (Ubuntu 24.04) erschienen jedoch alle Devanāgarī-Zeichen als Fragezeichen in Kästchen (`?`, Tofu).
* **Die Ursache:**
  1. Ubuntu 24.04 enthält im Basispaket `fonts-noto-core` keine indischen Schriftsysteme.
  2. Typst sucht standardmäßig nur in Betriebssystem-Pfaden.
* **Die Lösung:**
  1. **Hermetisches Font-Vendoring:** Ablage der Open-Source-Schriften direkt im Repository unter `data/fonts/`:
     * `NotoSerifDevanagari-Regular.ttf` & `NotoSerifDevanagari-Bold.ttf`
     * `LinLibertine_R.otf`, `LinLibertine_RB.otf`, `LinLibertine_RI.otf`
  2. **Automatischer Font-Pfad:** Übergabe von `--font-path data/fonts` beim Typst-Aufruf.
  3. **Universelle Schriftkaskade:**
     ```typst
     #set text(
       font: ("Linux Libertine O", "Baskerville", "Times New Roman", "Noto Serif Devanagari", "Devanagari MT", "Kohinoor Devanagari", "Noto Sans Devanagari"),
       size: 10pt,
       lang: "de"
     )
     ```
  4. **Systempakete im Worker-Container:** Installation von `fonts-noto-extra` (APT) und `pymupdf` (PIP).

---

## 4. Konfiguration für Headless-Linux-Deployments

Damit der gesamte Workflow auf Linux-Servern (`alex.local`, Synology, Debian/Ubuntu) headless und fehlerfrei durchläuft, sind folgende Einstellungen erforderlich:

### 4.1 Worker Dockerfile (`docker/worker/Dockerfile`)
```dockerfile
# Systemschriften inklusive indischer Schriftsysteme
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-linuxlibertine \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python-Bibliotheken für Bounding-Box-Audits & Typst-Orchestrierung
RUN pip install --no-cache-dir \
    pymupdf \
    pikepdf \
    lxml
```

### 4.2 Docker Compose Volume-Mounts (`deploy/docker-compose.alex.yml`)
Das Verzeichnis `data/` muss dem Container zugänglich sein, damit Schriften und Ground-Truth-Dateien ohne Rebuild verfügbar sind:
```yaml
volumes:
  - /data/input:/data/input
  - /data/processing:/data/processing
  - /data/output:/data/output
  - /opt/alexandria/scripts:/opt/alexandria/scripts:ro
  - /opt/alexandria/templates:/opt/alexandria/templates:ro
  - /opt/alexandria/data:/opt/alexandria/data:ro
```

### 4.3 Pipeline-Automatisierung (`scripts/run_pipeline.sh`)
Das Orchestrierungs-Skript erkennt vorhandene kanonische Ausrichtungsdaten automatisch:
```bash
if [ -f "data/dhatupatha_complete.json" ]; then
    echo "==> Generiere typografische Vektor-Neuedition via Typst..."
    python3 scripts/build_typeset_edition.py \
        --input data/dhatupatha_complete.json \
        --output data/output/pdf/Dhatu-patha.typeset_edition.pdf
fi
```

---

## 5. Validierung & Ergebnisse

| Eigenschaft | Roher OCR-Neusatz (initial) | AlexandriaSandwich Böhtlingk-Standard |
| :--- | :--- | :--- |
| **Faksimile-Ebene** | Fehlend oder ungenau | **100 % 1:1 Scan-Faksimile** (`*.perfect_sandwich.pdf`) |
| **Layout Front Matter** | Fälschlich 2-spaltig gequetscht | **1-spaltiger eleganter Fließtext** mit Scan-Referenzen |
| **Layout Wörterbuch** | 1-spaltig vermischt | **2-spaltiges Gitter** mit `grid.vline` & Gaṇa-Hierarchie |
| **Wurzelbestand** | ~1.850 Fragmente mit OCR-Fehlern | **2.259 Wurzeln (100 % lückenlos)** |
| **Devanāgarī-Rendering** | Tofu-Fragezeichen (`?`) auf Linux | **100 % saubere Vektorglyphen** (Noto Serif Devanagari) |
| **Kompilierungszeit** | Mehrere Minuten | **~2,4 Sekunden** für 229 Seiten (Typst 0.11.1) |
| **Dateigröße Neusatz** | Unbereinigt | **2,96 MB Vektor-PDF** (durchsuchbar, gestochen scharf) |
| **Zitierfähigkeit** | Seitenbezug ging verloren | **Marginal-Konkordanz `[S. XX]`** auf jeder Seite |

---

## 6. Zusammenfassendes Fazit

Die Qualität des Endprodukts entsteht nicht durch den Versuch, ein gedrucktes Layout aus unstrukturiertem OCR-Text „rückwärts zu erraten“ (*Reverse-Layout*), sondern durch das Zusammenspiel zweier autarker Pfade:
1. Das **Sandwich-PDF** archiviert und schützt das historische Originalbild mit absoluter 1:1-Treue.
2. Die **Typst-Neuedition** baut auf einer kanonisch verifizierten Datenbasis auf und wendet professionelle typografische Regeln sektionsspezifisch an.
