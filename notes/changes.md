# Change Log (append-only)

---

## 2026-04-28 — Day-0 bootstrap

**Agent:** claude-sonnet-4-6
**Action:** Initialized notes directory (`architecture.md`, `n8n-workflows.md`, `changes.md`)
**State at init:**
- Docker Compose stack scaffolded (postgres 17, ollama, ollama-pull, n8n) — code exists, stack not yet started
- Python layer in place: `AppConfig` (pydantic-settings), `compose-up` CLI entry point, empty `agents/` dir
- No n8n workflows exist; no models pulled; no Rails DB connected
- `.env` not yet populated with real secrets (`.env.example` present)
**No functional changes made to codebase.**

---

## 2026-04-28 — Mock DB schema + seed data

**Agent:** claude-sonnet-4-6
**Action:** Implemented `db_models.py` and `db_utils.py`; seeded local Postgres with mock data
**Changes:**
- `src/zefflow/db/db_models.py` — 8 SQLAlchemy 2.0 ORM models: `User`, `DataSource`, `Conversation`, `Message`, `AgentResponse`, `ToolCall`, `QueryExecution`, `AgentError`
- `src/zefflow/db/` — created `__init__.py`
- `src/zefflow/scripts/db_utils.py` — `create_db_engine`, `create_tables`, `drop_tables`, `populate_mock_db`; argparse CLI (`--reset`, `--populate`, `--db-url`)
- `src/zefflow/config/app_config.py` — added `postgres_host` field (default `localhost`) for local script connections
- `pyproject.toml` / `uv.lock` — added `psycopg2-binary==2.9.12`
**Seed data loaded into n8n-postgres (localhost:5432):**
- 3 users, 5 data sources (bigquery/postgres/redshift), 4 conversations, 8 messages, 4 agent responses, 5 tool calls, 4 query executions, 1 agent error
- Represents realistic sql-agent chatbot interactions: revenue queries, customer analytics, EXPLAIN ANALYZE, permission errors

---
