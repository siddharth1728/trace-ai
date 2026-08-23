"""Unit tests for AgentState and Lifecycle State Machine."""

import pytest

from trace.core.models import (
    Hypothesis,
    HypothesisStatus,
    InvestigationPlan,
    Observation,
    PlanStep,
    StepStatus,
)
from trace.core.state import (
    AgentState,
    InvalidStateTransitionError,
    LifecycleState,
)


def test_initial_state_creation():
    state = AgentState(
        user_goal="Fix zero division error in calculate_average",
        source_code="def calculate_average(nums):\n    return sum(nums) / len(nums)\n",
    )
    assert state.status == LifecycleState.CREATED
    assert state.iteration_count == 0
    assert len(state.observations) == 0
    assert len(state.hypotheses) == 0
    assert not state.is_terminal()


def test_valid_state_transitions():
    state = AgentState(
        user_goal="Test lifecycle",
        source_code="print('hello')",
    )
    
    state.transition_to(LifecycleState.UNDERSTANDING)
    assert state.status == LifecycleState.UNDERSTANDING

    state.transition_to(LifecycleState.PLANNING)
    assert state.status == LifecycleState.PLANNING

    state.transition_to(LifecycleState.INVESTIGATING)
    assert state.status == LifecycleState.INVESTIGATING

    state.transition_to(LifecycleState.TESTING)
    assert state.status == LifecycleState.TESTING

    state.transition_to(LifecycleState.EVALUATING)
    assert state.status == LifecycleState.EVALUATING

    state.transition_to(LifecycleState.DIAGNOSING)
    assert state.status == LifecycleState.DIAGNOSING

    state.transition_to(LifecycleState.EXPLAINING)
    assert state.status == LifecycleState.EXPLAINING

    state.transition_to(LifecycleState.COMPLETED)
    assert state.status == LifecycleState.COMPLETED
    assert state.is_terminal()


def test_invalid_state_transition_raises_error():
    state = AgentState(
        user_goal="Test illegal transition",
        source_code="print('hello')",
    )
    
    # Direct jump from CREATED to COMPLETED is forbidden
    with pytest.raises(InvalidStateTransitionError):
        state.transition_to(LifecycleState.COMPLETED)


def test_blocked_transition():
    state = AgentState(
        user_goal="Test blocked transition",
        source_code="print('hello')",
    )
    state.transition_to(LifecycleState.BLOCKED, reason="Safety policy violation")
    assert state.status == LifecycleState.BLOCKED
    assert state.blocked_reason == "Safety policy violation"
    assert state.is_terminal()


def test_observation_and_hypothesis_management():
    state = AgentState(
        user_goal="Test hypotheses",
        source_code="x = None\nprint(len(x))",
    )

    obs = Observation(
        tool_name="python_executor",
        input_args={"source_code": state.source_code},
        output_data={"exit_code": 1},
        is_success=True,
        summary="TypeError: object of type 'NoneType' has no len()",
    )
    state.add_observation(obs)
    assert len(state.observations) == 1

    hyp = Hypothesis(
        statement="Variable 'x' is None when len() is called.",
        confidence=0.6,
        status=HypothesisStatus.PROPOSED,
    )
    state.add_hypothesis(hyp)
    assert len(state.hypotheses) == 1

    # Update hypothesis status
    state.update_hypothesis_status(
        hypothesis_id=hyp.id,
        new_status=HypothesisStatus.SUPPORTED,
        confidence=0.9,
        supporting_obs_id=obs.id,
        rationale="Executor stderr confirmed TypeError on NoneType",
    )

    updated_hyp = state.get_hypothesis(hyp.id)
    assert updated_hyp is not None
    assert updated_hyp.status == HypothesisStatus.SUPPORTED
    assert updated_hyp.confidence == 0.9
    assert obs.id in updated_hyp.supporting_observation_ids
    assert "TypeError" in updated_hyp.rationale


def test_iteration_limit_enforcement():
    state = AgentState(
        user_goal="Test iteration limits",
        source_code="print(1)",
        max_iterations=3,
    )

    assert state.increment_iteration() is True  # iter 1
    assert state.increment_iteration() is True  # iter 2
    assert state.increment_iteration() is False  # iter 3 (exceeded/reached max)
    assert state.iteration_count == 3
