# AlexandriaSandwich OCR worker
# Headless preprocess: ImageMagick deskew + unpaper (ScanTailor replaced — GUI-only)
# Multi-arch: linux/amd64 (alex.local) + linux/arm64 (M2)
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Preprocess
    unpaper \
    imagemagick \
    # OCR / PDF
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    tesseract-ocr-san \
    pngquant \
    jbig2 \
    jbig2dec \
    poppler-utils \
    qpdf \
    # Fonts & Typst dependencies
    fonts-linuxlibertine \
    fonts-dejavu-core \
    fonts-noto-core \
    xz-utils \
    tar \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Typst multi-arch binary
ARG TARGETARCH
RUN set -e; \
    if [ "$TARGETARCH" = "arm64" ]; then \
      TYPST_ARCH="aarch64"; \
    else \
      TYPST_ARCH="x86_64"; \
    fi; \
    curl -fsSL "https://github.com/typst/typst/releases/download/v0.11.1/typst-${TYPST_ARCH}-unknown-linux-musl.tar.xz" \
      | tar -xJ -C /usr/local/bin --strip-components=1 "typst-${TYPST_ARCH}-unknown-linux-musl/typst"; \
    chmod +x /usr/local/bin/typst; \
    typst --version

RUN python3 -m pip install --no-cache-dir --break-system-packages \
      ocrmypdf img2pdf mistralai

# Allow ImageMagick PDF read/write (IM6 and IM7 paths)
RUN set -e; \
    for policy in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do \
      if [ -f "$policy" ]; then \
        sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' "$policy" || true; \
      fi; \
    done

WORKDIR /data
CMD ["tail", "-f", "/dev/null"]
