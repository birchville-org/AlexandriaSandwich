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
              │    • <id>.aligned.pdf  (KI-synchron)  │
              └───────────────────────────────────────┘
```

---

## 2. Die einzelnen Zielformate im Detail

### 1. Faksimile-Ebene: Sandwich-PDF (`*.sandwich.pdf` / `*.aligned.pdf`)
* **Funktion:** Originaltreues, zitierfähiges Dokumentenarchiv.
* **Aufbau:** 
  * Oben: Unverändertes 300-DPI-Scanbild (Faksimile) mit historischem Bleisatzbild, Marginalien, Vergilbung und Original-Typographie.
  * Unten: Unsichtbarer Vektor-Textlayer mit pixelgenauen Bounding-Box-Koordinaten für jedes Wort.
* **Post-Assembly Textlayer-Korrektur (KI-Synchronisation):** Der unsichtbare Textlayer wird mit der semantischen Erkennung von Mistral OCR synchronisiert. Erkennungsfehler und Rausch-Halluzinationen (z. B. auf gepunkteten Leitlinien) werden bereinigt, während die exakten Pixel-Koordinaten des Originaldrucks erhalten bleiben (`*.aligned.pdf`).

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

1. **Als KI-synchronisiertes Faksimile (`*.aligned.pdf`):**
   * Das historische Druckbild bleibt 1:1 sichtbar. Zeilenumbrüche, Trennstriche, Schriftsetzerfehler, Ligaturen und Fußnotenpositionen bleiben identisch zum Originalexemplar der Bibliothek.
2. **Als geometrischer Vektor-Nachsatz:**
   * Da in `book.json` für jedes Wort und jede Zeile die geometrische Position (`bbox`), Zeilenabstände und Schriftgrößen hinterlegt sind, kann das Original-Layout mathematisch exakt mit modernen Vektorschriften neu gesetzt werden (identischer Satzspiegel, aber ohne Scan-Körnigkeit).

### Strategie 2: Völliges Neulayouten des Inhalts

1. **Fließendes E-Reader-Buch (EPUB 3):**
   * Der semantische Text fließt frei. Auf kleinen Bildschirmen passt sich der Zeilenumbruch an; Schriftart, Kontrast und Zeilenhöhe werden vom Leser bestimmt.
2. **Neues Print-Format (z. B. Studien-Arbeitsbuch via Typst):**
   * Aus dem konsolidierten Text (`book.json` / `book.md`) wird auf Knopfdruck ein neues Werk generiert:
     * Formatwechsel (z. B. von historischem Klein-Oktav zu DIN A4 oder ISO-B5).
     * Großzügiger Korrekturrand für studentische Notizen.
     * Moderne Typographie (z. B. *Linux Libertine O* + *Noto Serif Devanagari*).
     * Parallele Synopsen (Originaltext links, deutsche Übersetzung rechts).

---

## 4. Semantischer Neusatz vs. Reverse-Layout-Rekonstruktion (Das Böhtlingk- & Dhātupāṭha-Modell)

Aus den praktischen Fallstudien (*Böhtlingk 1887* und *Dhātu-Pāṭha*) leitet sich eine zentrale editionsphilologische Erkenntnis für die AlexandriaSandwich-Architektur ab:

### 4.1 Warum blindes "Reverse-Layout" scheitert
Versucht eine Pipeline, aus rohem, unstrukturiertem OCR-Fließtext das visuelle Seitenbild eines komplexen Werkes krampfhaft Seite für Seite geometrisch nachzubauen, scheitert der typografische Vektorneusatz:
* **Serialisierungsverlust:** Eine OCR-Engine liest mehrspaltige Tabellenwerke (z. B. Wurzelspalte links, Bedeutungsspalte rechts) sequentiell aus. Die 2D-Tabellenflucht wird zu einem flachen 1D-Fließtext reduziert.
* **Layout-Raten:** Typst muss ohne semantisches Modell raten, wo Spalten brechen, wodurch optische Unwuchten, asymmetrische Satzspiegel oder Zeilenüberläufe entstehen („digitalisiert, aber ohne Layout“).

### 4.2 Die Lösung: Die 3 Säulen der Dual-Path-Architektur

1. **Pfad 1: Die Faksimile-Garantie (`*.perfect_sandwich.pdf`)**
   * Das hochauflösende Originalscanbild bleibt zu 100 % erhalten.
   * Der OCR-Text wird unsichtbar an exakten Bounding-Box-Koordinaten als Suchlayer projiziert (PDF Text Rendering Mode 3).
   * **Garantie:** 100 % Original-Layout, 0 % Layout-Risiko, absolute historische Zitierfähigkeit.

2. **Pfad 2: Kanonisches Ground-Truth-Alignment (`scripts/align_*.py`)**
   * Anstatt den Scan blind geometrisch nachzuahmen, wird der OCR-Text per Fuzzy Matching (`difflib.SequenceMatcher`) gegen eine maschinenlesbare Referenzdatenbank (z. B. 3.997 Sūtras in `sutras.json` oder 2.259 Wurzeln in `dhatupatha_canonical.json`) abgeglichen.
   * OCR-Fehler bei komplexen Ligaturen werden automatisch repariert und der Text in eine strukturierte Master-JSON (`dhatupatha_complete.json`) überführt.

3. **Layout-Treue zum Original durch sektionsspezifische Typografie**
   * Kein starres globales 2-Spalten-Zwangskorsett über das gesamte Buch:
     * **Front Matter (Vorwort, Einleitung):** Einspaltiger, eleganter Fließtext mit Originalabsätzen und Randverweisen auf die Originalscans (`[S. 6]`).
     * **Hauptteil (Wörterbuch/Tabellen):** Zweispaltiger Satz mit vertikalem Trennstrich (`grid.vline`) und zentrierten Kolophonen.
     * **Back Matter (Register/Anhänge):** Strukturgetreue Darstellung der historischen Verzeichnisse.

---

## 5. Standard-Ordnerstruktur pro Buch

Jedes von AlexandriaSandwich verarbeitete Werk erzeugt die folgende einheitliche Ordnerstruktur:

```text
output/books/<buch_id>/
├── <buch_id>.sandwich.pdf          # 1:1 Faksimile + Tesseract Textlayer
├── <buch_id>.perfect_sandwich.pdf  # Restauriertes Faksimile + optimierter Mistral-Textlayer
├── <buch_id>.typeset_edition.pdf   # Semantische Vektor-Neuedition via Typst (Böhtlingk-Standard)
├── <buch_id>.digital.pdf           # 1:1 Page-Concordance Digital-PDF
├── <buch_id>.epub                  # Reflowable eBook mit eingebetteten Schriften
├── <buch_id>.tei.xml               # TEI-P5 Langzeitarchiv-XML
├── book.json                       # Vollständiger semantischer Syntaxbaum (AST)
└── book.md                         # Konsolidierter UTF-8 Markdown-Volltext
```
