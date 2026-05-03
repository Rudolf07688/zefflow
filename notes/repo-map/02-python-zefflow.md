# Python package: `zefflow` (root)

Path: [src/zefflow/](../../src/zefflow/) — declared by the root [pyproject.toml](../../pyproject.toml).

## Role

Owns **infra glue** for the Compose stack: env-var schema, a wrapper around `compose_up.sh`, and a Postgres seed/reset CLI for the n8n-side database. It does *not* contain any agent code.

## Entry points

Declared under `[project.scripts]`:

| Command | Target | What it does |
|---|---|---|
| `compose-up` | [`zefflow.scripts.compose_up:main`](../../src/zefflow/scripts/compose_up.py) | `chmod +x compose_up.sh` then `bash compose_up.sh "$@"` (which is `docker-compose up -d` + `ps`). |
| `db` | [`zefflow.scripts.db_utils:cli`](../../src/zefflow/scripts/db_utils.py) | Typer CLI: `create_db_engine`, `create_tables`, `drop_tables`, `populate_mock_db` — seeds a chatbot-style schema. |

## Modules

| File | Purpose |
|---|---|
| [config/app_config.py](../../src/zefflow/config/app_config.py) | `AppConfig(BaseSettings)` — every env var the Compose stack consumes, with descriptions. Exports `default_app_config` singleton. |
| [db/db_models.py](../../src/zefflow/db/db_models.py) | SQLAlchemy 2.0 ORM: `User`, `DataSource`, `Conversation`, `Message`, `AgentResponse`, `ToolCall`, `QueryExecution`, `AgentError`. Schema looks like a SQL-agent chat product. |
| [scripts/db_utils.py](../../src/zefflow/scripts/db_utils.py) | Builds a `postgresql+psycopg2://…` URL from `AppConfig`, creates/drops/seeds tables. `notes/changes.md` confirms it ran successfully on 2026-04-28 against `localhost:5432`. |
| [scripts/compose_up.py](../../src/zefflow/scripts/compose_up.py) | Thin Python wrapper for `compose_up.sh`. |
| [agents/](../../src/zefflow/agents/) | **Empty** (only `__init__.py`). |

## Key facts

- Python ≥3.11. Managed with `uv`. Single root `uv.lock`.
- Deps: `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg2-binary`, `typer`, `google-genai`. The last two only make sense if this package is going to absorb agent code later — currently unused here.
- `[tool.hatch.build.targets.wheel].packages` in root `pyproject.toml` lists `["src/zefflow", "srt"]`. `"srt"` is almost certainly a **typo** (likely a leftover from when `src/agent-workflows` was the second package); see [05-open-questions.md](05-open-questions.md).

## What it does *not* do (yet)

- Connect to a Rails DB.
- Run any agent or LLM call.
- Reference the `agent-workflows` package in any way.


---
*Last verified against commit `c8221e0` on 2026-05-03.*