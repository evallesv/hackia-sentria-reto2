"""Endpoints de intake y gestión documental de expedientes (T01)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.models import (
    ActiveDocumentsRequest,
    Claim,
    ClaimCreateRequest,
    DocumentKind,
    StoredDocument,
)
from app.services.intake import IntakeService

router = APIRouter(prefix="/api/claims", tags=["claims"])


def get_intake_service(request: Request) -> IntakeService:
    service = getattr(request.app.state, "intake_service", None)
    if not service:
        raise HTTPException(500, "Servicio de intake no inicializado")
    return service


ServiceDep = Annotated[IntakeService, Depends(get_intake_service)]


@router.post("", response_model=Claim, status_code=201)
def create_claim(
    service: ServiceDep,
    payload: ClaimCreateRequest | None = None,
):
    """Crea un nuevo expediente de siniestro."""
    claim_id = payload.claim_id if payload else None
    return service.create_claim(claim_id)


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
    file: Annotated[UploadFile, File(...)],
    kind: Annotated[DocumentKind, Form(...)],
    service: ServiceDep,
):
    """Sube un documento (PDF o XLSX) validando límites reales, magic bytes y unicidad."""
    content = await file.read()
    original_name = file.filename or "archivo_sin_nombre"
    return service.upload_document(
        claim_id=claim_id,
        data=content,
        original_filename=original_name,
        kind=kind,
    )


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
