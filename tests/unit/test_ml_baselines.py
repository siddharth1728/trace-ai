"""Unit tests for TRACE v0.4 Baselines, Dataset Quality Auditor, and Experiment Runner."""

import pytest
from trace.ml.schemas import BehaviorArchetype, TelemetryFeatures
from trace.ml.baselines import (
    compute_deterministic_habits,
    generate_deterministic_strengths_and_growth,
    MajorityClassBaseline,
    RuleBasedBehaviorClassifier,
)
from trace.ml.dataset import (
    DatasetAuditor,
    SyntheticBenchmarkDatasetGenerator,
)
from trace.ml.experiments import ExperimentRunner


def test_deterministic_habits_computation():
    sample1 = TelemetryFeatures(
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
        hypothesis_churn_count=2,
        hypothesis_rejection_ratio=0.5,
        countercheck_execution_rate=1.0,
        direct_evidence_ratio=0.8,
    )
    sample2 = TelemetryFeatures(
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
        hypothesis_churn_count=4,
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
    sys_sample = TelemetryFeatures(
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
        hypothesis_churn_count=2,
        hypothesis_rejection_ratio=0.5,
        countercheck_execution_rate=0.8,
        direct_evidence_ratio=0.8,
    )
    guess_sample = TelemetryFeatures(
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
        hypothesis_churn_count=3,
        hypothesis_rejection_ratio=0.66,
        countercheck_execution_rate=0.0,
        direct_evidence_ratio=0.2,
    )

    pred_sys = RuleBasedBehaviorClassifier.predict_one(sys_sample)
    pred_guess = RuleBasedBehaviorClassifier.predict_one(guess_sample)

    assert pred_sys == BehaviorArchetype.SYSTEMATIC_VERIFICATION
    assert pred_guess == BehaviorArchetype.RAPID_TRIAL_AND_ERROR


def test_dataset_auditor_and_experiment_runner():
    # Generate balanced synthetic benchmark dataset
    records = SyntheticBenchmarkDatasetGenerator.generate_test_dataset(n_per_class=10)
    assert len(records) == 30

    audit_report = DatasetAuditor.audit(records)
    assert audit_report.total_samples == 30
    assert audit_report.synthetic_samples == 30
    assert audit_report.is_balanced is True
    assert audit_report.leakage_guard_passed is True

    # Run comparative experiment benchmark
    gate_report = ExperimentRunner.run_benchmark(records, n_splits=3)
    assert gate_report.dataset_size == 30
    assert gate_report.num_folds == 3
    assert len(gate_report.all_model_results) == 5

    majority_res = next(r for r in gate_report.all_model_results if r.model_name == "Majority Class Baseline")
    rule_res = next(r for r in gate_report.all_model_results if r.model_name == "Rule-Based Baseline")
    rf_res = next(r for r in gate_report.all_model_results if "Random Forest" in r.model_name)

    assert majority_res.macro_f1 < rule_res.macro_f1
    assert rf_res.macro_f1 > 0.70
    assert len(gate_report.gate_justification) > 10
