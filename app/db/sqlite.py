"""Persistencia relacional SQLite para siniestros, documentos y extracciones (T02/T03)."""

import json
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from fastapi import HTTPException

from app.models import (
    Claim,
    ClaimStatus,
    DocumentKind,
    StoredDocument,
)


class SqliteClaimRepository:
    """Repositorio transaccional en SQLite con modo WAL y soporte de clave foránea."""

    def __init__(self, db_path: Path, storage_dir: Path):
        self.db_path = Path(db_path)
        self.storage_dir = Path(storage_dir)
        self._lock = Lock()

        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            # Prueba de escritura
            test_conn = sqlite3.connect(str(self.db_path))
            test_conn.close()
        except (PermissionError, OSError):
            temp_base = Path(tempfile.gettempdir()) / "sentria"
            self.storage_dir = temp_base / "uploads"
            self.db_path = temp_base / "sentria.db"
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stored_documents (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    mime TEXT NOT NULL,
                    byte_count INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    active INTEGER NOT NULL,
                    internal_path TEXT NOT NULL,
                    FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS extraction_snapshots (
                    claim_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    confirmed INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_runs (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    audit_result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(claim_id) REFERENCES claims(id) ON DELETE CASCADE
                );
            """)

    def create_claim(self, claim_id: str | None = None) -> Claim:
        cid = claim_id or f"claim_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT id FROM claims WHERE id = ?", (cid,)).fetchone()
            if row:
                raise HTTPException(409, f"El expediente con ID '{cid}' ya existe")

            conn.execute(
                "INSERT INTO claims (id, status, created_at) VALUES (?, ?, ?)",
                (cid, ClaimStatus.DRAFT.value, now),
            )
        return Claim(id=cid, status=ClaimStatus.DRAFT, created_at=now, documents=[])

    def get_claim(self, claim_id: str) -> Claim | None:
        with self._lock, self._get_connection() as conn:
            c_row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not c_row:
                return None

            docs = self._load_documents(conn, claim_id)
            return Claim(
                id=c_row["id"],
                status=ClaimStatus(c_row["status"]),
                created_at=c_row["created_at"],
                documents=docs,
            )

    def _load_documents(self, conn: sqlite3.Connection, claim_id: str) -> list[StoredDocument]:
        rows = conn.execute(
            "SELECT * FROM stored_documents WHERE claim_id = ? ORDER BY version ASC",
            (claim_id,),
        ).fetchall()
        docs = []
        for r in rows:
            docs.append(
                StoredDocument(
                    id=r["id"],
                    claim_id=r["claim_id"],
                    kind=DocumentKind(r["kind"]),
                    mime=r["mime"],
                    byte_count=r["byte_count"],
                    sha256=r["sha256"],
                    filename=r["filename"],
                    version=r["version"],
                    active=bool(r["active"]),
                )
            )
        return docs

    def list_claims(self) -> list[Claim]:
        with self._lock, self._get_connection() as conn:
            c_rows = conn.execute("SELECT * FROM claims ORDER BY created_at DESC").fetchall()
            claims = []
            for cr in c_rows:
                docs = self._load_documents(conn, cr["id"])
                claims.append(
                    Claim(
                        id=cr["id"],
                        status=ClaimStatus(cr["status"]),
                        created_at=cr["created_at"],
                        documents=docs,
                    )
                )
            return claims

    def add_document(
        self, claim_id: str, doc: StoredDocument, internal_path: Path
    ) -> StoredDocument:
        with self._lock, self._get_connection() as conn:
            c_row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not c_row:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            conn.execute(
                """
                INSERT INTO stored_documents
                (id, claim_id, kind, mime, byte_count, sha256, filename,
                 version, active, internal_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    doc.claim_id,
                    doc.kind.value,
                    doc.mime,
                    doc.byte_count,
                    doc.sha256,
                    doc.filename,
                    doc.version,
                    1 if doc.active else 0,
                    str(internal_path),
                ),
            )
            return doc

    def get_document(self, claim_id: str, doc_id: str) -> tuple[StoredDocument, Path] | None:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM stored_documents WHERE claim_id = ? AND id = ?",
                (claim_id, doc_id),
            ).fetchone()
            if not row:
                return None

            doc = StoredDocument(
                id=row["id"],
                claim_id=row["claim_id"],
                kind=DocumentKind(row["kind"]),
                mime=row["mime"],
                byte_count=row["byte_count"],
                sha256=row["sha256"],
                filename=row["filename"],
                version=row["version"],
                active=bool(row["active"]),
            )
            return doc, Path(row["internal_path"])

    def list_documents(self, claim_id: str) -> list[StoredDocument]:
        with self._lock, self._get_connection() as conn:
            c_row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not c_row:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")
            return self._load_documents(conn, claim_id)

    def update_active_documents(
        self, claim_id: str, active_doc_ids: list[str]
    ) -> list[StoredDocument]:
        with self._lock, self._get_connection() as conn:
            c_row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not c_row:
                raise HTTPException(404, f"Expediente '{claim_id}' no encontrado")

            docs = self._load_documents(conn, claim_id)
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

            # Actualizar en BD
            conn.execute("UPDATE stored_documents SET active = 0 WHERE claim_id = ?", (claim_id,))
            if active_doc_ids:
                placeholders = ",".join("?" for _ in active_doc_ids)
                sql_update = (
                    "UPDATE stored_documents SET active = 1 "
                    f"WHERE claim_id = ? AND id IN ({placeholders})"
                )
                conn.execute(sql_update, [claim_id, *active_doc_ids])

            # Invalida snapshot previo al cambiar versión activa
            conn.execute("DELETE FROM extraction_snapshots WHERE claim_id = ?", (claim_id,))
            conn.execute(
                "UPDATE claims SET status = ? WHERE id = ?",
                (ClaimStatus.DRAFT.value, claim_id),
            )

            return self._load_documents(conn, claim_id)

    def delete_claim(self, claim_id: str) -> bool:
        with self._lock, self._get_connection() as conn:
            c_row = conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone()
            if not c_row:
                return False

            rows = conn.execute(
                "SELECT internal_path FROM stored_documents WHERE claim_id = ?", (claim_id,)
            ).fetchall()
            for r in rows:
                p = Path(r["internal_path"])
                if p.exists() and p.is_file():
                    p.unlink(missing_ok=True)

            conn.execute("DELETE FROM claims WHERE id = ?", (claim_id,))

            claim_folder = self.storage_dir / claim_id
            if claim_folder.exists() and claim_folder.is_dir():
                import shutil

                shutil.rmtree(claim_folder, ignore_errors=True)

            return True

    def save_snapshot(self, claim_id: str, data: dict, confirmed: bool = False) -> None:
        now = datetime.now(UTC).isoformat()
        serialized = json.dumps(data, ensure_ascii=False)
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO extraction_snapshots (claim_id, data_json, created_at, confirmed)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    created_at = excluded.created_at,
                    confirmed = excluded.confirmed
                """,
                (claim_id, serialized, now, 1 if confirmed else 0),
            )
            new_status = (
                ClaimStatus.READY_FOR_EXTRACTION.value if confirmed else ClaimStatus.DRAFT.value
            )
            conn.execute("UPDATE claims SET status = ? WHERE id = ?", (new_status, claim_id))

    def get_snapshot(self, claim_id: str) -> tuple[dict, bool] | None:
        with self._lock, self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, confirmed FROM extraction_snapshots WHERE claim_id = ?",
                (claim_id,),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["data_json"]), bool(row["confirmed"])
