"""Unit tests for SQLite persistence & SessionRepository in TRACE v0.3."""

from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import (
    FinalDiagnosis,
    Hypothesis,
    HypothesisStatus,
    InvestigationPlan,
    Observation,
    PlanStep,
    StepStatus,
)
from trace.core.state import AgentState, LifecycleState
from trace.db.models import Base
from trace.db.repository import SessionRepository


@pytest_asyncio.fixture
async def db_session(tmp_path: Path):
    """Create in-memory SQLite database session for testing."""
    test_db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_trace.db'}"
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_session_create_and_get(db_session: AsyncSession):
    """Test creating and retrieving a session record."""
    repo = SessionRepository(db_session)
    session_id = "test_sess_01"
    record = await repo.create_session(
        session_id=session_id,
        user_goal="Fix NoneType exception in user display name",
        source_code="def format_name(u): return u.get('name').upper()",
        title="NoneType Bug",
        error_description="AttributeError: 'NoneType' object has no attribute 'upper'",
    )

    assert record.id == session_id
    assert record.status == "CREATED"
    assert record.title == "NoneType Bug"

    fetched = await repo.get_session(session_id)
    assert fetched is not None
    assert fetched.user_goal == "Fix NoneType exception in user display name"
    assert fetched.confidence == 0.0


@pytest.mark.asyncio
async def test_save_full_agent_state_and_cascade(db_session: AsyncSession):
    """Test synchronizing complete AgentState into relational entities."""
    repo = SessionRepository(db_session)
    session_id = "test_sess_02"
    await repo.create_session(
        session_id=session_id,
        user_goal="Investigate ZeroDivision",
        source_code="def avg(nums): return sum(nums)/len(nums)",
    )

    # Build an AgentState
    state = AgentState(
        session_id=session_id,
        user_goal="Investigate ZeroDivision",
        source_code="def avg(nums): return sum(nums)/len(nums)",
    )
    state.status = LifecycleState.COMPLETED
    state.confidence = 0.95

    # Plan
    plan = InvestigationPlan(
        objective="Analyze divide by zero error",
        steps=[
            PlanStep(step_id=1, title="Run AST analysis", tool_name="ast_analyzer", expected_outcome="Identify functions and syntax", status=StepStatus.DONE),
            PlanStep(step_id=2, title="Execute sandbox", tool_name="python_executor", expected_outcome="Execute in sandbox", status=StepStatus.DONE),
        ]
    )
    state.current_plan = plan

    # Observation
    obs = Observation(
        tool_name="python_executor",
        is_success=True,
        summary="Execution FAILED: ZeroDivisionError: division by zero",
    )
    state.add_observation(obs)

    # Hypothesis
    hyp = Hypothesis(
        id="hyp_zero_01",
        statement="Denominator len(nums) is zero when nums is empty",
        status=HypothesisStatus.VERIFIED,
        confidence=0.95,
        rationale="Verified with countercheck",
    )
    state.add_hypothesis(hyp)

    # Evidence
    ev = Evidence(
        observation_id=obs.id,
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement=obs.summary,
        target_hypothesis_id=hyp.id,
        relation=EvidenceRelation.SUPPORTS,
    )
    state.add_evidence(ev)

    # Final Diagnosis
    state.final_diagnosis = FinalDiagnosis(
        problem_statement="ZeroDivisionError on empty list",
        investigation_summary="Investigated in sandbox",
        likely_root_cause="Dividing by empty collection length",
        evidence_summary=["Execution raised ZeroDivisionError"],
        confidence=0.95,
        what_trace_checked=["Controlled Subprocess Sandbox Execution"],
        what_remains_uncertain=[],
        learning_point="Check len(nums) > 0 before dividing.",
        suggested_fix_guidance="Add guard check `if not nums: return 0`.",
        verified_hypothesis_id=hyp.id,
    )

    # Save to SQLite
    await repo.save_full_agent_state(session_id, state)

    # Fetch and verify relational mapping
    loaded = await repo.get_session(session_id)
    assert loaded is not None
    assert loaded.status == "COMPLETED"
    assert loaded.confidence == 0.95
    assert loaded.likely_root_cause == "Dividing by empty collection length"
    assert len(loaded.plan_steps) == 2
    assert len(loaded.observations) == 1
    assert len(loaded.evidence) == 1
    assert len(loaded.hypotheses) == 1
    assert loaded.hypotheses[0].status == "VERIFIED"

    # Test cascade delete
    deleted = await repo.delete_session(session_id)
    assert deleted is True
    assert await repo.get_session(session_id) is None


@pytest.mark.asyncio
async def test_session_event_logging(db_session: AsyncSession):
    """Test logging and reading immutable investigation events."""
    repo = SessionRepository(db_session)
    session_id = "test_sess_03"
    await repo.create_session(
        session_id=session_id,
        user_goal="Test events",
        source_code="print(1)",
    )

    await repo.add_session_event(session_id, "session_status", {"status": "RUNNING"})
    await repo.add_session_event(session_id, "step_started", {"step_id": 1, "tool": "ast_analyzer"})
    await repo.add_session_event(session_id, "session_completed", {"status": "COMPLETED"})

    events = await repo.get_session_events(session_id)
    assert len(events) == 3
    assert events[0].event_type == "session_status"
    assert events[0].payload["status"] == "RUNNING"
    assert events[1].event_type == "step_started"
    assert events[2].event_type == "session_completed"
