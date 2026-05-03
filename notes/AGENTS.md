# AGENTS.md — onboarding for an AI agent

Audience: an AI agent picking up this repo and/or the job of keeping
`notes/repo-map/` current. Read this in full before doing anything else.

---

## 1. Where to look first

| Need | File |
|---|---|
| What the project is | `notes/repo-map/00-overview.md` |
| Stack / services | `notes/repo-map/01-stack-and-services.md` |
| Per-package detail | `notes/repo-map/02-python-zefflow.md`, `03-python-agent-workflows.md` |
| Run / test it | `notes/repo-map/04-dev-and-test.md` |
| Known drift | `notes/repo-map/05-open-questions.md` |
| Why the doc looks like that | `notes/repo_overwiew.md` (methodology) + `notes/repo-map/debrief.md` |
| What changed when | `notes/changes.md` (append-only) |
| Project rules / requirements | `GENERAL.md` |

If `notes/repo-map/.evidence.json` is missing or `make repo-map-check` reports
stale, the docs may not match the code — verify before trusting them.

---

## 2. Hard rules

1. **Never read `.env`.** Use `.env.example`, weighted ~80% (keys may have drifted).
2. **Never run** `compose up`, migrations, mutating tests, or anything that touches a live service.
3. **Read-only shell only.** `git`, `tree`, `grep`, `cat`, `pytest --collect-only`, `docker compose config`, package-manager `tree`/`list`.
4. **Distrust any tree the host hands you.** Re-derive from `tree -L 4 --gitignore` + `git ls-files` + `git status`.
5. **Trajectory artefacts are signals, not facts.** Down-weight `tickets.json`, `TODO.md`, `ROADMAP.md`. Hierarchy: `commit history > working code > config/manifests > READMEs > tickets/TODOs`.
6. **Default audience: a developer being onboarded.** Switch only if told.
7. **Cite a path or command for every non-trivial claim.**
8. **Don't create markdown to document your own changes.** Append a one-liner to `notes/changes.md` instead.

---

## 3. Phase-0 commands (always run first)

```bash
tree -L 4 --gitignore -a -I '.git|.venv|node_modules|__pycache__|dist|build|.next|.DS_Store|*.egg-info'
git status --short
git log -1 --stat
git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn
```

---

## 4. Maintaining `notes/repo-map/`

Pipeline is three tiers; you are responsible for tiers 2 and 3.

| Tier | What | Who | When |
|---|---|---|---|
| 1 | `scripts/check-repo-map.sh` (no LLM, never blocks) | git pre-commit hook | every commit |
| 2 | Refresh affected docs only | you | when tier 1 warns |
| 3 | Full re-run of methodology | you | when most docs affected, or on request |

### Tier 2 — refresh (preferred for small drift)

1. `make repo-map-check` — note which docs and which paths it flags.
2. For each flagged path: read the current file, compare to what the doc says.
3. Edit only the affected docs. Keep the existing structure and tone.
4. Update `notes/repo-map/.evidence.json`:
   - bump `git_sha` to current `HEAD`
   - bump `generated_at` to current UTC ISO-8601
   - add any newly-cited paths to the relevant doc's array
   - remove paths you no longer cite
5. Update each touched doc's footer to the new short SHA + date.
6. Append a single line to `notes/changes.md`.
7. Re-run `make repo-map-check` — must come back clean.

### Tier 3 — full rebuild

1. Follow `notes/repo_overwiew.md` from Phase 0 to Phase 4 verbatim.
2. Replace every `notes/repo-map/*.md` and `.evidence.json`.
3. Append a `Tier-3 rebuild` line to `notes/changes.md`.

---

## 5. Quality bar before declaring done

- [ ] `make repo-map-check` exits 0 with no `STALE` warning.
- [ ] Every cited path resolves (`ls`).
- [ ] Mermaid blocks parse (quoted labels; no edges into subgraphs; no inline `:::class` on shaped nodes).
- [ ] No claim sourced only from a trajectory artefact is stated as fact.
- [ ] No `.env` was read.
- [ ] `notes/changes.md` updated.

---

## 6. Common traps

- IDE-supplied workspace trees can be stale — always re-derive (Rule 4).
- `agent-workflows/` is a separate uv project: `uv sync` at root does **not** install it.
- Two unrelated SQLAlchemy `Base`s exist (one per package) — don't conflate them.
- Root `pyproject.toml` has historically held stale entries (e.g. `"srt"`); verify before quoting it.
- Mermaid: prefer quoted labels and `class X foo;` over `[(...)]:::foo`.

---

## 7. Escalate (don't guess) if

- You'd need to read `.env` to verify a claim.
- You'd need to run a mutating command.
- You'd need to commit / push / force-push.
- The methodology in `notes/repo_overwiew.md` and a request from the user disagree.
