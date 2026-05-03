"""Tier-2 incremental refresh of notes/repo-map/.

Single Agno agent, structured output. Code applies the patches; the LLM
never writes files directly.
"""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from agent_workflows.agents.base import BaseAgent
from agent_workflows.logging import get_logger
from agent_workflows.tools.repo_tools import (
    ALLOWED_DOCS,
    EVIDENCE_PATH_REL,
    REPO_MAP_DIR_REL,
    evidence_load,
    git_diff_names,
    git_head_sha,
    git_log,
    git_status,
    grep,
    mermaid_lint,
    read_file,
    repo_map_doc_read,
    repo_root,
)
from agent_workflows.workflows.base import BaseWorkflow

log = get_logger(__name__)


def _extract_first_json_object(text: str) -> str:
    """Return the first balanced top-level JSON object found in `text`.

    Tolerates: leading prose, ```json fences, trailing prose, escaped strings.
    Raises ValueError if no balanced object is found.
    """
    s = text.strip()
    # Strip a leading ```...``` fence if present (any language tag).
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]

    start = s.find("{")
    if start == -1:
        raise ValueError("no '{' found in agent output")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    raise ValueError("unbalanced JSON object in agent output")


def _coerce_plan(raw: Any) -> "RefreshPlan":
    """Normalise agno's varying structured-output return shapes."""
    if isinstance(raw, RefreshPlan):
        return raw
    if isinstance(raw, dict):
        return RefreshPlan.model_validate(raw)
    if isinstance(raw, str):
        try:
            return RefreshPlan.model_validate_json(_extract_first_json_object(raw))
        except Exception as exc:
            # Persist the raw output for debugging before re-raising.
            try:
                (repo_root() / "notes" / "repo-map" / ".last_agent_output.txt").write_text(raw)
            except Exception:  # pragma: no cover  -- best effort
                pass
            raise ValueError(f"failed to parse agent output as JSON: {exc}") from exc
    raise TypeError(f"unexpected agent response type: {type(raw).__name__}")


# ── Structured output ─────────────────────────────────────────────────────

class DocPatch(BaseModel):
    """Full-rewrite patch for one repo-map doc."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    filename: str = Field(
        validation_alias=AliasChoices("filename", "file", "path", "name"),
        description="One of the ALLOWED_DOCS names, e.g. '03-python-agent-workflows.md'",
    )
    new_content: str = Field(
        validation_alias=AliasChoices("new_content", "content", "body", "markdown"),
        description="Complete new file contents, including the 'Last verified' footer.",
    )
    rationale: str = Field(
        default="",
        validation_alias=AliasChoices("rationale", "reason", "why"),
        description="One-sentence reason this doc needs updating.",
    )


class RefreshPlan(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    docs_unchanged: list[str] = Field(default_factory=list)
    patches: list[DocPatch] = Field(
        default_factory=list,
        validation_alias=AliasChoices("patches", "plan", "docs", "updates"),
    )
    new_files_cited: dict[str, list[str]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("new_files_cited", "files_cited", "evidence"),
        description="filename -> list of cited paths AFTER the refresh.",
    )
    changes_md_line: str = Field(
        default="",
        validation_alias=AliasChoices("changes_md_line", "summary", "note"),
        description="One short line to append to notes/changes.md",
    )


# JSON skeleton injected into the prompt so the model can't invent fields.
_PLAN_SCHEMA_HINT = """\
Return ONLY a single JSON object matching exactly this shape — no prose, no
markdown fences, no trailing text:

{
  "patches": [
    {
      "filename": "<one of the ALLOWED_DOCS names>",
      "new_content": "<complete new file contents, including the Last verified footer>",
      "rationale": "<one short sentence>"
    }
  ],
  "docs_unchanged": ["<filename>", ...],
  "new_files_cited": {"<filename>": ["<path>", ...]},
  "changes_md_line": "<one short line for notes/changes.md>"
}
"""


# ── Refresh agent ─────────────────────────────────────────────────────────

class RepoMapRefreshAgent(BaseAgent):
    role: ClassVar[str] = "repo_map_refresher"
    instructions: ClassVar[list[str]] = [
        "You maintain notes/repo-map/ for an early-stage repo.",
        "You receive: the staleness report, the diff against the last-verified SHA,",
        "the current contents of every potentially-affected doc, and the .evidence.json.",
        "RULES:",
        "  1. Edit ONLY docs that need changes given the diff.",
        "  2. Preserve each doc's existing structure, tone, and headings.",
        "  3. Replace the 'Last verified' footer with the new short SHA + UTC date.",
        "  4. Cite a path or command for every non-trivial change.",
        "  5. Never narrate code that was deleted as if it still exists.",
        "  6. If something can't be verified from the provided contents, list it as an open question",
        "     in 05-open-questions.md rather than guessing.",
        "  7. Return a RefreshPlan. Patches are full-rewrites of the doc.",
        "  8. For mermaid: quoted labels, no inline `:::class` on shaped nodes, no edges into subgraphs.",
        "  9. Output ONLY a single raw JSON object. NO markdown fences. NO commentary before or after.",
        " 10. `filename` must be a BASENAME only (e.g. '00-overview.md'). Never include 'notes/repo-map/'.",
        " 11. Keys in `new_files_cited` must also be basenames matching `filename`s above.",
    ]


# ── Workflow ──────────────────────────────────────────────────────────────

class RepoMapRefreshWorkflow(BaseWorkflow):
    name: ClassVar[str] = "repo_map_refresh"

    def _execute(self) -> dict[str, Any]:
        root = repo_root()
        evidence = evidence_load()
        if not evidence:
            raise RuntimeError(
                "no notes/repo-map/.evidence.json — run the rebuild workflow first."
            )

        last_sha = evidence["git_sha"]
        head_sha = git_head_sha()
        head_short = git_head_sha(short=True)
        today = datetime.now(UTC).date().isoformat()

        # Filter out changes to the output dir itself.
        changed = [p for p in git_diff_names(last_sha) if not p.startswith("notes/repo-map/")]
        if not changed:
            log.info("repo_map_refresh.clean", last_sha=last_sha, head=head_sha)
            return {"status": "clean", "last_sha": last_sha, "head_sha": head_sha}

        # Which docs cited any changed path (or a directory containing one)?
        cited: dict[str, list[str]] = evidence.get("files_cited", {})
        affected_docs: dict[str, list[str]] = {}
        for doc, paths in cited.items():
            for p in paths:
                p = p.rstrip("/")
                hits = [c for c in changed if c == p or c.startswith(p + "/")]
                if hits:
                    affected_docs.setdefault(doc, []).extend(hits)

        if not affected_docs:
            return {"status": "clean", "last_sha": last_sha, "head_sha": head_sha}

        # Assemble the prompt context.
        ctx_parts: list[str] = []
        ctx_parts.append(f"# Last verified SHA: {last_sha}\n# Current HEAD: {head_sha} ({head_short})\n# Today (UTC): {today}\n")
        ctx_parts.append("## git status --short\n```\n" + (git_status() or "(clean)") + "\n```")
        ctx_parts.append("## git log -5 --stat\n```\n" + git_log(n=5, stat=True) + "\n```")
        ctx_parts.append(
            "## Affected docs\n" +
            "\n".join(f"- {d}: changed paths {sorted(set(ps))}" for d, ps in affected_docs.items())
        )
        # Current doc contents.
        for doc in affected_docs:
            ctx_parts.append(f"## CURRENT {doc}\n```markdown\n{repo_map_doc_read(doc)}\n```")
        # Diff bodies for changed cited files (capped).
        ctx_parts.append("## Changed files (post-change contents, truncated)")
        for p in sorted({p for ps in affected_docs.values() for p in ps})[:25]:
            try:
                ctx_parts.append(f"### {p}\n```\n{read_file(p, max_bytes=8000)}\n```")
            except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                ctx_parts.append(f"### {p}\n[unreadable: {type(e).__name__}: {e}]")

        ctx_parts.append(
            "Produce a RefreshPlan that updates ONLY the affected docs and "
            f"sets the new 'Last verified' footer to commit `{head_short}` on `{today}`."
        )
        ctx_parts.append(_PLAN_SCHEMA_HINT)
        prompt = "\n\n".join(ctx_parts)

        agent = RepoMapRefreshAgent()
        raw = agent.run_structured(prompt, response_model=RefreshPlan)
        plan = _coerce_plan(raw)

        # Apply (with allowlist + lint guardrails).
        applied: list[str] = []
        repo_map_dir = (root / REPO_MAP_DIR_REL).resolve()
        for patch in plan.patches:
            # Normalise: agents sometimes return 'notes/repo-map/foo.md' or
            # './foo.md' or 'foo.md'. Strip to a basename and re-anchor.
            requested = patch.filename.strip().lstrip("./")
            basename = Path(requested).name
            if basename not in ALLOWED_DOCS:
                raise PermissionError(
                    f"agent tried to write disallowed file: {patch.filename!r} "
                    f"(basename {basename!r} not in allowlist)"
                )
            target = (repo_map_dir / basename).resolve()
            if repo_map_dir not in target.parents:
                raise PermissionError(
                    f"resolved path escapes repo-map dir: {target}"
                )
            issues = mermaid_lint(patch.new_content)
            if issues:
                raise ValueError(f"{basename}: mermaid lint failed: {issues}")
            target.write_text(patch.new_content)
            applied.append(basename)

        # Update .evidence.json — new SHA, timestamp, files_cited (only for touched docs).
        # Normalise the agent's keys to basenames; ignore unknown ones.
        normalised_cited: dict[str, list[str]] = {}
        for key, paths in (plan.new_files_cited or {}).items():
            base = Path(key.strip().lstrip("./")).name
            if base in ALLOWED_DOCS:
                normalised_cited[base] = list(paths)
        new_evidence = dict(evidence)
        new_evidence["git_sha"] = head_sha
        new_evidence["git_short_sha"] = head_short
        new_evidence["generated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_evidence.setdefault("files_cited", {}).update(normalised_cited)
        (root / EVIDENCE_PATH_REL).write_text(json.dumps(new_evidence, indent=2) + "\n")

        # Append to changes.md.
        changes_md = root / "notes" / "changes.md"
        line = (
            f"\n## {today} — repo-map refresh\n"
            f"**Agent:** repo_map_refresh\n"
            f"**Action:** {plan.changes_md_line}\n"
            f"**Updated docs:** {', '.join(applied) or '(none)'}\n"
            f"**Verified against:** `{head_short}`\n"
        )
        with changes_md.open("a") as f:
            f.write(line)

        # Post-write Tier-1 verification (cheap, no LLM).
        check = subprocess.run(
            ["bash", str(root / "scripts" / "check-repo-map.sh")],
            capture_output=True, text=True,
        )
        clean = "STALE" not in (check.stderr + check.stdout)

        return {
            "status": "refreshed",
            "last_sha": last_sha,
            "head_sha": head_sha,
            "applied": applied,
            "unchanged": plan.docs_unchanged,
            "post_check_clean": clean,
        }
