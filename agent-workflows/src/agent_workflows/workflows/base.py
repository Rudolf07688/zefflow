"""BaseWorkflow ABC. All workflows subclass this and implement `_execute`."""
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from agent_workflows.logging import get_logger

log = get_logger(__name__)


class WorkflowResult(BaseModel):
    """Standard return envelope from any workflow run."""

    workflow_name: str
    status: Literal["success", "failed"]
    duration_seconds: float
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseWorkflow(ABC):
    """Subclass + set `name` + implement `_execute`."""

    name: ClassVar[str] = "base"

    def __init__(self, **kwargs: Any) -> None:
        self.config: dict[str, Any] = kwargs

    @abstractmethod
    def _execute(self) -> dict[str, Any]:
        """Subclass implementation. Return a JSON-serialisable dict."""

    def run(self) -> WorkflowResult:
        """Public entry point. Wraps `_execute` with logging and timing."""
        log.info("workflow.start", name=self.name, config=self.config)
        start = time.perf_counter()
        try:
            output = self._execute()
            duration = time.perf_counter() - start
            log.info("workflow.success", name=self.name, duration_seconds=duration)
            return WorkflowResult(
                workflow_name=self.name,
                status="success",
                duration_seconds=duration,
                output=output,
            )
        except Exception as exc:
            duration = time.perf_counter() - start
            log.exception("workflow.failed", name=self.name, duration_seconds=duration)
            return WorkflowResult(
                workflow_name=self.name,
                status="failed",
                duration_seconds=duration,
                error=str(exc),
            )
