# Dev environment & tests

## Bring up the Compose stack

```bash
# from repo root, inside the dev container
cp .env.example .env          # then fill in real secrets
uv run compose-up             # → bash compose_up.sh → docker-compose up -d
```

What you should see after a healthy start:
- `n8n` UI at <http://localhost:5678> (basic auth — user/pass from `.env`)
- Postgres on `localhost:5432`
- Ollama bound to `127.0.0.1:11434`; one-shot `ollama-pull` exits after pulling `llama3.2` + `nomic-embed-text`

> **Status note:** No artefact in the repo confirms a clean Compose start. The architecture checklist in [notes/architecture.md](../architecture.md) is entirely unchecked. Treat the above as the intended path, not a verified one.

## Seed / reset the n8n-side Postgres (chatbot demo schema)

```bash
uv run db --reset --populate            # drop + create + seed mock chatbot data
# or with a custom URL:
uv run db --populate --db-url postgresql+psycopg2://user:pw@host:5432/db
```

Seeded by [src/zefflow/scripts/db_utils.py](../../src/zefflow/scripts/db_utils.py); `notes/changes.md` confirms a successful run on 2026-04-28 (3 users, 5 data sources, 4 conversations, 8 messages, …).

## Run an agent workflow

```bash
cd agent-workflows
cp .env.example .env                     # set GOOGLE_API_KEY (or LLM_PROVIDER=vertex + GOOGLE_CLOUD_PROJECT)
uv sync
uv run seed-db --customers 3 --products 2 --orders 5    # SQLite by default (./dev.db)
uv run run-workflow daily_db_report
```

This path is **not yet verified end-to-end** — see `tickets.json` TICKET-3 (P1, todo).

## Run `repo-map` agent workflows

This invokes the `agent-workflows/scripts/agent_refresh.py` CLI via the top-level `Makefile` targets:

```bash
# from repo root
# First-time init:
cd agent-workflows
uv run agent-refresh init      # full first-time scan + write all repo-map docs (requires LLM)
cd .. # back to repo root
# Then for subsequent checks/updates (from repo root):
make repo-map-check            # detect staleness, no LLM call
make repo-map-status           # show detailed diff (requires LLM)
make repo-map-refresh          # generate & apply patches (requires LLM)
```

## Tests

```bash
cd agent-workflows
uv run pytest                            # smoke only, no LLM, no DB
uv run pytest --collect-only -q          # list without running
```

The root `zefflow` package has **no tests**.

## Common gotchas (read off `notes/architecture.md` and `AppConfig`)

- n8n's `DB_TYPE` must be `postgresdb`, not `postgres`. The env var name is enforced; the value is a frequent footgun.
- Inside Compose, n8n addresses Postgres as `postgres:5432` and Ollama as `ollama:11434` — never `localhost` from inside containers.
- Mac users wanting native Metal Ollama: set `OLLAMA_HOST=host.docker.internal:11434` in `.env` for n8n, and don't start the in-container `ollama` service.
- `N8N_ENCRYPTION_KEY` must be ≥32 chars and stable — changing it invalidates stored credentials.
- The two Python packages have separate `uv` projects. Activating the root `.venv` does **not** install `agent-workflows` deps; `cd agent-workflows && uv sync` is required.
- The `agent-workflows` package's `Settings` object is now lazy-loaded, allowing no-LLM `agent-refresh` commands (like `check` or `status`) to run without `GOOGLE_API_KEY` being present in the environment.


---
*Last verified against commit `b3aff61` on 2026-05-03. Run `make repo-map-check` to detect drift; `make repo-map-rebuild` for a full refresh.*