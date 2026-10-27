# Workflow für neue Dokumente & Evolutionäre Engine-Härtung

Dieses Dokument beschreibt den verbindlichen Standardarbeitsablauf, wenn ein neues Werk in **AlexandriaSandwich** digitalisiert wird und dabei neue typografische oder strukturelle Hürden auftreten.

---

## 1. Das Kernprinzip

> **Die Pipeline wächst mit jedem Buch.**  
> Skripte in `scripts/` werden niemals für einzelne Dokumente dupliziert oder geforkt. Alle Sonderfälle und Problembehebungen fließen direkt in die zentrale Engine ein und stehen automatisch allen bisherigen und zukünftigen Dokumenten zur Verfügung.

```text
 ┌────────────────────────────────────────────────────────┐
 │ 1. Ingress & Null-Lauf                                  │
 │    • Ordner anlegen: data/input/<job>/                 │
 │    • Seiten ablegen (PNG, 300 DPI)                     │
 │    • Standard-Pipeline ausführen: ./run_pipeline.sh    │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 2. Diagnose & Fehlstellenanalyse                       │
 │    • Prüfen: Pipeline-Report (<job>.pipeline.json)     │
 │    • Visuell: Perfect Sandwich vs. Vektor-Neusatz      │
 │    • Was scheitert? (Spalten, Ligaturen, Rauschen...)  │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 3. Generalisierte Lösung in Core-Engine                │
 │    • Merkmalserkennung statt Job-Name-Abfrage          │
 │    • Heuristik modular in scripts/ integrieren         │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 4. Regressions-Gate (Golden Master Guard)              │
 │    • Referenz-Jobs gegentesten (alex_smoke, katha_06)  │
 │    • Keine Qualitätsverluste bei Altbeständen          │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Die 4 Stufen im Detail

### Stufe 1: Ingress & Null-Lauf (Baseline)
1. **Verzeichnis bereitstellen:**
   ```bash
   mkdir -p data/input/mein_buch
   cp ~/scans/*.png data/input/mein_buch/
   ```
2. **Optionale Konfiguration (`job.config.json`):**
   Falls bucheigene Randbedingungen bekannt sind (z. B. altindischer Sprachmix oder abweichender Tesseract-Schwellenwert):
   ```json
   {
     "lang": "san+deu",
     "threshold": 95,
     "use_mistral": true
   }
   ```
3. **Pipeline-Start ohne Code-Modifikation:**
   ```bash
   ./scripts/run_pipeline.sh --job mein_buch
   ```

---

### Stufe 2: Diagnose & Fehlstellenanalyse
Untersuche die generierten Zielartefakte in `data/output/mein_buch/`:
- **`mein_buch.pipeline.json`:** Wie hoch ist die OCR-Pass-Rate? Wurde Mistral unverhältnismäßig oft aufgerufen?
- **`mein_buch.sandwich.pdf`:** Liegt der Textlayer exakt auf den Pixeln oder driftet er (Skew/Verzerrung)?
- **`mein_buch.typeset_edition.pdf` / `mein_buch.digital.pdf`:** Werden zweispaltige Wörterbuchstrukturen fälschlicherweise als einspaltiger Fließtext gerendert?

---

### Stufe 3: Generalisierte Lösung in der Core-Engine
Sobald die Ursache isoliert ist, wird die Behebung **ausschließlich in `scripts/`** implementiert.

**Verbindliche Entwurfsregeln:**
1. **Niemals auf Job-Namen prüfen:** Kein `if job == "mein_buch": ...` im Python- oder Bash-Code.
2. **Merkmale abstrahieren:**
   - Liegt ein zweispaltiges Layout vor? -> Analyse der X-Koordinaten-Dichte der Bounding Boxes.
   - Gibt es Leitlinien (z. B. gepunktete Linien im Wörterbuch)? -> Kantenerkennung via Morphologie (Open/Close) im Preprocessing.
   - Handelt es sich um Fußnoten? -> Filterung über relative Zeilenhöhe (`line_height < 0.8 * avg_line_height`).
3. **Konfigurationsparameter exposen:** Lässt sich das Verhalten nicht zu 100 % automatisieren, wird ein generischer Parameter in `job.config.json` eingeführt (z. B. `"column_mode": "two_column"`).

---

### Stufe 4: Regressions-Gate (Golden Master Guard)
Jede Änderung an Kernskripten (`preprocess.sh`, `assemble_sandwich.py`, `render_digital_pdf.py` etc.) muss vor dem Git-Commit gegen die bestehenden Golden-Master-Jobs getestet werden:

```bash
# Schneller Regressionslauf über Smoke- und Muster-Jobs
./scripts/run_pipeline.sh --job alex_smoke
./scripts/run_pipeline.sh --job katha_06 --limit 2
```

Wenn alle Golden-Master-Artefakte fehlerfrei und ohne Qualitätseinbußen kompilieren:
1. Das neue Werk `mein_buch` erneut durchlaufen lassen.
2. Nach erfolgreicher Generierung wird `mein_buch` zum neuen festen Bestandteil der Referenz-Bibliothek.

---

## 3. Das Triage- & Ökonomie-Modell: Core-Pipeline vs. Editions-Satelliten

Nicht jedes historische Werk kann oder soll vollautomatisch von der zentralen Engine bis zur druckreifen wissenschaftlichen Edition durchgerechnet werden. Das Einbetten buchspezifischer Spezialparser (z. B. für die 3.997 Sūtras von Böhtlingks Pāṇini oder die Metrik des Rigveda) in die Hauptpipeline führt zur **Monolith-Falle**: Die Engine wird überfrachtet, fragil und unwartbar.

Für den produktiven Service auf **`alex.birchville.org`** gilt daher ein ökonomisch optimiertes **Triage- und Trichtermodell**:

```text
               Nutzer reicht Scan / IIIF-Manifest ein
                                 │
                                 ▼
                     [ Automatische Pipeline ]
                     Scan -> Masking -> OCR ->
                     1:1 Sandwich-PDF + Rohtext
                                 │
                                 ▼
                   Ergebnis entspricht Erwartung?
                     ├── JA: Fertig (80–90 % aller Standardbücher)
                     └── NEIN: Fall zur Begutachtung einreichen
                                 │
                                 ▼
                     [ Philologische Triage ]
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
    Pfad A: Generischer Bug                 Pfad B: Echter Spezialfall
    (z. B. Spaltentrennung,                 (Kanonisches Referenzwerk:
     Margin-Farbe, Ligaturen)                Pāṇini, Wörterbücher, etc.)
             │                                       │
             ▼                                       ▼
      Verbesserung der                        Ausgründung als
      HAUPTPIPELINE                           EDITIONS-SATELLIT
      (AlexandriaSandwich)                    (Eigenes Repo, z. B. boethlingk)
             │                                       │
             ▼                                       ▼
      Alle zukünftigen Bücher                 Fokussierte Kuration,
      profitieren automatisch                 QA-Viewer & TEI-P5-Modellierung
```

### Ökonomische Bewertung

1. **Grenzkosten nahe null für Standardfälle:** 80–90 % aller Monographien und Dokumente laufen vollautomatisch ohne menschliche Intervention durch die Pipeline.
2. **Schutz vor Fehlallokation von Entwicklerzeit (*YAGNI*):** Es werden keine spekulativen Parser für hypothetische Sonderfälle gebaut. Speziallogik entsteht nur, wenn ein echtes Werk mit realem Bedarf vorliegt.
3. **Maximale Hebelwirkung bei Pipeline-Fixes (Pfad A):** Generische Verbesserungen werden in `AlexandriaSandwich/scripts/` gelöst und stehen allen nachfolgenden Werken zur Verfügung.
4. **Wissenschaftliche Kuration als Satelliten-Projekt (Pfad B):** Komplexe Werke erhalten ein eigenes Git-Repository (wie [`boethlingk`](https://github.com/birchville-org/boethlingk)), nutzen die AlexandriaSandwich-Ergebnisse als digitale Primärebene und implementieren domänenspezifische Statusmaschinen, Ground-Truth-Matcher und 1:1-Faksimile-Neusätze autark.

### Service-Level-Deklaration für `alex.birchville.org`

Die Web-Oberfläche kommuniziert diese Grenze transparent:
* **Standard-Verarbeitung:** Vollautomatische Erzeugung durchsuchbarer 1:1 Sandwich-PDFs und TEI-Texte für historische Druckwerke in lateinischen und indischen Standardschriften.
* **Komplexe Sonderfälle:** Bei anspruchsvollen philologischen Editionen (mehrsprachiger Satz, mehrspaltige Wörterbücher mit tiefer Lemmastruktur, Vers- und Sūtra-Werke) reicht die generische Automatisierung nicht aus.
* **Feedback-Schleife:** Entspricht das Resultat nicht den Erwartungen, wird der Fall mit dem Originalscan zur Begutachtung eingereicht. Wir prüfen, ob die Heuristik der Hauptpipeline erweitert werden kann (Pfad A) oder ob das Werk als kuratiertes Birchville-Editions-Projekt aufgesetzt werden soll (Pfad B).

