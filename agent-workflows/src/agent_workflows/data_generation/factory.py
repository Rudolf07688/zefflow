"""LLM-powered mock data generator. Think Faker, but the realism comes from the model."""
from typing import Any

from pydantic import BaseModel, RootModel

from agent_workflows.agents.base import BaseAgent
from agent_workflows.logging import get_logger

log = get_logger(__name__)


class _GeneratorAgent(BaseAgent):
    role = "mock_data_generator"
    instructions = [
        "You generate realistic synthetic data for testing.",
        "Match the requested schema EXACTLY. Keep distributions realistic.",
        "Do not repeat values across rows unless natural (e.g. country names).",
        "Return ONLY the structured response — no commentary.",
    ]


class MockDataFactory:
    """Generate batches of realistic rows for any pydantic schema."""

    def __init__(self, model_id: str | None = None) -> None:
        self._agent = _GeneratorAgent(model_id=model_id)

    def generate[T: BaseModel](self,schema: type[T], n: int, 
                               context: str = "", **agent_kwargs: Any,) -> list[T]:
        """Generate `n` rows matching `schema`.

        Args:
            schema: pydantic model class describing one row.
            n: number of rows to generate.
            context: free-text hint to bias generation (e.g. "UK fintech, 2024").
        """
        # Build a list-of-T root model on the fly so agno can parse the response.
        list_model = RootModel[list[schema]]  # type: ignore[valid-type]

        prompt = (
            f"Generate exactly {n} realistic rows matching the schema `{schema.__name__}`.\n"
            f"Context / domain hints: {context or 'general purpose'}.\n"
            f"Return a JSON array of {n} objects."
        )

        log.info(
            "mock_data.generate",
            schema=schema.__name__,
            n=n,
            context=context[:60] if context else None,
        )

        result = self._agent.run_structured(
            prompt, response_model=list_model, **agent_kwargs
        )
        return result.root  # type: ignore[attr-defined]
