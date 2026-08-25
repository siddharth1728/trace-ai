"""CLI & Automation script to execute the Stage v0.4-A Empirical Gate Evaluation."""

import json
from pathlib import Path
from trace.ml.dataset import DatasetAuditor, DatasetExporter, SyntheticBenchmarkDatasetGenerator
from trace.ml.experiments import ExperimentRunner


def main():
    print("=" * 70)
    print("TRACE v0.4 -- STAGE v0.4-A METHODOLOGICAL GATE EVALUATION")
    print("=" * 70)

    # 1. Generate / Load dataset (60 samples, 20 per archetype, 5 problem clusters)
    records = SyntheticBenchmarkDatasetGenerator.generate_test_dataset(n_per_class=20)
    dataset_path = Path("data/telemetry_gate_dataset.json")
    DatasetExporter.export_to_json(records, dataset_path)
    DatasetExporter.export_to_csv(records, Path("data/telemetry_gate_dataset.csv"))
    print(f"[OK] Labeled telemetry dataset exported: {len(records)} samples -> {dataset_path}")

    # 2. Data Quality Audit
    audit_report = DatasetAuditor.audit(records)
    print("\n--- DATA QUALITY & LEAKAGE AUDIT ---")
    print(f"Total Samples: {audit_report.total_samples}")
    print(f"Class Distribution: {audit_report.class_distribution} ({audit_report.class_distribution_pct})")
    print(f"Unique Problem Clusters: {audit_report.unique_problem_ids}")
    print(f"Class Balance Verified: {audit_report.is_balanced}")
    print(f"Leakage Guards Passed: {audit_report.leakage_guard_passed}")
    print(f"Collinear Feature Pairs (|r| > 0.85): {len(audit_report.collinear_feature_pairs)}")
    for f1, f2, r_val in audit_report.collinear_feature_pairs:
        print(f"   • {f1} <-> {f2}: r = {r_val}")

    # 3. Multi-Model Cross-Validation Experiments (5-Fold Stratified GroupKFold)
    print("\n--- 5-FOLD COMPARATIVE BENCHMARK EXPERIMENTS ---")
    gate_report = ExperimentRunner.run_benchmark(records, n_splits=5)

    print(f"{'Model Candidate':<30} | {'Macro P':<8} | {'Macro R':<8} | {'Macro F1':<8} | {'Acc':<6} | {'Fold Std':<8}")
    print("-" * 78)
    for res in gate_report.all_model_results:
        print(f"{res.model_name:<30} | {res.macro_precision:<8.3f} | {res.macro_recall:<8.3f} | {res.macro_f1:<8.3f} | {res.accuracy:<6.3f} | {res.fold_f1_std:<8.3f}")

    print("\n--- GATE VERDICT & EVALUATION ---")
    print(f"Rule Baseline Macro-F1:       {gate_report.baseline_rule_f1:.3f}")
    print(f"Best ML Model:                {gate_report.best_ml_model_name}")
    print(f"Best ML Macro-F1:             {gate_report.best_ml_model_f1:.3f}")
    print(f"Delta over Rule Baseline:     +{gate_report.improvement_over_rule_baseline * 100:.1f}%")
    print(f"Stage v0.4-B Gate Passed:     {gate_report.is_gate_passed}")
    print(f"\nJustification: {gate_report.gate_justification}")
    print("=" * 70)


if __name__ == "__main__":
    main()
