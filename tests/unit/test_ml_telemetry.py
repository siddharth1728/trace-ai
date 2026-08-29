"""Unit tests for TRACE v0.4 Telemetry Extractor and Feature Engineering."""

import pytest
from trace.core.state import AgentState, LifecycleState
from trace.core.models import Observation, Hypothesis, HypothesisStatus
from trace.core.evidence import Evidence, EvidenceType, EvidenceRelation
from trace.ml.telemetry import TelemetryExtractor, compute_ast_metrics, compute_tool_entropy
from trace.ml.schemas import TelemetryFeatures


def test_ast_metrics_valid_code():
    code = """
def calculate_sum(nums):
    total = 0
    for n in nums:
        if n > 0:
            total += n
    return total

print(calculate_sum([1, 2, 3]))
"""
    metrics = compute_ast_metrics(code)
    assert metrics["loc"] >= 6
    assert metrics["ast_node_count"] > 15
    assert metrics["ast_max_depth"] >= 4
    assert metrics["cyclomatic_complexity"] >= 3  # for + if + 1
    assert metrics["function_count"] == 1


def test_ast_metrics_syntax_error_graceful_fallback():
    broken_code = "def broken(\n  if x > 0 return 1"
    metrics = compute_ast_metrics(broken_code)
    assert metrics["loc"] == 2
    assert metrics["ast_node_count"] >= 1
    assert metrics["cyclomatic_complexity"] == 1
    assert metrics["function_count"] == 1


def test_compute_tool_entropy():
    # Single tool -> zero entropy
    assert compute_tool_entropy(["ast_analyzer", "ast_analyzer"]) == 0.0
    # Balanced tools -> higher entropy
    entropy = compute_tool_entropy(["ast_analyzer", "python_executor", "traceback_parser"])
    assert entropy > 0.8
    # Empty
    assert compute_tool_entropy([]) == 0.0


def test_telemetry_extractor_from_agent_state():
    state = AgentState(
        session_id="test_sess_001",
        lifecycle_state=LifecycleState.COMPLETED,
        user_goal="Debug TypeError in calculate_sum with None input",
        source_code="def calculate_sum(nums):\n    return sum(nums)",
        error_description="TypeError: unsupported operand type",
        traceback_input="Traceback (most recent call last):\n  File 'test.py', line 2\nTypeError",
    )

    # Add observations
    state.observations.append(
        Observation(
            id="obs_01",
            tool_name="ast_analyzer",
            input_args={},
            output_data={},
            is_success=True,
            summary="AST parsed successfully",
        )
    )
    state.observations.append(
        Observation(
            id="obs_02",
            tool_name="python_executor",
            input_args={},
            output_data={},
            is_success=True,
            summary="Executed and reproduced error",
        )
    )

    # Add hypothesis and evidence
    state.hypotheses.append(
        Hypothesis(
            id="hyp_01",
            statement="None passed into sum causes TypeError",
            confidence=0.9,
            status=HypothesisStatus.VERIFIED,
        )
    )
    state.evidence_store.append(
        Evidence(
            id="ev_01",
            observation_id="obs_02",
            tool_name="python_executor",
            target_hypothesis_id="hyp_01",
            evidence_type=EvidenceType.DIRECT,
            relation=EvidenceRelation.SUPPORTS,
            statement="TypeError reproduced in subprocess",
        )
    )

    telemetry = TelemetryExtractor.extract_telemetry_record(session_record=state, state=state, problem_id="prob_sum_01")
    features = TelemetryExtractor.extract_feature_vector(telemetry)

    assert features.session_id == "test_sess_001"
    assert features.problem_id == "prob_sum_01"
    assert features.has_traceback_input is True
    assert features.error_family_type_or_value is True
    assert features.ast_first_step is True
    assert features.static_to_exec_ratio >= 1.0
    assert features.failed_tool_ratio == 0.0
    assert features.hypothesis_count == 1
    assert features.direct_evidence_ratio == 1.0

    vector = features.to_feature_list()
    assert len(vector) == 18
    assert len(TelemetryFeatures.get_feature_provenance_map()) == 18
