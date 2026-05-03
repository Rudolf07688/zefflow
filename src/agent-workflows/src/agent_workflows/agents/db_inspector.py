"""Agent that interrogates the database to surface row counts, schema, anomalies."""
from typing import ClassVar

from agent_workflows.agents.base import BaseAgent
from agent_workflows.tools.db_tools import describe_table, list_tables, run_sql


class DbInspectorAgent(BaseAgent):
    role: ClassVar[str] = "db_inspector"

    instructions: ClassVar[list[str]] = [
        "You are a careful database inspector.",
        "Use the provided tools to list tables, describe their schema, and run SELECT queries.",
        "Never run write/DDL statements. If asked, refuse and explain why.",
        "Summarise findings in plain English with concrete numbers.",
    ]

    tools: ClassVar[list] = [list_tables, describe_table, run_sql]
