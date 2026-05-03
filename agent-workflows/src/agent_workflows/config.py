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


# Lazy singleton — instantiating Settings validates credentials, so we defer
# until first use. This keeps no-LLM entrypoints (e.g. `agent-refresh check`)
# importable without GOOGLE_API_KEY.
class _LazySettings:
    """Defer Settings() until first attribute access.

    If credentials are missing (e.g. running a no-LLM CLI subcommand without
    GOOGLE_API_KEY), fall back to a minimally-initialised Settings via
    `model_construct`, which skips validators. The Gemini factory in `llm.py`
    will still raise on first real use.
    """

    _instance: Settings | None = None

    def _resolve(self) -> Settings:
        if _LazySettings._instance is not None:
            return _LazySettings._instance
        try:
            _LazySettings._instance = Settings()  # type: ignore[call-arg]
        except Exception:  # validation failure (e.g. no GOOGLE_API_KEY)
            _LazySettings._instance = Settings.model_construct(
                llm_provider="gemini",
                default_model="gemini-2.5-flash",
                google_api_key=None,
                google_cloud_project=None,
                google_cloud_location="us-central1",
                database_url="sqlite:///./dev.db",
                log_level="INFO",
            )
        return _LazySettings._instance

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._resolve(), name)


settings = _LazySettings()  # type: ignore[assignment]
