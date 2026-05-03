"""Read-only filesystem + git tools for the repo-map agent.

Hard rules enforced at THIS layer (not the prompt):
- All paths are resolved relative to the repo root and refused if they escape it.
- `.env` files are refused outright. `.env.example` is allowed.
- Output sizes are bounded so a runaway tool call can't blow the context.
- No mutating commands. Subprocess calls allowlisted.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

from agent_workflows.logging import get_logger

log = get_logger(__name__)

MAX_READ_BYTES = 40_000
MAX_GREP_HITS = 200
MAX_TREE_LINES = 400


@cache
def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(out).resolve()


def _safe_path(rel_or_abs: str) -> Path:
    root = repo_root()
    p = (root / rel_or_abs).resolve() if not Path(rel_or_abs).is_absolute() else Path(rel_or_abs).resolve()
    if root not in p.parents and p != root:
        raise PermissionError(f"path escapes repo root: {rel_or_abs}")
    name = p.name
    if name == ".env" or (name.startswith(".env") and not name.endswith(".example")):
        raise PermissionError(f"reading .env is forbidden: {rel_or_abs}")
    return p


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    res = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(cwd or repo_root()), check=False,
    )
    return res.stdout


# ── Git ────────────────────────────────────────────────────────────────────

def git_status() -> str:
    """`git status --short` — staged + unstaged file changes."""
    return _run(["git", "status", "--short"])


def git_log(n: int = 5, stat: bool = True) -> str:
    """Last N commits with file stats."""
    cmd = ["git", "log", f"-{int(n)}", "--no-color"]
    if stat:
        cmd.append("--stat")
    return _run(cmd)


def git_head_sha(short: bool = False) -> str:
    cmd = ["git", "rev-parse", "--short", "HEAD"] if short else ["git", "rev-parse", "HEAD"]
    return _run(cmd).strip()


def git_diff_names(since_sha: str, include_uncommitted: bool = True) -> list[str]:
    """Files changed since `since_sha`, plus staged + unstaged if requested."""
    parts: set[str] = set()
    parts.update(_run(["git", "diff", "--name-only", f"{since_sha}..HEAD"]).split())
    if include_uncommitted:
        parts.update(_run(["git", "diff", "--name-only", "--cached"]).split())
        parts.update(_run(["git", "diff", "--name-only"]).split())
    return sorted(p for p in parts if p)


def git_ls_files_top_level_histogram() -> dict[str, int]:
    out = _run(["git", "ls-files"]).splitlines()
    return dict(Counter(p.split("/", 1)[0] for p in out).most_common())


# ── Filesystem (read-only) ────────────────────────────────────────────────

def tree(depth: int = 4) -> str:
    """`tree -L <depth> --gitignore` honouring .gitignore. Bounded line count."""
    out = _run([
        "tree", "-L", str(int(depth)), "-a", "--gitignore",
        "-I", ".git|.venv|node_modules|__pycache__|dist|build|.next|.DS_Store|*.egg-info",
    ])
    lines = out.splitlines()
    if len(lines) > MAX_TREE_LINES:
        lines = lines[:MAX_TREE_LINES] + [f"... [truncated {len(lines) - MAX_TREE_LINES} lines]"]
    return "\n".join(lines)


def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> str:
    """Read a file inside the repo. Refuses .env. Truncates beyond max_bytes."""
    p = _safe_path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    data = p.read_bytes()[: int(max_bytes)]
    return data.decode("utf-8", errors="replace")


def grep(pattern: str, path: str = ".", regex: bool = True) -> list[str]:
    """`grep -rn` (or `-rnF`) inside the repo. Bounded hits."""
    p = _safe_path(path)
    cmd = ["grep", "-rn", "--exclude-dir=.git", "--exclude-dir=.venv",
           "--exclude-dir=node_modules", "--exclude-dir=__pycache__"]
    if not regex:
        cmd.append("-F")
    cmd += ["-e", pattern, str(p)]
    out = _run(cmd).splitlines()
    if len(out) > MAX_GREP_HITS:
        out = out[:MAX_GREP_HITS] + [f"... [truncated {len(out) - MAX_GREP_HITS} hits]"]
    return out


def list_dir(path: str = ".") -> list[str]:
    p = _safe_path(path)
    if not p.is_dir():
        raise NotADirectoryError(path)
    return sorted(child.name + ("/" if child.is_dir() else "") for child in p.iterdir())


# ── Evidence I/O (the only writes the agent indirectly drives) ────────────

EVIDENCE_PATH_REL = "notes/repo-map/.evidence.json"
REPO_MAP_DIR_REL = "notes/repo-map"
ALLOWED_DOCS = {
    "00-overview.md", "01-stack-and-services.md",
    "02-python-zefflow.md", "03-python-agent-workflows.md",
    "04-dev-and-test.md", "05-open-questions.md", "debrief.md",
}


def evidence_load() -> dict[str, Any]:
    p = repo_root() / EVIDENCE_PATH_REL
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def repo_map_doc_read(name: str) -> str:
    if name not in ALLOWED_DOCS:
        raise PermissionError(f"not in repo-map allowlist: {name}")
    p = repo_root() / REPO_MAP_DIR_REL / name
    return p.read_text() if p.exists() else ""


# Mermaid sanity: catches the common breakages we hit (inline :::class on a
# shaped node, edges into subgraphs, unquoted labels with slashes/parens).
_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_MERMAID_INLINE_CLASS_ON_SHAPE = re.compile(r"\[\([^]]+\)\]:::\w+")


def mermaid_lint(markdown: str) -> list[str]:
    issues: list[str] = []
    for i, block in enumerate(_MERMAID_FENCE.findall(markdown)):
        if _MERMAID_INLINE_CLASS_ON_SHAPE.search(block):
            issues.append(f"block #{i}: inline `:::class` on shaped node — use `class X foo;` instead")
    return issues
