"""Puerto pequeño para cambiar de proveedor sin cambiar motor, API o pruebas."""

import json
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from app.agent.prompts import SYSTEM
from app.config import Settings
from app.models import Assessment, AuditInput, DocumentKind, SemanticReview


class ProviderError(Exception):
    """Error seguro: no incluye documentos, claves ni respuesta cruda del proveedor."""


@dataclass
class ProviderResult:
    review: SemanticReview
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class SemanticProvider(Protocol):
    def review(self, data: AuditInput) -> ProviderResult: ...


def validate_review(data: AuditInput, review: SemanticReview) -> None:
    ids = [a.item_id for a in review.assessments]
    if len(ids) != len(set(ids)) or set(ids) != {i.id for i in data.items}:
        raise ProviderError("Cobertura de líneas inválida")
    docs = {d.id: d for d in data.documents if d.active}
    evidence = {e.id: e for e in data.evidence if e.document_id in docs}
    items = {i.id: i for i in data.items}
    for assessment in review.assessments:
        if not set(assessment.evidence_ids) <= set(evidence):
            raise ProviderError("El proveedor citó evidencia inexistente o inactiva")
        if items[assessment.item_id].evidence_id not in assessment.evidence_ids:
            raise ProviderError("Falta referencia de la línea evaluada")
        if assessment.decision == "supported":
            kinds = {docs[evidence[e].document_id].kind for e in assessment.evidence_ids}
            if not {DocumentKind.INCIDENT, DocumentKind.INSPECTION} <= kinds:
                raise ProviderError("Falta respaldo de ambos reportes")


class MockProvider:
    def review(self, data: AuditInput) -> ProviderResult:
        docs = {d.id: d for d in data.documents if d.active}
        support = [
            e.id
            for e in data.evidence
            if e.document_id in docs
            and docs[e.document_id].kind in (DocumentKind.INCIDENT, DocumentKind.INSPECTION)
        ]
        assessments = []
        for item in data.items:
            supported = (
                item.damage_code in data.reported_damage_codes
                and item.damage_code in data.inspected_damage_codes
            )
            assessments.append(
                Assessment(
                    item_id=item.id,
                    decision="supported" if supported else "unsupported",
                    reason="Código respaldado en ambos reportes sintéticos."
                    if supported
                    else "La reparación requiere justificación; falta respaldo en ambos reportes.",
                    evidence_ids=[item.evidence_id, *support][:10],
                )
            )
        result = SemanticReview(assessments=assessments)
        validate_review(data, result)
        return ProviderResult(result)


class GeminiProvider:
    """Una llamada acotada, una herramienta permitida y validación local de su salida."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.calls = 0
        self.lock = Lock()

    def review(self, data: AuditInput) -> ProviderResult:
        from google import genai
        from google.genai import types

        s = self.settings
        if not s.gemini_api_key.get_secret_value() or not s.gemini_model:
            raise ProviderError("Proveedor sin configurar")
        self.reserve_call()
        active = {d.id for d in data.documents if d.active}
        payload = {
            "documents": [{"id": d.id, "kind": d.kind} for d in data.documents if d.active],
            "evidence": [e.model_dump() for e in data.evidence if e.document_id in active],
            "items": [
                {"item_id": i.id, "description": i.description, "evidence_id": i.evidence_id}
                for i in data.items
            ],
        }
        # Gemini 2.5 rechaza schemas complejos (error 400: too many states).
        # Schema mínimo equivalente sin metadatos de Pydantic.
        schema = {
            "type": "object",
            "required": ["assessments"],
            "properties": {
                "assessments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["item_id", "decision", "reason", "evidence_ids"],
                        "properties": {
                            "item_id": {"type": "string"},
                            "decision": {"type": "string", "enum": ["supported", "unsupported"]},
                            "reason": {"type": "string"},
                            "evidence_ids": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                }
            },
        }
        try:
            with genai.Client(
                api_key=s.gemini_api_key.get_secret_value(),
                http_options=types.HttpOptions(
                    timeout=int(s.llm_timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ) as client:
                response = client.models.generate_content(
                    model=s.gemini_model,
                    contents=json.dumps(payload, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM,
                        max_output_tokens=s.llm_max_output_tokens,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                        tools=[
                            types.Tool(
                                function_declarations=[
                                    types.FunctionDeclaration(
                                        name="submit_claim_assessments",
                                        description="Registrar evaluación y evidencia por línea.",
                                        parameters_json_schema=schema,
                                    )
                                ]
                            )
                        ],
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(
                                mode="ANY",
                                allowed_function_names=["submit_claim_assessments"],
                            )
                        ),
                    ),
                )
            if (
                not response.candidates
                or response.candidates[0].finish_reason != types.FinishReason.STOP
            ):
                raise ProviderError("Respuesta incompleta o bloqueada")
            calls = response.function_calls or []
            if len(calls) != 1 or calls[0].name != "submit_claim_assessments":
                raise ProviderError("Llamada de herramienta inválida")
            review = SemanticReview.model_validate(calls[0].args)
            validate_review(data, review)
            usage = response.usage_metadata
            return ProviderResult(
                review,
                response.model_version or s.gemini_model,
                (usage.prompt_token_count or 0) if usage else 0,
                ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0))
                if usage
                else 0,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("Proveedor no disponible o salida inválida") from exc

    def reserve_call(self):
        with self.lock:
            if self.calls >= self.settings.llm_max_calls_per_process:
                raise ProviderError("Límite de llamadas del proceso alcanzado")
            self.calls += 1
