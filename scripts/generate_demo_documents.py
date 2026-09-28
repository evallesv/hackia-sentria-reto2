"""Generador de documentos sintéticos oficiales en formato PDF y XLSX para los casos A, B, C y D."""

import io
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data/demo/sources"


def create_pdf(title: str, lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # Encabezado
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, title)
    c.drawString(
        50, 735, "Sentria · Auditor Agéntico de Facturación de Siniestros (Datos Sintéticos)"
    )
    c.setLineWidth(0.5)
    c.line(50, 725, 550, 725)

    # Contenido
    c.setFont("Helvetica", 10)
    y = 700
    for line in lines:
        if line.startswith("SUBTOTAL:") or line.startswith("TOTAL:"):
            c.setFont("Helvetica-Bold", 10)
            y -= 5
        c.drawString(50, y, line)
        if line.startswith("SUBTOTAL:") or line.startswith("TOTAL:"):
            c.setFont("Helvetica", 10)
        y -= 20
        if y < 50:
            c.showPage()
            y = 750

    c.save()
    return buf.getvalue()


def create_xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tarifario"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main():
    print("Generando documentos sintéticos oficiales en PDF y XLSX...")

    # ==========================
    # CASO A: Sin discrepancias
    # ==========================
    dir_a = SOURCES / "A"
    dir_a.mkdir(parents=True, exist_ok=True)

    (dir_a / "billing.pdf").write_bytes(
        create_pdf(
            "FACTURA DE REPARACIÓN VEHICULAR · EXPEDIENTE DEMO-A",
            [
                "Taller Automotriz: AutoReparaciones del Istmo S.A.",
                "Número de Factura: FAC-2026-001A | Moneda: USD",
                "",
                "DETALLE DE CONCEPTOS Y MANO DE OBRA:",
                "Pintura frontal: 8 HOUR × USD 45.00 = USD 360.00",
                "Parachoques frontal: 1 UNIT × USD 1490.00 = USD 1490.00",
                "",
                "SUBTOTAL: USD 1850.00",
                "IMPUESTOS: USD 0.00",
                "TOTAL: USD 1850.00",
            ],
        )
    )

    (dir_a / "incident.pdf").write_bytes(
        create_pdf(
            "DECLARACIÓN DE SINIESTRO AUTOMOTRIZ · EXPEDIENTE DEMO-A",
            [
                "Aseguradora: Seguros Sentria S.A. | Ramo: Automóvil",
                "Reporte de Evento: Declaración inicial del asegurado",
                "",
                "SINTÉTICO. Colisión frontal. Daño en parachoques, pintura y alineación frontal.",
                "El vehículo impactó contra poste a baja velocidad afectando la zona delantera.",
            ],
        )
    )

    (dir_a / "inspection.pdf").write_bytes(
        create_pdf(
            "INFORME PERICIAL DE INSPECCIÓN TÉCNICA · EXPEDIENTE DEMO-A",
            [
                "Perito Ajustador: Centro Técnico de Inspección Vehicular",
                "Verificación Visual de Daños:",
                "",
                "SINTÉTICO. Se confirma daño frontal. Cambiar parachoques, pintar y alinear.",
                "Correlación de daños: Impacto frontal directo conforme con el relato.",
            ],
        )
    )

    (dir_a / "tariff.xlsx").write_bytes(
        create_xlsx(
            [
                ["service_code", "description", "unit", "allowed_rate", "currency"],
                ["PAINT", "Pintura frontal y acabado", "HOUR", "45.00", "USD"],
                ["BUMPER", "Parachoques frontal original", "UNIT", "1490.00", "USD"],
                ["ALIGN", "Alineación y balanceo frontal", "UNIT", "170.00", "USD"],
            ]
        )
    )
    print("✓ Caso A generado (PDFs + XLSX)")

    # ==========================
    # CASO B: Diferencia tarifaria
    # ==========================
    dir_b = SOURCES / "B"
    dir_b.mkdir(parents=True, exist_ok=True)

    (dir_b / "billing.pdf").write_bytes(
        create_pdf(
            "FACTURA DE REPARACIÓN VEHICULAR · EXPEDIENTE DEMO-B",
            [
                "Taller Automotriz: AutoReparaciones del Istmo S.A.",
                "Número de Factura: FAC-2026-002B | Moneda: USD",
                "",
                "DETALLE DE CONCEPTOS Y MANO DE OBRA:",
                "Pintura frontal: 8 HOUR × USD 55.00 = USD 440.00",
                "Parachoques frontal: 1 UNIT × USD 1490.00 = USD 1490.00",
                "",
                "SUBTOTAL: USD 1930.00",
                "IMPUESTOS: USD 0.00",
                "TOTAL: USD 1930.00",
            ],
        )
    )

    (dir_b / "incident.pdf").write_bytes(
        create_pdf(
            "DECLARACIÓN DE SINIESTRO AUTOMOTRIZ · EXPEDIENTE DEMO-B",
            [
                "Aseguradora: Seguros Sentria S.A. | Ramo: Automóvil",
                "Reporte de Evento: Declaración inicial del asegurado",
                "",
                "SINTÉTICO. Colisión frontal. Daño en parachoques, pintura y alineación frontal.",
            ],
        )
    )

    (dir_b / "inspection.pdf").write_bytes(
        create_pdf(
            "INFORME PERICIAL DE INSPECCIÓN TÉCNICA · EXPEDIENTE DEMO-B",
            [
                "Perito Ajustador: Centro Técnico de Inspección Vehicular",
                "Verificación Visual de Daños:",
                "",
                "SINTÉTICO. Se confirma daño frontal. Cambiar parachoques, pintar y alinear.",
            ],
        )
    )

    (dir_b / "tariff.xlsx").write_bytes(
        create_xlsx(
            [
                ["service_code", "description", "unit", "allowed_rate", "currency"],
                ["PAINT", "Pintura frontal convenida", "HOUR", "45.00", "USD"],
                ["BUMPER", "Parachoques frontal original", "UNIT", "1490.00", "USD"],
            ]
        )
    )
    print("✓ Caso B generado (PDFs + XLSX)")

    # ==========================
    # CASO C: Múltiples hallazgos
    # ==========================
    dir_c = SOURCES / "C"
    dir_c.mkdir(parents=True, exist_ok=True)

    (dir_c / "billing.pdf").write_bytes(
        create_pdf(
            "FACTURA DE REPARACIÓN VEHICULAR · EXPEDIENTE DEMO-C",
            [
                "Taller Automotriz: Taller Central del Pacífico",
                "Número de Factura: FAC-2026-003C | Moneda: USD",
                "",
                "DETALLE DE CONCEPTOS Y MANO DE OBRA:",
                "Pintura frontal: 8 HOUR × USD 55.00 = USD 440.00",
                "Parachoques frontal: 1 UNIT × USD 1480.00 = USD 1480.00",
                "Alineación frontal: 1 UNIT × USD 170.00 = USD 170.00",
                "Alineación frontal: 1 UNIT × USD 170.00 = USD 170.00",
                "Reparación de dirección: 1 UNIT × USD 170.00 = USD 170.00",
                "",
                "SUBTOTAL: USD 2430.00",
                "IMPUESTOS: USD 0.00",
                "TOTAL: USD 2430.00",
            ],
        )
    )

    (dir_c / "incident.pdf").write_bytes(
        create_pdf(
            "DECLARACIÓN DE SINIESTRO AUTOMOTRIZ · EXPEDIENTE DEMO-C",
            [
                "Aseguradora: Seguros Sentria S.A. | Ramo: Automóvil",
                "Reporte de Evento: Declaración inicial del asegurado",
                "",
                "SINTÉTICO. Colisión frontal. Daño en parachoques, pintura y alineación frontal.",
            ],
        )
    )

    (dir_c / "inspection.pdf").write_bytes(
        create_pdf(
            "INFORME PERICIAL DE INSPECCIÓN TÉCNICA · EXPEDIENTE DEMO-C",
            [
                "Perito Ajustador: Centro Técnico de Inspección Vehicular",
                "Verificación Visual de Daños:",
                "",
                "SINTÉTICO. Se confirma daño frontal. Cambiar parachoques, pintar y alinear.",
            ],
        )
    )

    (dir_c / "tariff.xlsx").write_bytes(
        create_xlsx(
            [
                ["service_code", "description", "unit", "allowed_rate", "currency"],
                ["PAINT", "Pintura frontal convenida", "HOUR", "45.00", "USD"],
                ["BUMPER", "Parachoques frontal", "UNIT", "1480.00", "USD"],
                ["ALIGN", "Alineación frontal", "UNIT", "170.00", "USD"],
                ["STEER", "Reparación de dirección", "UNIT", "170.00", "USD"],
            ]
        )
    )
    print("✓ Caso C generado (PDFs + XLSX)")

    # ==========================
    # CASO D: Información incompleta (sin tarifario)
    # ==========================
    dir_d = SOURCES / "D"
    dir_d.mkdir(parents=True, exist_ok=True)

    (dir_d / "billing.pdf").write_bytes(
        create_pdf(
            "FACTURA DE REPARACIÓN VEHICULAR · EXPEDIENTE DEMO-D",
            [
                "Taller Automotriz: Taller Rápido Especializado",
                "Número de Factura: FAC-2026-004D | Moneda: USD",
                "",
                "DETALLE DE CONCEPTOS Y MANO DE OBRA:",
                "Pintura frontal: 8 HOUR × USD 55.00 = USD 440.00",
                "Parachoques frontal: 1 UNIT × USD 1490.00 = USD 1490.00",
                "",
                "SUBTOTAL: USD 1930.00",
                "IMPUESTOS: USD 0.00",
                "TOTAL: USD 1930.00",
            ],
        )
    )

    (dir_d / "incident.pdf").write_bytes(
        create_pdf(
            "DECLARACIÓN DE SINIESTRO AUTOMOTRIZ · EXPEDIENTE DEMO-D",
            [
                "Aseguradora: Seguros Sentria S.A. | Ramo: Automóvil",
                "",
                "SINTÉTICO. Colisión frontal. Daño en parachoques, pintura y alineación frontal.",
            ],
        )
    )

    (dir_d / "inspection.pdf").write_bytes(
        create_pdf(
            "INFORME PERICIAL DE INSPECCIÓN TÉCNICA · EXPEDIENTE DEMO-D",
            [
                "Perito Ajustador: Centro Técnico de Inspección Vehicular",
                "",
                "SINTÉTICO. Se confirma daño frontal. Cambiar parachoques, pintar y alinear.",
            ],
        )
    )
    # NOTA: En Caso D deliberadamente NO se genera tariff.xlsx
    print("✓ Caso D generado (PDFs, sin tarifario deliberadamente)")
    print("Generación completada exitosamente.")


if __name__ == "__main__":
    main()
