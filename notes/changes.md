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

## 2026-05-03 — agent-refresh CLI implemented (Tier 1 + 2)

**Agent:** copilot (claude-opus-4.7) — manual implementation
**Action:** Built end-to-end pipeline for keeping `notes/repo-map/` current.
**Components added:**
- `notes/repo_overwiew.md` — methodology spec (Phase 0 ground-truth, .env policy, audience, evidence rule)
- `notes/AGENTS.md` — onboarding doc for the next AI agent
- `notes/repo-map/` — 7 markdown docs + `.evidence.json` produced from manual dry run
- `scripts/check-repo-map.sh` — Tier-1 staleness detector (no LLM, never blocks)
- `scripts/install-hooks.sh` — installs non-blocking pre-commit hook
- `Makefile` — `repo-map-check`, `repo-map-refresh`, `repo-map-rebuild` targets
- `agent-workflows/src/agent_workflows/tools/repo_tools.py` — read-only tool layer with `.env` rejection at the boundary, repo-root path lock, bounded outputs
- `agent-workflows/src/agent_workflows/workflows/repo_map_refresh.py` — Tier-2 single-agent workflow that emits a structured `RefreshPlan`, code applies the patches; mermaid lint + filename allowlist + post-write Tier-1 re-check
- `agent-workflows/scripts/agent_refresh.py` — Typer CLI: `check`, `status`, `refresh`; bare `agent-refresh` runs check then offers refresh
- `agent-workflows/pyproject.toml` — declared `agent-refresh` script + packaged `scripts/` (was missing — pre-existing bug; `run-workflow` and `seed-db` were also broken)
- `agent-workflows/src/agent_workflows/config.py` — replaced eager Settings singleton with lazy proxy so no-LLM CLI subcommands work without `GOOGLE_API_KEY`

**Verified working:** `agent-refresh check`, `agent-refresh status`, pre-flight key check, registry lookup. Tier-2 refresh reaches the LLM; full end-to-end run pending a `GOOGLE_API_KEY` in env.

## 2026-05-03 — repo-map refresh
**Agent:** repo_map_refresh
**Action:** 2026-05-03 — agent-refresh CLI implemented (Tier 1 + 2)
**Updated docs:** 00-overview.md, 02-python-zefflow.md, 03-python-agent-workflows.md, 04-dev-and-test.md, debrief.md
**Verified against:** `6319dfb`
