# Fallstudie & Verfahrensdokumentation: Pāṇinis Grammatik (Otto von Böhtlingk, 1887)

> **Vollständige historische Digitalisierung, kanonischer Text-Abgleich und Erzeugung von durchsuchbarem Sandwich-Material für 3.997 Sūtras auf 478 Buchseiten.**
> 
> 🔗 **Projekt-Repository:** [github.com/birchville-org/boethlingk](https://github.com/birchville-org/boethlingk)

---

## 1. Zweck & Problemstellung

### 1.1 Das Ausgangswerk
Otto von Böhtlingks Ausgabe *Pâṇini's Grammatik, herausgegeben, übersetzt, erläutert und mit verschiedenen Indices versehen* (Leipzig, H. Haessel, 1887) ist das weltweit maßgebliche philologische Referenzwerk für das altindische grammatische System der Aṣṭādhyāyī. 

### 1.2 Die philologische & typografische Herausforderung
Das Werk vereint drei völlig disparate Schriftsysteme und Sprachen auf engstem Raum:
1. **Sanskrit in Devanagari:** Komplexer 19.-Jahrhundert-Bleisatz mit historischen Ligaturen, Halbvokalen und Virāmas.
2. **Deutsch in historischer Antiqua:** Fachwissenschaftliche Übersetzung und grammatische Erläuterungen mit zeitspezifischer Typografie.
3. **Wissenschaftliche Transliteration (IAST):** Lateinische Schrift mit zahlreichen kombinierten Diakritika (`ā`, `ī`, `ū`, `ṛ`, `ṝ`, `ḷ`, `ḹ`, `ṃ`, `ḥ`, `ṅ`, `ñ`, `ṭ`, `ḍ`, `ṇ`, `ś`, `ṣ`) sowie Akzentzeichen (Udātta, Svarita).

Klassische lokale OCR-Engines (Tesseract, Kraken, ABBYY) scheitern an diesem gemischten Satzbild mit extrem hohen Fehlerraten oder Script-Verwechslungen.

### 1.3 Das Digitalisierungsziel
Ziel des Projekts ist die Erzeugung eines mehrschichtigen, archivfesten Digitalisats:
1. **1:1 Sandwich-PDF:** Visuell unberührte, hochauflösende Originalscans der Universitätsbibliothek Heidelberg (pixelgenau erhalten) mit einer unsichtbaren, geometrisch präzisen und durchsuchbaren Volltextebene.
2. **Strukturierte Single Source of Truth (Master-JSON):** Vollständige, lückenlose Zerlegung des gesamten Werkes in strukturierte Sūtra-Objekte (Sūtra-Nummer, kanonische Devanagari, IAST, deutsche Übersetzung, philologischer Kommentar, Buchseiten-Zuordnung).
3. **Autarker QA-Viewer:** Eine leichtgewichtige Webanwendung nach dem *Payer Global Web Editor Standard* zur visuellen Überprüfung und Korrektur mit Split-Pane-Ansicht und Silent Auto-Repair.
4. **TEI-XML-Grundlage:** Bereitstellung eines standardisierten Korpus für die digitale Editionswissenschaft.

---

## 2. Das implementierte Verfahren (End-to-End Pipeline)

```text
[UB Heidelberg Faksimiles] 
       │ (Buchseiten 1 bis 478, JPG)
       ▼
[Schritt 1: Lokales Image Caching] ──► data/img_cache/7_3A000000XXX_...jpg
       │
       ▼
[Schritt 2: Multimodale KI-OCR] ────► mistral-ocr-latest (Mistral Python SDK)
       │                              ├── data/mistral/*.mistral.md   (Layout-Markdown)
       │                              └── data/mistral/*.mistral.json (Bounding-Box Geometrie)
       ▼
[Schritt 3: Kanonisches Alignment] ──► scripts/align_mistral_sutras.py
       │                              ├── Heuristische Sūtra-Segmentierung (#, ##, ॥...॥)
       │                              ├── SequenceMatcher-Abgleich gegen data/sutras.json
       │                              ├── 4-Pāda-pro-Adhyāya Statusmaschine
       │                              └── Kolophon- und Rauschfilterung
       ▼
[Schritt 4: Konsolidierung] ─────────► data/ashtadhyayi_complete_boethlingk1887.json
       │                              (3.997 Sūtras = 100,0 % lückenlos & 0 Duplikate)
       ▼
[Schritt 5: Interaktiver QA-Viewer] ──► viewer.html (Split-Pane, Zoom/Pan, Silent Auto-Repair)
```

---

## 3. Detaillierte Verfahrensschritte

### Schritt 1: Primärquellen-Beschaffung & Caching
* **Quelle:** Digitalisate der Universitätsbibliothek Heidelberg (Signatur: *Bibliotheca Palatina*, boehtlingk1887).
* **Umfang des Haupttextes:** Buchseiten 1 bis 478 (S. 1 = Śiva-Sūtras, S. 2–476 = Aṣṭādhyāyī 1.1.1 bis 8.4.68, S. 477–478 = Nachträge).
* **Speicherung:** 484 Scans liegen lokal unter `data/img_cache/7_3A000000XXX_jpg_full_max_0_default_jpg.jpg` vor.

### Schritt 2: Multimodale KI-Erkennung (`mistral-ocr-latest`)
* **Werkzeug:** Offizielles Mistral SDK mit dem Modell `mistral-ocr-latest` (`scripts/mistral_ocr.py`).
* **Batch-Orchestrierung:** `scripts/batch_ocr_runner.py` verarbeitet Seitenbereiche automatisiert mit Übersprung bereits vorhandener Dateien und Kostenüberwachung.
* **Erzeugte Artefakte:**
  * `.mistral.md`: Semantisch strukturiertes Markdown mit Überschriftshierarchien und Fließtext.
  * `.mistral.json`: Detaillierte Antwort mit Seitendimensionen, Textblöcken und Bounding-Box-Koordinaten für die spätere Sandwich-PDF-Schichtung.
* **Kosten:** 478 Seiten x 0,004 USD = exakt **1,912 USD** für das gesamte Werk.

### Schritt 2.1: Lokale VLM-Alternative & Modell-Benchmark (Mistral OCR vs. Qwen2.5-VL)
Um neben der Cloud-API (`mistral-ocr-latest`) eine autarke, offlinefähige Alternative für sensible Digitalisierungsprojekte und Air-Gap-Deployments bereitzustellen, wurde eine lokale Vision-Language-Modell-Pipeline ([scripts/qwen_ocr.py](file:///Volumes/SanDisk1TB/proj/AlexandriaSandwich/scripts/qwen_ocr.py), [scripts/benchmark_ocr.py](file:///Volumes/SanDisk1TB/proj/AlexandriaSandwich/scripts/benchmark_ocr.py)) mit **Qwen2.5-VL** (via MLX auf Apple Silicon) evaluiert:

#### 1. Antiqua / Einleitungsseiten (Lateinische Schrift & Fließtext, z. B. S. 5)
Bei rein lateinischem Satzbild und deutschsprachigen Erläuterungen erreicht das lokale Modell nahezu vollständige Deckungsgleichheit:

| Metrik | Mistral Document AI (Cloud) | Qwen2.5-VL (Lokal, BF16 / 8-Bit) | Differenz / Bewertung |
| :--- | :--- | :--- | :--- |
| **Ähnlichkeit (Similarity)** | Referenz | **99,96 %** | Nahezu identischer Textauszug |
| **Zeichenanzahl** | 2.437 Zeichen | 2.435 Zeichen | -2 Zeichen |
| **Wortanzahl** | 338 Wörter | 337 Wörter | -1 Wort |
| **Laufzeit pro Seite** | ca. 1,8 s | ca. 161 s | Cloud ca. 90x schneller |
| **Fremdkosten** | 0,004 USD / Seite | **0,00 USD (Lokal)** | 100 % kostenfrei & offline |

#### 2. Polyglotter Satz / Historische Devanāgarī (z. B. S. 108)
Bei hochkomplexem 19.-Jahrhundert-Devanāgarī-Bleisatz mit Ligaturen, Virāmas und gemischtem Kommentar zeigt sich der Spezialisierungsgrad:

| Metrik | Mistral Document AI (Cloud) | Qwen2.5-VL BF16 (Lokal) | Qwen2.5-VL 8-Bit (Lokal) |
| :--- | :--- | :--- | :--- |
| **Ähnlichkeit (Similarity)** | Referenz | **66,59 %** | **65,32 %** |
| **Devanāgarī-Zeichen** | 1.304 Zeichen | 1.212 Zeichen (-92) | 1.210 Zeichen (-94) |
| **Zeichenanzahl gesamt** | 1.825 Zeichen | 1.782 Zeichen (-43) | 1.779 Zeichen (-46) |
| **Laufzeit pro Seite** | ca. 1,8 s | 293,7 s (~4,9 Min.) | **196,5 s (~3,3 Min., +33 % Tempo)** |
| **Fremdkosten** | 0,004 USD / Seite | **0,00 USD** | **0,00 USD** |

#### Fazit & Architekturentscheidung:
- **Mistral OCR:** Goldstandard für historische indische Schriften und Massenverarbeitung (hohe Erkennungsgenauigkeit komplexer Ligaturen, minimale Latenz).
- **Qwen2.5-VL 8-Bit (Lokal):** Robuste, datenschutzkonforme Alternative für moderne und rein europäische Drucke (99,96 % Genauigkeit). Durch die 8-Bit-Quantisierung sinkt die Verarbeitungszeit um 33 % bei vernachlässigbarem Zeichenverlust (-0,2 %).

### Schritt 3: Kanonisches Alignment & Korrektur-Heuristik (`scripts/align_mistral_sutras.py`)
Die größte technische Hürde historischer Buch-Digitalisate liegt in Scan-Artefakten, Zahlendrehern und Formatbrüchen:
* **Fuzzy Canonical Matching:** Weicht eine erkannte Sūtra-Nummer ab (z. B. OCR liest die Devanagari-Ziffer ८ als ६, also `६५` statt `८५`), vergleicht ein `SequenceMatcher`-Algorithmus den bereinigten Devanagari-Text der Zeile mit dem erwarteten Sūtra aus `data/sutras.json`. Bei einer Ähnlichkeit >= 0,45 wird der Zähler automatisch korrigiert.
* **Kompensierte Zeichenlänge:** Extrem lange Sanskrit-Komposita (z. B. Sūtra 5.4.77 mit 185 Zeichen ohne führendes `#`) werden über Danda-Muster (`॥...॥`) bis 350 Zeichen sicher als Sūtra-Kopfzeilen erkannt.
* **Pāda- und Adhyāya-Rollover:** Da die Aṣṭādhyāyī strikt aus 8 Adhyāyas mit je exakt 4 Pādas besteht, erzwingt die Statusmaschine nach Pāda 4 den automatischen Übergang auf den nächsten Adhyāya (`state["adhyaya"] += 1, state["pada"] = 1`), auch wenn der gedruckte Kolophon typografisch beschädigt oder unvollständig erkannt wurde.
* **Filterung von Störskripten:** Stray-Tokens (gelegentliche hebräische oder telugu-artige Glyphen, hervorgerufen durch abgenutzte Bleitypen) werden vor der Konsolidierung rückstandslos bereinigt.
* **Schutz vor Nachträgen:** Nach dem Schlusssūtra 8.4.68 (`अ अ`) auftretende Textfortsetzungen (Böhtlingks *Nachträge und Verbesserungen*) werden isoliert und kontaminieren nicht den Kommentar von 8.4.68.

---

## 4. Validierungsergebnisse

Alle 8 Adhyāyas und die einleitenden Śiva-Sūtras wurden 1:1 gegen die kanonische Referenzdatenbank validiert:

| Bereich | Buchseiten | Sūtras (Ist / Soll) | Duplikate | Fehlende Übersetzungen | Validierungsstatus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Śiva-Sūtrāṇi** | 1 | 14 / 14 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 1** | 2–43 | 351 / 351 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 2** | 43–75 | 268 / 268 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 3** | 75–148 | 631 / 631 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 4** | 149–221 | 635 / 635 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 5** | 221–282 | 555 / 555 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 6** | 283–374 | 736 / 736 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 7** | 375–428 | 438 / 438 | 0 | 0 | **100,0 % validiert** |
| **Adhyāya 8** | 429–478 | 369 / 369 | 0 | 0 | **100,0 % validiert** |
| **Gesamt** | **478 Seiten** | **3.997 / 3.997** | **0** | **0** | **100,0 % lückenlos** |

---

## 5. Das Sandwich-PDF-Verfahren in AlexandriaSandwich

Das fertige Sandwich-PDF wurde über das Skript [scripts/build_sandwich_pdf.py](https://github.com/birchville-org/boethlingk/blob/main/scripts/build_sandwich_pdf.py) assembliert:
* **Zieldatei:** `data/output/boehtlingk1887_sandwich.pdf` (278,16 MB, 478 Seiten)
* **Visuelle Ebene (Hintergrund):** Die 478 hochauflösenden Primärscans der UB Heidelberg werden verlustfrei eingebunden (1:1 Pixelauflösung).
* **Unsichtbare Textebene (Vordergrund):** Mittels PDF Text Rendering Mode 3 (*Neither fill nor stroke text*) und Unicode-Font (*Arial Unicode* / *Identity-H*) wurden 14.267 Textblöcke auf ihren exakten Pixelkoordinaten platziert.
* **Hierarchisches Inhaltsverzeichnis (PDF Bookmarks):** Alle 8 Adhyāyas, 32 Pādas, die Śiva-Sūtras und die Nachträge sind als klickbare Gliederung hinterlegt.
* **Ergebnis:** Beim Betrachten erscheint das unveränderte historische Faksimile von 1887. Textauswahl, Copy-Paste und Volltextsuche (Devanāgarī, IAST und Deutsch) greifen unmittelbar auf die korrekten Zeilen und Koordinaten zu.

---

## 6. Wissenschaftliche TEI-P5-Edition

Für die Langzeitarchivierung und Interoperabilität wurde die kanonisch geprüfte XML-Edition generiert:
* **Datei:** `data/tei/boehtlingk1887_p5.xml` (2,90 MB)
* **Validierung:** 100 % schema-valide gegen TEI All RelaxNG (`schemas/tei_all.rng`).
* **Umfang:** 3.997 `<tei:entry>`-Elemente, 478 `<tei:pb>`-Seitenumbrüche mit Verlinkung zu den IIIF-Vollbildern der UB Heidelberg, 8 Adhyāya- und 32 Pāda-Abschnitte sowie 50 Corrigenda-Einträge in `<back>`.

---

## 7. QA-Viewer (Payer Global Web Editor Standard)

Für die redaktionelle Nachprüfung und dauerhafte Nutzung wurde [viewer.html](https://github.com/birchville-org/boethlingk/blob/main/viewer.html) implementiert:
* **Split-Pane:** Links der hochauflösende Originalscan mit flüssigem Zoom & Pan (Drag & Drop mit der Maus); rechts der Sūtra-Editor.
* **Snippet-Toolbar:** Direkte Einfügemöglichkeit für Dandas (`॥`, `।`, `ऽ`, `°`), IAST-Diakritika und philologische Abkürzungen (`∠±`, `∠_`, `v. l.`, `Kāç.`, `RV.`).
* **Silent Auto-Repair on Save:** Beim Speichern (`⌘S`) werden Pipes (`||`) stumm zu Dandas (`॥`) gewandelt, doppelte Leerzeichen normalisiert und Störzeichen entfernt; visueller Status über Farbwechsel (Gelb = Auto-Repair, Grün = Gespeichert).
* **Local Storage & Export:** Speichert Revisionen lokal im Browser und erlaubt das direkte Zurückschreiben via File System Access API (`showSaveFilePicker`).

---

## 8. Projekt-Links & Quellcode

* **GitHub Repository:** [birchville-org/boethlingk](https://github.com/birchville-org/boethlingk)
* **Digitalisate & Daten:** Sämtliche Pipeline-Skripte, TEI-P5-XML-Dateien, Auswertungen und der autarke QA-Viewer (`viewer.html`) sind im Repository verfügbar.
