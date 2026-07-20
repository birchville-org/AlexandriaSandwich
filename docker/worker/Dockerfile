# Offizielles Multi-Architektur Python Image (unterstützt linux/arm64 & linux/amd64)
FROM python:3.11-slim

# Installiere Bildverarbeitungs- und OCR-Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    scantailor \
    unpaper \
    imagemagick \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    pngquant \
    jbig2enc \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Installiere Python-Pakete für OCR & PDF Bundling
RUN pip install --no-cache-dir ocrmypdf img2pdf

# ImageMagick-Sicherheitsrichtlinie für PDF-Lese-/Schreibrechte anpassen
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml

WORKDIR /data

CMD ["tail", "-f", "/dev/null"]
