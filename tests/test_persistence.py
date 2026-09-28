"""Pruebas rigurosas de persistencia, migraciones e idempotencia (T03)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.db.repository import SqlAlchemyClaimRepository
from app.db.session import get_engine, run_migrations
from app.main import create_app
from app.models import DocumentKind, StoredDocument


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_sentria.db"
    storage_dir = tmp_path / "uploads"
    engine = get_engine(f"sqlite:///{db_file}")
    run_migrations(engine)
    return SqlAlchemyClaimRepository(engine=engine, storage_dir=storage_dir)


def test_alembic_migrations_create_all_tables_and_indexes(tmp_path):
    """Verifica que Alembic cree desde cero las tablas e índices obligatorios de T03."""
    db_file = tmp_path / "fresh.db"
    engine = get_engine(f"sqlite:///{db_file}")
    run_migrations(engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "claims" in tables
    assert "stored_documents" in tables
    assert "extraction_snapshots" in tables
    assert "audit_runs" in tables
    assert "alembic_version" in tables

    # Verificar índices
    doc_indexes = [idx["name"] for idx in inspector.get_indexes("stored_documents")]
    assert any("sha256" in name for name in doc_indexes if name)
    assert any("claim_id" in name for name in doc_indexes if name)

    audit_indexes = [idx["name"] for idx in inspector.get_indexes("audit_runs")]
    assert any("idempotency_key" in name for name in audit_indexes if name)


def test_claim_and_document_persistence_across_reconnect(repo, tmp_path):
    """Verifica que los datos persistan de forma idéntica tras reconectar la BD."""
    claim = repo.create_claim("CLM-RESTART-001")
    assert claim.id == "CLM-RESTART-001"

    doc_file = tmp_path / "uploads" / "CLM-RESTART-001" / "doc1.pdf"
    doc_file.parent.mkdir(parents=True, exist_ok=True)
    doc_file.write_bytes(b"%PDF-1.4 dummy content")

    valid_sha = "a" * 64
    doc = StoredDocument(
        id="doc_001",
        claim_id=claim.id,
        kind=DocumentKind.BILLING,
        mime="application/pdf",
        byte_count=len(b"%PDF-1.4 dummy content"),
        sha256=valid_sha,
        filename="doc1.pdf",
        version=1,
        active=True,
    )
    repo.add_document(claim.id, doc, doc_file)

    # Simular reconexión creando una nueva instancia del repositorio sobre la misma BD
    new_repo = SqlAlchemyClaimRepository(engine=repo.engine, storage_dir=repo.storage_dir)
    loaded_claim = new_repo.get_claim("CLM-RESTART-001")
    assert loaded_claim is not None
    assert loaded_claim.id == "CLM-RESTART-001"
    assert len(loaded_claim.documents) == 1
    assert loaded_claim.documents[0].filename == "doc1.pdf"
    assert loaded_claim.documents[0].sha256 == valid_sha


def test_active_documents_atomic_conflict_and_isolation(repo, tmp_path):
    """Verifica que no se permita más de un documento activo por rol (invariante T01/T03)."""
    claim = repo.create_claim("CLM-ISO-001")

    f1 = tmp_path / "uploads" / claim.id / "factura_v1.pdf"
    f2 = tmp_path / "uploads" / claim.id / "factura_v2.pdf"
    f1.parent.mkdir(parents=True, exist_ok=True)
    f1.write_bytes(b"v1")
    f2.write_bytes(b"v2")

    doc1 = StoredDocument(
        id="doc_v1",
        claim_id=claim.id,
        kind=DocumentKind.BILLING,
        mime="application/pdf",
        byte_count=2,
        sha256="1" * 64,
        filename="factura_v1.pdf",
        version=1,
        active=True,
    )
    doc2 = StoredDocument(
        id="doc_v2",
        claim_id=claim.id,
        kind=DocumentKind.BILLING,
        mime="application/pdf",
        byte_count=2,
        sha256="2" * 64,
        filename="factura_v2.pdf",
        version=2,
        active=False,
    )
    repo.add_document(claim.id, doc1, f1)
    repo.add_document(claim.id, doc2, f2)

    # Intentar activar ambos con el mismo rol BILLING debe lanzar conflicto 409
    with pytest.raises(Exception) as exc:
        repo.update_active_documents(claim.id, ["doc_v1", "doc_v2"])
    assert "no se permite más de un documento activo para el rol" in str(exc.value)

    # Solo doc_v1 sigue activo
    docs = repo.list_documents(claim.id)
    doc_map = {d.id: d.active for d in docs}
    assert doc_map["doc_v1"] is True
    assert doc_map["doc_v2"] is False


def test_audit_idempotency_via_api(tmp_path):
    """Verifica que reintentar la auditoría sea idempotente y no ejecute duplicados (T03)."""
    db_file = tmp_path / "api_test.db"
    storage_dir = tmp_path / "uploads"
    settings = Settings(
        ai_mode="mock",
        database_url=f"sqlite:///{db_file}",
        upload_dir=str(storage_dir),
    )
    app = create_app(settings)
    client = TestClient(app)

    # 1. Crear claim y subir documentos activos para BILLING y TARIFF
    cid = "CLM-IDEMPOTENCY-TEST"
    client.post("/api/claims", json={"claim_id": cid})
    dummy_pdf_1 = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    dummy_pdf_2 = b"%PDF-1.4\n2 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 2 0 R>>\n%%EOF"
    client.post(
        f"/api/claims/{cid}/documents",
        data={"kind": DocumentKind.BILLING.value},
        files={"file": ("factura.pdf", dummy_pdf_1, "application/pdf")},
    )
    client.post(
        f"/api/claims/{cid}/documents",
        data={"kind": DocumentKind.TARIFF.value},
        files={"file": ("tarifario.pdf", dummy_pdf_2, "application/pdf")},
    )

    # 2. Guardar snapshot normalizado confirmado
    norm_payload = {
        "billing_kind": "INVOICE",
        "reported_damage_codes": ["FRONT_PAINT"],
        "inspected_damage_codes": ["FRONT_PAINT"],
        "items": [
            {
                "id": "item_1",
                "description": "Pintura",
                "service_code": "PAINT",
                "damage_code": "FRONT_PAINT",
                "unit": "HOUR",
                "quantity": "5.0000",
                "unit_price": "50.00",
                "line_total": "250.00",
                "evidence_id": "ev_1",
            }
        ],
        "tariffs": [
            {
                "service_code": "PAINT",
                "unit": "HOUR",
                "allowed_rate": "50.00",
                "evidence_id": "ev_t1",
            }
        ],
        "subtotal": "250.00",
        "taxes": "0.00",
        "total": "250.00",
    }
    res_norm = client.put(f"/api/claims/{cid}/normalized", json=norm_payload)
    assert res_norm.status_code == 200

    # 3. Primera auditoría
    res_audit_1 = client.post(f"/api/claims/{cid}/audits")
    assert res_audit_1.status_code == 200
    data_1 = res_audit_1.json()

    # 4. Segunda auditoría (reintento idéntico) -> debe devolver resultado en cache
    res_audit_2 = client.post(f"/api/claims/{cid}/audits")
    assert res_audit_2.status_code == 200
    data_2 = res_audit_2.json()

    assert data_1 == data_2
    assert data_2["status"] == "INFORMATION_REQUIRED"
    assert data_2["flagged_difference"] == "0.00"

    # Verificar que solo hay 1 fila registrada en audit_runs para esa clave de idempotencia
    repo = app.state.claim_repo
    with repo._get_session() as session:
        from sqlalchemy import func, select

        from app.db.schema import AuditRunModel

        count = session.execute(
            select(func.count()).select_from(AuditRunModel).where(AuditRunModel.claim_id == cid)
        ).scalar()
        assert count == 1

    # 5. Modificar el snapshot normalizado: invalida la clave de idempotencia
    norm_payload_modified = dict(norm_payload)
    norm_payload_modified["total"] = "300.00"
    norm_payload_modified["items"] = [
        {
            "id": "item_1",
            "description": "Pintura",
            "service_code": "PAINT",
            "damage_code": "FRONT_PAINT",
            "unit": "HOUR",
            "quantity": "6.0000",
            "unit_price": "50.00",
            "line_total": "300.00",
            "evidence_id": "ev_1",
        }
    ]
    res_norm_mod = client.put(f"/api/claims/{cid}/normalized", json=norm_payload_modified)
    assert res_norm_mod.status_code == 200

    res_audit_3 = client.post(f"/api/claims/{cid}/audits")
    assert res_audit_3.status_code == 200
    data_3 = res_audit_3.json()
    assert data_3["billed_amount"] == "300.00"

    # Ahora debe haber 2 filas en audit_runs
    with repo._get_session() as session:
        count_2 = session.execute(
            select(func.count()).select_from(AuditRunModel).where(AuditRunModel.claim_id == cid)
        ).scalar()
        assert count_2 == 2


def test_claim_deletion_cascades_and_removes_physical_files(repo, tmp_path):
    """Verifica que borrar un claim elimine registros en cascada y archivos."""
    claim_a = repo.create_claim("CLM-DEL-A")
    claim_b = repo.create_claim("CLM-DEL-B")

    file_a = tmp_path / "uploads" / "CLM-DEL-A" / "file_a.pdf"
    file_b = tmp_path / "uploads" / "CLM-DEL-B" / "file_b.pdf"
    file_a.parent.mkdir(parents=True, exist_ok=True)
    file_b.parent.mkdir(parents=True, exist_ok=True)
    file_a.write_bytes(b"content a")
    file_b.write_bytes(b"content b")

    doc_a = StoredDocument(
        id="doc_a",
        claim_id=claim_a.id,
        kind=DocumentKind.BILLING,
        mime="application/pdf",
        byte_count=9,
        sha256="3" * 64,
        filename="file_a.pdf",
        version=1,
        active=True,
    )
    doc_b = StoredDocument(
        id="doc_b",
        claim_id=claim_b.id,
        kind=DocumentKind.BILLING,
        mime="application/pdf",
        byte_count=9,
        sha256="4" * 64,
        filename="file_b.pdf",
        version=1,
        active=True,
    )
    repo.add_document(claim_a.id, doc_a, file_a)
    repo.add_document(claim_b.id, doc_b, file_b)

    # Borrar claim A
    deleted = repo.delete_claim(claim_a.id)
    assert deleted is True

    # Comprobar que en BD A no existe y B sí existe
    assert repo.get_claim(claim_a.id) is None
    assert repo.get_claim(claim_b.id) is not None

    # Comprobar que los archivos de A fueron eliminados pero los de B permanecen intactos
    assert not file_a.exists()
    assert file_b.exists()


def test_purge_policy_with_dry_run_and_execution(repo):
    """Verifica que la purga por retención soporte dry-run y ejecute cuando corresponda."""
    # Crear un claim reciente y simular uno antiguo
    repo.create_claim("CLM-RECENT")
    repo.create_claim("CLM-OLD")

    # Modificar fecha de creación de CLM-OLD a 10 días atrás
    ten_days_ago = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    with repo._get_session() as session:
        from sqlalchemy import update

        from app.db.schema import ClaimModel

        session.execute(
            update(ClaimModel).where(ClaimModel.id == "CLM-OLD").values(created_at=ten_days_ago)
        )
        session.commit()

    # 1. Ejecutar purga con dry_run=True (antigüedad > 7 días)
    res_dry = repo.purge_claims(older_than_seconds=7 * 86400, dry_run=True)
    assert res_dry["dry_run"] is True
    assert res_dry["candidate_count"] == 1
    assert "CLM-OLD" in res_dry["candidates"]

    # Ambos reclamos deben seguir existiendo tras el dry-run
    assert repo.get_claim("CLM-OLD") is not None
    assert repo.get_claim("CLM-RECENT") is not None

    # 2. Ejecutar purga real con dry_run=False
    res_real = repo.purge_claims(older_than_seconds=7 * 86400, dry_run=False)
    assert res_real["dry_run"] is False
    assert res_real["purged_count"] == 1
    assert "CLM-OLD" in res_real["purged"]

    # CLM-OLD ya no debe existir, CLM-RECENT debe permanecer
    assert repo.get_claim("CLM-OLD") is None
    assert repo.get_claim("CLM-RECENT") is not None
