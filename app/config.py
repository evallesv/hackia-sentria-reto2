from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_mode: Literal["mock", "gemini"] = "mock"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    enable_custom_input: bool = False
    max_request_bytes: int = Field(default=262144, ge=1024, le=1048576)
    llm_timeout_seconds: float = Field(default=30, gt=0, le=60)
    llm_max_output_tokens: int = Field(default=3000, ge=512, le=8000)
    llm_max_calls_per_process: int = Field(default=20, ge=0, le=1000)
