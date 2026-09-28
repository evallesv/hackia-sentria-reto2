import json
from pathlib import Path

from app.models import (
    AuditInput,
    AuditResult,
    Claim,
    ExtractionJob,
    SemanticReview,
    StoredDocument,
)

root = Path(__file__).resolve().parent.parent / "contracts"
root.mkdir(exist_ok=True)
for model in (AuditInput, AuditResult, SemanticReview, Claim, StoredDocument, ExtractionJob):
    (root / f"{model.__name__}.schema.json").write_text(
        json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
    )
