import hashlib
from decimal import Decimal
from time import perf_counter

from app.agent.provider import ProviderError, SemanticProvider, validate_review
from app.audit.engine import (
    ZERO,
    check_financials,
    check_integrity,
    check_semantic,
    derive_status,
    money,
)
from app.config import Settings
from app.models import AuditInput, AuditResult, Finding


def run_audit(
    data: AuditInput,
    provider: SemanticProvider,
    mode: str = "mock",
    tax_rate: Decimal | None = None,
    tax_name: str = "ITBMS",
) -> AuditResult:
    start = perf_counter()
    trace = ["integrity_check"]
    findings = check_integrity(data)
    difference = ZERO
    model, input_tokens, output_tokens = None, 0, 0
    if not findings:
        if tax_rate is None:
            try:
                s = Settings(_env_file=None)
                tax_rate = s.tax_rate
                tax_name = s.tax_name
            except Exception:
                tax_rate = Decimal("0.07")
                tax_name = "ITBMS"

        financials, difference = check_financials(
            data, expected_tax_rate=tax_rate, tax_name=tax_name
        )
        findings.extend(financials)
        trace.extend(["quote_check", "tariff_check"])
        try:
            output = provider.review(data)
            validate_review(data, output.review)
            findings.extend(check_semantic(output.review))
            model = output.model
            input_tokens, output_tokens = output.input_tokens, output.output_tokens
            trace.append(
                "claim_check:simulated" if mode == "mock" else "submit_claim_assessments:validated"
            )
        except ProviderError:
            findings.append(
                Finding(
                    code="SEMANTIC_UNAVAILABLE",
                    blocking=True,
                    description="Revisión semántica incompleta. Reintentar o revisar manualmente.",
                )
            )
            trace.append("claim_check:unavailable")
    trace.append("deterministic_consolidation")
    reference = None
    if not any(f.blocking for f in findings) and data.subtotal is not None:
        reference = money(max(ZERO, data.subtotal - difference))
    return AuditResult(
        claim_id=data.claim_id,
        status=derive_status(findings),
        billed_amount=data.total,
        flagged_difference=difference,
        reference_subtotal=reference,
        findings=findings,
        evidence=data.evidence,
        mode=mode,
        trace=trace,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=round((perf_counter() - start) * 1000),
        input_sha256=hashlib.sha256(data.model_dump_json().encode()).hexdigest(),
    )
