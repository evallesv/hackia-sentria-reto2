"""Consulta modelos disponibles en la cuenta sin imprimir la clave."""

from google import genai

from app.config import Settings

s = Settings()
if not s.gemini_api_key.get_secret_value():
    raise SystemExit("Configura GEMINI_API_KEY en .env antes de consultar modelos.")
with genai.Client(api_key=s.gemini_api_key.get_secret_value()) as client:
    for model in client.models.list():
        if "generateContent" in (model.supported_actions or []):
            print(model.name)
