"""Unit tests for TRACE telemetry export CLI."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from trace.cli.main import app
from trace.db.models import SessionRecord, SessionTelemetryRecord
from trace.db.session import DEFAULT_DB_URL, get_session_factory, init_db

runner = CliRunner()


@pytest.mark.asyncio
async def test_cli_export_telemetry_and_dataset_report(tmp_path: Path):
    """Test exporting telemetry to JSON/CSV and rendering dataset report."""
    import uuid
    sess_id = f"test_export_{uuid.uuid4().hex[:8]}"

    await init_db(DEFAULT_DB_URL)
    factory = get_session_factory(DEFAULT_DB_URL)
    async with factory() as db:
        sess = SessionRecord(
            id=sess_id,
            user_goal="Test export functionality",
            source_code="def f(): pass",
            status="COMPLETED",
        )
        db.add(sess)
        await db.commit()

        telem = SessionTelemetryRecord(
            session_id=sess_id,
            data_source="REAL",
            problem_id="prob_01",
            loc=15,
            ast_node_count=42,
            ast_max_depth=5,
            cyclomatic_complexity=2,
            function_count=1,
            has_traceback_input=True,
            error_desc_length=30,
            error_family_syntax=False,
            error_family_type_or_value=True,
            ast_first_step=True,
            static_to_exec_ratio=0.5,
            failed_tool_ratio=0.0,
            tool_sequence_entropy=1.2,
            total_investigation_steps=4,
            hypothesis_count=2,
            hypothesis_rejection_ratio=0.5,
            countercheck_execution_rate=1.0,
            direct_evidence_ratio=0.75,
        )
        db.add(telem)
        await db.commit()

    # 1. Export JSON
    json_out = tmp_path / "export.json"
    result = runner.invoke(app, ["export", "telemetry", "--output", str(json_out), "--format", "json"])
    assert result.exit_code == 0
    assert json_out.exists()
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert len(data) >= 1
    record = next(r for r in data if r["session_id"] == sess_id)
    assert record["loc"] == 15
    assert record["data_source"] == "REAL"

    # 2. Export CSV
    csv_out = tmp_path / "export.csv"
    result_csv = runner.invoke(app, ["export", "telemetry", "--output", str(csv_out), "--format", "csv"])
    assert result_csv.exit_code == 0
    assert csv_out.exists()
    csv_text = csv_out.read_text(encoding="utf-8")
    assert sess_id in csv_text
    assert "REAL" in csv_text

    # 3. Dataset Report
    rep_out = tmp_path / "report.md"
    result_rep = runner.invoke(app, ["export", "dataset-report", "--output", str(rep_out)])
    assert result_rep.exit_code == 0
    assert "TRACE Telemetry Dataset Quality Report" in result_rep.stdout
    assert rep_out.exists()
    rep_text = rep_out.read_text(encoding="utf-8")
    assert "Total Recorded Sessions" in rep_text
