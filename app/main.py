from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent.provider import GeminiProvider, MockProvider
from app.api.documents import router as documents_router
from app.config import Settings
from app.models import AuditInput, AuditResult
from app.services.audit_service import run_audit
from app.services.intake import InMemoryClaimRepository, IntakeService

ROOT = Path(__file__).resolve().parent.parent
CASES = {
    "A": "Sin discrepancias",
    "B": "Diferencia tarifaria",
    "C": "Múltiples hallazgos",
    "D": "Información incompleta",
}


def load_case(case_id: str) -> AuditInput:
    if case_id not in CASES:
        raise HTTPException(404, "Caso inexistente")
    return AuditInput.model_validate_json((ROOT / "data/demo" / f"case_{case_id}.json").read_text())


class RequestLimit:
    """Limita bytes reales, distinguiendo entradas JSON frente a subidas documentales."""

    def __init__(self, app, max_bytes: int, max_upload_bytes: int = 12 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes
        self.max_upload_bytes = max_upload_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        limit = (
            self.max_upload_bytes
            if ("/documents" in path and path.startswith("/api/claims/"))
            else self.max_bytes
        )

        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                return await JSONResponse({"detail": "Solicitud demasiado grande"}, 413)(
                    scope, receive, send
                )
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay():
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None):
    s = settings or Settings()
    api = FastAPI(title="Auditor de siniestros · Equipo Sentria", version="0.1.0")
    api.add_middleware(
        RequestLimit,
        max_bytes=s.max_request_bytes,
        max_upload_bytes=s.max_upload_bytes + 262144,
    )
    api.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=ROOT / "templates")
    provider = MockProvider() if s.ai_mode == "mock" else GeminiProvider(s)
    cache, cache_lock = {}, Lock()

    upload_storage = ROOT / s.upload_dir
    claim_repo = InMemoryClaimRepository(storage_dir=upload_storage)
    intake_service = IntakeService(
        repository=claim_repo,
        storage_dir=upload_storage,
        max_file_bytes=s.max_upload_bytes,
    )
    api.state.claim_repo = claim_repo
    api.state.intake_service = intake_service
    api.include_router(documents_router)

    @api.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path == "/":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
            )
        return response

    @api.get("/healthz")
    def health():
        return {"status": "ok", "mode": s.ai_mode, "version": "0.1.0"}

    @api.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "cases": CASES,
                "mode": s.ai_mode,
                "custom_input": s.enable_custom_input,
            },
        )

    @api.get("/api/demo/{case_id}", response_model=AuditInput)
    def fixture(case_id: str):
        return load_case(case_id)

    @api.post("/api/demo/{case_id}/audit", response_model=AuditResult)
    def demo(case_id: str):
        data = load_case(case_id)
        # Solo cuatro entradas inmutables. Una llamada por caso/proceso evita abuso de gasto.
        with cache_lock:
            if case_id not in cache:
                cache[case_id] = run_audit(data, provider, s.ai_mode)
            return cache[case_id]

    @api.post("/api/audits", response_model=AuditResult)
    def audit(data: AuditInput):
        if not s.enable_custom_input:
            raise HTTPException(403, "La demo pública solo permite los casos sintéticos incluidos")
        return run_audit(data, provider, s.ai_mode)

    return api


app = create_app()
