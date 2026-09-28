# Zielformat-Architektur & Duale Reproduktion

## 1. Die Zielstruktur: Die 4-Ebenen-Pyramide

In der wissenschaftlichen Digitalisierung und Editionsphilologie kann kein einzelnes Dateiformat alle praktischen Anforderungen gleichzeitig erfüllen:
- **Faksimiles** sind unverzichtbar für Zitate und Nachweise, aber unbrauchbar auf E-Readern (kein Textfluss).
- **Fließtext** ist ideal für Mobilgeräte und KI, verliert aber das historische Satzbild.
- **XML** garantiert 50+ Jahre Archivsicherheit, ist aber für Menschen schwer lesbar.

AlexandriaSandwich löst dieses Problem durch eine **4-Ebenen-Architektur**, in der jedes Buch in einen festen Satz komplementärer Formate überführt wird:

```text
              ┌───────────────────────────────────────┐
              │ 1. Rezeptionsschicht (Endnutzer)      │
              │    • EPUB 3 (Reflowable E-Reader)     │
              │    • Digital-PDF (Typst Vektor-Neusatz│
              └───────────────────▲───────────────────┘
                                  │ Kompilierung
              ┌───────────────────┴───────────────────┐
              │ 2. Arbeits- & KI-Ebene                │
              │    • book.md (UTF-8 Plain Markdown)   │
              └───────────────────▲───────────────────┘
                                  │ Konsolidierung
              ┌───────────────────┴───────────────────┐
              │ 3. Semantische & Archiv-Ebene         │
              │    • book.json (Single Source of Truth│
              │    • tei.xml   (TEI-P5 Akademie-Norm) │
              └───────────────────▲───────────────────┘
                                  │ OCR & Token-Alignment
              ┌───────────────────┴───────────────────┐
              │ 4. Faksimile- & Beweisebene           │
              │    • <id>.sandwich.pdf (Scan + Layer) │
              │    • <id>.pathb.pdf    (Mistral-Clean)│
              └───────────────────────────────────────┘
```

---

## 2. Die einzelnen Zielformate im Detail

### 1. Faksimile-Ebene: Sandwich-PDF (`*.sandwich.pdf` / `*.pathb.pdf`)
* **Funktion:** Originaltreues, zitierfähiges Dokumentenarchiv.
* **Aufbau:** 
  * Oben: Unverändertes 300-DPI-Scanbild (Faksimile) mit historischem Bleisatzbild, Marginalien, Vergilbung und Original-Typographie.
  * Unten: Unsichtbarer Vektor-Textlayer mit pixelgenauen Bounding-Box-Koordinaten für jedes Wort.
* **Weg B (Mistral Token Alignment):** Der unsichtbare Textlayer wird mit der semantischen Erkennung von Mistral OCR synchronisiert. Erkennungsfehler und Rausch-Halluzinationen (z. B. auf gepunkteten Leitlinien) werden bereinigt, während die exakten Pixel-Koordinaten des Originaldrucks erhalten bleiben.

### 2. Maschinenlesbare "Single Source of Truth": `book.json` (AST)
* **Funktion:** Zentrales, softwareunabhängiges Zwischenformat.
* **Aufbau:** Hierarchischer Abstract Syntax Tree (AST), der Metadaten, Seiten, Absätze, Überschriften, Token-Listen, Konfidenzen und Bounding-Boxes (`[ymin, xmin, ymax, xmax]`) vereint.
* **Bedeutung:** Aus dieser Datei kann jederzeit per Skript jedes neue Zielformat (HTML, EPUB, Typst, LaTeX, SQL-Datenbanken) ohne erneuten OCR-Lauf erzeugt werden.

### 3. Philologischer Akademie-Standard: `tei.xml` (TEI-P5)
* **Funktion:** Globale Langzeitarchivierung (50+ Jahre) und Schnittstelle zu Bibliotheken und Digital-Humanities-Repositorien (DTA, SARIT, Perseus).
* **Aufbau:** Streng valides TEI-P5 XML mit `<teiHeader>`, Faksimile-Verknüpfung (`<surface>`, `<zone>`) und semantischem Textkörper (`<body>`, `<div n="..." type="...">`, `<p>`, `<table>`).

### 4. Text- & KI-Ebene: `book.md` (UTF-8 Markdown)
* **Funktion:** Unmittelbare Bearbeitung, Versionskontrolle und Sprachmodell-Verarbeitung.
* **Aufbau:** Reines UTF-8 Markdown ohne proprietären Ballast.
* **Einsatz:** 
  * Direkte Versionierung in Git mit zeilenweisen Diffs (`git diff`).
  * Optimale Eingabe für Retrieval-Augmented Generation (RAG), Vektor-Datenbanken und Volltext-Suchwerkzeuge (`grep`).

### 5. Rezeptions- & Lese-Ebene: `*.epub` (EPUB 3) & `*.digital.pdf`
* **Funktion:** Optimale Rezeption durch den Menschen auf modernen Lesegeräten.
* **EPUB 3:** Dynamischer Textfluss (Reflow) für E-Reader (Tolino, Kindle, Kobo, iPad) mit eingebetteten Unicode-Schriften für Devanagari (*Noto Serif Devanagari*) und IAST-Transliteration (*Linux Libertine* / *Charis SIL*).
* **Digital-PDF (Typst):** Gestochen scharf gerenderter Vektor-Neusatz für hochwertigen Druck.

---

## 3. Die Dualität: Original reproduzieren vs. Neu layouten

Durch die strikte Trennung von Bilddaten, geometrischen Koordinaten und semantischem Text ermöglicht die Pipeline zwei gegensätzliche Publikationsstrategien:

```text
                        ┌──────────────────┐
                        │ Rohscan / Quelle │
                        └────────┬─────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
     [ STRATEGIE 1: REPRODUKTION ]    [ STRATEGIE 2: NEULAYOUT ]
     • Pixelgenaues Sandwich-PDF      • Reflowable EPUB 3
     • Vektor-Nachsatz via bbox       • Responsive HTML / Web
     • Erhalt historischer Typen      • Großformatiges Arbeitsbuch (Typst)
     • Zitate nach Original-Seiten    • Variable Schriftgrößen / Dark Mode
```

### Strategie 1: Reproduktion des Originallayouts

1. **Als Faksimile (`*.pathb.pdf`):**
   * Das historische Druckbild bleibt 1:1 sichtbar. Zeilenumbrüche, Trennstriche, Schriftsetzerfehler, Ligaturen und Fußnotenpositionen bleiben identisch zum Originalexemplar der Bibliothek.
2. **Als geometrischer Vektor-Nachsatz:**
   * Da in `book.json` für jedes Wort und jede Zeile die geometrische Position (`bbox`), Zeilenabstände und Schriftgrößen hinterlegt sind, kann das Original-Layout mathematisch exakt mit modernen Vektorschriften neu gesetzt werden (identischer Satzspiegel, aber ohne Scan-Körnigkeit).

### Strategie 2: Völliges Neulayouten des Inhalts

1. **Fließendes E-Reader-Buch (EPUB 3):**
   * Der semantische Text fließt frei. Auf kleinen Bildschirmen passt sich der Zeilenumbruch an; Schriftart, Kontrast und Zeilenhöhe werden vom Leser bestimmt.
2. **Neues Print-Format (z. B. Studien-Arbeitsbuch via Typst):**
   * Aus dem konsolidierten Text (`book.json` / `book.md`) wird auf Knopfdruck ein neues Werk generiert:
     * Formatwechsel (z. B. von historischem Klein-Oktav zu DIN A4).
     * Großzügiger Korrekturrand für studentische Notizen.
     * Moderne Typographie (z. B. *EB Garamond* + *Noto Serif Devanagari*).
     * Parallele Synopsen (Originaltext links, deutsche Übersetzung rechts).

---

## 4. Standard-Ordnerstruktur pro Buch

Jedes von AlexandriaSandwich verarbeitete Werk erzeugt die folgende einheitliche Ordnerstruktur:

```text
output/books/<buch_id>/
├── <buch_id>.sandwich.pdf   # 1:1 Faksimile + Tesseract Textlayer
├── <buch_id>.pathb.pdf      # Faksimile + Mistral-korrigierter Textlayer (0 Rauschen)
├── <buch_id>.digital.pdf    # Vektor-Neusatz via Typst
├── <buch_id>.epub           # Reflowable eBook mit eingebetteten Schriften
├── <buch_id>.tei.xml        # TEI-P5 Langzeitarchiv-XML
├── book.json                # Vollständiger semantischer Syntaxbaum (AST)
└── book.md                  # Konsolidierter UTF-8 Markdown-Volltext
```
