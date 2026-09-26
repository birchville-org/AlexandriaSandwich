# 📖 AlexandriaSandwich Example Scans

Dieses Verzeichnis enthält lizenzfreie, synthetische Test-Buchscans für Funktions- und Rauchtests der Pipeline.

## Struktur
* `sample_book/`: Zwei saubere Buchseiten (`page_01.png`, `page_02.png`) für einen vollständigen Durchlauf aller Pipeline-Stufen.

## Direkter Test mit Docker
```bash
# Sobald alexandria_worker läuft:
docker exec -it alexandria_worker /opt/alexandria/scripts/run_pipeline.sh \
  --job sample_test \
  --input /opt/alexandria/examples/sample_book \
  --no-mistral
```

Die Ergebnisse liegen anschließend im lokalen Verzeichnis `./data/output/`:
* `data/output/pdf/sample_test.sandwich.pdf` (1:1 Sandwich-PDF)
* `data/output/tei/sample_test.tei.xml` (TEI-P5 Archivierungs-XML)
* `data/output/pdf/sample_test.digital.pdf` (Typst Neusatz-PDF)
