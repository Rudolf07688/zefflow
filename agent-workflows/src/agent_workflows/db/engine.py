"""SQLAlchemy engine factory. Cached singleton based on DATABASE_URL."""
from functools import cache

from sqlalchemy import Engine, create_engine

from agent_workflows.config import settings
from agent_workflows.logging import get_logger

log = get_logger(__name__)


@cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine for the configured DATABASE_URL."""
    log.debug("db.engine.create", url=settings.database_url.split("@")[-1])
    return create_engine(settings.database_url, future=True)


def init_db() -> None:
    """Create all tables defined on Base.metadata."""
    from agent_workflows.db.models import Base

    engine = get_engine()
    Base.metadata.create_all(engine)
    log.info("db.init", tables=list(Base.metadata.tables.keys()))
