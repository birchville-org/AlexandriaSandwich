# Fallstudie: Bṛhadāraṇyaka-Upaniṣad I.4 (Synoptische Edition)

> **Multilaterales philologisches Alignment dreier Textzeugen (Devanagari, IAST, 2 deutsche Übersetzungen) zu einer 33-seitigen synoptischen Edition und interaktivem QA-Viewer.**
> 
> 🔗 **Projekt-Repository:** [github.com/birchville-org/brhadaranyaka](https://github.com/birchville-org/brhadaranyaka)

---

## 1. Ausgangslage & Problemstellung

Im Gegensatz zur unilinearen Buchverarbeitung (einzelne Scan-Folge `=>` Sandwich-PDF) erforderte die Lektüre der **Bṛhadāraṇyaka-Upaniṣad I.4** (Mādhyandina-Rezension: Das *Ursubjekt* und der Schöpfungsmythos) die synoptische Zusammenführung dreier disparater Quellen:

1. **Kanonischer Sanskrit-Text:** Wissenschaftliche IAST-Transliteration nach Anna Esposito.
2. **Walter Slaje (2009):** *Upanischaden: Arkanum des Veda* (Insel Verlag) mit moderner Übersetzung, philosophischer Terminologie (*Ursubjekt*) und 36-teiligem Stellenkommentar.
3. **Otto von Böhtlingk (1889):** *Bṛhadāraṇjakopanishad in der Mādhyandina-Recension* (St. Petersburg) mit historischer Erstübersetzung und kritischem Apparat.

---

## 2. Implementierte Verfahrensschritte

1. **KI-OCR & Layout-Extraktion (`mistral-ocr-latest`):**
   * Vollständige Texterfassung der Drucke von Böhtlingk 1889 (12 Seiten) und Slaje 2009 (15 Seiten).
   * Automatische Trennung von Übersetzungstext (Buchseiten 108–117) und Stellenkommentar (Buchseiten 482–493).
2. **Kanonisches Alignment:**
   * Segmentierung aller drei Quellen nach den 31 Sinnabschnitten (`1.4.1` bis `1.4.31`).
   * Phonetisch exakte Devanagari-Generierung mit Danda-Gliederung.
   * Zuordnung der Lemma-Kommentare aus Slajes philologischem Apparat.
3. **Auslagerung in eigenständiges Editions-Repository:**
   * Analog zum Fallbeispiel [boethlingk](https://github.com/birchville-org/boethlingk) wurde die Edition vollständig in das Repository [birchville-org/brhadaranyaka](https://github.com/birchville-org/brhadaranyaka) überführt.

---

## 3. Erzeugte Zielformate im Editions-Repository

* **QA-Viewer ([viewer.html](https://github.com/birchville-org/brhadaranyaka/blob/main/viewer.html)):** Interaktiver Split-Pane Editor nach dem Payer Global Web Editor Standard mit Snippet-Bar, File System Access API und Silent Auto-Repair.
* **Satz-PDF (`brhadaranyaka_1_4_synopsis.pdf`):** 33-seitige typografische Publikation via WeasyPrint.
* **TEI-P5 XML (`brhadaranyaka_1_4.tei.xml`):** Standardkonformes Archivformat mit parallelen `<ab>`-Elementen.
* **EPUB 3 (`brhadaranyaka_1_4.epub`):** Reflowable E-Book mit eingebetteten Schriften (*Noto Serif Devanagari* & *Linux Libertine O*).
* **Single Source Master-JSON (`brhadaranyaka_1_4_master.json`):** Strukturierter AST aller 31 Abschnitte.
