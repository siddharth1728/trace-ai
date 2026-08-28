"""Unit tests for Student Hypothesis domain and persistence in TRACE v0.5."""

import pytest
from trace.core.models import (
    Hypothesis,
    HypothesisStatus,
    InvestigationMode,
    StudentHypothesis,
    StudentHypothesisStatus,
)
from trace.core.state import AgentState, LifecycleState
from trace.db.models import SessionRecord, StudentHypothesisRecord
from trace.db.repository import SessionRepository


def test_student_hypothesis_separation_from_agent_hypothesis():
    """Verify StudentHypothesis is distinct and never conflated with TRACE internal Hypothesis."""
    student_hyp = StudentHypothesis(
        hypothesis_text="I think dividing by zero causes the ZeroDivisionError",
        target_function_or_line="divide",
        student_confidence=0.85,
        turn_number=1,
    )
    agent_hyp = Hypothesis(
        statement="Denominator value is evaluated to 0 prior to division operator execution",
        rationale="AST audit confirmed unvalidated input in divide()",
        confidence=0.92,
        status=HypothesisStatus.SUPPORTED,
    )

    assert isinstance(student_hyp, StudentHypothesis)
    assert isinstance(agent_hyp, Hypothesis)
    assert student_hyp.status == StudentHypothesisStatus.UNTESTED
    assert student_hyp.hypothesis_text != agent_hyp.statement


def test_agent_state_interactive_methods():
    """Verify AgentState interactive methods work and manage turn sequence."""
    state = AgentState(
        session_id="test_sess_01",
        user_goal="Fix zero division",
        source_code="def f(x): return 10 / x",
        mode=InvestigationMode.INTERACTIVE,
    )
    assert state.mode == InvestigationMode.INTERACTIVE
    assert len(state.student_hypotheses) == 0

    shyp = state.add_student_hypothesis(
        hypothesis_text="x is 0 when called from main",
        target_function_or_line="f",
        student_confidence=0.9,
    )
    assert len(state.student_hypotheses) == 1
    assert shyp.turn_number == 1
    assert len(state.interaction_turns) == 1
    assert state.interaction_turns[0].speaker.value == "STUDENT"


@pytest.mark.asyncio
async def test_repository_student_hypothesis_crud(async_db_session):
    """Test persisting and querying student hypotheses in SQLite."""
    repo = SessionRepository(async_db_session)
    sess = await repo.create_session(
        session_id="sess_shyp_test",
        user_goal="Test student hyp persistence",
        source_code="x = 1\n",
        mode="INTERACTIVE",
    )

    shyp = await repo.add_student_hypothesis(
        session_id="sess_shyp_test",
        hypothesis_text="NameError caused by undefined variable",
        target_function_or_line="main",
        student_confidence=0.75,
        turn_number=2,
    )
    assert shyp.id.startswith("shyp_")
    assert shyp.status == "UNTESTED"

    # List
    all_hyp = await repo.list_student_hypotheses("sess_shyp_test")
    assert len(all_hyp) == 1
    assert all_hyp[0].hypothesis_text == "NameError caused by undefined variable"

    # Update status
    updated = await repo.update_student_hypothesis_status(shyp.id, "SUPPORTED")
    assert updated.status == "SUPPORTED"
