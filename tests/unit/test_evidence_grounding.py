"""Unit and regression tests for TRACE v0.1.1 evidence-grounding & reliability guarantees."""

from pathlib import Path
import pytest

from trace.agent.evaluator import InvestigationEvaluator
from trace.agent.orchestrator import InvestigationOrchestrator
from trace.agent.planner import InvestigationPlanner
from trace.core.models import (
    Hypothesis,
    HypothesisStatus,
    InvestigationPlan,
    Observation,
    PlanStep,
    StepStatus,
)
from trace.core.state import AgentState, LifecycleState
from trace.llm.mock_provider import MockLLMProvider
from trace.llm.schemas import ActionType, NextActionDecision
from trace.tools.registry import create_default_registry


def test_empty_traceback_skips_traceback_parser():
    """Test 1: When traceback input is empty or missing, planner does not schedule traceback_parser."""
    state = AgentState(
        user_goal="Investigate bug without traceback",
        source_code="def func(x): return x.upper()",
        traceback_input=None,
    )
    planner = InvestigationPlanner(MockLLMProvider())
    plan = planner.create_initial_plan(state, tools_summary="ast_analyzer, python_executor, traceback_parser")

    tool_names = [step.tool_name for step in plan.steps]
    assert "traceback_parser" not in tool_names
    assert "ast_analyzer" in tool_names or "python_executor" in tool_names


def test_failed_tool_cannot_support_hypothesis():
    """Test 2: A failed observation (is_success=False) cannot transition hypothesis to SUPPORTED or CONFIRMED."""
    state = AgentState(
        user_goal="Test hypothesis safety gate",
        source_code="print('hello')",
    )
    failed_obs = Observation(
        tool_name="traceback_parser",
        input_args={"traceback_text": ""},
        output_data={},
        is_success=False,
        summary="Traceback parsing failed: Empty traceback text provided",
    )
    state.add_observation(failed_obs)

    hyp = Hypothesis(
        statement="A variable is None at runtime.",
        confidence=0.5,
        status=HypothesisStatus.PROPOSED,
    )
    state.add_hypothesis(hyp)

    # Attempt to mark SUPPORTED with the failed observation
    state.update_hypothesis_status(
        hypothesis_id=hyp.id,
        new_status=HypothesisStatus.SUPPORTED,
        confidence=0.90,
        supporting_obs_id=failed_obs.id,
        rationale="False claim based on failed tool",
    )

    updated_hyp = state.get_hypothesis(hyp.id)
    assert updated_hyp.status != HypothesisStatus.SUPPORTED
    assert updated_hyp.status == HypothesisStatus.PROPOSED
    assert updated_hyp.confidence <= 0.40


def test_missing_supporting_observation_prevents_supported_or_confirmed():
    """Test 3: Passing non-existent observation ID prevents SUPPORTED/CONFIRMED status."""
    state = AgentState(
        user_goal="Test missing obs ID gate",
        source_code="print('hello')",
    )
    hyp = Hypothesis(
        statement="Potential IndexError",
        confidence=0.5,
        status=HypothesisStatus.PROPOSED,
    )
    state.add_hypothesis(hyp)

    state.update_hypothesis_status(
        hypothesis_id=hyp.id,
        new_status=HypothesisStatus.CONFIRMED,
        confidence=0.95,
        supporting_obs_id="obs_non_existent",
    )

    updated = state.get_hypothesis(hyp.id)
    assert updated.status != HypothesisStatus.CONFIRMED
    assert updated.confidence <= 0.40


def test_unsupported_hypothesis_confidence_capped_at_40_percent():
    """Test 4: Unsupported hypothesis confidence is hard-capped at <= 0.40."""
    state = AgentState(
        user_goal="Test confidence cap",
        source_code="print(1)",
    )
    hyp = Hypothesis(
        statement="Unverified speculation",
        confidence=0.5,
        status=HypothesisStatus.PROPOSED,
    )
    state.add_hypothesis(hyp)

    # Try setting 0.99 confidence without observation
    state.update_hypothesis_status(
        hypothesis_id=hyp.id,
        new_status=HypothesisStatus.SUPPORTED,
        confidence=0.99,
    )

    updated = state.get_hypothesis(hyp.id)
    assert updated.confidence <= 0.40


def test_no_early_termination_on_failed_first_step_when_steps_remain():
    """Test 5: If initial tool fails, evaluator rejects early termination and continues investigation."""
    state = AgentState(
        user_goal="Test termination guard",
        source_code="print('test')",
    )
    # Add 1 failed observation
    failed_obs = Observation(
        tool_name="traceback_parser",
        input_args={},
        is_success=False,
        summary="Failed parsing",
    )
    state.add_observation(failed_obs)

    # Add plan with 2 steps (step 1 done/failed, step 2 pending)
    state.current_plan = InvestigationPlan(
        objective="Investigate",
        steps=[
            PlanStep(
                step_id=1,
                title="Traceback parser",
                tool_name="traceback_parser",
                expected_outcome="Parse traceback frames",
                status=StepStatus.FAILED,
            ),
            PlanStep(
                step_id=2,
                title="Execute in sandbox",
                tool_name="python_executor",
                expected_outcome="Execute in sandbox to observe error",
                status=StepStatus.PENDING,
            ),
        ],
    )

    evaluator = InvestigationEvaluator(MockLLMProvider())
    decision = NextActionDecision(
        reasoning="Attempting to finalize early",
        action_type=ActionType.FINALIZE_DIAGNOSIS,
    )

    should_stop, reason = evaluator.check_termination_condition(state, decision)
    # Must reject early termination because 0 successful observations exist and step 2 is pending
    assert should_stop is False
    assert "rejected" in reason.lower()


def test_what_trace_checked_contains_only_successful_tools():
    """Test 6: what_trace_checked in final diagnosis only includes successfully executed tools."""
    state = AgentState(
        user_goal="Test diagnosis grounding",
        source_code="def add(a, b): return a + b",
    )
    # Record one failed tool and one successful tool
    state.record_tool_call(
        tool_name="traceback_parser",
        arguments={},
        success=False,
        execution_time_ms=5.0,
        error="Empty input",
    )
    state.record_tool_call(
        tool_name="ast_analyzer",
        arguments={"source_code": state.source_code},
        success=True,
        execution_time_ms=10.0,
    )
    state.add_observation(
        Observation(
            tool_name="ast_analyzer",
            is_success=True,
            summary="AST analysis succeeded: 1 function(s) ['add'].",
        )
    )

    orchestrator = InvestigationOrchestrator(provider=MockLLMProvider())
    diagnosis = orchestrator._formulate_final_diagnosis(state)

    # TracebackParser must NOT be in what_trace_checked because it failed
    checked_text = " ".join(diagnosis.what_trace_checked)
    assert "AST" in checked_text
    assert "Traceback" not in checked_text


def test_diagnosis_confidence_penalty_on_missing_execution():
    """Test 7: Overall diagnosis confidence is penalised and uncertainty recorded when execution is missing."""
    state = AgentState(
        user_goal="Test confidence penalty",
        source_code="def divide(a, b): return a / b",
    )
    # Zero successful observations
    orchestrator = InvestigationOrchestrator(provider=MockLLMProvider())
    diagnosis = orchestrator._formulate_final_diagnosis(state)

    assert diagnosis.confidence <= 0.25
    assert any("lacked successful tool observations" in unc.lower() for unc in diagnosis.what_remains_uncertain)


def test_mock_provider_grounds_decisions_strictly_in_successful_observations():
    """Test 8: Mock provider does not finalize or support hypotheses from failed observations in prompt."""
    provider = MockLLMProvider()
    prompt = """Current Investigation State:
Objective: Test
Current Iteration: 1/8

SOURCE CODE:
```python
x = None
print(x.upper())
```

ACTIVE HYPOTHESES:
- [hyp_100] Status: PROPOSED, Confidence: 0.50 | Statement: 'A variable value becomes None at runtime.' | Rationale: Initial

OBSERVATIONS RECORDED SO FAR:
- [obs_001] Tool: traceback_parser, Success: False | Summary: Traceback parsing failed: Empty traceback text provided

CURRENT PLAN REMAINING STEPS:
- Step 2: AST analysis (ast_analyzer)
- Step 3: Run sandbox execution (python_executor)
"""
    decision = provider._decide_next_action(prompt)
    # Must NOT finalize and must NOT confirm hypothesis on failed observation
    assert decision.action_type == ActionType.EXECUTE_TOOL
    assert len(decision.hypothesis_evaluations) == 0


def test_e2e_reproduce_manual_failure_scenario_fixed():
    """
    Test 9: Exact manual failure scenario:
    Run NoneType error investigation without traceback input.
    Verify:
    1. traceback_parser is NOT called.
    2. ast_analyzer and python_executor run successfully.
    3. Final diagnosis claims ONLY tools that actually succeeded.
    4. Confirmed hypothesis is backed by actual execution observation.
    """
    fixtures_dir = Path(__file__).parent.parent / "e2e" / "fixtures"
    target_file = fixtures_dir / "bug_type_error.py"
    source_code = target_file.read_text(encoding="utf-8")

    orchestrator = InvestigationOrchestrator(provider=MockLLMProvider())
    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Investigate NoneType error",
        error_description=None,
        traceback_input=None,  # No traceback provided
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED

    # 1. Verify traceback_parser was NOT executed
    executed_tools = [t.tool_name for t in state.tool_history]
    assert "traceback_parser" not in executed_tools
    assert "ast_analyzer" in executed_tools
    assert "python_executor" in executed_tools

    # 2. Verify all observations are successful
    for obs in state.observations:
        assert obs.is_success is True

    # 3. Verify diagnosis claims only what actually ran
    diag = state.final_diagnosis
    assert diag is not None
    checked_str = " ".join(diag.what_trace_checked)
    assert "Traceback" not in checked_str
    assert "AST" in checked_str
    assert "Sandbox Execution" in checked_str

    # 4. Verify hypothesis has valid supporting observation
    supported = [h for h in state.hypotheses if h.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED)]
    assert len(supported) >= 1
    for h in supported:
        assert len(h.supporting_observation_ids) > 0
        for obs_id in h.supporting_observation_ids:
            obs = state.get_observation(obs_id)
            assert obs is not None
            assert obs.is_success is True
