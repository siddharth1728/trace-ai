"""Rich CLI for TRACE AI debugging investigations with cross-platform safe encoding."""

import os
from pathlib import Path
import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import typer

from trace.agent.orchestrator import InvestigationOrchestrator
from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.models import HypothesisStatus
from trace.core.state import AgentState, LifecycleState
from trace.llm.provider import LLMProviderFactory

# Set UTF-8 stream handling where supported
console = Console(force_terminal=True, highlight=False)

app = typer.Typer(
    name="trace",
    help="TRACE: Understand your bugs. Understand how you debug.",
    add_completion=False,
    no_args_is_help=True,
)


def format_status_badge(status: HypothesisStatus) -> Text:
    """Format colorful badge for hypothesis status."""
    if status == HypothesisStatus.CONFIRMED:
        return Text(" CONFIRMED ", style="bold black on bright_green")
    elif status == HypothesisStatus.SUPPORTED:
        return Text(" SUPPORTED ", style="bold black on bright_cyan")
    elif status == HypothesisStatus.REJECTED:
        return Text(" REJECTED ", style="bold white on bright_red")
    elif status == HypothesisStatus.WEAKENED:
        return Text(" WEAKENED ", style="bold black on bright_yellow")
    return Text(" PROPOSED ", style="bold white on blue")


def render_cli_event(event: TraceEvent) -> None:
    """Live CLI event renderer subscribed to the global event bus."""
    if event.event_type == EventType.PLAN_CREATED:
        console.print(f"[bold cyan][PLAN OBJECTIVE][/bold cyan] {event.payload.get('objective')}")
        console.print(f"[dim]   Created {event.payload.get('step_count')} investigation step(s)[/dim]\n")
    elif event.event_type == EventType.STEP_STARTED:
        console.print(f"[bold yellow]>> {event.message}[/bold yellow]")
    elif event.event_type == EventType.OBSERVATION_RECORDED:
        obs = event.payload.get("observation", {})
        tool = obs.get("tool_name", "tool")
        success = obs.get("is_success", True)
        icon = "[+]" if success else "[-]"
        style = "green" if success else "red"
        console.print(f"  [{style}]{icon} [{tool}]:[/] {obs.get('summary')}\n")
    elif event.event_type == EventType.HYPOTHESIS_UPDATED:
        eval_item = event.payload.get("evaluation", {})
        hid = eval_item.get("hypothesis_id", "hyp")
        status_val = eval_item.get("new_status")
        status_str = status_val.value if hasattr(status_val, "value") else str(status_val)
        conf = eval_item.get("confidence", 0.0)
        console.print(f"  [magenta][EVAL] Hypothesis ({hid}):[/magenta] [bold]{status_str}[/bold] (confidence: {conf*100:.0f}%)")


@app.command(name="investigate", help="Investigate a Python script for bugs, tracebacks, or logic failures.")
def investigate_cmd(
    file_path: Path = typer.Argument(..., help="Path to the Python file to investigate"),
    goal: str = typer.Option(
        ...,
        "--goal",
        "-g",
        help="Description of what problem or bug you are trying to solve",
    ),
    error: Optional[str] = typer.Option(
        None,
        "--error",
        "-e",
        help="Optional error description or unexpected behavior description",
    ),
    traceback_file: Optional[Path] = typer.Option(
        None,
        "--traceback",
        "-t",
        help="Optional file path containing raw traceback text",
    ),
    provider: str = typer.Option(
        "auto",
        "--provider",
        "-p",
        help="LLM provider: 'mock', 'openai', or 'auto' (default)",
    ),
    max_iterations: int = typer.Option(
        8,
        "--max-iterations",
        "-i",
        help="Maximum agent investigation iterations",
    ),
) -> None:
    """Run an evidence-driven AI debugging investigation on a Python program."""
    # Banner
    console.print(
        Panel.fit(
            "[bold white]TRACE[/bold white] [dim]v0.1.0[/dim]\n"
            "[cyan]Understand your bugs. Understand how you debug.[/cyan]",
            border_style="bright_blue",
            box=box.ROUNDED,
        )
    )

    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' does not exist.")
        raise typer.Exit(code=1)

    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as ex:
        console.print(f"[bold red]Error reading file:[/bold red] {ex}")
        raise typer.Exit(code=1)

    traceback_text: Optional[str] = None
    if traceback_file and traceback_file.exists():
        traceback_text = traceback_file.read_text(encoding="utf-8")

    # Display Session Info
    info_table = Table(box=box.SIMPLE, show_header=False)
    info_table.add_row("[bold]Target File:[/bold]", str(file_path.resolve()))
    info_table.add_row("[bold]Goal:[/bold]", goal)
    info_table.add_row("[bold]Provider:[/bold]", provider)
    info_table.add_row("[bold]Max Iterations:[/bold]", str(max_iterations))
    console.print(Panel(info_table, title="[bold]Session Context[/bold]", border_style="blue"))
    console.print()

    # Subscribe live event renderer
    global_event_bus.subscribe(render_cli_event)

    # Initialize LLM Provider & Orchestrator
    llm_provider = LLMProviderFactory.create(provider_name=provider)
    orchestrator = InvestigationOrchestrator(
        provider=llm_provider,
        workspace_root=file_path.parent,
    )

    console.print("[bold green]Starting Investigation Loop...[/bold green]\n")

    state: AgentState = orchestrator.investigate(
        source_code=source_code,
        user_goal=goal,
        error_description=error,
        traceback_input=traceback_text,
        file_path=str(file_path.resolve()),
        max_iterations=max_iterations,
    )

    console.print("\n" + "=" * 60 + "\n")

    if state.status == LifecycleState.BLOCKED:
        console.print(
            Panel(
                f"[bold red]Investigation Blocked:[/bold red] {state.blocked_reason}",
                title="[bold red]Blocked Session[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # 1. Hypotheses Evaluation Board
    if state.hypotheses:
        hyp_table = Table(title="[bold]Hypothesis Evaluation Board[/bold]", box=box.ROUNDED)
        hyp_table.add_column("ID", style="dim", width=10)
        hyp_table.add_column("Statement", style="white")
        hyp_table.add_column("Status", justify="center", width=14)
        hyp_table.add_column("Confidence", justify="right", width=12)

        for h in state.hypotheses:
            badge = format_status_badge(h.status)
            conf_bar = f"{h.confidence * 100:.0f}%"
            hyp_table.add_row(h.id, h.statement, badge, conf_bar)

        console.print(hyp_table)
        console.print()

    # 2. Final Evidence-Grounded Diagnosis
    if state.final_diagnosis:
        diag = state.final_diagnosis

        diag_content = Text()
        diag_content.append("[PROBLEM STATEMENT]\n", style="bold cyan")
        diag_content.append(f"  {diag.problem_statement}\n\n")

        diag_content.append("[LIKELY ROOT CAUSE]\n", style="bold red")
        diag_content.append(f"  {diag.likely_root_cause}\n\n")

        diag_content.append("[EVIDENCE COLLECTED]\n", style="bold green")
        for ev in diag.evidence_summary:
            diag_content.append(f"  * {ev}\n")
        diag_content.append("\n")

        diag_content.append("[STUDENT LEARNING POINT]\n", style="bold yellow")
        diag_content.append(f"  {diag.learning_point}\n\n")

        diag_content.append("[HOW TO FIX IT - CONCEPTUAL GUIDANCE]\n", style="bold bright_blue")
        diag_content.append(f"  {diag.suggested_fix_guidance}\n\n")

        diag_content.append(f"Confidence: {diag.confidence * 100:.0f}%\n", style="dim")
        if diag.what_remains_uncertain:
            diag_content.append("Remaining Uncertainties:\n", style="dim italic")
            for unc in diag.what_remains_uncertain:
                diag_content.append(f"  * {unc}\n", style="dim italic")

        console.print(
            Panel(
                diag_content,
                title="[bold green]TRACE Final Diagnosis & Learning Takeaway[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )


@app.command(name="version")
def version_cmd() -> None:
    """Print TRACE version."""
    console.print("[bold]TRACE[/bold] version 0.1.0 (v0.1 Investigation Core)")


if __name__ == "__main__":
    app()
