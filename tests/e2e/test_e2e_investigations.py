"""End-to-End Benchmark Suite for TRACE AI Debugging Investigations."""

from pathlib import Path
import pytest

from trace.agent.orchestrator import InvestigationOrchestrator
from trace.core.models import HypothesisStatus
from trace.core.state import LifecycleState
from trace.llm.mock_provider import MockLLMProvider
from trace.tools.registry import create_default_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def orchestrator():
    provider = MockLLMProvider()
    registry = create_default_registry()
    return InvestigationOrchestrator(provider=provider, registry=registry)


def test_benchmark_1_syntax_error(orchestrator: InvestigationOrchestrator):
    """Case 1: Syntax Error investigation."""
    target_file = FIXTURES_DIR / "bug_syntax_error.py"
    source_code = target_file.read_text(encoding="utf-8")

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Fix syntax error preventing calculate_cart_total from running",
        error_description="SyntaxError: invalid syntax",
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED
    assert len(state.observations) >= 1
    assert len(state.hypotheses) >= 2
    assert state.final_diagnosis is not None
    assert "syntax" in state.final_diagnosis.likely_root_cause.lower()
    assert state.final_diagnosis.learning_point != ""
    assert state.confidence >= 0.8


def test_benchmark_2_runtime_error(orchestrator: InvestigationOrchestrator):
    """Case 2: Runtime ZeroDivisionError investigation."""
    target_file = FIXTURES_DIR / "bug_runtime_error.py"
    source_code = target_file.read_text(encoding="utf-8")

    raw_traceback = """Traceback (most recent call last):
  File "bug_runtime_error.py", line 7, in <module>
    print("Average score:", calculate_class_average(empty_scores))
  File "bug_runtime_error.py", line 4, in calculate_class_average
    return sum(scores) / len(scores)
ZeroDivisionError: division by zero"""

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Investigate ZeroDivisionError when passing empty score list",
        error_description="ZeroDivisionError: division by zero",
        traceback_input=raw_traceback,
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED
    assert len(state.observations) >= 1
    assert state.final_diagnosis is not None
    assert "zero" in state.final_diagnosis.likely_root_cause.lower() or "division" in state.final_diagnosis.likely_root_cause.lower()
    assert "ZeroDivisionError" in state.final_diagnosis.learning_point or "0" in state.final_diagnosis.learning_point
    assert state.confidence >= 0.8


def test_benchmark_3_type_error(orchestrator: InvestigationOrchestrator):
    """Case 3: Type Error on NoneType operation."""
    target_file = FIXTURES_DIR / "bug_type_error.py"
    source_code = target_file.read_text(encoding="utf-8")

    raw_traceback = """Traceback (most recent call last):
  File "bug_type_error.py", line 8, in <module>
    print("Display Name:", format_user_display_name(guest_user))
  File "bug_type_error.py", line 5, in format_user_display_name
    return raw_name.upper()
AttributeError: 'NoneType' object has no attribute 'upper'"""

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Investigate crash when user name is None in profile record",
        error_description="AttributeError: 'NoneType' object has no attribute 'upper'",
        traceback_input=raw_traceback,
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED
    assert len(state.observations) >= 1
    assert state.final_diagnosis is not None
    assert "none" in state.final_diagnosis.likely_root_cause.lower() or "type" in state.final_diagnosis.likely_root_cause.lower()
    assert "None" in state.final_diagnosis.learning_point
    assert state.confidence >= 0.8


def test_benchmark_4_logic_error(orchestrator: InvestigationOrchestrator):
    """Case 4: Logic / Indexing Error investigation."""
    target_file = FIXTURES_DIR / "bug_logic_error.py"
    source_code = target_file.read_text(encoding="utf-8")

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Investigate IndexError when looking up 5th element in numbers list",
        error_description="IndexError: list index out of range",
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED
    assert len(state.observations) >= 1
    assert state.final_diagnosis is not None
    assert state.final_diagnosis.learning_point != ""
    assert state.confidence >= 0.8


def test_benchmark_5_input_validation(orchestrator: InvestigationOrchestrator):
    """Case 5: Input Validation / Zero inputs."""
    target_file = FIXTURES_DIR / "bug_input_validation.py"
    source_code = target_file.read_text(encoding="utf-8")

    state = orchestrator.investigate(
        source_code=source_code,
        user_goal="Investigate zero division when calculate_grade_percentage receives zero max_score",
        error_description="ZeroDivisionError: division by zero",
        file_path=str(target_file),
    )

    assert state.status == LifecycleState.COMPLETED
    assert len(state.observations) >= 1
    assert state.final_diagnosis is not None
    assert state.final_diagnosis.learning_point != ""
    assert state.confidence >= 0.8
