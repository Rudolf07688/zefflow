"""Object-oriented agent workflows powered by Agno + Gemini/Vertex AI."""
from typing import Any

from agent_workflows.workflows.base import BaseWorkflow, WorkflowResult
from agent_workflows.workflows.registry import WORKFLOWS

__all__ = ["BaseWorkflow", "WorkflowResult", "run", "list_workflows"]


def run(name: str, **kwargs: Any) -> WorkflowResult:
    """Run a registered workflow by name.

    Example:
        >>> from agent_workflows import run
        >>> result = run("daily_db_report")
    """
    if name not in WORKFLOWS:
        raise KeyError(
            f"Workflow '{name}' not found. Available: {sorted(WORKFLOWS.keys())}"
        )
    return WORKFLOWS[name](**kwargs).run()


def list_workflows() -> list[str]:
    """Return all registered workflow names."""
    return sorted(WORKFLOWS.keys())
