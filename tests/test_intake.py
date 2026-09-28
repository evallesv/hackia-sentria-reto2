"""Pruebas exhaustivas para el intake seguro y contratos documentales (T01)."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import DocumentKind


def make_valid_pdf_bytes(label: str = "test") -> bytes:
    content = f"1 0 obj\n<< /Title ({label}) >>\nendobj\n"
    return f"%PDF-1.4\n{content}trailer\n<<>>\n%%EOF\n".encode("latin-1")


def make_valid_xlsx_bytes(sheet_name: str = "Sheet1") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b"<Types><Default Extension='xml'/></Types>")
        workbook_xml = f"<workbook><sheet name='{sheet_name}'/></workbook>".encode()
        zf.writestr("xl/workbook.xml", workbook_xml)
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


def test_create_and_get_claim(client):
    res = client.post("/api/claims", json={"claim_id": "CLM-2026-001"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "CLM-2026-001"
    assert data["status"] == "DRAFT"
    assert data["documents"] == []

    # Obtener el claim creado
    res2 = client.get("/api/claims/CLM-2026-001")
    assert res2.status_code == 200
    assert res2.json()["id"] == "CLM-2026-001"

    # Claim inexistente
    res3 = client.get("/api/claims/NO_EXISTE")
    assert res3.status_code == 404


def test_upload_valid_pdf_and_xlsx(client):
    client.post("/api/claims", json={"claim_id": "CLM-VALID"})

    pdf_bytes = make_valid_pdf_bytes("Siniestro 001")
    res_pdf = client.post(
        "/api/claims/CLM-VALID/documents",
        data={"kind": DocumentKind.INCIDENT.value},
        files={"file": ("informe_siniestro.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_pdf.status_code == 201
    doc_pdf = res_pdf.json()
    assert doc_pdf["claim_id"] == "CLM-VALID"
    assert doc_pdf["kind"] == "INCIDENT_REPORT"
    assert doc_pdf["mime"] == "application/pdf"
    assert doc_pdf["byte_count"] == len(pdf_bytes)
    assert len(doc_pdf["sha256"]) == 64
    assert doc_pdf["version"] == 1
    assert doc_pdf["active"] is True
    # Invariante de seguridad: no exponer rutas internas del filesystem
    assert "storage_path" not in doc_pdf
    assert "internal_path" not in doc_pdf
    assert "/" not in doc_pdf["filename"]

    xlsx_bytes = make_valid_xlsx_bytes("Tarifario 2026")
    res_xlsx = client.post(
        "/api/claims/CLM-VALID/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={
            "file": (
                "tarifario_acordado.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert res_xlsx.status_code == 201
    doc_xlsx = res_xlsx.json()
    assert doc_xlsx["kind"] == "TARIFF"
    assert doc_xlsx["version"] == 1
    assert doc_xlsx["active"] is True


def test_four_documents_intake_with_reproducible_hashes(client):
    client.post("/api/claims", json={"claim_id": "CLM-FOUR"})

    roles = [
        (DocumentKind.INCIDENT, "informe_siniestro.pdf", make_valid_pdf_bytes("Siniestro")),
        (DocumentKind.INSPECTION, "taller_inspeccion.pdf", make_valid_pdf_bytes("Inspeccion")),
        (DocumentKind.BILLING, "factura_taller.pdf", make_valid_pdf_bytes("Factura")),
        (DocumentKind.TARIFF, "tarifario.xlsx", make_valid_xlsx_bytes("Tarifas")),
    ]

    for kind, name, data in roles:
        res = client.post(
            "/api/claims/CLM-FOUR/documents",
            data={"kind": kind.value},
            files={"file": (name, data, "application/octet-stream")},
        )
        assert res.status_code == 201

    list_res = client.get("/api/claims/CLM-FOUR/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) == 4
    active_kinds = {d["kind"] for d in docs if d["active"]}
    assert active_kinds == {
        "INCIDENT_REPORT",
        "WORKSHOP_REPORT",
        "BILLING_DOCUMENT",
        "TARIFF",
    }


def test_reject_path_traversal_filenames(client):
    client.post("/api/claims", json={"claim_id": "CLM-SEC"})
    pdf = make_valid_pdf_bytes()

    traversal_names = [
        "../../etc/passwd.pdf",
        "..\\..\\boot.ini.pdf",
        "/etc/shadow.pdf",
        "folder/evil.pdf",
    ]
    for bad_name in traversal_names:
        res = client.post(
            "/api/claims/CLM-SEC/documents",
            data={"kind": DocumentKind.INCIDENT.value},
            files={"file": (bad_name, pdf, "application/pdf")},
        )
        assert res.status_code == 400
        detail = res.json()["detail"].lower()
        assert "secuencias de ruta" in detail or "caracteres" in detail


def test_reject_executable_and_script_mime_spoofing(client):
    client.post("/api/claims", json={"claim_id": "CLM-EXE"})

    # Windows PE spoofing as PDF
    res1 = client.post(
        "/api/claims/CLM-EXE/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura.pdf", b"MZ\x90\x00\x03\x00\x00\x00", "application/pdf")},
    )
    assert res1.status_code == 400
    assert "ejecutable" in res1.json()["detail"].lower()

    # Linux ELF spoofing as XLSX
    res2 = client.post(
        "/api/claims/CLM-EXE/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={"file": ("tarifario.xlsx", b"\x7fELF\x02\x01\x01\x00", "application/octet-stream")},
    )
    assert res2.status_code == 400
    assert "ejecutable" in res2.json()["detail"].lower()

    # Shell script spoofing as PDF
    res3 = client.post(
        "/api/claims/CLM-EXE/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("script.pdf", b"#!/bin/bash\nrm -rf /", "application/pdf")},
    )
    assert res3.status_code == 400


def test_reject_corrupt_pdf(client):
    client.post("/api/claims", json={"claim_id": "CLM-CORRUPT"})

    # Falta %PDF-
    res1 = client.post(
        "/api/claims/CLM-CORRUPT/documents",
        data={"kind": DocumentKind.INCIDENT.value},
        files={"file": ("corrupto1.pdf", b"DATOS_INVALIDOS%%EOF", "application/pdf")},
    )
    assert res1.status_code == 400

    # Falta %%EOF
    res2 = client.post(
        "/api/claims/CLM-CORRUPT/documents",
        data={"kind": DocumentKind.INCIDENT.value},
        files={"file": ("corrupto2.pdf", b"%PDF-1.4\n1 0 obj\nsin final", "application/pdf")},
    )
    assert res2.status_code == 400
    assert "corrupto" in res2.json()["detail"].lower()


def test_reject_xlsx_with_macros_or_bad_structure(client):
    client.post("/api/claims", json={"claim_id": "CLM-MACRO"})

    # XLSX con macro (vbaProject.bin)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("xl/vbaProject.bin", b"MACRO_PAYLOAD")
    res_macro = client.post(
        "/api/claims/CLM-MACRO/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={"file": ("tarifas.xlsx", buf.getvalue(), "application/octet-stream")},
    )
    assert res_macro.status_code == 400
    assert "macro" in res_macro.json()["detail"].lower()

    # XLSX sin [Content_Types].xml
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as zf:
        zf.writestr("test.txt", b"plain text")
    res_bad = client.post(
        "/api/claims/CLM-MACRO/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={"file": ("invalido.xlsx", buf2.getvalue(), "application/octet-stream")},
    )
    assert res_bad.status_code == 400


def test_reject_empty_and_oversized_files(client):
    client.post("/api/claims", json={"claim_id": "CLM-LIMITS"})

    # Archivo vacío (0 bytes)
    res_empty = client.post(
        "/api/claims/CLM-LIMITS/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("vacio.pdf", b"", "application/pdf")},
    )
    assert res_empty.status_code == 400
    assert "vacío" in res_empty.json()["detail"].lower()

    # Archivo que excede 10 MiB
    oversized = b"%PDF-1.4\n" + (b"A" * (10 * 1024 * 1024 + 10)) + b"\n%%EOF"
    res_big = client.post(
        "/api/claims/CLM-LIMITS/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("grande.pdf", oversized, "application/pdf")},
    )
    assert res_big.status_code == 413


def test_reject_duplicate_file_in_same_claim(client):
    client.post("/api/claims", json={"claim_id": "CLM-DUP"})
    pdf = make_valid_pdf_bytes("Identico")

    # Primera subida -> 201
    res1 = client.post(
        "/api/claims/CLM-DUP/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura_v1.pdf", pdf, "application/pdf")},
    )
    assert res1.status_code == 201

    # Segunda subida del mismo contenido -> 409 Conflicto
    res2 = client.post(
        "/api/claims/CLM-DUP/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura_repetida.pdf", pdf, "application/pdf")},
    )
    assert res2.status_code == 409
    assert "duplicado" in res2.json()["detail"].lower()


def test_versioning_and_two_active_invoices_produce_conflict(client):
    client.post("/api/claims", json={"claim_id": "CLM-VERS"})

    # Versión 1 de factura -> queda activa
    pdf1 = make_valid_pdf_bytes("Factura v1")
    res1 = client.post(
        "/api/claims/CLM-VERS/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura_v1.pdf", pdf1, "application/pdf")},
    )
    assert res1.status_code == 201
    doc1 = res1.json()
    assert doc1["version"] == 1
    assert doc1["active"] is True

    # Versión 2 de factura (contenido distinto) -> versión 2, queda inactiva por defecto
    pdf2 = make_valid_pdf_bytes("Factura v2 corregida")
    res2 = client.post(
        "/api/claims/CLM-VERS/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura_v2.pdf", pdf2, "application/pdf")},
    )
    assert res2.status_code == 201
    doc2 = res2.json()
    assert doc2["version"] == 2
    assert doc2["active"] is False

    # Invariante T01: Si el usuario intenta activar dos facturas al mismo tiempo -> CONFLICTO 409
    patch_conflict = client.patch(
        "/api/claims/CLM-VERS/active-documents",
        json={"active_document_ids": [doc1["id"], doc2["id"]]},
    )
    assert patch_conflict.status_code == 409
    assert "no se permite más de un documento activo" in patch_conflict.json()["detail"].lower()

    # Activar solo la versión 2 -> ÉXITO
    patch_ok = client.patch(
        "/api/claims/CLM-VERS/active-documents",
        json={"active_document_ids": [doc2["id"]]},
    )
    assert patch_ok.status_code == 200
    updated_docs = patch_ok.json()
    doc1_updated = next(d for d in updated_docs if d["id"] == doc1["id"])
    doc2_updated = next(d for d in updated_docs if d["id"] == doc2["id"])
    assert doc1_updated["active"] is False
    assert doc2_updated["active"] is True


def test_cross_claim_isolation_and_download(client):
    client.post("/api/claims", json={"claim_id": "CLM-A"})
    client.post("/api/claims", json={"claim_id": "CLM-B"})

    pdf = make_valid_pdf_bytes("Claim A Secret Data")
    res_upload = client.post(
        "/api/claims/CLM-A/documents",
        data={"kind": DocumentKind.INCIDENT.value},
        files={"file": ("privado.pdf", pdf, "application/pdf")},
    )
    doc_id = res_upload.json()["id"]

    # Descarga legítima desde Claim A
    res_dl = client.get(f"/api/claims/CLM-A/documents/{doc_id}")
    assert res_dl.status_code == 200
    assert res_dl.content == pdf

    # Intento de acceso cruzado desde Claim B -> 404
    res_cross = client.get(f"/api/claims/CLM-B/documents/{doc_id}")
    assert res_cross.status_code == 404

    # Intento de activar documento ajeno en Claim B -> 404
    res_patch = client.patch(
        "/api/claims/CLM-B/active-documents",
        json={"active_document_ids": [doc_id]},
    )
    assert res_patch.status_code == 404


def test_delete_claim_and_storage_cleanup(client):
    client.post("/api/claims", json={"claim_id": "CLM-DEL"})
    pdf = make_valid_pdf_bytes("Para borrar")
    res_upload = client.post(
        "/api/claims/CLM-DEL/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("borrar.pdf", pdf, "application/pdf")},
    )
    assert res_upload.status_code == 201

    # Borrado
    del_res = client.delete("/api/claims/CLM-DEL")
    assert del_res.status_code == 204

    # Verificar que ya no existe
    assert client.get("/api/claims/CLM-DEL").status_code == 404
    assert client.get("/api/claims/CLM-DEL/documents").status_code == 404
