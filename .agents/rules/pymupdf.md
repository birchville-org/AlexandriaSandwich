# PyMuPDF Import Standard

- In sämtlichen Python-Skripten, CLI-Befehlen, Ad-hoc-Analysen und Testaufrufen NIEMALS `fitz` oder `import fitz` verwenden.
- Ausschließlich `import pymupdf` verwenden:
  ```python
  import pymupdf
  doc = pymupdf.open(...)
  ```
- `fitz` ist in aktuellen PyMuPDF-Versionen veraltet und wirft `warning: The fitz API is deprecated and will be removed in future. Use import pymupdf instead.` auf `stderr`.
