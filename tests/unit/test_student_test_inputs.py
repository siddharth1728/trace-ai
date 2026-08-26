"""Unit tests for Student Test Inputs execution and persistence in TRACE v0.5."""

import pytest
from trace.core.models import StudentTestInput
from trace.db.repository import SessionRepository


def test_student_test_input_model():
    t_input = StudentTestInput(
        turn_number=1,
        input_expression="divide(10, 0)",
        student_rationale="Checking division by zero",
        is_boundary_case=True,
    )
    assert t_input.input_expression == "divide(10, 0)"
    assert t_input.is_boundary_case is True
    assert t_input.executed is False


@pytest.mark.asyncio
async def test_student_test_input_repository_flow(async_db_session):
    repo = SessionRepository(async_db_session)
    await repo.create_session(
        session_id="sess_test_input_01",
        user_goal="Test inputs",
        source_code="def divide(a, b): return a / b\n",
        mode="INTERACTIVE",
    )

    # Add test input
    t_rec = await repo.add_student_test_input(
        session_id="sess_test_input_01",
        input_expression="divide(4, 2)",
        student_rationale="Normal positive case",
        is_boundary_case=False,
        turn_number=1,
    )
    assert t_rec.id.startswith("stest_")
    assert t_rec.executed is False

    # Update execution result
    updated = await repo.update_student_test_input_result(
        test_id=t_rec.id,
        executed=True,
        execution_success=True,
        stdout="2.0\n",
        stderr="",
        execution_time_ms=12.5,
    )
    assert updated.executed is True
    assert updated.execution_success is True
    assert "2.0" in updated.stdout

    # List
    inputs = await repo.list_student_test_inputs("sess_test_input_01")
    assert len(inputs) == 1
    assert inputs[0].input_expression == "divide(4, 2)"
