"""Centralised config loaded from .env. Fails fast on missing required keys."""
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM provider toggle
    llm_provider: Literal["gemini", "vertex"] = "gemini"
    default_model: str = "gemini-2.5-flash"

    # Gemini (Google AI Studio)
    google_api_key: str | None = None

    # Vertex AI
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"

    # DB
    database_url: str = "sqlite:///./dev.db"

    # Logging
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> "Settings":
        if self.llm_provider == "gemini" and not self.google_api_key:
            raise ValueError(
                "LLM_PROVIDER=gemini requires GOOGLE_API_KEY in env / .env"
            )
        if self.llm_provider == "vertex" and not self.google_cloud_project:
            raise ValueError(
                "LLM_PROVIDER=vertex requires GOOGLE_CLOUD_PROJECT in env / .env"
            )
        return self


# Singleton — import this everywhere instead of re-instantiating.
settings = Settings()  # type: ignore[call-arg]
