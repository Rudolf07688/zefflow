# Debrief: heuristics for the future repo-explainer agent

> Lessons from running the methodology in [notes/repo_overwiew.md](../repo_overwiew.md)
> manually on this repo. These should become rules / prompts inside the real agent.

---

## What worked

1.  **Manifest-first sweep produced ~70% of the doc.**
    `pyproject.toml` × 2, `docker-compose.yml`, `README` × 2, the `notes/` directory, and `tickets.json` between them implied almost every fact in the final overview. Source reading was needed only to confirm the spine and catch drift.

2.  **Walking `[project.scripts]` outward was the right entrypoint.**
    `compose-up`, `db`, `run-workflow`, `seed-db` form a complete map of "what this code is meant to be invoked as," and from each, **one hop** into imports gave the spine. Reading every file would have wasted budget on `__init__.py`s and the empty `agents/` dir.

3.  **Pre-drill hypothesis caught the over-confidence trap.**
    The manifest-only read made the project look noticeably more mature than it is. Capturing that and contrasting it explicitly is the most useful artifact in `00-overview.md`.

4.  **`git status` and `git log -1` were disproportionately valuable.**
    The single most important discovery — that `agent-workflows` had just been moved out of `src/` and the repo state was mid-refactor — came from `git status`, not from reading source. **The agent should run `git status` and `git log --stat -5` early, every time.** The workspace tree the IDE handed over was stale.

5.  **Cheap dep↔import cross-check surfaced drift.**
    One `grep -rE "from agno|google\.genai|…"` pass produced the import histogram that exposed unused root-level deps and the absence of `agno` from `src/zefflow/`.

6.  **Counting node types in big JSON beat reading it.**
    `Counter(n['type'] for n in nodes)` summarised the n8n export in one line; reading the JSON would have burned tokens for no extra signal.

## What I'd tell the next agent (rules)

-   **R1. Always run `git status` + `git log -1 --stat` first.** Treat any IDE-supplied tree or summary as potentially stale. This is now directly implemented by the `repo_tools` in the `repo-map-refresh` workflow. ([agent-workflows/src/agent_workflows/tools/repo_tools.py](../../agent-workflows/src/agent_workflows/tools/repo_tools.py))
-   **R2. Maturity gate before synthesis.** Decide scaffold / partial / mature. If scaffold or partial, the doc must include an explicit *"Where this is heading (informed guess)"* section with cited signals (README, tickets, deps, naming, commits). Never narrate empty code as if it works.
-   **R3. Manifest-first; entrypoints next; source last.** Only read source where a claim is unverifiable from manifests + READMEs.
-   **R4. Always reconcile multiple Python packages.** Note canonical-vs-secondary, schema/Base divergence, and whether they import each other. This is the question owners actually want answered.
-   **R5. Always do a deps↔imports cross-check.** Cheap, surfaces drift in seconds. The `repo_tools` now support this type of introspection. ([agent-workflows/src/agent_workflows/tools/repo_tools.py](../../agent-workflows/src/agent_workflows/tools/repo_tools.py))
-   **R6. Sample, don't ingest, large generated artefacts** (n8n exports, lockfiles, OpenAPI dumps): trigger types, node-type counts, top-level keys only.
-   **R7. Capture and surface the pre-drill hypothesis.** Not as flair — as a calibration artifact.
-   **R8. Flag, don't paper over.** Empty `Dockerfile`, typo'd packages, naive guards (`run_sql` keyword filter), default `change_me_*` creds — call them out by name.
-   **R9. Cite a file path or command for every non-trivial claim.** "Tests are smoke-only" → link the test file. "Env validates fail-fast" → link the validator.
-   **R10. Diagrams only where structure beats prose** — system architecture and data flow yes; per-module call graphs no.

## What I'd add to the methodology

-   A formal **"signals dictionary"** for guessing trajectory on early-stage repos. Tier signals: `tickets.json/issues > unchecked checklists in notes/ > declared-but-unused deps > naming > commit messages > READMEs`. Tickets/issues beat README aspirations because they're concretely scheduled.
-   A **`grep`-based dep↔import script** the agent runs once per detected `pyproject.toml`, producing a histogram and a "declared, never imported" list.
-   **Workspace-tree distrust:** the agent's first action should be a `git ls-files | head -200` + `git status --short` to ground-truth what's tracked vs. uncommitted vs. dropped from the IDE's view.

## What didn't pay off

-   Reading `__init__.py` files generally added nothing (most are empty or pure re-exports).
-   Reading `notes/architecture.md` deeply: it was useful as a *hypothesis* but its checklist + dates were stale. **Treat human-authored architecture notes as `t-1` snapshots, not ground truth.**
-   Looking at `infra/Dockerfile` (empty) — but discovering it's empty *was* a signal worth reporting. So: cheap to look, worth doing.

## Suggested agent shape (sketch)

```text
phase 1  Orient
  ├── git status + log -1
  ├── ls-files top-level histogram
  ├── read every manifest + README + notes/*.md
  └── emit hypothesis  ─┐
                        │
phase 2  Drill          │
  ├── walk [project.scripts] entrypoints, 1 hop in
  ├── read each pkg spine (config, LLM factory, base, registry, one concrete impl)
  ├── reconcile multiple packages
  ├── (new) invoke agent-workflows.repo_map_refresh.RepoMapRefreshWorkflow to collect facts
  ├── skim large generated artifacts
  ├── read tests
  ├── run read-only commands
  └── cross-check declared deps vs actual imports ─┤
                                                  │
phase 3  Synthesize                               │
  ├── reconcile multiple packages (again, with facts)
  ├── (if scaffold) add "Where this is heading" with cited signals
  ├── architecture + dir→responsibility + data-flow diagrams
  └── multi-file output (repo-map docs)         │
                                                │
phase 4  Self-review  ◄─────────────────────────┘
  ├── verify every cited path/symbol/command
  ├── produce agent-design debrief
  └── emit notes/repo-map/.evidence.json
```


---
*Last verified against commit `6319dfb` on 2026-05-03. Run `make repo-map-check` to detect drift; `make repo-map-rebuild` for a full refresh.*