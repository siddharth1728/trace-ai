"""Unit tests for TRACE v1.0 Deterministic Habits."""

import pytest
from trace.ml.schemas import FeatureVector
from trace.ml.baselines import (
    compute_deterministic_habits,
    generate_deterministic_strengths_and_growth,
)


def test_deterministic_habits_computation():
    sample1 = FeatureVector(
        session_id="s1",
        loc=10,
        ast_node_count=20,
        ast_max_depth=3,
        cyclomatic_complexity=1,
        function_count=1,
        has_traceback_input=True,
        error_desc_length=30,
        error_family_syntax=False,
        error_family_type_or_value=True,
        ast_first_step=True,
        static_to_exec_ratio=1.5,
        failed_tool_ratio=0.0,
        tool_sequence_entropy=0.8,
        total_investigation_steps=4,
        hypothesis_count=2,
        hypothesis_rejection_ratio=0.5,
        countercheck_execution_rate=1.0,
        direct_evidence_ratio=0.8,
    )
    sample2 = FeatureVector(
        session_id="s2",
        loc=15,
        ast_node_count=35,
        ast_max_depth=4,
        cyclomatic_complexity=2,
        function_count=1,
        has_traceback_input=False,
        error_desc_length=15,
        error_family_syntax=True,
        error_family_type_or_value=False,
        ast_first_step=False,
        static_to_exec_ratio=0.2,
        failed_tool_ratio=0.4,
        tool_sequence_entropy=0.3,
        total_investigation_steps=6,
        hypothesis_count=4,
        hypothesis_rejection_ratio=0.75,
        countercheck_execution_rate=0.0,
        direct_evidence_ratio=0.2,
    )

    habits = compute_deterministic_habits([sample1, sample2])
    assert habits.total_sessions == 2
    assert habits.ast_first_rate == 50.0
    assert habits.traceback_provided_rate == 50.0
    assert habits.countercheck_rigor_rate == 50.0
    assert habits.avg_investigation_steps == 5.0
    assert habits.avg_hypotheses_per_session == 3.0
    assert habits.tool_failure_rate == 20.0

    strengths, growth = generate_deterministic_strengths_and_growth(habits)
    assert len(strengths) > 0
    assert len(growth) > 0
