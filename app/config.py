from decimal import Decimal
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_mode: Literal["mock", "gemini"] = "mock"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    enable_custom_input: bool = False
    demo_auth_enabled: bool = False
    demo_username: str = Field(default="jurado", min_length=1, max_length=100)
    demo_password: SecretStr = SecretStr("")
    max_request_bytes: int = Field(default=262144, ge=1024, le=1048576)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    upload_dir: str = "storage/uploads"
    database_url: str = ""
    llm_timeout_seconds: float = Field(default=30, gt=0, le=60)
    llm_max_output_tokens: int = Field(default=3000, ge=512, le=8000)
    llm_max_calls_per_process: int = Field(default=20, ge=0, le=1000)

    # Configuración impositiva (por defecto 7% ITBMS para Panamá, configurable para otros países)
    tax_name: str = Field(default="ITBMS", max_length=50)
    tax_rate: Decimal = Field(default=Decimal("0.07"), ge=0, le=1)
