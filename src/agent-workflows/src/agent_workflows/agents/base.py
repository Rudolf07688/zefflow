"""BaseAgent — thin wrapper around agno.Agent.

Subclasses set class-level `role`, `instructions`, and `tools`, then __init__
constructs the underlying agno agent with the LLM from the project factory.
"""
from typing import Any, ClassVar

from pydantic import BaseModel

from agent_workflows.llm import build_model
from agent_workflows.logging import get_logger

log = get_logger(__name__)


class BaseAgent:
    """Subclass and override class attributes to define a new agent."""

    role: ClassVar[str] = "generic"
    instructions: ClassVar[list[str]] = []
    tools: ClassVar[list[Any]] = []

    def __init__(self, model_id: str | None = None, **agno_kwargs: Any) -> None:
        # Lazy import — keeps test/CI imports light.
        from agno.agent import Agent  # type: ignore[import-not-found]

        self._model_id = model_id
        self.agno_agent = Agent(
            model=build_model(model_id),
            tools=list(self.tools),
            instructions=list(self.instructions),
            markdown=True,
            **agno_kwargs,
        )

    def run(self, prompt: str, **kwargs: Any) -> str:
        """Run the agent on a prompt and return its text content."""
        log.info("agent.run", role=self.role, model=self._model_id)
        result = self.agno_agent.run(prompt, **kwargs)
        return getattr(result, "content", str(result))

    def run_structured[T: BaseModel](
        self, prompt: str, response_model: type[T], **kwargs: Any
    ) -> T:
        """Run with a pydantic response_model and return the parsed object."""
        log.info("agent.run_structured", role=self.role, schema=response_model.__name__)
        result = self.agno_agent.run(prompt, response_model=response_model, **kwargs)
        return result.content  # agno populates .content with the parsed model
