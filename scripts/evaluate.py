"""Eval determinística reproducible; no atribuye precisión a un LLM no evaluado."""

import json

from app.agent.provider import MockProvider
from app.main import load_case
from app.services.audit_service import run_audit

EXPECTED = {
    "A": ("CANDIDATE_FOR_APPROVAL", "0.00"),
    "B": ("REVIEW_REQUIRED", "80.00"),
    "C": ("REVIEW_REQUIRED", "250.00"),
    "D": ("INFORMATION_REQUIRED", "0.00"),
}


def main():
    reports = []
    for case, (status, difference) in EXPECTED.items():
        r = run_audit(load_case(case), MockProvider())
        passed = r.status.value == status and str(r.flagged_difference) == difference
        reports.append(
            {
                "case": case,
                "passed": passed,
                "status": r.status.value,
                "difference": str(r.flagged_difference),
                "mode": r.mode,
            }
        )
    print(json.dumps(reports, indent=2))
    raise SystemExit(0 if all(r["passed"] for r in reports) else 1)


if __name__ == "__main__":
    main()
