"""Unit tests for TRACE v0.4-A / v0.5 Baselines, Dataset Quality, and Quarantine Suite."""

import pytest
from trace.ml.schemas import BehaviorArchetype, DataSourceType, FeatureVector, TelemetryFeatures
from trace.ml.baselines import (
    compute_deterministic_habits,
    generate_deterministic_strengths_and_growth,
    MajorityClassBaseline,
    RuleBasedBehaviorClassifier,
)
from trace.ml.dataset import (
    DatasetExporter,
    LabelingWorkflow,
    SyntheticBenchmarkQuarantine,
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


def test_rule_based_behavior_classifier():
    sys_sample = FeatureVector(
        session_id="sys",
        loc=20,
        ast_node_count=40,
        ast_max_depth=4,
        cyclomatic_complexity=2,
        function_count=1,
        has_traceback_input=True,
        error_desc_length=30,
        error_family_syntax=False,
        error_family_type_or_value=True,
        ast_first_step=True,
        static_to_exec_ratio=2.0,
        failed_tool_ratio=0.0,
        tool_sequence_entropy=0.8,
        total_investigation_steps=4,
        hypothesis_count=2,
        hypothesis_rejection_ratio=0.5,
        countercheck_execution_rate=0.8,
        direct_evidence_ratio=0.8,
    )
    guess_sample = FeatureVector(
        session_id="guess",
        loc=10,
        ast_node_count=20,
        ast_max_depth=2,
        cyclomatic_complexity=1,
        function_count=1,
        has_traceback_input=False,
        error_desc_length=10,
        error_family_syntax=False,
        error_family_type_or_value=True,
        ast_first_step=False,
        static_to_exec_ratio=0.2,
        failed_tool_ratio=0.3,
        tool_sequence_entropy=0.4,
        total_investigation_steps=5,
        hypothesis_count=3,
        hypothesis_rejection_ratio=0.66,
        countercheck_execution_rate=0.0,
        direct_evidence_ratio=0.2,
    )

    pred_sys = RuleBasedBehaviorClassifier.predict_one(sys_sample)
    pred_guess = RuleBasedBehaviorClassifier.predict_one(guess_sample)

    assert pred_sys == BehaviorArchetype.SYSTEMATIC_VERIFIER
    assert pred_guess == BehaviorArchetype.GUESS_AND_CHECK


def test_synthetic_benchmark_quarantine_and_exporter():
    # 1. Generate quarantined synthetic benchmark traces
    traces = SyntheticBenchmarkQuarantine.generate_benchmark_traces(count_per_archetype=5)
    assert len(traces) == 20
    assert all(f.data_source == DataSourceType.SYNTHETIC for f, _ in traces)

    features = [f for f, _ in traces]

    # 2. Rule labeling proposal
    labels = LabelingWorkflow.propose_rule_labels(features)
    assert len(labels) == 20
    assert all(l.reviewer_status == "UNREVIEWED" for l in labels)

    # 3. Expert review and confirmation
    label_map = {}
    for i, l in enumerate(labels):
        if i == 0:
            reviewed = LabelingWorkflow.review_label(l, confirmed_label=BehaviorArchetype.SYSTEMATIC_VERIFIER)
            assert reviewed.reviewer_status == "CONFIRMED"
        elif i == 1:
            reviewed = LabelingWorkflow.review_label(l, is_ambiguous=True)
            assert reviewed.reviewer_status == "AMBIGUOUS"
        else:
            reviewed = l
        label_map[l.session_id] = reviewed

    # 4. Tabular CSV and JSON Export (Zero raw code leakage)
    json_out = DatasetExporter.export_json(features, label_map)
    csv_out = DatasetExporter.export_csv(features, label_map)

    assert "session_id" in json_out
    assert "loc" in csv_out
    assert "def " not in csv_out  # Zero raw code leakage
