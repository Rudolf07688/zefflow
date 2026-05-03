"""Read-only DB tools exposed to agents."""
from typing import Any

from sqlalchemy import inspect, text

from agent_workflows.db.engine import get_engine
from agent_workflows.logging import get_logger

log = get_logger(__name__)

_FORBIDDEN_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "truncate", "create"}


def list_tables() -> list[str]:
    """Return the list of table names in the configured database."""
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    log.debug("tools.list_tables", count=len(tables))
    return tables


def describe_table(table_name: str) -> list[dict[str, Any]]:
    """Return column metadata (name, type, nullable, default) for a table."""
    engine = get_engine()
    inspector = inspect(engine)
    cols = inspector.get_columns(table_name)
    return [
        {
            "name": c["name"],
            "type": str(c["type"]),
            "nullable": c.get("nullable", True),
            "default": c.get("default"),
        }
        for c in cols
    ]


def run_sql(query: str, limit: int = 100) -> list[dict[str, Any]]:
    """Execute a read-only SQL query and return up to `limit` rows.

    Refuses any query containing write/DDL keywords as a basic safeguard.
    """
    lowered = query.lower()
    if any(kw in lowered.split() for kw in _FORBIDDEN_KEYWORDS):
        raise PermissionError(
            "run_sql is read-only. Refused query containing write/DDL keywords."
        )

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(query)).mappings().fetchmany(limit)

    log.debug("tools.run_sql", returned=len(rows))
    return [dict(r) for r in rows]
