from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from app.models import AuditInput, DocumentKind, Finding, SemanticReview, Status

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def check_integrity(data: AuditInput) -> list[Finding]:
    findings = []
    active = [d for d in data.documents if d.active]
    for kind in DocumentKind:
        count = sum(d.kind == kind for d in active)
        if count != 1:
            findings.append(
                Finding(
                    code="MISSING_INFORMATION" if count == 0 else "DOCUMENT_VERSION_CONFLICT",
                    description=f"{kind.value}: se requiere una versión activa; recibidas {count}.",
                    blocking=True,
                )
            )
    hashes = defaultdict(list)
    for doc in active:
        hashes[doc.sha256].append(doc.id)
    for ids in hashes.values():
        if len(ids) > 1:
            findings.append(
                Finding(
                    code="DOCUMENT_DUPLICATE",
                    blocking=True,
                    description="Documentos activos con contenido idéntico: " + ", ".join(ids),
                )
            )
    if not data.items or not data.tariffs:
        findings.append(
            Finding(
                code="MISSING_INFORMATION",
                blocking=True,
                description="Faltan líneas de facturación o del tarifario.",
            )
        )
    doc_map = {d.id: d for d in active}
    for kind in (DocumentKind.INCIDENT, DocumentKind.INSPECTION):
        if not any(
            e.document_id in doc_map and doc_map[e.document_id].kind == kind for e in data.evidence
        ):
            findings.append(
                Finding(
                    code="MISSING_INFORMATION",
                    blocking=True,
                    description=f"Falta evidencia de {kind.value}.",
                )
            )
    return findings


def check_financials(
    data: AuditInput,
    expected_tax_rate: Decimal | None = None,
    tax_name: str = "ITBMS",
) -> tuple[list[Finding], Decimal]:
    """Diferencias potenciales sin impuestos. Duplicados nunca se descuentan automáticamente."""
    findings: list[Finding] = []
    impact_by_item: dict[str, Decimal] = {}
    tariff_index = defaultdict(list)
    for rate in data.tariffs:
        tariff_index[(rate.service_code, rate.unit)].append(rate)
    signatures = {}
    computed_lines = []
    for item in data.items:
        if item.quantity is None or item.unit_price is None or item.line_total is None:
            findings.append(
                Finding(
                    code="MISSING_INFORMATION",
                    item_id=item.id,
                    blocking=True,
                    description="Línea incompleta; no se infieren importes.",
                    evidence_ids=[item.evidence_id],
                )
            )
            continue
        computed = money(item.quantity * item.unit_price)
        computed_lines.append(computed)
        if computed != item.line_total:
            findings.append(
                Finding(
                    code="LINE_TOTAL_MISMATCH",
                    item_id=item.id,
                    description="El total de línea difiere de cantidad por precio.",
                    calculation=f"{item.quantity} × {item.unit_price} = {computed}",
                    evidence_ids=[item.evidence_id],
                    blocking=True,
                )
            )
        key = (
            item.service_code,
            item.damage_code,
            item.unit,
            item.quantity,
            item.unit_price,
            item.description.casefold(),
        )
        if key in signatures:
            # Una línea repetida podría ser legítima: revisar, jamás darla por fraude.
            findings.append(
                Finding(
                    code="DUPLICATE_ITEM",
                    item_id=item.id,
                    description=f"Posible duplicado de {signatures[key]}; confirmar.",
                    financial_impact=computed,
                    calculation=f"1 × {computed} = {computed}",
                    evidence_ids=[
                        item.evidence_id,
                        next(x.evidence_id for x in data.items if x.id == signatures[key]),
                    ],
                )
            )
            impact_by_item[item.id] = computed
        else:
            signatures[key] = item.id
        rates = tariff_index[(item.service_code, item.unit)]
        if len(rates) != 1:
            findings.append(
                Finding(
                    code="TARIFF_UNRESOLVED",
                    item_id=item.id,
                    blocking=True,
                    description="Tarifa inexistente o ambigua para el código y unidad.",
                    evidence_ids=[item.evidence_id] + [r.evidence_id for r in rates],
                )
            )
            continue
        rate = rates[0]
        difference = money(max(ZERO, item.unit_price - rate.allowed_rate) * item.quantity)
        if difference > ZERO:
            findings.append(
                Finding(
                    code="RATE_MISMATCH",
                    item_id=item.id,
                    description="Precio unitario superior al tarifario contratado.",
                    financial_impact=difference,
                    calculation=(
                        f"({item.unit_price} − {rate.allowed_rate}) "
                        f"× {item.quantity} = {difference}"
                    ),
                    evidence_ids=[item.evidence_id, rate.evidence_id],
                )
            )
            # La tarifa de una línea duplicada ya está incluida en su importe completo.
            impact_by_item[item.id] = max(impact_by_item.get(item.id, ZERO), difference)
    if data.subtotal is None or data.taxes is None or data.total is None:
        findings.append(
            Finding(
                code="MISSING_INFORMATION",
                blocking=True,
                description="Faltan subtotal, impuestos o total declarado.",
            )
        )
    elif len(computed_lines) == len(data.items):
        subtotal = money(sum(computed_lines, ZERO))
        if subtotal != data.subtotal or money(data.subtotal + data.taxes) != data.total:
            findings.append(
                Finding(
                    code="TOTAL_MISMATCH",
                    blocking=True,
                    description="Totales inconciliables. Corregir antes de proyectar saldo.",
                    calculation=f"Σ líneas = {subtotal}; subtotal + impuestos = "
                    f"{money(data.subtotal + data.taxes)}",
                    evidence_ids=[i.evidence_id for i in data.items],
                )
            )

    # Verificación de impuestos (no impactan el ahorro, pero se auditan si están incorrectos)
    if (
        expected_tax_rate is not None
        and expected_tax_rate > ZERO
        and data.taxes is not None
        and data.subtotal is not None
    ):
        expected_tax = money(data.subtotal * expected_tax_rate)
        if data.taxes != expected_tax:
            tax_pct = money(expected_tax_rate * Decimal("100"))
            findings.append(
                Finding(
                    code="TAX_CALCULATION_MISMATCH",
                    blocking=False,
                    description=(
                        f"Cálculo de impuestos ({tax_name}) incorrecto: "
                        f"declarado USD {data.taxes}, esperado USD {expected_tax} "
                        f"({tax_pct}% de subtotal USD {data.subtotal})."
                    ),
                    calculation=(
                        f"{data.subtotal} × {expected_tax_rate} = {expected_tax} ≠ {data.taxes}"
                    ),
                    evidence_ids=[i.evidence_id for i in data.items if i.evidence_id][:1],
                )
            )

    return findings, money(sum(impact_by_item.values(), ZERO))


def check_semantic(review: SemanticReview) -> list[Finding]:
    return [
        Finding(
            code="CLAIM_INCONSISTENCY" if a.decision == "unsupported" else "SEMANTIC_UNCERTAIN",
            item_id=a.item_id,
            description=a.reason,
            evidence_ids=a.evidence_ids,
            blocking=a.decision == "uncertain",
        )
        for a in review.assessments
        if a.decision != "supported"
    ]


def derive_status(findings: list[Finding]) -> Status:
    if any(f.blocking for f in findings):
        return Status.INFORMATION
    return Status.REVIEW if findings else Status.CANDIDATE
