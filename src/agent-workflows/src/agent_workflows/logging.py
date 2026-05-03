"""Structlog configuration. Import `get_logger` everywhere."""
import logging
import sys

import structlog
from structlog.typing import FilteringBoundLogger

from agent_workflows.config import settings

# Processors shared between structlog's chain and the stdlib foreign_pre_chain
# so that all log entries — regardless of origin — receive the same enrichment.
_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    structlog.processors.CallsiteParameterAdder(
        [
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
        ]
    ),
]


def configure_logging() -> None:
    """Idempotently configure structlog + stdlib logging."""
    if structlog.is_configured():
        return

    log_level: int = logging.getLevelNamesMapping().get(
        settings.log_level.upper(), logging.INFO
    )

    # Route all stdlib log records through the same ProcessorFormatter so that
    # third-party libraries (SQLAlchemy, httpx, …) share the same rich output.
    formatter = structlog.stdlib.ProcessorFormatter(
        # Applied to non-structlog records before the final processors run.
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=True,
                ),
            ),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            # Hand off to ProcessorFormatter for final rendering.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a configured logger. Configures on first call."""
    configure_logging()
    return structlog.get_logger(name)
