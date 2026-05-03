---
date: 2026-05-03
status: methodology spec — manual dry run before building the agent
---

# Repo-Explainer: Methodology

> We are **not** writing the agent yet. This document captures the workflow we
> will execute manually on this very repo so we can observe what works, then
> codify it into the real agent. The most valuable artifact at the end is the
> **debrief** — the heuristics the future agent should encode.

---

## TL;DR

- **Goal:** produce a repo explanation a project owner can sanity-check in <60s and drill into when they want detail.
- **Output:** multi-file under `notes/repo-map/` with three diagrams (architecture, directory→responsibility, data flow).
- **Approach:** medium depth, read-only commands allowed, four phases — orient → drill → synthesize → self-review.
- **Audience:** project owner / reviewer (so: flag drift, don't cheerlead).

---

## Phases & Steps

### Phase 0 — Ground truth (do this first, every time)

> Distrust any tree the IDE/host gives you. Establish ground truth from the
> filesystem and git, not from supplied summaries.

0a. `tree -L 4 --gitignore -a -I '.git|.venv|node_modules|__pycache__|dist|build|.next|.DS_Store|*.egg-info'` — canonical structural source of truth.
0b. `git status --short` and `git log -1 --stat` — detect uncommitted refactors and recent activity. Large moves/deletes ⇒ any pre-supplied tree is stale.
0c. `git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn` — tracked-file weight per top-level dir.

### Phase 1 — Orient (breadth, no detail)

1. Read all manifest files: every `pyproject.toml` / `package.json` / `Cargo.toml`, `docker-compose.yml`, `Dockerfile`s, root `README.md`, `GENERAL.md` / `AGENTS.md` / `CLAUDE.md`, every file in `notes/` or `docs/`.
2. **`.env` policy:** never read `.env`. `.env.example` is permitted but weighted at ~80% certainty — keys may have been added/removed/renamed since. Cite anything from it as "per `.env.example`" so the reader can re-verify.
3. From manifests, derive language(s), package manager, declared entrypoints, services, load-bearing deps.
4. Write a 3–5-sentence **pre-drill hypothesis** before reading any source. Keep for comparison.

**Default audience: a developer being onboarded to the repo.** Optimise for "what do I need to understand to make my first useful change," not "what would impress a reviewer." Switch audience only when explicitly told.

**Trajectory artefacts (`tickets.json`, `TODO.md`, `ROADMAP.md`) are read but down-weighted.** Treat them as "what someone wrote down once," not as fact — they are routinely out of date. **Citation hierarchy when claims conflict: commit history > working code > config/manifests > READMEs > tickets/TODOs/roadmap docs.** If a trajectory artefact is the *only* source for a claim, mark it as a guess.

### Phase 2 — Drill (depth on the spine)

> Confirm/refute the hypothesis by following entrypoints, not by reading everything.

5. Walk every declared `[project.scripts]` entrypoint and follow imports one hop deep.
6. Read each Python package's "spine" (config, LLM/client factory, base classes, registries, one concrete implementation per kind, db engine + models, tools).
7. Reconcile multiple packages explicitly: which is canonical? what's overlap/drift?
8. Skim large generated artifacts (e.g. n8n JSON exports) at headers only — node names, trigger types — don't ingest.
9. Read tests to understand the test surface (not to run them yet).
10. Run read-only commands to ground-truth claims:
    - `git ls-files` counts per top-level dir
    - `git log -1 --stat` for recency signal
    - `uv tree` (per package) or parse lockfiles
    - `docker compose config` to verify the compose graph resolves
    - `pytest --collect-only -q` to list tests without executing
11. **Cross-check declared deps vs actual imports** — flag declared-but-unused or used-but-undeclared.

### Phase 3 — Synthesize (write for the reviewer)

> **Maturity check first.** Before writing, decide where the repo sits on the
> scaffold ↔ mature spectrum. If it's mostly empty / scaffolded / aspirational,
> the doc must lead with that fact and include an explicit **"Where this is
> heading (informed guess)"** section, citing the signals (README, tickets,
> deps, naming, commit history) that justify the guess. Never narrate empty
> code as if it works.

12. Reconcile multiple packages into one clear story. For owner-sanity-check audiences this is usually the single most important clarification.
13. Produce the multi-file output set:
    - `00-overview.md` — TL;DR, mental model, "pre-drill vs verified" sidebar, status vs any existing checklist, owner callouts.
    - `01-stack-and-services.md` — services, ports, volumes, env, external integrations.
    - `02-python-<pkg-a>.md` — per-package deep dive.
    - `03-python-<pkg-b>.md` — per-package deep dive.
    - `04-dev-and-test.md` — bring-up, run-a-workflow, tests, required env, gotchas.
    - `05-open-questions.md` — drift, dead-code suspicions, unverified claims.
14. Embed required Mermaid diagrams:
    - **Architecture** — containers + packages + external services.
    - **Directory → responsibility** — tree-style mermaid (or table fallback).
    - **Data flow** — trigger → routing → output.

### Phase 4 — Self-review

15. Re-read each file as the owner; replace vague/inferred claims with file-referenced facts or move them to `05-open-questions.md`.
16. Verify every path, symbol, and command actually exists / runs (`ls`, `--help`).
17. Produce the **agent-design debrief** — heuristics the real agent should encode. This is the primary takeaway from the exercise.
18. **Emit `notes/repo-map/.evidence.json`.** Every output run records the git SHA, timestamp, and the list of files cited per output doc. This is the contract downstream tooling uses to detect staleness without an LLM:

    ```json
    {
      "git_sha": "<HEAD sha at run time>",
      "generated_at": "<ISO-8601 UTC>",
      "files_cited": {
        "00-overview.md": ["docker-compose.yml", "src/zefflow/scripts/db_utils.py", "..."],
        "03-python-agent-workflows.md": ["..."]
      }
    }
    ```

    Each output doc also gets a footer:

    ```markdown
    ---
    *Last verified against commit `<short_sha>` on `<YYYY-MM-DD>`. Run `make repo-map` after changes to manifests, entrypoints, or top-level structure.*
    ```

---

## Method principles (the real artifact)

- **Manifest-first, source-second.** ~70% of most repos is in `pyproject.toml` + `docker-compose.yml` + `README`. Only drill where claims are unverifiable from manifests.
- **Follow entrypoints, not directories.** Reading every file is a trap; reading from `[project.scripts]` outward gives the live spine.
- **Always reconcile multiple packages.** When a repo has more than one Python package, explicitly state which is canonical or how they relate.
- **Write the hypothesis before the drill.** Pre vs post catches misleading surface signals.
- **Cross-check deps ↔ imports.** Cheap; routinely surfaces drift / dead code.
- **Reviewer audience ⇒ flag, don't paper over.** Better to surface a suspicious entry (e.g. a typo'd package path) than to omit it.
- **Diagrams replace prose only where structure > narrative.** Architecture and data flow yes; per-function detail no.
- **Empty / early-stage repos: say so, then guess the trajectory.** If most directories are empty, scaffolds, or `TODO`s, do not pretend the repo does more than it does. Explicitly flag it as early-stage / scaffold and make an **informed guess** at where the devs are heading, grounded in the strongest signals available (README aspirations, ticket/issue files, commit messages, dependency choices, naming, existing scaffolds). Mark every such guess as a guess and cite the signal that prompted it.
- **Distrust pre-supplied trees.** Always re-derive structure from `tree --gitignore` + `git ls-files` + `git status`. The IDE-supplied workspace tree can be stale.
- **Never read `.env`.** `.env.example` only, marked as ~80% accurate.
- **Trajectory artefacts are signals, not facts.** Down-weight `tickets.json`, `TODO.md`, `ROADMAP.md`. Commit history and working code beat them every time.

---

## Scope

**In:** documentation pass into `notes/repo-map/`, with diagrams + method debrief.

**Out (deliberately):** building the agent, modifying source, running tests that mutate state, **reading `.env`**, running `compose up`.

---

## Verification

1. Every file path / symbol / command in the output exists or runs.
2. `00-overview.md` explicitly answers each `GENERAL.md` requirement (structure, module links, dirs→responsibility, key deps, dev env, tests).
3. Mermaid blocks parse cleanly.
4. Owner-readability: TL;DR digestible in under a minute, no scrolling.
5. Debrief lists ≥3 concrete heuristics the future agent should encode.

---

## Decisions captured

| Question | Decision |
|---|---|
| Output shape | Multi-file under `notes/repo-map/` + `.evidence.json` |
| Audience (default) | Developer being onboarded |
| Depth | Medium — manifests + entrypoints + dep cross-check |
| Tooling | Full shell allowed, read-only (no `.env`, no writes, no `compose up`) |
| Diagrams | Architecture (required), directory→responsibility, data flow |
| Freshness | Pre-commit hook detects, human triggers refresh; `.evidence.json` is the contract |

---

## Further considerations (decide before execution)

1. **Pre-drill hypothesis — visible or hidden?**
   - A) Inline as a "first impression vs verified" sidebar in `00-overview.md`.
   - B) Keep only in debrief.
   - **Recommend A** — most useful artifact for designing the real agent.
2. **Large generated artifacts (e.g. n8n JSON) — how deep?**
   - A) List trigger + node-type counts only.
   - B) Enumerate each workflow's purpose.
   - **Recommend A** at medium depth; promote to B only if the existing notes are thin.
3. **Order of writing the overview.**
   - A) Write `00-overview.md` last (safer, less rework).
   - B) Write it first and revise.
   - **Recommend A.**
