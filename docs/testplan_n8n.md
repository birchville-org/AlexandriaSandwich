# Testplan: n8n‑Workflow für AlexandriaSandwich OCR Pipeline

Dieses Dokument beschreibt, wie du einen kompletten Durchlauf des n8n‑OCR‑Workflows testen kannst – von der Ablage der Eingabedaten über den Webhook‑Aufruf bis hin zur Prüfung der Zwischenergebnisse undfinalen Ausgaben.

---

## 1. Vorbereitung – Eingabedaten ablegen

| Pfad (auf dem Host, gemountet im Worker) | Inhalt | Hinweis |
|------------------------------------------|--------|---------|
| `/opt/alexandria/data/input/<JOB_NAME>/` | Ein oder mehr Bild‑Seiten (PNG, TIFF, JPEG) – je ein Bild pro Buchseite. | Der Ordner **muss** existieren. Der Name `<JOB_NAME>` wird später im Webhook‑Body mitgegeben („job“‑Feld). |
| Beispiel                                 | `mkdir -p /opt/alexandria/data/input/testjob`<br>`cp ~/scans/page001.png /opt/alexandria/data/input/testjob/` | – |

> Der Worker‑Container mountet `/opt/alexandria/data` (siehe STATE‑Eintrag *Compose: `/opt/alexandria/docker-compose.yml`*). Damit sieht der Container exakt denselben Pfad.

---

## 2. n8n‑Workflow aktivieren (falls noch nicht geschehen)

```bash
# Auf dem Host, einmalig (oder nach Änderungen)
bash scripts/deploy_n8n_alex.sh   # stellt sicher, dass n8n läuft und das Workflow‑JSON importiert ist
```

- UI: <http://alex.local:5678/>
- Workflow **AlexandriaSandwich OCR Pipeline** muss **aktiv** sein (Toggle oben rechts).

---

## 3. Job starten (Webhook‑Aufruf)

```bash
JOB="testjob"                     # ← muss dem Ordnernamen oben entsprechen
curl -sS -X POST http://alex.local:5678/webhook/alexandria/ocr \
     -H "Content-Type: application/json" \
     -d "{
           \"job\": \"$JOB\",
           \"pull\": false,
           \"push\": false,
           \"lang\": \"deu+eng\",
           \"threshold\": 85,
           \"limit\": 0,
           \"no_mistral\": false
         }"
```

- Antwort (JSON) enthält mindestens `"ok": true` und die Pfade zu den erzeugten Artefakten.

---

## 4. Ausführung im n8n‑UI überwachen

1. Öffne **Executions** (links im n8n-Menü).
2. Suche die gerade gestartete Ausführung nach dem Job‑Namen oder dem Zeitstempel.
3. Klicke darauf → sieh den Durchlauf Schritt‑für‑Schritt:
   - **Webhook OCR Job** → **Build docker exec command** → **Run OCR pipeline** → **Parse pipeline report** → **Respond to Webhook**.
4. Bei jedem Node kannst du die **Output‑Daten** einsehen (z. B. das gebaute `docker exec …` Kommando, den stdout des Workers, das geparste Report‑JSON).

---

## 5. Wo finde ich die Zwischenergebnisse?

Alle Pfade sind relativ zum gemeinsamen Daten‑Volumen (`/opt/alexandria/data`).

| Schritt                     | Unterordner (unter `/opt/alexandria/data/`)                | Dateiname / Beispiel                                            |
|-----------------------------|-------------------------------------------------------------|-----------------------------------------------------------------|
| **Eingabe**                 | `input/<JOB_NAME>/`                                                 |
| **Pre‑process** (Img/>`                                      | `page001.png`, `page002.png` …                                 |
| **Pre‑process** (ImgMagick + unpaper) | `processing/preprocessed/<JOB_NAME>/`                     | `page001.png` (deskewed/unpaped)                               |
| **Qualitäts‑Check**         | `processing/quality/<JOB_NAME>/`                            | `<page>.quality.json` (enthält `mean_confidence`, `decision`)  |
| **Markdown‑Zwischenschritt**| `output/markdown/<JOB_NAME>/`                               | `<page>.md` (OCR‑Text)                                         |
| **Pipeline‑Report**         | `output/reports/<JOB_NAME>.pipeline.json`                  | Gesamter Lauf‑Report (ähnlich `e2e_m1.pipeline.json`)          |
| **Endprodukte**             | `output/pdf/<JOB_NAME>/`                                    | `<JOB_NAME>.sandwich.pdf` (OCRmyPDF‑Sandwich)<br>`<JOB_NAME>.pathb.pdf` (Post‑PDF‑Text‑Layer) |
| **Side‑Car‑Text**           | `output/pdf/<JOB_NAME>.sidecar.txt`                                 | Klartext‑Version des Sandwich PDFs (falls erzeugt)            

| der **pipeline‑Report** muss `"status": "PASS"` enthalten.                -| **decision`: "pass"` und **meanfidence ≥ 85` 85`| –||

:::::grammarbox
::::indent
:::important
:mark[asdf]
:sig[asdf]
:::
::::
:::::
