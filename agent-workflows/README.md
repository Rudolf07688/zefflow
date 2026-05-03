# agent-workflows

Object-oriented agent workflows powered by **Agno** + **Gemini / Vertex AI**.

## Why

- Workflows are first-class Python classes — single-line execution after import.
- Agents are reusable building blocks composed inside workflows.
- LLM-backed mock data generation for seeding dev/test databases.
- Provider-agnostic LLM factory: toggle Gemini ↔ Vertex AI via env var.

## Quick start

```bash
# 1. Install
uv sync

# 2. Configure
cp .env.example .env
# fill in GOOGLE_API_KEY (or set LLM_PROVIDER=vertex + GOOGLE_CLOUD_PROJECT)

# 3. Seed a demo DB with realistic mock data
uv run seed-db

# 4. Run a workflow
uv run run-workflow daily_db_report
```

## Single-line UX

```python
from agent_workflows import run

result = run("daily_db_report")
print(result.output["report"])
```

Or class-style:

```python
from agent_workflows.workflows import DailyDbReportWorkflow

DailyDbReportWorkflow().run()
```

## Structure

```
src/agent_workflows/
├── config.py            # pydantic-settings, fail-fast on missing keys
├── llm.py               # Gemini / Vertex factory
├── logging.py           # structlog setup
├── agents/              # BaseAgent + concrete agents
├── tools/               # @tool functions for agno
├── workflows/           # BaseWorkflow + concrete workflows + registry
├── data_generation/     # MockDataFactory (LLM-backed Faker)
└── db/                  # SQLAlchemy engine + models
```

## Adding a new workflow

1. Subclass `BaseWorkflow` in `workflows/your_workflow.py`.
2. Implement `_execute() -> dict[str, Any]`.
3. Register in `workflows/registry.py`.
4. Run with `run("your_workflow")`.

## Adding a new mock-data schema

1. Define a pydantic model in `data_generation/schemas.py`.
2. `MockDataFactory().generate(YourSchema, n=100, context="...")`.
3. Pipe through `seeders.write_to_table(...)`.
