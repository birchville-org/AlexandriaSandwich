# Case Study: Bṛhadāraṇyaka-Upaniṣad I.4 (Synoptic Edition)

> **Multilateral philological alignment of three textual witnesses (Devanagari, IAST, 2 German translations) into a 33-page synoptic edition and interactive QA viewer.**
> 
> 🔗 **Project Repository:** [github.com/birchville-org/brhadaranyaka](https://github.com/birchville-org/brhadaranyaka)

---

## 1. Context & Challenge

Unlike standard unilinear book digitization (scanned pages `=>` sandwich PDF), reading **Bṛhadāraṇyaka-Upaniṣad I.4** (Mādhyandina recension: The *Ur-Subject* and creation myth) required the synoptic synchronization of three disparate sources:

1. **Canonical Sanskrit Text:** Scholarly IAST transliteration by Anna Esposito.
2. **Walter Slaje (2009):** *Upanischaden: Arkanum des Veda* (Insel Verlag) offering modern philosophical translation, terminology (*Ursubjekt*), and a 36-entry philological commentary.
3. **Otto von Böhtlingk (1889):** *Bṛhadāraṇjakopanishad in der Mādhyandina-Recension* (St. Petersburg) providing the historical critical edition and notes.

---

## 2. Implementation Steps

1. **Multimodal AI OCR (`mistral-ocr-latest`):**
   * Extracted Böhtlingk 1889 (12 pages) and Slaje 2009 (15 pages).
   * Structured translation pages (pp. 108–117) and philological commentary (pp. 482–493).
2. **Canonical Alignment:**
   * Aligned all sources across 31 semantic sections (`1.4.1` to `1.4.31`).
   * Generated ligature-safe Devanagari with danda formatting.
3. **Repository Decoupling:**
   * Following the [boethlingk](https://github.com/birchville-org/boethlingk) model, all artifacts were transferred to the dedicated repository [birchville-org/brhadaranyaka](https://github.com/birchville-org/brhadaranyaka).

---

## 3. Output Formats in the Edition Repository

* **QA Viewer ([viewer.html](https://github.com/birchville-org/brhadaranyaka/blob/main/viewer.html)):** Interactive split-pane editor adhering to the Payer Global Web Editor Standard with silent auto-repair and diacritics bar.
* **Typeset PDF (`brhadaranyaka_1_4_synopsis.pdf`):** 33-page scholarly publication via WeasyPrint.
* **TEI-P5 XML (`brhadaranyaka_1_4.tei.xml`):** Standard archival format with parallel alignment.
* **EPUB 3 (`brhadaranyaka_1_4.epub`):** Reflowable eBook with embedded fonts (*Noto Serif Devanagari* & *Linux Libertine O*).
* **Master JSON (`brhadaranyaka_1_4_master.json`):** Single Source of Truth AST.
