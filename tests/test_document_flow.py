import io

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.main import create_app
from app.models import DocumentKind


def pdf(text):
    stream = io.BytesIO()
    page = canvas.Canvas(stream)
    page.drawString(30, 700, text)
    page.save()
    return stream.getvalue()


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(
            _env_file=None,
            ai_mode="mock",
            upload_dir=str(tmp_path / "uploads"),
            standard_tariff_enabled=True,
        )
    )
    return TestClient(app)


def test_new_claim_automatically_includes_standard_tariff(client):
    response = client.post("/api/claims", json={"claim_id": "CLM-STANDARD"})
    assert response.status_code == 201
    documents = client.get("/api/claims/CLM-STANDARD/documents").json()
    assert len(documents) == 1
    assert documents[0]["kind"] == "TARIFF"
    assert documents[0]["active"] is True
    assert "estandar" in documents[0]["filename"]


def test_upload_without_role_uses_classifier_and_allows_correction(client):
    class Classifier:
        def classify(self, pages):
            assert "COTIZACION" in pages[0][1]
            return DocumentKind.BILLING

    client.app.state.document_provider = Classifier()
    client.post("/api/claims", json={"claim_id": "CLM-AUTO"})
    response = client.post(
        "/api/claims/CLM-AUTO/documents",
        files={"file": ("formato_taller.pdf", pdf("COTIZACION del taller sintetico"))},
    )
    assert response.status_code == 201
    doc = response.json()
    assert doc["kind"] == "BILLING_DOCUMENT"
    corrected = client.patch(
        f"/api/claims/CLM-AUTO/documents/{doc['id']}", json={"kind": "WORKSHOP_REPORT"}
    )
    assert corrected.status_code == 200
    assert corrected.json()["kind"] == "WORKSHOP_REPORT"


def test_classifier_failure_does_not_store_unclassified_document(client):
    from app.agent.provider import ProviderError

    class FailedClassifier:
        def classify(self, pages):
            raise ProviderError("No disponible")

    client.app.state.document_provider = FailedClassifier()
    client.post("/api/claims", json={"claim_id": "CLM-FAILED"})
    response = client.post(
        "/api/claims/CLM-FAILED/documents",
        files={"file": ("desconocido.pdf", pdf("documento sintetico sin clasificacion"))},
    )
    assert response.status_code == 503
    docs = client.get("/api/claims/CLM-FAILED/documents").json()
    assert [d["kind"] for d in docs] == ["TARIFF"]


def test_standard_tariff_replacement_affects_only_new_claims(client):
    from openpyxl import Workbook

    client.post("/api/claims", json={"claim_id": "CLM-BEFORE"})
    original = client.get("/api/claims/CLM-BEFORE/documents").json()[0]
    workbook = Workbook()
    workbook.active.append(["service_code", "unit", "allowed_rate", "currency"])
    workbook.active.append(["PAINT", "HOUR", "40.00", "USD"])
    stream = io.BytesIO()
    workbook.save(stream)
    response = client.put(
        "/api/claims/settings/standard-tariff",
        files={"file": ("nuevo.xlsx", stream.getvalue())},
    )
    assert response.status_code == 200
    client.post("/api/claims", json={"claim_id": "CLM-AFTER"})
    updated = client.get("/api/claims/CLM-AFTER/documents").json()[0]
    assert original["sha256"] != updated["sha256"]
    assert client.get("/api/claims/CLM-BEFORE/documents").json()[0]["sha256"] == original["sha256"]


def test_gemini_extracts_supplier_layout_and_rejects_unbacked_values(client):
    from app.agent.documents import GeminiDocumentProvider
    from app.agent.provider import GeminiProvider, ProviderError
    from app.models import StoredDocument
    from app.services.extraction import extract_pdf_pages

    claim_id = "CLM-FORMAT"
    client.post(f"/api/claims/{claim_id}/preset/B")
    service = client.app.state.intake_service
    documents = [
        StoredDocument.model_validate(d)
        for d in client.get(f"/api/claims/{claim_id}/documents").json()
    ]
    paths = {d.id: service.get_document_file(claim_id, d.id)[1] for d in documents}
    billing = next(d for d in documents if d.kind == DocumentKind.BILLING)
    text = extract_pdf_pages(paths[billing.id])[0][1]
    lines = text.splitlines()
    quote = next(line for line in lines if "Pintura frontal: 8" in line)
    total_quote = text[text.index("SUBTOTAL:") :]
    settings = Settings(_env_file=None, gemini_api_key="test-key", gemini_model="test-model")
    provider = GeminiDocumentProvider(settings, GeminiProvider(settings))
    output = {
        "billing_kind": "QUOTE",
        "items": [
            {
                "description": "Pintura frontal",
                "service_code": "PAINT",
                "damage_code": "FRONT",
                "unit": "HOUR",
                "quantity": "8",
                "unit_price": "55.00",
                "line_total": "440.00",
                "page": 1,
                "quote": quote,
            }
        ],
        "reported_damage_codes": [],
        "inspected_damage_codes": [],
        "sources": [],
        "subtotal": "1930.00",
        "taxes": "135.10",
        "total": "2065.10",
        "totals_page": 1,
        "totals_quote": total_quote,
        "review_notes": [],
    }
    provider.generate = lambda *args: output
    snapshot = provider.extract(claim_id, documents, paths)
    assert snapshot.billing_kind == "QUOTE"
    assert str(snapshot.items[0].unit_price) == "55.00"
    assert snapshot.evidence[-2].text == quote
    output["items"][0]["unit_price"] = "999.00"
    with pytest.raises(ProviderError, match="respaldo"):
        provider.extract(claim_id, documents, paths)
    output["items"][0]["unit_price"] = "55.00"
    output["items"][0]["quote"] = "Cita inventada"
    with pytest.raises(ProviderError, match="inexistente"):
        provider.extract(claim_id, documents, paths)


def test_classification_requires_real_quote_and_budget_is_shared(monkeypatch):
    import json
    from types import SimpleNamespace

    from google import genai
    from google.genai import types

    from app.agent.documents import GeminiDocumentProvider
    from app.agent.provider import GeminiProvider, ProviderError

    result = {"kind": "BILLING_DOCUMENT", "page": 1, "quote": "COTIZACION"}
    captured = {}

    class Client:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(generate_content=self.generate)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def generate(self, **kwargs):
            captured.update(kwargs)
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        finish_reason="STOP",
                        content=types.Content(parts=[types.Part(text=json.dumps(result))]),
                    )
                ]
            )

    monkeypatch.setattr(genai, "Client", Client)
    settings = Settings(
        _env_file=None,
        gemini_api_key="test-key",
        gemini_model="test-model",
        llm_max_calls_per_process=2,
    )
    budget = GeminiProvider(settings)
    provider = GeminiDocumentProvider(settings, budget)
    assert provider.classify([(1, "COTIZACION sintetica")]) == DocumentKind.BILLING
    assert captured["config"].automatic_function_calling.disable is True
    assert captured["config"].tools is None
    result["quote"] = "Texto inventado"
    with pytest.raises(ProviderError, match="inexistente"):
        provider.classify([(1, "COTIZACION sintetica")])
    with pytest.raises(ProviderError, match="Límite"):
        budget.reserve_call()


@pytest.mark.parametrize("unit,rate", [("DESCONOCIDA", "45.00"), ("HOUR", "=20+25")])
def test_invalid_standard_tariff_preserves_previous_version(client, unit, rate):
    from openpyxl import Workbook

    original = client.get("/api/claims/settings/standard-tariff/file").content
    workbook = Workbook()
    workbook.active.append(["service_code", "unit", "allowed_rate", "currency"])
    workbook.active.append(["PAINT", unit, rate, "USD"])
    stream = io.BytesIO()
    workbook.save(stream)
    response = client.put(
        "/api/claims/settings/standard-tariff", files={"file": ("invalido.xlsx", stream.getvalue())}
    )
    assert response.status_code == 422
    assert client.get("/api/claims/settings/standard-tariff/file").content == original


def test_correction_invalidates_snapshot_and_normalization_cannot_invent_evidence(client):
    claim_id = "CLM-CORRECT"
    response = client.post(f"/api/claims/{claim_id}/preset/B")
    snapshot = response.json()
    fields = [
        "billing_kind",
        "reported_damage_codes",
        "inspected_damage_codes",
        "items",
        "tariffs",
        "subtotal",
        "taxes",
        "total",
    ]
    payload = {key: snapshot[key] for key in fields}
    for item in [*payload["items"], *payload["tariffs"]]:
        item.pop("review_reason", None)
    assert client.put(f"/api/claims/{claim_id}/normalized", json=payload).status_code == 200
    document = next(
        d
        for d in client.get(f"/api/claims/{claim_id}/documents").json()
        if d["kind"] == "BILLING_DOCUMENT"
    )
    assert (
        client.patch(
            f"/api/claims/{claim_id}/documents/{document['id']}", json={"kind": "WORKSHOP_REPORT"}
        ).status_code
        == 200
    )
    assert client.post(f"/api/claims/{claim_id}/audits").status_code == 400
    payload["items"][0]["evidence_id"] = "INVENTADO"
    assert client.put(f"/api/claims/{claim_id}/normalized", json=payload).status_code == 422


def test_failed_reextraction_blocks_previously_confirmed_audit(client):
    claim_id = "CLM-REEXTRACT"
    snapshot = client.post(f"/api/claims/{claim_id}/preset/B").json()
    fields = [
        "billing_kind",
        "reported_damage_codes",
        "inspected_damage_codes",
        "items",
        "tariffs",
        "subtotal",
        "taxes",
        "total",
    ]
    payload = {key: snapshot[key] for key in fields}
    for row in [*payload["items"], *payload["tariffs"]]:
        row.pop("review_reason", None)
    assert client.put(f"/api/claims/{claim_id}/normalized", json=payload).status_code == 200

    class FailedExtraction:
        def extract(self, *args):
            raise ValueError("Invalid provider units")

    client.app.state.document_provider = FailedExtraction()
    assert client.post(f"/api/claims/{claim_id}/extract").status_code == 422
    assert client.post(f"/api/claims/{claim_id}/audits").status_code == 400
