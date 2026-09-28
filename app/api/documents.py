import hashlib
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.agent.provider import ProviderError
from app.models import (
    ActiveDocumentsRequest,
    AuditInput,
    AuditResult,
    Claim,
    ClaimCreateRequest,
    ConfirmNormalizedRequest,
    Document,
    DocumentKind,
    Evidence,
    ExtractedItem,
    ExtractedTariff,
    ExtractionSnapshot,
    StoredDocument,
)
from app.services.audit_service import run_audit
from app.services.extraction import extract_claim_snapshot, extract_pdf_pages, extract_xlsx_tariffs
from app.services.intake import IntakeService, inspect_and_validate_file, validate_safe_filename

router = APIRouter(prefix="/api/claims", tags=["claims"])


def get_intake_service(request: Request) -> IntakeService:
    service = getattr(request.app.state, "intake_service", None)
    if not service:
        raise HTTPException(500, "Servicio de intake no inicializado")
    return service


ServiceDep = Annotated[IntakeService, Depends(get_intake_service)]


@router.post("", response_model=Claim, status_code=201)
def create_claim(
    request: Request,
    service: ServiceDep,
    payload: ClaimCreateRequest | None = None,
):
    """Crea un nuevo expediente de siniestro."""
    claim_id = payload.claim_id if payload else None
    claim = service.create_claim(claim_id)
    standard = getattr(request.app.state, "standard_tariff", None)
    if standard:
        standard.attach(service, claim.id)
    return service.get_claim(claim.id)


@router.get("/{claim_id}", response_model=Claim)
def get_claim(
    claim_id: str,
    service: ServiceDep,
):
    """Obtiene los detalles y documentos de un expediente."""
    return service.get_claim(claim_id)


@router.get("/{claim_id}/documents", response_model=list[StoredDocument])
def list_documents(
    claim_id: str,
    service: ServiceDep,
):
    """Lista todos los documentos almacenados para un expediente."""
    return service.list_documents(claim_id)


@router.post("/{claim_id}/documents", response_model=StoredDocument, status_code=201)
async def upload_document(
    claim_id: str,
    request: Request,
    file: Annotated[UploadFile, File(...)],
    service: ServiceDep,
    kind: Annotated[DocumentKind | None, Form()] = None,
):
    """Sube un documento (PDF o XLSX) validando límites reales, magic bytes y unicidad."""
    content = await file.read()
    original_name = file.filename or "archivo_sin_nombre"
    clean_name = validate_safe_filename(original_name)
    inspect_and_validate_file(content, clean_name)
    if len(content) > service.max_file_bytes:
        raise HTTPException(413, "Archivo demasiado grande")
    if kind is None:
        if clean_name.lower().endswith(".xlsx"):
            kind = DocumentKind.TARIFF
        else:
            provider = getattr(request.app.state, "document_provider", None)
            if provider is None:
                raise HTTPException(422, "Clasificación Gemini no disponible; selecciona el tipo.")
            with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary:
                temporary.write(content)
                temporary.flush()
                pages = extract_pdf_pages(Path(temporary.name))
            if any("[DOCUMENTO ESCANEADO" in text for _, text in pages):
                raise HTTPException(422, "Documento sin texto digital; requiere OCR.")
            try:
                kind = await run_in_threadpool(provider.classify, pages)
            except ProviderError as exc:
                raise HTTPException(503, str(exc)) from None
    return service.upload_document(
        claim_id=claim_id,
        data=content,
        original_filename=original_name,
        kind=kind,
    )


class DocumentCorrection(BaseModel):
    kind: DocumentKind


@router.patch("/{claim_id}/documents/{doc_id}", response_model=StoredDocument)
def correct_document_kind(
    claim_id: str, doc_id: str, payload: DocumentCorrection, service: ServiceDep
):
    document, path = service.get_document_file(claim_id, doc_id)
    document = document.model_copy(update={"kind": payload.kind, "active": False})
    service.repository.add_document(claim_id, document, path)
    active = [
        d.id
        for d in service.list_documents(claim_id)
        if d.active and d.kind != payload.kind and d.id != doc_id
    ]
    service.set_active_documents(claim_id, [*active, doc_id])
    return service.get_document_file(claim_id, doc_id)[0]


@router.get("/settings/standard-tariff/file")
def standard_tariff_file(request: Request):
    standard = getattr(request.app.state, "standard_tariff", None)
    if not standard:
        raise HTTPException(404, "Tarifario estándar no configurado")
    return FileResponse(standard.path, filename="tarifario_estandar.xlsx")


@router.put("/settings/standard-tariff")
async def replace_standard_tariff(request: Request, file: Annotated[UploadFile, File(...)]):
    standard = getattr(request.app.state, "standard_tariff", None)
    if not standard:
        raise HTTPException(404, "Tarifario estándar no configurado")
    data = await file.read()
    name = validate_safe_filename(file.filename or "tarifario.xlsx")
    inspect_and_validate_file(data, name)
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(422, "El tarifario estándar debe ser XLSX")
    with (
        standard.lock,
        tempfile.NamedTemporaryFile(dir=standard.path.parent, suffix=".xlsx") as tmp,
    ):
        tmp.write(data)
        tmp.flush()
        rates = extract_xlsx_tariffs(Path(tmp.name))
        keys = [(r["service_code"], r["unit"]) for r in rates]
        if not rates or len(keys) != len(set(keys)):
            raise HTTPException(422, "Tarifario vacío o con tarifas ambiguas")
        replacement = standard.path.with_suffix(".pending")
        replacement.write_bytes(data)
        replacement.replace(standard.path)
    return {
        "message": "Tarifario estándar actualizado para nuevos expedientes.",
        "rates": len(rates),
    }


@router.patch("/{claim_id}/active-documents", response_model=list[StoredDocument])
def update_active_documents(
    claim_id: str,
    payload: ActiveDocumentsRequest,
    service: ServiceDep,
):
    """Actualiza la selección de documentos activos (máximo un documento activo por rol)."""
    return service.set_active_documents(claim_id, payload.active_document_ids)


@router.get("/{claim_id}/documents/{doc_id}")
def download_document(
    claim_id: str,
    doc_id: str,
    service: ServiceDep,
):
    """Descarga de forma segura el archivo asegurando aislamiento por expediente."""
    doc, file_path = service.get_document_file(claim_id, doc_id)
    return FileResponse(
        path=file_path,
        media_type=doc.mime,
        filename=doc.filename,
    )


@router.delete("/{claim_id}")
def delete_claim(
    claim_id: str,
    service: ServiceDep,
):
    """Elimina el expediente y todos sus archivos asociados de almacenamiento."""
    service.delete_claim(claim_id)
    return Response(status_code=204)


@router.post("/{claim_id}/extract", response_model=ExtractionSnapshot)
def extract_documents(
    claim_id: str,
    request: Request,
    service: ServiceDep,
):
    """Extrae evidencia y datos candidatos desde los documentos activos del expediente (T02)."""
    claim = service.get_claim(claim_id)
    active_docs = [d for d in claim.documents if d.active]
    if not active_docs:
        raise HTTPException(
            400, "No hay documentos activos configurados para extraer en este expediente"
        )

    doc_paths = {}
    for d in active_docs:
        _, p = service.get_document_file(claim_id, d.id)
        doc_paths[d.id] = p

    provider = getattr(request.app.state, "document_provider", None)
    repo = service.repository
    previous = repo.get_snapshot(claim_id) if hasattr(repo, "get_snapshot") else None
    if previous and hasattr(repo, "save_snapshot"):
        repo.save_snapshot(claim_id, previous[0], confirmed=False)
    try:
        snapshot = (
            provider.extract(claim_id, active_docs, doc_paths)
            if provider
            else extract_claim_snapshot(claim_id, active_docs, doc_paths)
        )
    except (ProviderError, ValueError):
        raise HTTPException(
            422, "Extracción incompleta o sin evidencia válida; revisa documentos y reintenta."
        ) from None

    repo = service.repository
    if hasattr(repo, "save_snapshot"):
        repo.save_snapshot(claim_id, snapshot.model_dump(mode="json"), confirmed=False)

    return snapshot


@router.get("/{claim_id}/snapshot", response_model=ExtractionSnapshot)
def get_extraction_snapshot(
    claim_id: str,
    service: ServiceDep,
):
    """Obtiene el último snapshot de extracción del expediente."""
    repo = service.repository
    if not hasattr(repo, "get_snapshot"):
        raise HTTPException(404, "Repositorio sin soporte de snapshots")

    res = repo.get_snapshot(claim_id)
    if not res:
        msg = f"No existe snapshot de extracción para el expediente '{claim_id}'"
        raise HTTPException(404, msg)

    data, confirmed = res
    data["confirmed"] = confirmed
    return ExtractionSnapshot.model_validate(data)


@router.put("/{claim_id}/normalized", response_model=AuditInput)
def confirm_normalized_claim(
    claim_id: str,
    payload: ConfirmNormalizedRequest,
    service: ServiceDep,
):
    """Confirma los campos normalizados y construye la entrada validada para la auditoría."""
    claim = service.get_claim(claim_id)
    active_docs = [d for d in claim.documents if d.active]
    if not active_docs:
        raise HTTPException(400, "No hay documentos activos para normalizar")

    repo = service.repository
    snapshot_res = repo.get_snapshot(claim_id) if hasattr(repo, "get_snapshot") else None
    evidence_list: list[Evidence] = []
    if snapshot_res:
        snap_data, _ = snapshot_res
        evidence_list = [Evidence.model_validate(e) for e in snap_data.get("evidence", [])]

    # Las correcciones conservan fuentes existentes; nunca inventan evidencia documental.
    for item in payload.items:
        if not any(e.id == item.evidence_id for e in evidence_list):
            raise HTTPException(422, "La línea corregida debe conservar una evidencia existente.")

    for tariff in payload.tariffs:
        if not any(e.id == tariff.evidence_id for e in evidence_list):
            raise HTTPException(422, "La tarifa debe conservar una evidencia existente.")

    audit_docs = [
        Document(
            id=d.id,
            kind=d.kind,
            filename=d.filename,
            sha256=d.sha256,
            active=True,
        )
        for d in active_docs
    ]

    audit_input = AuditInput(
        schema_version="1.0",
        claim_id=claim_id,
        currency="USD",
        billing_kind=payload.billing_kind,
        documents=audit_docs,
        evidence=evidence_list,
        reported_damage_codes=payload.reported_damage_codes,
        inspected_damage_codes=payload.inspected_damage_codes,
        items=payload.items,
        tariffs=payload.tariffs,
        subtotal=payload.subtotal,
        taxes=payload.taxes,
        total=payload.total,
    )

    if hasattr(repo, "save_snapshot"):
        repo.save_snapshot(claim_id, audit_input.model_dump(mode="json"), confirmed=True)

    return audit_input


@router.post("/{claim_id}/preset/{case_id}", response_model=ExtractionSnapshot)
def load_preset_case(
    claim_id: str,
    case_id: str,
    service: ServiceDep,
):
    """Carga un caso sintético (A, B, C o D) en el expediente para inspección y auditoría."""
    from app.main import load_case

    normalized_case_id = case_id.upper()
    try:
        case_data = load_case(normalized_case_id)
    except Exception:
        raise HTTPException(404, f"Caso de prueba '{case_id}' no encontrado") from None

    claim = service.repository.get_claim(claim_id)
    if not claim:
        claim = service.repository.create_claim(claim_id)

    claim_storage = service.storage_dir / claim_id
    claim_storage.mkdir(parents=True, exist_ok=True)

    root_dir = Path(__file__).resolve().parent.parent.parent
    sources_dir = root_dir / "data/demo/sources" / normalized_case_id
    doc_id_map = {d.id: f"{claim_id}_{d.id}" for d in case_data.documents}
    for d in case_data.documents:
        ext = ".xlsx" if d.kind == DocumentKind.TARIFF else ".pdf"
        candidate_file = sources_dir / f"{d.id}{ext}"
        if not candidate_file.exists():
            candidate_file = sources_dir / d.filename

        if candidate_file.exists():
            file_bytes = candidate_file.read_bytes()
            clean_name = candidate_file.name
        else:
            clean_name = f"{d.id}{ext}"
            file_bytes = (
                f"CONTENIDO DEL EXPEDIENTE {claim_id}\nROL: {d.kind.value}\nDOC: {d.filename}\n"
            ).encode()

        target_path = claim_storage / f"{d.id}_{clean_name}"
        target_path.write_bytes(file_bytes)

        if clean_name.endswith(".pdf"):
            mime = "application/pdf"
        elif clean_name.endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            mime = "text/plain"

        stored_doc = StoredDocument(
            id=doc_id_map[d.id],
            claim_id=claim_id,
            kind=d.kind,
            mime=mime,
            byte_count=len(file_bytes),
            sha256=hashlib.sha256(file_bytes).hexdigest(),
            filename=clean_name,
            version=1,
            active=True,
        )
        service.repository.add_document(claim_id, stored_doc, target_path)

    now = datetime.now(UTC).isoformat()
    extracted_items = [
        ExtractedItem(
            id=it.id,
            description=it.description,
            service_code=it.service_code,
            damage_code=it.damage_code,
            unit=it.unit,
            quantity=it.quantity,
            unit_price=it.unit_price,
            line_total=it.line_total,
            evidence_id=it.evidence_id,
        )
        for it in case_data.items
    ]
    extracted_tariffs = [
        ExtractedTariff(
            service_code=tf.service_code,
            unit=tf.unit,
            allowed_rate=tf.allowed_rate,
            evidence_id=tf.evidence_id,
        )
        for tf in case_data.tariffs
    ]
    remapped_evidence = [
        Evidence(
            id=e.id,
            document_id=doc_id_map.get(e.document_id, e.document_id),
            location=e.location,
            text=e.text,
        )
        for e in case_data.evidence
    ]

    snapshot = ExtractionSnapshot(
        claim_id=claim_id,
        created_at=now,
        confirmed=False,
        billing_kind=case_data.billing_kind,
        reported_damage_codes=case_data.reported_damage_codes,
        inspected_damage_codes=case_data.inspected_damage_codes,
        items=extracted_items,
        tariffs=extracted_tariffs,
        subtotal=case_data.subtotal,
        taxes=case_data.taxes,
        total=case_data.total,
        evidence=remapped_evidence,
        review_notes=[],
    )

    repo = service.repository
    if hasattr(repo, "save_snapshot"):
        repo.save_snapshot(claim_id, snapshot.model_dump(mode="json"), confirmed=False)

    return snapshot


@router.post("/{claim_id}/audits", response_model=AuditResult)
def run_claim_audit(
    claim_id: str,
    request: Request,
    service: ServiceDep,
):
    """Ejecuta la auditoría agéntica sobre el expediente con idempotencia (T03)."""
    repo = service.repository
    if not hasattr(repo, "get_snapshot"):
        raise HTTPException(400, "El expediente no cuenta con datos normalizados confirmados")

    res = repo.get_snapshot(claim_id)
    if not res or not res[1]:
        msg = (
            "El expediente no ha sido normalizado y confirmado previamente "
            "(use PUT /api/claims/{id}/normalized)"
        )
        raise HTTPException(400, msg)

    data, _ = res
    audit_input = AuditInput.model_validate(data)

    provider = getattr(request.app.state, "provider", None)
    settings = getattr(request.app.state, "settings", None)
    ai_mode = settings.ai_mode if settings else "mock"
    model_name = getattr(settings, "gemini_model", "mock") or "mock"
    rule_version = "1.0"
    prompt_version = "1.0"

    # Idempotencia por claim + snapshot_hash + rule_version + prompt_version + model
    canonical_snapshot = json.dumps(data, sort_keys=True, ensure_ascii=False)
    snapshot_hash = hashlib.sha256(canonical_snapshot.encode("utf-8")).hexdigest()
    idempotency_raw = f"{claim_id}:{snapshot_hash}:{rule_version}:{prompt_version}:{model_name}"
    idempotency_key = hashlib.sha256(idempotency_raw.encode("utf-8")).hexdigest()

    if hasattr(repo, "get_audit_run"):
        cached = repo.get_audit_run(idempotency_key)
        if cached:
            return AuditResult.model_validate(cached)

    start_t = time.perf_counter()
    result = run_audit(audit_input, provider, ai_mode)
    latency_ms = int((time.perf_counter() - start_t) * 1000)

    if hasattr(repo, "save_audit_run"):
        repo.save_audit_run(
            idempotency_key=idempotency_key,
            claim_id=claim_id,
            snapshot_hash=snapshot_hash,
            rule_version=rule_version,
            prompt_version=prompt_version,
            model_name=model_name,
            input_data=audit_input.model_dump(mode="json"),
            output_data=result.model_dump(mode="json"),
            latency_ms=latency_ms,
            mode=ai_mode,
        )

    return result


@router.post("/admin/purge")
def purge_claims_retention(
    service: ServiceDep,
    older_than_seconds: int = 86400,
    dry_run: bool = True,
):
    """Purga reclamos antiguos según política de retención con soporte para dry-run (T03)."""
    repo = service.repository
    if not hasattr(repo, "purge_claims"):
        raise HTTPException(400, "El repositorio no soporta purga por política")
    return repo.purge_claims(older_than_seconds=older_than_seconds, dry_run=dry_run)
