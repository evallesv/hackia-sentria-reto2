"""Prueba opt-in: consume como máximo tres llamadas Gemini con datos sintéticos."""

from app.agent.provider import GeminiProvider
from app.config import Settings
from app.main import load_case
from app.models import Status
from app.services.audit_service import run_audit

s = Settings()
if not s.gemini_model or not s.gemini_api_key.get_secret_value():
    raise SystemExit("Configura GEMINI_API_KEY y GEMINI_MODEL en .env.")
provider = GeminiProvider(s)
failed = False
for case in "ABC":
    r = run_audit(load_case(case), provider, "gemini")
    expected = Status.CANDIDATE if case == "A" else Status.REVIEW
    failed |= r.status != expected
    if case == "C":
        failed |= "CLAIM_INCONSISTENCY" not in {f.code for f in r.findings}
    print(case, r.status.value, r.flagged_difference, r.model, r.input_tokens, r.output_tokens)
raise SystemExit(1 if failed else 0)
