"""Pruebas exhaustivas para la extracción estructurada de documentos (T02)."""

import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from app.config import Settings
from app.main import create_app
from app.models import DocumentKind
from app.services.extraction import (
    extract_pdf_pages,
    extract_xlsx_tariffs,
)


def create_sample_pdf(pages_text: list[str]) -> bytes:
    writer = PdfWriter()
    for _text in pages_text:
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_pdf_with_text(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 25
    c.save()
    return buf.getvalue()


def create_sample_xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tarifas"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        ai_mode="mock",
        upload_dir=str(tmp_path / "uploads"),
        max_upload_bytes=10 * 1024 * 1024,
    )
    app = create_app(settings)
    return TestClient(app)


def test_extract_xlsx_tariffs_success(tmp_path):
    rows = [
        ["service_code", "description", "unit", "allowed_rate", "currency"],
        ["PAINT", "Pintura general", "HOUR", "45.00", "USD"],
        ["BUMPER", "Parachoques frontal", "UNIT", "1490.00", "USD"],
        ["ALIGNMENT", "Alineación y balanceo", "UNIT", "60.00", "USD"],
    ]
    xlsx_path = tmp_path / "test_tarifario.xlsx"
    xlsx_path.write_bytes(create_sample_xlsx(rows))

    tariffs = extract_xlsx_tariffs(xlsx_path)
    assert len(tariffs) == 3
    assert tariffs[0]["service_code"] == "PAINT"
    assert tariffs[0]["allowed_rate"] == "45.00"
    assert tariffs[0]["unit"] == "HOUR"
    assert tariffs[1]["service_code"] == "BUMPER"
    assert tariffs[1]["allowed_rate"] == "1490.00"


def test_extract_xlsx_rejects_missing_headers(tmp_path):
    rows = [
        ["col1", "col2", "col3"],
        ["A", "B", "C"],
    ]
    xlsx_path = tmp_path / "invalido.xlsx"
    xlsx_path.write_bytes(create_sample_xlsx(rows))

    with pytest.raises(Exception) as exc:
        extract_xlsx_tariffs(xlsx_path)
    assert "Encabezados requeridos no encontrados" in str(exc.value)


def test_extract_pdf_pages_detects_scanned_pdf(tmp_path):
    pdf_bytes = create_sample_pdf(["", ""])
    pdf_path = tmp_path / "escaneado.pdf"
    pdf_path.write_bytes(pdf_bytes)

    pages = extract_pdf_pages(pdf_path)
    assert len(pages) == 1
    assert "DOCUMENTO ESCANEADO" in pages[0][1]


def test_extract_pdf_rejects_excessive_pages(tmp_path):
    pdf_bytes = create_sample_pdf(["página"] * 35)
    pdf_path = tmp_path / "largo.pdf"
    pdf_path.write_bytes(pdf_bytes)

    with pytest.raises(Exception) as exc:
        extract_pdf_pages(pdf_path, max_pages=30)
    assert "excede el límite máximo de 30 páginas" in str(exc.value)


def test_end_to_end_extraction_normalization_and_audit(client):
    # 1. Crear claim
    res_claim = client.post("/api/claims", json={"claim_id": "CLM-E2E-EXTRACT"})
    assert res_claim.status_code == 201

    # 2. Generar documentos con texto simulado para caso B (tarifa 55 vs 45 x 8 = 80 USD)
    incident_text = "SINTÉTICO. Colisión frontal. Daño en parachoques y pintura frontal."
    inspection_text = "SINTÉTICO. Se confirma daño frontal. Cambiar parachoques y pintar."
    billing_text = (
        "SINTÉTICO. FACTURA 001\n"
        "Pintura frontal: 8 HOUR × USD 55.00 = USD 440.00\n"
        "Parachoques frontal: 1 UNIT × USD 1490.00 = USD 1490.00\n"
    )
    tariff_rows = [
        ["service_code", "description", "unit", "allowed_rate", "currency"],
        ["PAINT", "Pintura frontal", "HOUR", "45.00", "USD"],
        ["BUMPER", "Parachoques frontal", "UNIT", "1490.00", "USD"],
    ]

    xlsx_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Subir documentos al claim
    client.post(
        "/api/claims/CLM-E2E-EXTRACT/documents",
        data={"kind": DocumentKind.INCIDENT.value},
        files={"file": ("siniestro.pdf", create_pdf_with_text([incident_text]))},
    )
    client.post(
        "/api/claims/CLM-E2E-EXTRACT/documents",
        data={"kind": DocumentKind.INSPECTION.value},
        files={"file": ("inspeccion.pdf", create_pdf_with_text([inspection_text]))},
    )
    client.post(
        "/api/claims/CLM-E2E-EXTRACT/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura.pdf", create_pdf_with_text(billing_text.splitlines()))},
    )
    client.post(
        "/api/claims/CLM-E2E-EXTRACT/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={"file": ("tarifas.xlsx", create_sample_xlsx(tariff_rows), xlsx_mime)},
    )

    # 3. Ejecutar extracción
    res_ext = client.post("/api/claims/CLM-E2E-EXTRACT/extract")
    assert res_ext.status_code == 200
    snapshot = res_ext.json()
    assert snapshot["claim_id"] == "CLM-E2E-EXTRACT"
    assert len(snapshot["items"]) == 2
    assert len(snapshot["tariffs"]) == 2
    assert "FRONT_PAINT" in snapshot["reported_damage_codes"]
    assert "FRONT_BUMPER" in snapshot["reported_damage_codes"]

    # 4. Consultar snapshot persistido
    res_snap = client.get("/api/claims/CLM-E2E-EXTRACT/snapshot")
    assert res_snap.status_code == 200
    assert res_snap.json()["items"][0]["service_code"] == "PAINT"

    # 5. Confirmar normalización (PUT /api/claims/{id}/normalized)
    confirm_payload = {
        "billing_kind": "INVOICE",
        "reported_damage_codes": snapshot["reported_damage_codes"],
        "inspected_damage_codes": snapshot["inspected_damage_codes"],
        "items": [
            {
                "id": "item_1",
                "description": "Pintura frontal",
                "service_code": "PAINT",
                "damage_code": "FRONT_PAINT",
                "unit": "HOUR",
                "quantity": "8.0000",
                "unit_price": "55.00",
                "line_total": "440.00",
                "evidence_id": snapshot["items"][0]["evidence_id"],
            },
            {
                "id": "item_2",
                "description": "Parachoques frontal",
                "service_code": "BUMPER",
                "damage_code": "FRONT_BUMPER",
                "unit": "UNIT",
                "quantity": "1.0000",
                "unit_price": "1490.00",
                "line_total": "1490.00",
                "evidence_id": snapshot["items"][1]["evidence_id"],
            },
        ],
        "tariffs": [
            {
                "service_code": "PAINT",
                "unit": "HOUR",
                "allowed_rate": "45.00",
                "evidence_id": snapshot["tariffs"][0]["evidence_id"],
            },
            {
                "service_code": "BUMPER",
                "unit": "UNIT",
                "allowed_rate": "1490.00",
                "evidence_id": snapshot["tariffs"][1]["evidence_id"],
            },
        ],
        "subtotal": "1930.00",
        "taxes": "0.00",
        "total": "1930.00",
    }

    res_norm = client.put("/api/claims/CLM-E2E-EXTRACT/normalized", json=confirm_payload)
    assert res_norm.status_code == 200
    norm_data = res_norm.json()
    assert norm_data["subtotal"] == "1930.00"

    # 6. Ejecutar auditoría sobre el siniestro normalizado
    res_audit = client.post("/api/claims/CLM-E2E-EXTRACT/audits")
    assert res_audit.status_code == 200
    audit = res_audit.json()
    assert audit["status"] == "REVIEW_REQUIRED"
    assert audit["billed_amount"] == "1930.00"
    # Diferencia por tarifa en pintura: (55 - 45) * 8 = 80.00 USD exactos
    assert audit["flagged_difference"] == "80.00"
    assert audit["reference_subtotal"] == "1850.00"
    assert any(f["code"] == "RATE_MISMATCH" for f in audit["findings"])
