"""CLI: `uv run run-workflow <name>` — runs any registered workflow."""
import json

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent_workflows import list_workflows, run

app = typer.Typer(add_completion=False, help="Run a registered workflow by name.")
console = Console()


@app.command()
def main(
    name: str = typer.Argument(..., help="Workflow name (e.g. 'daily_db_report')."),
    show_findings: bool = typer.Option(False, "--findings", help="Also print raw findings."),
) -> None:
    available = list_workflows()
    if name not in available:
        console.print(f"[red]Unknown workflow: {name}[/red]")
        console.print(f"Available: {', '.join(available)}")
        raise typer.Exit(code=1)

    console.print(Panel.fit(f"Running [bold]{name}[/bold]", border_style="cyan"))
    result = run(name)

    console.print(
        Panel.fit(
            f"status: [{'green' if result.status == 'success' else 'red'}]{result.status}[/]\n"
            f"duration: {result.duration_seconds:.2f}s",
            title="Result",
            border_style="cyan",
        )
    )

    if result.status == "failed":
        console.print(f"[red]error:[/red] {result.error}")
        raise typer.Exit(code=1)

    if show_findings and "findings" in result.output:
        console.print(Panel(result.output["findings"], title="Findings"))

    if "report" in result.output:
        console.print(Markdown(result.output["report"]))
    else:
        console.print_json(json.dumps(result.output, default=str))


if __name__ == "__main__":
    app()
