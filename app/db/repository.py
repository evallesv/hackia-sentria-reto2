"""Repositorio de persistencia e integridad relacional con SQLAlchemy 2 (T03)."""

import hashlib
import json
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

from fastapi import HTTPException
from sqlalchemy import Engine, delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.schema import (
    AuditRunModel,
    ClaimModel,
    ExtractionSnapshotModel,
    StoredDocumentModel,
)
from app.models import (
    Claim,
    ClaimStatus,
    DocumentKind,
    StoredDocument,
)


class SqlAlchemyClaimRepository:
    """Repositorio transaccional en SQLAlchemy 2 con soporte de migraciones,

    idempotencia de auditorías, aislamiento entre claims y purga por política.
    """

    def __init__(self, engine: Engine, storage_dir: Path):
        self.engine = engine
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine, expire_on_commit=False
        )
        self._lock = Lock()

    def _get_session(self) -> Session:
        return self.session_factory()

    def create_claim(self, claim_id: str | None = None) -> Claim:
        cid = claim_id or f"claim_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        with self._lock, self._get_session() as session:
            existing = session.execute(
                select(ClaimModel).where(ClaimModel.id == cid)
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(409, f"El expediente con ID '{cid}' ya existe")

            claim_record = ClaimModel(id=cid, status=ClaimStatus.DRAFT.value, created_at=now)
            session.add(claim_record)
            session.commit()

        return Claim(id=cid, status=ClaimStatus.DRAFT, created_at=now, documents=[])

    def get_claim(self, claim_id: str) -> Claim | None:
        with self._lock, self._get_session() as session:
            c = session.execute(
                select(ClaimModel).where(ClaimModel.id == claim_id)
            ).scalar_one_or_none()
            if not c:
                return None

            docs = self._load_documents(session, claim_id)
            return Claim(
                id=c.id,
                status=ClaimStatus(c.status),
                created_at=c.created_at,
                documents=docs,
            )

    def list_claims(self) -> list[Claim]:
        with self._lock, self._get_session() as session:
            claims = (
                session.execute(select(ClaimModel).order_by(ClaimModel.created_at.desc()))
                .scalars()
                .all()
            )
            result = []
            for c in claims:
                docs = self._load_documents(session, c.id)
                result.append(
                    Claim(
                        id=c.id,
                        status=ClaimStatus(c.status),
                        created_at=c.created_at,
                        documents=docs,
                    )
                )
            return result

    def _load_documents(self, session: Session, claim_id: str) -> list[StoredDocument]:
        records = (
            session.execute(
                select(StoredDocumentModel)
                .where(StoredDocumentModel.claim_id == claim_id)
                .order_by(StoredDocumentModel.version.asc())
            )
            .scalars()
            .all()
        )

        docs = []
        for r in records:
            docs.append(
                StoredDocument(
                    id=r.id,
                    claim_id=r.claim_id,
                    kind=DocumentKind(r.kind),
                    mime=r.mime,
                    byte_count=r.byte_count,
                    sha256=r.sha256,
                    filename=r.filename,
                    version=r.version,
                    active=r.active,
                )
            )
        return docs

    def add_document(
        self, claim_id: str, doc: StoredDocument, internal_path: Path
    ) -> StoredDocument:
        with self._lock, self._get_session() as session:
            c = session.execute(
                select(ClaimModel).where(ClaimModel.id == claim_id)
            ).scalar_one_or_none()
            if not c:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            existing = session.execute(
                select(StoredDocumentModel).where(StoredDocumentModel.id == doc.id)
            ).scalar_one_or_none()
            if existing:
                existing.claim_id = doc.claim_id
                existing.kind = doc.kind.value
                existing.mime = doc.mime
                existing.byte_count = doc.byte_count
                existing.sha256 = doc.sha256
                existing.filename = doc.filename
                existing.version = doc.version
                existing.active = doc.active
                existing.internal_path = str(internal_path)
            else:
                doc_model = StoredDocumentModel(
                    id=doc.id,
                    claim_id=doc.claim_id,
                    kind=doc.kind.value,
                    mime=doc.mime,
                    byte_count=doc.byte_count,
                    sha256=doc.sha256,
                    filename=doc.filename,
                    version=doc.version,
                    active=doc.active,
                    internal_path=str(internal_path),
                )
                session.add(doc_model)
            session.commit()
            return doc

    def get_document(self, claim_id: str, doc_id: str) -> tuple[StoredDocument, Path] | None:
        with self._lock, self._get_session() as session:
            r = session.execute(
                select(StoredDocumentModel).where(
                    StoredDocumentModel.claim_id == claim_id,
                    StoredDocumentModel.id == doc_id,
                )
            ).scalar_one_or_none()
            if not r:
                return None

            doc = StoredDocument(
                id=r.id,
                claim_id=r.claim_id,
                kind=DocumentKind(r.kind),
                mime=r.mime,
                byte_count=r.byte_count,
                sha256=r.sha256,
                filename=r.filename,
                version=r.version,
                active=r.active,
            )
            return doc, Path(r.internal_path)

    def list_documents(self, claim_id: str) -> list[StoredDocument]:
        with self._lock, self._get_session() as session:
            c = session.execute(
                select(ClaimModel).where(ClaimModel.id == claim_id)
            ).scalar_one_or_none()
            if not c:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")
            return self._load_documents(session, claim_id)

    def update_active_documents(
        self, claim_id: str, active_doc_ids: list[str]
    ) -> list[StoredDocument]:
        with self._lock, self._get_session() as session:
            c = session.execute(
                select(ClaimModel).where(ClaimModel.id == claim_id)
            ).scalar_one_or_none()
            if not c:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            docs = self._load_documents(session, claim_id)
            doc_map = {d.id: d for d in docs}
            for aid in active_doc_ids:
                if aid not in doc_map:
                    raise HTTPException(
                        404, f"El documento '{aid}' no existe o no pertenece al expediente"
                    )

            # Invariante: como máximo un documento activo por rol
            active_kinds = set()
            for aid in active_doc_ids:
                kind = doc_map[aid].kind
                if kind in active_kinds:
                    msg = f"Conflicto: no se permite más de un documento activo para el rol {kind}"
                    raise HTTPException(409, msg)
                active_kinds.add(kind)

            # Transacción atómica: resetear y activar seleccionados
            session.execute(
                update(StoredDocumentModel)
                .where(StoredDocumentModel.claim_id == claim_id)
                .values(active=False)
            )
            if active_doc_ids:
                session.execute(
                    update(StoredDocumentModel)
                    .where(
                        StoredDocumentModel.claim_id == claim_id,
                        StoredDocumentModel.id.in_(active_doc_ids),
                    )
                    .values(active=True)
                )

            # Invalida snapshot previo al cambiar versión activa
            session.execute(
                delete(ExtractionSnapshotModel).where(ExtractionSnapshotModel.claim_id == claim_id)
            )
            session.execute(
                update(ClaimModel)
                .where(ClaimModel.id == claim_id)
                .values(status=ClaimStatus.DRAFT.value)
            )
            session.commit()

            return self._load_documents(session, claim_id)

    def delete_claim(self, claim_id: str) -> bool:
        with self._lock, self._get_session() as session:
            c = session.execute(
                select(ClaimModel).where(ClaimModel.id == claim_id)
            ).scalar_one_or_none()
            if not c:
                return False

            docs = (
                session.execute(
                    select(StoredDocumentModel).where(StoredDocumentModel.claim_id == claim_id)
                )
                .scalars()
                .all()
            )

            for d in docs:
                p = Path(d.internal_path)
                if p.exists() and p.is_file():
                    p.unlink(missing_ok=True)

            session.delete(c)
            session.commit()

            claim_folder = self.storage_dir / claim_id
            if claim_folder.exists() and claim_folder.is_dir():
                shutil.rmtree(claim_folder, ignore_errors=True)

            return True

    def save_snapshot(self, claim_id: str, data: dict, confirmed: bool = False) -> str:
        now = datetime.now(UTC).isoformat()
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        snapshot_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        with self._lock, self._get_session() as session:
            snap = session.execute(
                select(ExtractionSnapshotModel).where(ExtractionSnapshotModel.claim_id == claim_id)
            ).scalar_one_or_none()

            if snap:
                snap.data_json = serialized
                snap.snapshot_hash = snapshot_hash
                snap.created_at = now
                snap.confirmed = confirmed
            else:
                snap = ExtractionSnapshotModel(
                    claim_id=claim_id,
                    snapshot_hash=snapshot_hash,
                    data_json=serialized,
                    created_at=now,
                    confirmed=confirmed,
                )
                session.add(snap)

            new_status = (
                ClaimStatus.READY_FOR_EXTRACTION.value if confirmed else ClaimStatus.DRAFT.value
            )
            session.execute(
                update(ClaimModel).where(ClaimModel.id == claim_id).values(status=new_status)
            )
            session.commit()

        return snapshot_hash

    def get_snapshot(self, claim_id: str) -> tuple[dict, bool] | None:
        with self._lock, self._get_session() as session:
            snap = session.execute(
                select(ExtractionSnapshotModel).where(ExtractionSnapshotModel.claim_id == claim_id)
            ).scalar_one_or_none()
            if not snap:
                return None
            return json.loads(snap.data_json), snap.confirmed

    def get_snapshot_hash(self, claim_id: str) -> str | None:
        with self._lock, self._get_session() as session:
            snap = session.execute(
                select(ExtractionSnapshotModel.snapshot_hash).where(
                    ExtractionSnapshotModel.claim_id == claim_id
                )
            ).scalar_one_or_none()
            return snap

    def get_snapshot_created_at(self, claim_id: str) -> str | None:
        with self._lock, self._get_session() as session:
            return session.execute(
                select(ExtractionSnapshotModel.created_at).where(
                    ExtractionSnapshotModel.claim_id == claim_id
                )
            ).scalar_one_or_none()

    def get_audit_run(self, idempotency_key: str) -> dict | None:
        """Busca una auditoría previa por su clave de idempotencia."""
        with self._lock, self._get_session() as session:
            ar = session.execute(
                select(AuditRunModel).where(AuditRunModel.idempotency_key == idempotency_key)
            ).scalar_one_or_none()
            if not ar:
                return None
            return json.loads(ar.output_json)

    def save_audit_run(
        self,
        idempotency_key: str,
        claim_id: str,
        snapshot_hash: str,
        rule_version: str,
        prompt_version: str,
        model_name: str,
        input_data: dict,
        output_data: dict,
        latency_ms: int | None = None,
        mode: str = "mock",
    ) -> None:
        """Registra una auditoría inmutable de forma idempotente."""
        now = datetime.now(UTC).isoformat()
        run_id = f"audit_{uuid.uuid4().hex[:12]}"
        input_json = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
        output_json = json.dumps(output_data, sort_keys=True, ensure_ascii=False)

        with self._lock, self._get_session() as session:
            existing = session.execute(
                select(AuditRunModel).where(AuditRunModel.idempotency_key == idempotency_key)
            ).scalar_one_or_none()
            if existing:
                return

            run = AuditRunModel(
                id=run_id,
                claim_id=claim_id,
                idempotency_key=idempotency_key,
                snapshot_hash=snapshot_hash,
                rule_version=rule_version,
                prompt_version=prompt_version,
                model_name=model_name,
                input_json=input_json,
                output_json=output_json,
                created_at=now,
                latency_ms=latency_ms,
                mode=mode,
            )
            session.add(run)
            session.commit()

    def purge_claims(self, older_than_seconds: int = 86400, dry_run: bool = True) -> dict:
        """Purga reclamos antiguos según política de retención con soporte para dry-run."""
        cutoff = (datetime.now(UTC) - timedelta(seconds=older_than_seconds)).isoformat()
        candidates: list[str] = []

        with self._lock, self._get_session() as session:
            claims = (
                session.execute(select(ClaimModel.id).where(ClaimModel.created_at < cutoff))
                .scalars()
                .all()
            )
            candidates = list(claims)

        if dry_run:
            return {
                "dry_run": True,
                "cutoff": cutoff,
                "candidate_count": len(candidates),
                "candidates": candidates,
            }

        purged = []
        for cid in candidates:
            if self.delete_claim(cid):
                purged.append(cid)

        return {
            "dry_run": False,
            "cutoff": cutoff,
            "purged_count": len(purged),
            "purged": purged,
        }
