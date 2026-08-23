"""Integration tests for TRACE agent loop and lifecycle orchestration."""

from pathlib import Path
import pytest

from trace.agent.orchestrator import InvestigationOrchestrator
from trace.core.models import HypothesisStatus
from trace.core.state import LifecycleState
from trace.llm.mock_provider import MockLLMProvider
from trace.tools.registry import create_default_registry


def test_agent_orchestrator_complete_lifecycle(tmp_path: Path):
    source_code = """
def calculate_discount(price, discount_percent):
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid discount percentage")
    return price * (1 - discount_percent / 100)

print(calculate_discount(100, 20))
"""
    provider = MockLLMProvider()
    registry = create_default_registry(workspace_root=str(tmp_path))
    orchestrator = InvestigationOrchestrator(provider=provider, registry=registry)

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Verify discount calculation",
        max_iterations=5,
    )

    # Verify final terminal state
    assert state.status == LifecycleState.COMPLETED
    assert not state.is_terminal() is False

    # Verify plan creation
    assert state.current_plan is not None
    assert len(state.current_plan.steps) >= 2

    # Verify tool execution & observations
    assert len(state.observations) >= 1
    assert len(state.tool_history) >= 1

    # Verify hypotheses tracking
    assert len(state.hypotheses) >= 2

    # Verify diagnosis
    assert state.final_diagnosis is not None
    assert state.final_diagnosis.likely_root_cause != ""
    assert state.final_diagnosis.learning_point != ""
    assert state.confidence > 0.7


def test_agent_orchestrator_syntax_error(tmp_path: Path):
    broken_code = """
def process_data(items)
    total = sum(items)
    return total
"""
    provider = MockLLMProvider()
    registry = create_default_registry(workspace_root=str(tmp_path))
    orchestrator = InvestigationOrchestrator(provider=provider, registry=registry)

    state = orchestrator.investigate(
        source_code=broken_code,
        user_goal="Fix syntax error preventing script from running",
        error_description="SyntaxError: invalid syntax",
    )

    assert state.status == LifecycleState.COMPLETED
    assert state.final_diagnosis is not None
    assert "syntax" in state.final_diagnosis.likely_root_cause.lower()
    
    # Check that at least one hypothesis was confirmed
    confirmed = [h for h in state.hypotheses if h.status == HypothesisStatus.CONFIRMED]
    assert len(confirmed) >= 1
