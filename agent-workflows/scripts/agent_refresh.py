"""CLI: `agent-refresh` — keep notes/repo-map/ current.

Subcommands:
  check    Tier-1 staleness detector (no LLM).
  status   Print evidence summary (sha, age, cited paths).
  refresh  Tier-2 incremental refresh via the repo_map_refresh workflow.

Bare `agent-refresh` = check, then offer to run refresh if stale.
"""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False, help="Keep notes/repo-map/ current.")
console = Console()


def _repo_root() -> Path:
    return Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    ).resolve()


def _run_check() -> tuple[int, str]:
    root = _repo_root()
    res = subprocess.run(
        ["bash", str(root / "scripts" / "check-repo-map.sh")],
        capture_output=True, text=True,
    )
    return res.returncode, res.stderr + res.stdout


@app.command()
def check() -> None:
    """Run the Tier-1 staleness detector. No LLM."""
    code, output = _run_check()
    if "STALE" in output:
        console.print(Panel(output.strip(), title="repo-map: STALE", border_style="yellow"))
        raise typer.Exit(code=2)
    console.print(Panel("repo-map is fresh.", border_style="green"))


@app.command()
def status() -> None:
    """Print a summary of the current evidence file."""
    root = _repo_root()
    ev_path = root / "notes" / "repo-map" / ".evidence.json"
    if not ev_path.exists():
        console.print("[red]no .evidence.json — repo-map has never been generated.[/red]")
        raise typer.Exit(code=1)
    ev = json.loads(ev_path.read_text())
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    age = "?"
    try:
        gen = datetime.fromisoformat(ev["generated_at"].replace("Z", "+00:00"))
        age = str(datetime.now(UTC) - gen).split(".")[0]
    except Exception:  # pragma: no cover  -- best-effort display only
        pass

    t = Table(show_header=False)
    t.add_row("verified sha", ev.get("git_short_sha", ev.get("git_sha", "?")))
    t.add_row("HEAD sha", head[:7])
    t.add_row("generated_at", ev.get("generated_at", "?"))
    t.add_row("age", age)
    t.add_row("docs", str(len(ev.get("files_cited", {}))))
    t.add_row(
        "cited paths",
        str(sum(len(v) for v in ev.get("files_cited", {}).values())),
    )
    console.print(t)


def _require_api_key() -> None:
    """Pre-flight: fail fast if the LLM has no creds. Never reads .env."""
    import os

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        console.print(
            "[red]GOOGLE_API_KEY not set in environment.[/red]\n"
            "Export it for this shell:  [bold]export GOOGLE_API_KEY=...[/bold]\n"
            "or place it in a `.env` file (loaded automatically), then re-run."
        )
        raise typer.Exit(code=1)


@app.command()
def init(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing repo-map docs."
    ),
) -> None:
    """Tier-3: full first-time scan + write all repo-map docs."""
    _require_api_key()

    repo_map_dir = _repo_root() / "notes" / "repo-map"
    existing = (
        sorted(p.name for p in repo_map_dir.glob("*.md"))
        if repo_map_dir.exists()
        else []
    )
    if existing and not force:
        console.print(
            f"[yellow]notes/repo-map/ already contains {len(existing)} docs.[/yellow]\n"
            "Use [bold]agent-refresh refresh[/bold] for incremental updates,\n"
            "or [bold]agent-refresh init --force[/bold] to rebuild from scratch."
        )
        raise typer.Exit(code=2)

    if not yes:
        ok = typer.confirm(
            "Run a full agent-driven init of notes/repo-map/? (this is a Tier-3 LLM call)",
            default=True,
        )
        if not ok:
            raise typer.Exit(code=0)

    from agent_workflows import run

    result = run("repo_map_init")
    console.print(
        Panel.fit(
            f"status: [{'green' if result.status == 'success' else 'red'}]{result.status}[/]\n"
            f"duration: {result.duration_seconds:.2f}s",
            title="agent-refresh init",
            border_style="cyan",
        )
    )
    if result.status == "failed":
        console.print(f"[red]error:[/red] {result.error}")
        raise typer.Exit(code=1)

    out = result.output
    console.print(f"wrote: [bold]{', '.join(out.get('applied') or [])}[/bold]")
    if out.get("missing_docs"):
        console.print(f"[yellow]missing:[/yellow] {', '.join(out['missing_docs'])}")
    console.print(f"post-check clean: [bold]{out.get('post_check_clean')}[/bold]")
    console.print(
        "[yellow]Review then commit:[/yellow]\n"
        "  git add notes/repo-map/ notes/changes.md\n"
        f"  git commit -m \"docs(repo-map): init against {out.get('head_sha', '')[:7]}\""
    )


@app.command()
def refresh(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    from_cache: bool = typer.Option(
        False,
        "--from-cache",
        help="Re-apply notes/repo-map/.last_agent_output.txt instead of calling the LLM.",
    ),
) -> None:
    """Tier-2: incremental refresh of affected docs via the agent."""
    if from_cache:
        cache_path = _repo_root() / "notes" / "repo-map" / ".last_agent_output.txt"
        if not cache_path.exists():
            console.print(
                "[red]No cached agent output at "
                "notes/repo-map/.last_agent_output.txt.[/red]\n"
                "Run [bold]agent-refresh refresh[/bold] without --from-cache first; "
                "the response is saved before parsing."
            )
            raise typer.Exit(code=1)

        from agent_workflows.workflows.repo_map_refresh import apply_cached_plan

        try:
            out = apply_cached_plan(cache_path.read_text())
        except Exception as exc:
            console.print(f"[red]apply failed:[/red] {exc}")
            raise typer.Exit(code=1)

        console.print(
            Panel.fit(
                "status: [green]success[/] (replayed cache)",
                title="agent-refresh", border_style="cyan",
            )
        )
        console.print(f"updated docs: [bold]{', '.join(out.get('applied') or [])}[/bold]")
        console.print(f"post-check clean: [bold]{out.get('post_check_clean')}[/bold]")
        console.print(
            "[yellow]Review changes, then commit:[/yellow]\n"
            "  git add notes/repo-map/ notes/changes.md\n"
            f"  git commit -m \"docs(repo-map): refresh against {out.get('head_sha', '')[:7]}\""
        )
        return

    _require_api_key()

    if not yes:
        ok = typer.confirm("Run agent-driven refresh of notes/repo-map/?", default=True)
        if not ok:
            raise typer.Exit(code=0)

    # Lazy import — keeps `check` / `status` LLM-free.
    from agent_workflows import run

    result = run("repo_map_refresh")
    console.print(Panel.fit(
        f"status: [{'green' if result.status == 'success' else 'red'}]{result.status}[/]\n"
        f"duration: {result.duration_seconds:.2f}s",
        title="agent-refresh", border_style="cyan",
    ))
    if result.status == "failed":
        console.print(f"[red]error:[/red] {result.error}")
        raise typer.Exit(code=1)

    out = result.output
    if out.get("status") == "clean":
        console.print("[green]Already fresh — no changes needed.[/green]")
        return

    console.print(f"updated docs: [bold]{', '.join(out.get('applied') or [])}[/bold]")
    console.print(f"post-check clean: [bold]{out.get('post_check_clean')}[/bold]")
    console.print(
        "[yellow]Review changes, then commit:[/yellow]\n"
        "  git add notes/repo-map/ notes/changes.md\n"
        f"  git commit -m \"docs(repo-map): refresh against {out.get('head_sha', '')[:7]}\""
    )


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    """Bare `agent-refresh` = check, then offer refresh if stale."""
    if ctx.invoked_subcommand is not None:
        return
    code, output = _run_check()
    if "STALE" not in output:
        console.print(Panel("repo-map is fresh.", border_style="green"))
        return
    console.print(Panel(output.strip(), title="repo-map: STALE", border_style="yellow"))
    if typer.confirm("Run agent-driven refresh now?", default=True):
        ctx.invoke(refresh, yes=True)


if __name__ == "__main__":
    app()
