"""Genera un PDF sintético de imagen sin capa de texto para evaluar OCR real."""

import io
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / "data/demo/ocr/cotizacion-escaneada.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = io.BytesIO()
    document = canvas.Canvas(source, pagesize=(612, 792), invariant=True)
    document.setFont("Helvetica", 14)
    lines = [
        "COTIZACION DE TALLER - DATOS SINTETICOS",
        "Propuesta de reparacion frontal; requiere aprobacion previa.",
        "Pintura frontal: 8 HOUR x USD 55.00 = USD 440.00",
        "Parachoques frontal: 1 UNIT x USD 1490.00 = USD 1490.00",
        "SUBTOTAL: USD 1930.00",
        "ITBMS 7%: USD 135.10",
        "TOTAL: USD 2065.10",
    ]
    for index, text in enumerate(lines):
        document.drawString(36, 740 - index * 45, text)
    document.save()
    with pdfium.PdfDocument(source.getvalue()) as pdf:
        page = pdf[0]
        bitmap = page.render(scale=300 / 72)
        image = bitmap.to_pil()
        try:
            scan = canvas.Canvas(str(target), pagesize=(612, 792), invariant=True)
            scan.drawImage(ImageReader(image), 0, 0, width=612, height=792)
            scan.save()
        finally:
            image.close()
            bitmap.close()
            page.close()
    print(target)


if __name__ == "__main__":
    main()
