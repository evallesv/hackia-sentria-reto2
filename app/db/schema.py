"""Definición declarativa de esquemas relacionales con SQLAlchemy 2 (T03)."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""

    pass


class ClaimModel(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)

    documents: Mapped[list["StoredDocumentModel"]] = relationship(
        "StoredDocumentModel",
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    snapshot: Mapped["ExtractionSnapshotModel | None"] = relationship(
        "ExtractionSnapshotModel",
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    audit_runs: Mapped[list["AuditRunModel"]] = relationship(
        "AuditRunModel",
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class StoredDocumentModel(Base):
    __tablename__ = "stored_documents"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    internal_path: Mapped[str] = mapped_column(String(500), nullable=False)

    claim: Mapped["ClaimModel"] = relationship("ClaimModel", back_populates="documents")


class ExtractionSnapshotModel(Base):
    __tablename__ = "extraction_snapshots"

    claim_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    claim: Mapped["ClaimModel"] = relationship("ClaimModel", back_populates="snapshot")


class AuditRunModel(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)

    claim: Mapped["ClaimModel"] = relationship("ClaimModel", back_populates="audit_runs")
