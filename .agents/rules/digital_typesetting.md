# Digitaler Neusatz: Standard & Quality-Gate (AlexandriaSandwich)

Gilt verbindlich für jeden digitalen Neusatz, Nachsatz oder seitenkonkordanten typografischen Neuaufbau eines gescannten Buches in diesem Projekt.

## 1. Verbindlicher 6-Stufen-Workflow

Sobald ein digitaler Neusatz angefordert wird, MUSS die Umsetzung zwingend in folgenden 6 Phasen erfolgen:

### Phase 1: OCR & Stil-Extraktion (Textgrundlage)
1. Vollständige OCR-Transkription (Mistral OCR `mistral-ocr-latest`).
2. Vision-basierte Extraktion typografischer Auszeichnungen (`scripts/extract_italics_pixtral.py`): Buchtitel, arabische/hebräische Transliterationen, fremdsprachliche Termini und Zitate in Kursivschrift erfassen.
3. Bereinigung von Trennstrichen am Zeilenende: Scan-Trennstriche (z. B. `Contro-\nversy` -> `Controversy`, `masoret-\nskou` -> `masoretskou`) zwingend auflösen, um die digitale Durchsuchbarkeit und nachgelagerte Übersetzung nicht zu beschädigen.
4. Generierung des **Master-Markdown** (`Alexandros_Tschechisch.md`) mit Seitenankern (`<!-- PAGE N -->`), bereinigten Absätzen, Fußnoten und Markdown-Kursive (`*...*`).

### Phase 2: Automatisches Layout-Profiling (`scripts/profile_scan_layout.py`)
Vor dem Schreiben des Typst-Codes MUSS das Originallayout über Stichproben-Seiten vermessen werden:
- Satzspiegel: Margins links, rechts, oben, unten in pt.
- Kopfzeile: Grundlinie y, Zentrierung vs. Außenbündigkeit.
- Fußzeile / Seitenzahl: Exakte Grundlinie y, Abstand zur Unterkante (`footer-descent`).
- Fußnoten-Anatomie:
  - Abstand Fließtext -> Haarlinie (14 pt).
  - Haarlinien-Länge (25 %) und Stärke (0.4 pt).
  - Haarlinie -> erste Fußnote (4 pt, Typst-Kompensation `#v(-7pt)`).
  - Ziffernspalte (8.5 pt) und hängender Einzug (8.5 pt).
  - Kein Doppel-Superscript: Unicode-Ziffern vor `#super` normalisieren (`translate`).
- Generiert `layout_profile.json` als Referenz.

### Phase 3: Typst-Satz (Seitentreue 1:1)
- Engine: Typst mit Schriftart `STIX Two Text` (vollständige Unterstützung für Tschechisch, IAST, Devanāgarī, Arabisch, Hebräisch).
- Fließtext: Blocksatz (`justify: true`), 12pt Absatzeinzug (unterdrückt bei Folgeabschnitten nach Titeln und Seitenfortsetzungen).
- Fußnoten: Bündig untereinander (`hanging-indent: 8.5pt`, `box(width: 8.5pt)`), kompakter Abstand (`spacing: 4.5pt`, `leading: 0.46em`).
- Strikte 1:1-Seitenparität: Jede Buchseite entspricht exakt einer PDF-Seite.

### Phase 4: Automatisierter Pre-Flight-Check (`scripts/verify_typographic_diff.py`)
Vor der Übergabe an den Benutzer MUSS der Verifier auf Testseiten (mind. 5 Seiten) ausgeführt werden:
1. **Toleranzen**:
   - Grundlinie der Seitenzahl: |Δy| <= 1.5 pt.
   - Grundlinie der Haarlinie: |Δy| <= 3.0 pt.
   - Fußnotenziffer-Skalierung: >= 60 % der Versalhöhe (kein Doppel-Superscript).
2. **Rot/Cyan-Diff-Overlay**: Generierung von Anaglyphen-Bildern (`diff_overlay_page_*.png`) zur Prüfung auf Farbränder.

### Phase 5: PDF-Metadaten & Synchronisation
1. Native PDF-Seitenzahlen über PyMuPDF (`set_page_labels`) auf die Buchseitennummern (z. B. 11..64) setzen.
2. Vollständiges Inhaltsverzeichnis (TOC / Bookmarks) im PDF hinterlegen.
3. Bereitstellung sowohl lokal (`data/output/...`) als auch im konfigurierten Cloud-Exportverzeichnis (`~/pCloud Drive/...` bzw. `$ALEXANDRIA_PCLOUD_DIR`).

### Phase 6: Multi-Format Artefakt-Export (Canonical AST & TEI-P5 XML)
1. **Canonical Book AST (`book.json`)**: Konsolidierung via `scripts/consolidate_book.py` mit de-hyphenated Fließtextblöcken, Bounding-Boxes und Metadaten.
2. **Standardisiertes TEI-P5 XML (`<job>.tei.xml`)**: Export via `scripts/export_tei.py` mit vollständigem `<teiHeader>`, seitengetreuen `<pb facs="..." n="..."/>` Break-Tags, semantischen Absätzen und Fußnoten (`<note place="bottom">`).
3. **EPUB 3 (`<job>.epub`)**: Generierung des barrierefreien E-Books via `scripts/export_epub.py`.
