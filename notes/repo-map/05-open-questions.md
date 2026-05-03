# Open questions, drift, and dead code

> Things a reviewer should resolve before assuming this repo behaves as
> documented. Each item cites its evidence so the owner can verify quickly.

## Drift / structural

1. **`agent-workflows` location is in flux.**
   `git status` shows 30+ deletions under `src/agent-workflows/` and the same files exist (un-tracked) at top-level `agent-workflows/`. The move hasn't been committed.
   *Action:* commit the move (or revert) and update the root `pyproject.toml`.

2. **Root `pyproject.toml` has a probable typo.**
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = [
       "src/zefflow",
       "srt"        # ← almost certainly stale / typo
   ]
   ```
   Likely a leftover from when `src/agent-workflows/src/agent_workflows` was the second packaged dir. Either remove it or replace with the correct path post-move.

3. **Two unrelated SQLAlchemy schemas.**
   - [src/zefflow/db/db_models.py](../../src/zefflow/db/db_models.py) — chatbot domain (users, conversations, tool_calls, agent_errors).
   - [agent-workflows/src/agent_workflows/db/models.py](../../agent-workflows/src/agent_workflows/db/models.py) — e-commerce demo (customers, products, orders).
   They share neither `Base` nor schema. Owner should confirm whether one is throwaway demo data and the other is the real target.

4. **No Rails DB anywhere.** The README and `notes/architecture.md` repeatedly cite a "Rails app Postgres" as the analytical target, but nothing in the code references one — no schema, no env var, no n8n credential. This is the single biggest gap between intent and implementation.

5. **`infra/Dockerfile` is empty.** Either delete or implement.

6. **`shared/` is empty.** It's bind-mounted into n8n at `/data/shared`; fine to leave empty until a workflow uses it.

## Stale notes

7. **`notes/architecture.md` and `notes/n8n-workflows.md`** are dated 2026-04-28 and are now out of step with code (the entire `agent-workflows` package post-dates them). Recommend updating after the next milestone or moving them under `notes/repo-map/` where this snapshot lives.

8. **`CLAUDE.md.bak`** at the repo root and `.claude/` directory suggest a previous Claude-driven workflow. Decide: archive or delete.

## Dependency drift

9. **Root `pyproject.toml` declares `google-genai` and `sqlalchemy`** but no code in `src/zefflow/` uses them. Imports cross-check (62 grep hits across both packages) shows zero hits in `src/zefflow/` for `google.genai`, `agno`, `structlog`. Either the root package is intended to grow into the agent runtime or these are stale.

10. **`agno` is unpinned** (`>=1.1.0`). `tickets.json` TICKET-2 explicitly flags this as a P1 risk because Agno's `models.google.Gemini` API has been moving.

## Security / safety nits (not urgent at this stage)

11. **`run_sql` keyword guard is naive.** [agent-workflows/.../tools/db_tools.py](../../agent-workflows/src/agent_workflows/tools/db_tools.py) blocks `insert/update/delete/drop/alter/truncate/create` by splitting on whitespace and lowercasing. Trivially bypassable (e.g. comment injection, multi-statement queries, `WITH` chains). Acceptable for a demo against a dev DB; tighten before pointing it at any real DB. Best fix: connect with a read-only Postgres role and stop pretending the keyword filter is a guarantee.

12. **Default credentials in `AppConfig`** (`change_me_strong_password`, `change_me_now`, `replace_with_long_random_secret_32chars_min`) are sensible defaults, but `AppConfig` will load them silently if `.env` is missing keys. Consider a `model_validator` that refuses the literal `change_me_*` strings outside of dev.

## Verification checklist (for the owner)

- [ ] Confirm intended layout for `agent-workflows` (top-level vs `src/`); commit the move.
- [ ] Decide whether `zefflow` package will host agent code or stay infra-only; clean its declared deps accordingly.
- [ ] Reconcile or delete one of the two demo SQLAlchemy schemas.
- [ ] Add the Rails Postgres connection target (env, n8n credential, or a SQLAlchemy URL).
- [ ] Pin `agno` and `n8nio/n8n` images.
- [ ] Either fill `infra/Dockerfile` or remove it.


---
*Last verified against commit `6319dfb` on 2026-05-03. Run `make repo-map-check` to detect drift; `make repo-map-rebuild` for a full refresh.*
