"""CLI commands for exporting anonymized telemetry datasets and data quality auditing."""

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from trace.db.repository import SessionRepository
from trace.db.session import DEFAULT_DB_URL, get_session_factory, init_db

console = Console(force_terminal=True, highlight=False)
export_app = typer.Typer(help="Export telemetry data and generate data quality reports.")

FEATURE_FIELDS = [
    "session_id",
    "data_source",
    "problem_id",
    "loc",
    "ast_node_count",
    "ast_max_depth",
    "cyclomatic_complexity",
    "function_count",
    "has_traceback_input",
    "error_desc_length",
    "error_family_syntax",
    "error_family_type_or_value",
    "ast_first_step",
    "static_to_exec_ratio",
    "failed_tool_ratio",
    "tool_sequence_entropy",
    "total_investigation_steps",
    "hypothesis_count",
    "hypothesis_rejection_ratio",
    "countercheck_execution_rate",
    "direct_evidence_ratio",
    "created_at",
]


async def _fetch_telemetry_records(data_source: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch and format all telemetry records from SQLite."""
    await init_db(DEFAULT_DB_URL)
    factory = get_session_factory(DEFAULT_DB_URL)
    async with factory() as db:
        repo = SessionRepository(db)
        records = await repo.list_all_telemetry(data_source=data_source)
        results = []
        for r in records:
            item = {
                "session_id": r.session_id,
                "data_source": r.data_source,
                "problem_id": r.problem_id,
                "loc": r.loc,
                "ast_node_count": r.ast_node_count,
                "ast_max_depth": r.ast_max_depth,
                "cyclomatic_complexity": r.cyclomatic_complexity,
                "function_count": r.function_count,
                "has_traceback_input": r.has_traceback_input,
                "error_desc_length": r.error_desc_length,
                "error_family_syntax": r.error_family_syntax,
                "error_family_type_or_value": r.error_family_type_or_value,
                "ast_first_step": r.ast_first_step,
                "static_to_exec_ratio": r.static_to_exec_ratio,
                "failed_tool_ratio": r.failed_tool_ratio,
                "tool_sequence_entropy": r.tool_sequence_entropy,
                "total_investigation_steps": r.total_investigation_steps,
                "hypothesis_count": r.hypothesis_count,
                "hypothesis_rejection_ratio": r.hypothesis_rejection_ratio,
                "countercheck_execution_rate": r.countercheck_execution_rate,
                "direct_evidence_ratio": r.direct_evidence_ratio,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            results.append(item)
        return results


def _run_async(coro):
    """Safely execute an async coroutine from synchronous Typer CLI context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


@export_app.command(name="telemetry", help="Export session telemetry records to JSON or CSV.")
def export_telemetry_cmd(
    output: Path = typer.Option(
        Path("telemetry_export.json"),
        "--output",
        "-o",
        help="Path for exported data file (.json or .csv)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export file format: 'json' or 'csv'",
    ),
    data_source: Optional[str] = typer.Option(
        None,
        "--data-source",
        "-s",
        help="Filter by data source (e.g. 'REAL', 'BENCHMARK')",
    ),
) -> None:
    """Export debugging telemetry for research and offline analytics."""
    records = _run_async(_fetch_telemetry_records(data_source=data_source))
    if not records:
        console.print("[bold yellow]Warning:[/bold yellow] No telemetry records found in the database.")
        raise typer.Exit(code=0)

    output_format = format.lower().strip()
    if output_format == "csv" or str(output).endswith(".csv"):
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FEATURE_FIELDS)
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        console.print(f"[bold green]Exported {len(records)} records to CSV:[/bold green] {output.resolve()}")
    else:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        console.print(f"[bold green]Exported {len(records)} records to JSON:[/bold green] {output.resolve()}")


@export_app.command(name="dataset-report", help="Generate a comprehensive dataset quality and habit audit report.")
def dataset_report_cmd(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional markdown file path to save the dataset report",
    ),
) -> None:
    """Print or save a data quality and completeness report for all recorded telemetry."""
    records = _run_async(_fetch_telemetry_records())
    if not records:
        console.print("[bold yellow]No telemetry data available to generate report.[/bold yellow]")
        raise typer.Exit(code=0)

    total_count = len(records)
    real_count = sum(1 for r in records if r.get("data_source") == "REAL")
    bench_count = sum(1 for r in records if r.get("data_source") != "REAL")

    avg_loc = sum(r.get("loc", 0) for r in records) / total_count
    avg_steps = sum(r.get("total_investigation_steps", 0) for r in records) / total_count
    avg_hyp = sum(r.get("hypothesis_count", 0) for r in records) / total_count
    avg_evidence_ratio = sum(r.get("direct_evidence_ratio", 0.0) for r in records) / total_count
    avg_countercheck = sum(r.get("countercheck_execution_rate", 0.0) for r in records) / total_count
    ast_first_rate = (sum(1 for r in records if r.get("ast_first_step")) / total_count) * 100
    tb_provided_rate = (sum(1 for r in records if r.get("has_traceback_input")) / total_count) * 100

    report_table = Table(title="[bold]TRACE Telemetry Dataset Quality Report[/bold]", box=box.ROUNDED)
    report_table.add_column("Metric / Dimension", style="cyan", width=35)
    report_table.add_column("Observed Value", justify="right", style="bold green", width=20)

    report_table.add_row("Total Recorded Sessions", str(total_count))
    report_table.add_row("Real User Sessions", str(real_count))
    report_table.add_row("Benchmark / Evaluation Sessions", str(bench_count))
    report_table.add_row("Average Lines of Code (LOC)", f"{avg_loc:.1f}")
    report_table.add_row("Average Investigation Steps", f"{avg_steps:.1f}")
    report_table.add_row("Average Hypotheses Proposed", f"{avg_hyp:.1f}")
    report_table.add_row("Direct Evidence Ratio", f"{avg_evidence_ratio * 100:.1f}%")
    report_table.add_row("Countercheck Execution Rate", f"{avg_countercheck * 100:.1f}%")
    report_table.add_row("AST Inspection Before Execution", f"{ast_first_rate:.1f}%")
    report_table.add_row("Traceback Framing Rate", f"{tb_provided_rate:.1f}%")

    console.print(report_table)

    if output:
        md_content = f"""# TRACE Telemetry Dataset Quality Report

Generated at: {records[0].get('created_at', 'N/A')}

| Metric / Dimension | Value |
| --- | --- |
| **Total Recorded Sessions** | {total_count} |
| **Real User Sessions** | {real_count} |
| **Benchmark Sessions** | {bench_count} |
| **Average Lines of Code (LOC)** | {avg_loc:.1f} |
| **Average Investigation Steps** | {avg_steps:.1f} |
| **Average Hypotheses Proposed** | {avg_hyp:.1f} |
| **Direct Evidence Ratio** | {avg_evidence_ratio * 100:.1f}% |
| **Countercheck Execution Rate** | {avg_countercheck * 100:.1f}% |
| **AST Inspection Before Execution** | {ast_first_rate:.1f}% |
| **Traceback Framing Rate** | {tb_provided_rate:.1f}% |
"""
        output.write_text(md_content, encoding="utf-8")
        console.print(f"\n[bold green]Report saved to:[/bold green] {output.resolve()}")
