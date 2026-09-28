"""Prueba real del motor local en la imagen Docker, sin claves ni llamadas a IA."""

import sys
from pathlib import Path

from pypdf import PdfReader

from app.services.extraction import extract_pdf_pages


def main():
    path = Path(sys.argv[1])
    assert not PdfReader(path).pages[0].extract_text(), "El fixture debe ser una imagen"
    pages = extract_pdf_pages(path, ocr_enabled=True)
    assert len(pages) == 1 and getattr(pages[0][1], "ocr", False)
    text = pages[0][1]
    for value in ("8 HOUR", "55.00", "440.00", "1490.00", "1930.00", "135.10", "2065.10"):
        assert value in text, f"OCR no conservó {value}"
    print("OCR real: página y siete campos críticos conservados; fixture sintético.")


if __name__ == "__main__":
    main()
