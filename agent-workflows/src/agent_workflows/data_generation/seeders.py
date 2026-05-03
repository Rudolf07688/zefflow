"""Persist generated rows into a SQL table via SQLAlchemy core."""
from typing import Sequence

from pydantic import BaseModel
from sqlalchemy import MetaData, Table

from agent_workflows.db.engine import get_engine
from agent_workflows.logging import get_logger

log = get_logger(__name__)


def seed_table(table_name: str, rows: Sequence[BaseModel]) -> int:
    """Bulk insert pydantic rows into `table_name`. Returns count inserted."""
    if not rows:
        return 0

    engine = get_engine()
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    payload = [r.model_dump(mode="json") for r in rows]

    with engine.begin() as conn:
        conn.execute(table.insert(), payload)

    log.info("seeder.inserted", table=table_name, rows=len(payload))
    return len(payload)
