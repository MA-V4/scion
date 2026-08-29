from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCION_", env_file=".env", extra="ignore")

    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = Field(
        default="postgresql+asyncpg://scion:scion@localhost:5432/scion",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    ollama_base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    vllm_base_url: str = Field(
        default="http://localhost:8080", validation_alias="VLLM_BASE_URL"
    )

    otel_endpoint: str = Field(
        default="http://localhost:4317", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(default="scion-gateway", validation_alias="OTEL_SERVICE_NAME")

    models_config_path: str = "serving/models.yaml"


settings = Settings()
