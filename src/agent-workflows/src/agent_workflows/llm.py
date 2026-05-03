"""LLM factory. Returns an agno-compatible model instance based on env config.

Toggle via LLM_PROVIDER env var:
- "gemini" -> Google AI Studio (uses GOOGLE_API_KEY)
- "vertex" -> Vertex AI (uses ADC + GOOGLE_CLOUD_PROJECT)
"""
from typing import Any

from agent_workflows.config import settings
from agent_workflows.logging import get_logger

log = get_logger(__name__)


def build_model(model_id: str | None = None, **kwargs: Any) -> Any:
    """Return an Agno-compatible model instance.

    Note: agno exposes Gemini through `agno.models.google.Gemini` and supports
    Vertex AI through the same class with `vertexai=True` (subject to agno
    version — adjust import if your installed version differs).
    """
    chosen_model = model_id or settings.default_model

    # Imported lazily so that missing optional deps don't break import-time.
    from agno.models.google import Gemini  # type: ignore[import-not-found]

    if settings.llm_provider == "gemini":
        log.debug("llm.build", provider="gemini", model=chosen_model)
        return Gemini(id=chosen_model, api_key=settings.google_api_key, **kwargs)

    if settings.llm_provider == "vertex":
        log.debug(
            "llm.build",
            provider="vertex",
            model=chosen_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
        return Gemini(
            id=chosen_model,
            vertexai=True,
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            **kwargs,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
