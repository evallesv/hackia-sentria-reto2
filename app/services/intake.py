"""Servicio de intake seguro y validación de archivos para siniestros (T01)."""

import hashlib
import io
import re
import shutil
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Protocol

from fastapi import HTTPException

from app.models import (
    Claim,
    ClaimStatus,
    DocumentKind,
    StoredDocument,
)

SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.\- ]{1,200}$")
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB
MAX_ZIP_EXPANDED_BYTES = 50 * 1024 * 1024  # 50 MiB
MAX_VERSIONS_PER_ROLE = 10

MIME_PDF = "application/pdf"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def validate_safe_filename(filename: str) -> str:
    """Valida y sanea el nombre del archivo para prevenir path traversal e inyecciones."""
    if not filename or not filename.strip():
        raise HTTPException(400, "Nombre de archivo vacío")

    clean = filename.strip()
    if ".." in clean or "/" in clean or "\\" in clean or "\x00" in clean:
        raise HTTPException(
            400, "Nombre de archivo no válido: contiene secuencias de ruta o caracteres prohibidos"
        )

    if not SAFE_FILENAME_RE.match(clean):
        raise HTTPException(400, "Nombre de archivo contiene caracteres no permitidos")

    suffix = Path(clean).suffix.lower()
    if suffix not in (".pdf", ".xlsx"):
        raise HTTPException(
            400, f"Extensión no permitida: '{suffix}'. Solo se admiten archivos .pdf y .xlsx"
        )

    return clean


def inspect_and_validate_file(data: bytes, filename: str) -> tuple[int, str, str]:
    """Inspecciona bytes reales, previene ejecutables/macros/zip bombs y retorna metadatos."""
    byte_count = len(data)
    if byte_count == 0:
        raise HTTPException(400, "El archivo está vacío (0 bytes)")

    if byte_count > MAX_FILE_BYTES:
        raise HTTPException(413, "El archivo excede el límite máximo permitido de 10 MiB")

    # Detección temprana de ejecutables y scripts peligrosos
    if (
        data.startswith(b"MZ")
        or data.startswith(b"\x7fELF")
        or data.startswith(b"\xca\xfe\xba\xbe")
        or data.startswith(b"\xcf\xfa\xed\xfe")
        or data.startswith(b"#!")
    ):
        raise HTTPException(400, "Archivo ejecutable o script no permitido")

    sha256_hash = hashlib.sha256(data).hexdigest()
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise HTTPException(
                400, "Contenido no coincide con un documento PDF válido (magic bytes inválidos)"
            )
        if b"%%EOF" not in data[-2048:]:
            raise HTTPException(
                400, "Documento PDF corrupto o incompleto (sin marcador de fin de archivo)"
            )
        mime = MIME_PDF

    elif suffix == ".xlsx":
        if not data.startswith(b"PK\x03\x04"):
            raise HTTPException(
                400, "Contenido no coincide con un archivo XLSX válido (formato ZIP no detectado)"
            )

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Detección de bomba ZIP (ratio de descompresión o tamaño inflado excesivo)
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                if total_uncompressed > MAX_ZIP_EXPANDED_BYTES:
                    raise HTTPException(
                        413, "Archivo XLSX descomprimido excede el límite de seguridad (50 MiB)"
                    )

                namelist = zf.namelist()
                for name in namelist:
                    lower = name.lower()
                    if (
                        lower.endswith((".bin", ".exe", ".dll", ".bat", ".cmd", ".vbs", ".ps1"))
                        or "vbaproject" in lower
                    ):
                        raise HTTPException(
                            400, "Archivo XLSX rechazado: contiene macros (.xlsm) o ejecutables"
                        )

                # Estructura básica de OpenXML para hojas de cálculo
                if not any("[Content_Types].xml" in name for name in namelist):
                    raise HTTPException(
                        400, "Estructura OpenXML inválida para hoja de cálculo XLSX"
                    )

        except zipfile.BadZipFile:
            raise HTTPException(
                400, "Archivo XLSX corrupto o no legible como archivo ZIP"
            ) from None

        mime = MIME_XLSX

    else:
        raise HTTPException(400, f"Formato no soportado: {suffix}")

    return byte_count, sha256_hash, mime


class ClaimRepository(Protocol):
    def create_claim(self, claim_id: str | None = None) -> Claim: ...
    def get_claim(self, claim_id: str) -> Claim | None: ...
    def list_claims(self) -> list[Claim]: ...
    def add_document(
        self, claim_id: str, doc: StoredDocument, internal_path: Path
    ) -> StoredDocument: ...
    def get_document(self, claim_id: str, doc_id: str) -> tuple[StoredDocument, Path] | None: ...
    def list_documents(self, claim_id: str) -> list[StoredDocument]: ...
    def update_active_documents(
        self, claim_id: str, active_doc_ids: list[str]
    ) -> list[StoredDocument]: ...
    def delete_claim(self, claim_id: str) -> bool: ...


class InMemoryClaimRepository:
    """Repositorio en memoria con soporte de aislamiento de expedientes y bloqueo seguro."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.storage_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            import tempfile

            self.storage_dir = Path(tempfile.gettempdir()) / "sentria" / "uploads"
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._claims: dict[str, Claim] = {}
        self._doc_paths: dict[str, Path] = {}
        self._lock = Lock()

    def create_claim(self, claim_id: str | None = None) -> Claim:
        with self._lock:
            cid = claim_id or f"claim_{uuid.uuid4().hex[:12]}"
            if cid in self._claims:
                raise HTTPException(409, f"El expediente con ID '{cid}' ya existe")

            now = datetime.now(UTC).isoformat()
            claim = Claim(id=cid, status=ClaimStatus.DRAFT, created_at=now, documents=[])
            self._claims[cid] = claim
            return claim

    def get_claim(self, claim_id: str) -> Claim | None:
        with self._lock:
            return self._claims.get(claim_id)

    def list_claims(self) -> list[Claim]:
        with self._lock:
            return list(self._claims.values())

    def add_document(
        self, claim_id: str, doc: StoredDocument, internal_path: Path
    ) -> StoredDocument:
        with self._lock:
            claim = self._claims.get(claim_id)
            if not claim:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            claim.documents.append(doc)
            self._doc_paths[doc.id] = internal_path
            return doc

    def get_document(self, claim_id: str, doc_id: str) -> tuple[StoredDocument, Path] | None:
        with self._lock:
            claim = self._claims.get(claim_id)
            if not claim:
                return None
            for d in claim.documents:
                if d.id == doc_id:
                    path = self._doc_paths.get(doc_id)
                    if path:
                        return d, path
            return None

    def list_documents(self, claim_id: str) -> list[StoredDocument]:
        with self._lock:
            claim = self._claims.get(claim_id)
            if not claim:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")
            return list(claim.documents)

    def update_active_documents(
        self, claim_id: str, active_doc_ids: list[str]
    ) -> list[StoredDocument]:
        with self._lock:
            claim = self._claims.get(claim_id)
            if not claim:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            doc_map = {d.id: d for d in claim.documents}
            for aid in active_doc_ids:
                if aid not in doc_map:
                    raise HTTPException(
                        404, f"El documento '{aid}' no existe o no pertenece al expediente"
                    )

            # Invariante T01: solo un documento activo por rol
            active_kinds = set()
            for aid in active_doc_ids:
                kind = doc_map[aid].kind
                if kind in active_kinds:
                    msg = f"Conflicto: no se permite más de un documento activo para el rol {kind}"
                    raise HTTPException(409, msg)
                active_kinds.add(kind)

            # Actualizar estado activo
            active_set = set(active_doc_ids)
            for d in claim.documents:
                d.active = d.id in active_set

            return list(claim.documents)

    def delete_claim(self, claim_id: str) -> bool:
        with self._lock:
            claim = self._claims.pop(claim_id, None)
            if not claim:
                return False

            for d in claim.documents:
                self._doc_paths.pop(d.id, None)

            # Limpiar archivos del directorio de este expediente
            claim_folder = self.storage_dir / claim_id
            if claim_folder.exists() and claim_folder.is_dir():
                shutil.rmtree(claim_folder, ignore_errors=True)

            return True


class IntakeService:
    """Coordinador de intake documental seguro."""

    def __init__(
        self,
        repository: ClaimRepository,
        storage_dir: Path,
        max_file_bytes: int = MAX_FILE_BYTES,
    ):
        self.repository = repository
        resolved_dir = getattr(repository, "storage_dir", storage_dir)
        self.storage_dir = Path(resolved_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def create_claim(self, claim_id: str | None = None) -> Claim:
        return self.repository.create_claim(claim_id)

    def get_claim(self, claim_id: str) -> Claim:
        claim = self.repository.get_claim(claim_id)
        if not claim:
            raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")
        return claim

    def list_documents(self, claim_id: str) -> list[StoredDocument]:
        return self.repository.list_documents(claim_id)

    def upload_document(
        self,
        claim_id: str,
        data: bytes,
        original_filename: str,
        kind: DocumentKind,
    ) -> StoredDocument:
        claim = self.get_claim(claim_id)

        clean_filename = validate_safe_filename(original_filename)
        byte_count, sha256_hash, mime = inspect_and_validate_file(data, clean_filename)

        # Invariante: evitar duplicados ciegos con el mismo hash en el mismo expediente
        for existing in claim.documents:
            if existing.sha256 == sha256_hash:
                raise HTTPException(
                    409,
                    f"Documento duplicado: ya existe un archivo con SHA-256 (ID: {existing.id})",
                )

        # Gestión de versiones por rol
        existing_role_docs = [d for d in claim.documents if d.kind == kind]
        version = len(existing_role_docs) + 1
        if version > MAX_VERSIONS_PER_ROLE:
            raise HTTPException(
                400,
                f"Límite de versiones excedido para el rol {kind} (máximo {MAX_VERSIONS_PER_ROLE})",
            )

        # Primer documento del rol activo; versiones posteriores inactivas por defecto
        has_active_role_doc = any(d.active for d in existing_role_docs)
        active = not has_active_role_doc

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        suffix = Path(clean_filename).suffix.lower()

        # Guardar en almacenamiento seguro fuera de static
        claim_storage = self.storage_dir / claim_id
        claim_storage.mkdir(parents=True, exist_ok=True)
        target_path = claim_storage / f"{doc_id}{suffix}"
        target_path.write_bytes(data)

        # Contrato público: no contiene ruta absoluta de almacenamiento
        stored_doc = StoredDocument(
            id=doc_id,
            claim_id=claim_id,
            kind=kind,
            mime=mime,
            byte_count=byte_count,
            sha256=sha256_hash,
            filename=clean_filename,
            version=version,
            active=active,
        )

        return self.repository.add_document(claim_id, stored_doc, target_path)

    def set_active_documents(
        self, claim_id: str, active_doc_ids: list[str]
    ) -> list[StoredDocument]:
        return self.repository.update_active_documents(claim_id, active_doc_ids)

    def get_document_file(self, claim_id: str, doc_id: str) -> tuple[StoredDocument, Path]:
        self.get_claim(claim_id)
        doc_pair = self.repository.get_document(claim_id, doc_id)
        if not doc_pair:
            raise HTTPException(
                404, f"Documento '{doc_id}' no encontrado en el expediente '{claim_id}'"
            )
        return doc_pair

    def delete_claim(self, claim_id: str) -> bool:
        if not self.repository.get_claim(claim_id):
            raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")
        return self.repository.delete_claim(claim_id)
