Test‑Plan: Einen Dokument‑Durchlauf über den n8n‑Workflow starten

1. Vorbereitung – Eingabe‑Daten ablegen
Ort (auf dem Host)	Was dort hineinlegen	Hinweis
/opt/alexandria/data/input/<JOB_NAME>/	Ein oder mehr Bild‑Seiten (PNG, TIFF, JPEG) – je ein Bild pro Buchseite.	Der Ordner muss existieren; der Name <JOB_NAME> wird im Webhook‑Body mitgegeben („job“‑Feld).
Beispiel	mkdir -p /opt/alexandria/data/input/testjob
cp ~/scans/page001.png /opt/alexandria/data/input/testpage/	–
Der Worker‑Container mountet /opt/alexandria/data (siehe STATE‑Eintrag Compose: /opt/alexandria/docker-compose.yml). Damit sieht der Container exakt denselben Pfad.

2. n8n‑Workflow aktivieren (falls noch nicht geschehen)
# Auf dem Host, einmalig (oder nach Änderungen)
bash scripts/deploy_n8n_alex.sh   # stellt sicher, dass n8n läuft und das Workflow‑JSON importiert ist
UI: http://alex.local:5678/
Workflow AlexandriaSandwich OCR Pipeline muss aktiv sein (Toggle oben rechts).
3. Job starten (Webhook‑Aufruf)
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
Antwort (JSON) enthält mindestens "ok": true und die Pfade zu den erzeugten Artefakten.
4. Ausführung im n8n‑UI überwachen
Öffne Executions (links im n8n-Menü).
Suche die gerade gestartete Ausführung nach dem Job‑Namen oder dem Zeitstempel.
Klicke darauf → sieh den Durchlauf Schritt‑für‑Schritt:
Webhook OCR Job → Build docker exec command → Run OCR pipeline → Parse pipeline report → Respond to Webhook.
Bei jedem Node kannst du die Output‑Daten einsehen (z. B. das gebaute docker exec … Kommando, den stdout des Workers, das geparste Report‑JSON).
5. Wo finde ich die Zwischenergebnisse?
Alle Pfade sind relativ zum gemeinsamen Daten‑Volumen (/opt/alexandria/data).

Schritt	Unterordner (unter /opt/alexandria/data/)	Dateiname / Beispiel
Eingabe	input/<JOB_NAME>/	page001.png, page002.png …
Pre‑process (ImgMagick + unpaper)	processing/preprocessed/<JOB_NAME>/	page001.png (deskewed/unpaped)
Qualitäts‑Check	processing/quality/<JOB_NAME>/	<page>.quality.json (enthält mean_confidence, decision)
Markdown‑Zwischenschritt	output/markdown/<JOB_NAME>/	<page>.md (OCR‑Text)
Pipeline‑Report	output/reports/<JOB_NAME>.pipeline.json	Gesamter Lauf‑Report (ähnlich e2e_m1.pipeline.json)
Endprodukte	output/pdf/<JOB_NAME>/	<JOB_NAME>.sandwich.pdf (OCRmyPDF‑Sandwich)
<JOB_NAME>.pathb.pdf (Post‑PDF‑Text‑Layer)
Side‑Car‑Text	output/pdf/<JOB_NAME>.sidecar.txt	Klartext‑Version des Sandwich PDFs (falls erzeugt)
6. Erfolgskriterien prüfen
Der pipeline‑Report muss "status": "PASS" enthalten.
Alle Seiten müssen "decision": "pass" und mean_confidence ≥ 85 zeigen (sonst wird automatisch das Mistral‑Fall‑back getriggert – das ist ebenfalls OK, solange am Ende ein PDF entsteht).
Die beiden PDF‑Dateien existieren und sind nicht leer (ls -lh).
Optional: öffne das PDF und prüfe, dass der Text layer vorhanden (bei Path‑B) bzw. das Bild‑Overlay (bei Sandwich).
7. Fehlerdiagnose (falls etwas fehlschlägt)
Symptom	Wo nachschauen
Webhook liefert 404	Sicherstellen, dass der Workflow aktiv ist und die URL exakt /webhook/alexandria/ocr lautet (nicht /webhook-test/).
docker exec …: exec failed	Der Worker‑Container läuft? (docker ps). Fehlt bash im Container → das Deploy‑Skript muss neu ausgeführt werden (es bindet /usr/bin/docker und legt den User auf root).
Keine Ausgabedateien	Schau dir den Run OCR pipeline Node Output an – dort steht der stdout/stderr des run_pipeline.sh. Typische Ursachen: fehlende Eingabebilder, falscher Job‑Name, Berechtigungen im /data‑Verzeichnis.
Qualitäts‑Check schlägt fehl (conf < 85)	Im processing/quality/<JOB_NAME>/<page>.quality.json den Wert prüfen; bei Bedarf das Bild nachbessern oder --no-mistral setzen, um trotzdem weiterzumachen (werden dann dennoch mit niedriger Konfidenz verarbeitet).
Kurz‑Checkliste zum Ausprobieren
# 1. Test‑Daten bereitstellen
mkdir -p /opt/alexandria/data/input/demo
cp /path/to/scan1.png /opt/alexandria/data/input/demo/
cp /path/to/scan2.png /opt/alexandria/data/input/demo/

# 2. n8n sicherstellen (einmalig)
bash scripts/deploy_n8n_alex.sh

# 3. Job starten
JOB=demo
curl -sS -X POST http://alex.local:5678/webhook/alexandria/ocr \
     -H "Content-Type: application/json" \
     -d "{\"job\":\"$JOB\",\"pull\":false,\"push\":false,\"lang\":\"deu+eng\",\"threshold\":80,\"limit\":0,\"no_mistral\":false}"

# 4. In n8n UI → Executions → zuletzt erfolgreich? → Output‑Pfade notieren
# 5. Ergebnisse prüfen
ls -lh /opt/alexandria/data/output/pdf/demo/
Damit hast du einen kompletten End‑to‑End‑Durchlauf vom Einlegen der Rohbilder über den n8n‑Trigger, den Worker‑Container bis hin zu den finalen PDF‑Ausgaben samt aller Zwischenartefakte. Viel Erfolg beim Testen!
