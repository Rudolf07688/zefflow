"""Tier-3: full initialisation of notes/repo-map/.

Runs the methodology in notes/repo_overwiew.md from Phase 0 to Phase 4 in
one shot: orient → drill → synthesize → emit. The LLM proposes file
contents; this code applies them under the same allowlist + lint guardrails
as the refresh workflow.
"""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from agent_workflows.agents.base import BaseAgent
from agent_workflows.logging import get_logger
from agent_workflows.tools.repo_tools import (
    ALLOWED_DOCS,
    EVIDENCE_PATH_REL,
    REPO_MAP_DIR_REL,
    git_head_sha,
    git_log,
    git_ls_files_top_level_histogram,
    git_status,
    mermaid_lint,
    read_file,
    repo_root,
    tree,
)
from agent_workflows.workflows.base import BaseWorkflow
from agent_workflows.workflows.repo_map_refresh import (
    RefreshPlan,
    _PLAN_SCHEMA_HINT,
    _coerce_plan,
)

log = get_logger(__name__)

# Manifest files we always read fully (best-effort — missing files are skipped).
_MANIFEST_CANDIDATES = (
    "README.md",
    "GENERAL.md",
    "AGENTS.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "docker-compose.yml",
    "compose.yml",
    "Dockerfile",
    ".env.example",
)


class RepoMapInitAgent(BaseAgent):
    role: ClassVar[str] = "repo_map_initialiser"
    instructions: ClassVar[list[str]] = [
        "You are producing a complete repo overview from scratch.",
        "Audience: a developer being onboarded to the repo.",
        "Follow the methodology in notes/repo_overwiew.md (Phase 0..4).",
        "Output exactly the seven docs listed below as full rewrites; if a doc",
        "doesn't apply (e.g. only one Python package, so no '03-python-...md'),",
        "still emit it but say 'Not applicable for this repo' in the body.",
        "RULES:",
        "  1. Maturity check FIRST. If most code is empty/scaffold, lead with that and add a",
        "     'Where this is heading (informed guess)' section, citing signals.",
        "  2. Distrust any pre-supplied tree; rely on the `tree` + `git status` blocks below.",
        "  3. Never read .env. .env.example only, weighted ~80%.",
        "  4. Trajectory artefacts (tickets.json, TODO.md) are signals, not facts.",
        "  5. Cite a path or command for every non-trivial claim.",
        "  6. Mermaid: quoted labels, no inline `:::class` on shaped nodes, no edges into subgraphs.",
        "  7. Output ONLY a single raw JSON object. NO markdown fences. NO commentary.",
        "  8. `filename` must be a basename only (one of the 7 allowlisted names).",
        "  9. Each doc ends with a 'Last verified' footer that the runner will replace.",
    ]


class RepoMapInitWorkflow(BaseWorkflow):
    name: ClassVar[str] = "repo_map_init"

    def _execute(self) -> dict[str, Any]:  # noqa: C901  -- single-shot orchestrator
        root = repo_root()
        head_sha = git_head_sha()
        head_short = git_head_sha(short=True)
        today = datetime.now(UTC).date().isoformat()

        # ── Phase 0: ground truth ───────────────────────────────────────
        ctx: list[str] = []
        ctx.append(
            f"# Init run\n# HEAD: {head_sha} ({head_short})\n# Today (UTC): {today}\n"
        )
        ctx.append("## tree -L 4 --gitignore\n```\n" + tree(depth=4) + "\n```")
        ctx.append("## git status --short\n```\n" + (git_status() or "(clean)") + "\n```")
        ctx.append("## git log -10 --stat\n```\n" + git_log(n=10, stat=True) + "\n```")
        ctx.append(
            "## git ls-files top-level histogram\n```\n"
            + "\n".join(
                f"{n:>5}  {p}" for p, n in git_ls_files_top_level_histogram().items()
            )
            + "\n```"
        )

        # ── Phase 1+2: manifests + entrypoints (best-effort) ────────────
        ctx.append("## Manifests")
        for rel in _MANIFEST_CANDIDATES:
            try:
                content = read_file(rel, max_bytes=12_000)
                ctx.append(f"### {rel}\n```\n{content}\n```")
            except (FileNotFoundError, IsADirectoryError, PermissionError):
                continue

        # Also pull each pyproject.toml found anywhere in the tree.
        for p in sorted(root.glob("**/pyproject.toml")):
            if any(part in {".venv", "node_modules", ".git", "__pycache__"} for part in p.parts):
                continue
            rel = str(p.relative_to(root))
            if rel in _MANIFEST_CANDIDATES:
                continue
            try:
                ctx.append(f"### {rel}\n```\n{read_file(rel, max_bytes=12_000)}\n```")
            except Exception:  # pragma: no cover  -- best effort
                continue

        # Existing notes (often the best concentrated context).
        for note in ("notes/architecture.md", "notes/n8n-workflows.md", "notes/changes.md", "notes/AGENTS.md"):
            try:
                ctx.append(f"### {note}\n```\n{read_file(note, max_bytes=8000)}\n```")
            except (FileNotFoundError, IsADirectoryError, PermissionError):
                continue

        # ── Synthesis instructions ──────────────────────────────────────
        ctx.append(
            "Produce a RefreshPlan whose `patches` cover ALL SEVEN docs:\n"
            + "\n".join(f"- {d}" for d in sorted(ALLOWED_DOCS))
            + f"\nEach `new_content` MUST end with this exact footer line:\n"
            + f"`*Last verified against commit \\`{head_short}\\` on {today}.*`\n"
            + "Populate `new_files_cited` with the basename->paths map for each doc.\n"
            + "`docs_unchanged` should be empty (this is an init).\n"
            + "`changes_md_line` should describe this as a Tier-3 init."
        )
        ctx.append(_PLAN_SCHEMA_HINT)
        prompt = "\n\n".join(ctx)

        # Persist the prompt for debugging — never contains .env.
        repo_map_dir = root / REPO_MAP_DIR_REL
        repo_map_dir.mkdir(parents=True, exist_ok=True)
        (repo_map_dir / ".last_init_prompt.txt").write_text(prompt)

        # ── LLM call ────────────────────────────────────────────────────
        agent = RepoMapInitAgent()
        raw = agent.run_structured(prompt, response_model=RefreshPlan)
        plan = _coerce_plan(raw)

        # ── Apply (allowlist + lint, normalising basenames) ─────────────
        applied: list[str] = []
        repo_map_resolved = repo_map_dir.resolve()
        for patch in plan.patches:
            requested = patch.filename.strip().lstrip("./")
            basename = Path(requested).name
            if basename not in ALLOWED_DOCS:
                raise PermissionError(
                    f"agent tried to write disallowed file: {patch.filename!r}"
                )
            target = (repo_map_resolved / basename).resolve()
            if repo_map_resolved not in target.parents:
                raise PermissionError(f"resolved path escapes repo-map dir: {target}")
            issues = mermaid_lint(patch.new_content)
            if issues:
                raise ValueError(f"{basename}: mermaid lint failed: {issues}")
            target.write_text(patch.new_content)
            applied.append(basename)

        if not applied:
            raise RuntimeError("init workflow produced no patches")

        # ── Build .evidence.json from the plan's files_cited ────────────
        normalised_cited: dict[str, list[str]] = {}
        for key, paths in (plan.new_files_cited or {}).items():
            base = Path(key.strip().lstrip("./")).name
            if base in ALLOWED_DOCS:
                normalised_cited[base] = list(paths)

        evidence = {
            "schema_version": 1,
            "git_sha": head_sha,
            "git_short_sha": head_short,
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": f"{self.name} workflow",
            "files_cited": normalised_cited,
            "manifest_fingerprint_inputs": list(_MANIFEST_CANDIDATES),
        }
        (root / EVIDENCE_PATH_REL).write_text(json.dumps(evidence, indent=2) + "\n")

        # ── Append to changes.md ────────────────────────────────────────
        changes_md = root / "notes" / "changes.md"
        if changes_md.parent.exists():
            line = (
                f"\n## {today} — repo-map init\n"
                f"**Agent:** {self.name}\n"
                f"**Action:** {plan.changes_md_line or 'Tier-3 full initialisation of notes/repo-map/'}\n"
                f"**Wrote docs:** {', '.join(applied)}\n"
                f"**Verified against:** `{head_short}`\n"
            )
            with changes_md.open("a") as f:
                f.write(line)

        # ── Post-write Tier-1 verification ──────────────────────────────
        check_script = root / "scripts" / "check-repo-map.sh"
        clean = True
        if check_script.exists():
            res = subprocess.run(
                ["bash", str(check_script)], capture_output=True, text=True
            )
            clean = "STALE" not in (res.stderr + res.stdout)

        return {
            "status": "initialised",
            "head_sha": head_sha,
            "applied": applied,
            "missing_docs": sorted(ALLOWED_DOCS - set(applied)),
            "post_check_clean": clean,
        }
