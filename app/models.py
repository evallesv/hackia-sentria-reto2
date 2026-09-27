"""Contratos v1: dinero decimal, referencias comprobables y entradas acotadas."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def decimal_input(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Usar una cadena decimal, nunca números JSON o booleanos")
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(decimal_input, json_schema_input_type=str),
    Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False),
]
Quantity = Annotated[
    Decimal,
    BeforeValidator(decimal_input, json_schema_input_type=str),
    Field(gt=0, le=10000, max_digits=10, decimal_places=4, allow_inf_nan=False),
]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
# Agregados pueden superar el límite de una línea (100 líneas × 10.000 unidades).
Amount = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=2, allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentKind(StrEnum):
    INCIDENT = "INCIDENT_REPORT"
    INSPECTION = "WORKSHOP_REPORT"
    BILLING = "BILLING_DOCUMENT"
    TARIFF = "TARIFF"


class Status(StrEnum):
    CANDIDATE = "CANDIDATE_FOR_APPROVAL"
    REVIEW = "REVIEW_REQUIRED"
    INFORMATION = "INFORMATION_REQUIRED"


class Document(Model):
    id: Identifier
    kind: DocumentKind
    filename: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    active: bool = True


class Evidence(Model):
    id: Identifier
    document_id: Identifier
    location: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)


class Item(Model):
    id: Identifier
    description: str = Field(min_length=1, max_length=300)
    service_code: Identifier
    damage_code: Identifier
    unit: Literal["HOUR", "UNIT"]
    quantity: Quantity | None
    unit_price: Money | None
    line_total: Money | None
    evidence_id: Identifier


class Tariff(Model):
    service_code: Identifier
    unit: Literal["HOUR", "UNIT"]
    allowed_rate: Money
    evidence_id: Identifier


class AuditInput(Model):
    schema_version: Literal["1.0"] = "1.0"
    claim_id: Identifier
    currency: Literal["USD"] = "USD"
    billing_kind: Literal["INVOICE", "QUOTE"] = "INVOICE"
    documents: list[Document] = Field(max_length=20)
    evidence: list[Evidence] = Field(max_length=250)
    reported_damage_codes: list[Identifier] = Field(max_length=50)
    inspected_damage_codes: list[Identifier] = Field(max_length=50)
    items: list[Item] = Field(max_length=100)
    tariffs: list[Tariff] = Field(max_length=100)
    subtotal: Money | None
    taxes: Money | None
    total: Money | None

    @model_validator(mode="after")
    def references(self):
        for entries in (self.documents, self.evidence, self.items):
            ids = [x.id for x in entries]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs duplicados")
        docs = {d.id: d for d in self.documents}
        evidence = {e.id: e for e in self.evidence}
        for e in self.evidence:
            if e.document_id not in docs:
                raise ValueError("Evidencia sin documento")
        for rows, kind in ((self.items, DocumentKind.BILLING), (self.tariffs, DocumentKind.TARIFF)):
            for row in rows:
                source = evidence.get(row.evidence_id)
                if not source or docs[source.document_id].kind != kind:
                    raise ValueError("Referencia de línea incompatible")
                if not docs[source.document_id].active:
                    raise ValueError("Referencia a documento inactivo")
        return self


class Finding(Model):
    code: str
    description: str
    item_id: str | None = None
    financial_impact: Amount | None = None
    calculation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    blocking: bool = False


class Assessment(Model):
    item_id: Identifier
    decision: Literal["supported", "unsupported", "uncertain"]
    reason: str = Field(min_length=1, max_length=600)
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=10)


class SemanticReview(Model):
    assessments: list[Assessment] = Field(max_length=100)


class AuditResult(Model):
    schema_version: Literal["1.0"] = "1.0"
    claim_id: str
    status: Status
    currency: Literal["USD"] = "USD"
    billed_amount: Money | None
    flagged_difference: Amount
    reference_subtotal: Amount | None
    findings: list[Finding]
    evidence: list[Evidence]
    mode: Literal["mock", "gemini"]
    trace: list[str]
    rule_version: str = "rules-v1"
    prompt_version: str = "consistency-v1"
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    input_sha256: str = ""
