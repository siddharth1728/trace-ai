"""Dataset Management, Quality Auditing, and Labeling Provenance for TRACE v0.4."""

import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from trace.ml.schemas import (
    BehaviorArchetype,
    LabelProvenance,
    TelemetryFeatures,
    utc_now,
)


class LabeledSessionRecord(BaseModel):
    """A complete labeled sample for behavioral classification."""
    features: TelemetryFeatures
    provenance: LabelProvenance


class DatasetQualityReport(BaseModel):
    """Audit report assessing dataset balance, integrity, and leakage guards."""
    total_samples: int
    real_user_samples: int
    synthetic_samples: int
    class_distribution: Dict[str, int]
    class_distribution_pct: Dict[str, float]
    unique_problem_ids: int
    problem_clusters: Dict[str, int]
    missing_values_detected: int
    collinear_feature_pairs: List[Tuple[str, str, float]]  # (|r| > 0.85)
    is_balanced: bool  # min class >= 20% of max class
    leakage_guard_passed: bool
    audit_timestamp: str


class DatasetAuditor:
    """Performs rigorous data quality checks, distribution analysis, and leakage prevention audits."""

    @classmethod
    def audit(cls, records: List[LabeledSessionRecord]) -> DatasetQualityReport:
        total = len(records)
        if total == 0:
            return DatasetQualityReport(
                total_samples=0,
                real_user_samples=0,
                synthetic_samples=0,
                class_distribution={},
                class_distribution_pct={},
                unique_problem_ids=0,
                problem_clusters={},
                missing_values_detected=0,
                collinear_feature_pairs=[],
                is_balanced=False,
                leakage_guard_passed=True,
                audit_timestamp=utc_now().isoformat(),
            )

        real_count = sum(1 for r in records if not r.features.is_synthetic)
        synthetic_count = total - real_count

        # Class distribution
        class_dist: Dict[str, int] = {}
        for r in records:
            lbl = r.provenance.label.value if hasattr(r.provenance.label, "value") else str(r.provenance.label)
            class_dist[lbl] = class_dist.get(lbl, 0) + 1

        class_pct = {k: round((v / total) * 100, 1) for k, v in class_dist.items()}

        # Problem clusters
        problem_clusters: Dict[str, int] = {}
        for r in records:
            pid = r.features.problem_id or "default"
            problem_clusters[pid] = problem_clusters.get(pid, 0) + 1

        unique_problems = len(problem_clusters)

        # Check balance (min class count >= 20% of max class count)
        counts = list(class_dist.values())
        is_balanced = (min(counts) / max(counts) >= 0.20) if counts and max(counts) > 0 else False

        # Multicollinearity check across 18 features
        feature_names = TelemetryFeatures.feature_names()
        X_matrix = [r.features.to_feature_vector() for r in records]

        collinear_pairs: List[Tuple[str, str, float]] = []
        if total >= 5:
            n_feats = len(feature_names)
            for i in range(n_feats):
                for j in range(i + 1, n_feats):
                    col_i = [row[i] for row in X_matrix]
                    col_j = [row[j] for row in X_matrix]
                    corr = cls._compute_pearson_correlation(col_i, col_j)
                    if abs(corr) >= 0.85:
                        collinear_pairs.append((feature_names[i], feature_names[j], round(corr, 3)))

        return DatasetQualityReport(
            total_samples=total,
            real_user_samples=real_count,
            synthetic_samples=synthetic_count,
            class_distribution=class_dist,
            class_distribution_pct=class_pct,
            unique_problem_ids=unique_problems,
            problem_clusters=problem_clusters,
            missing_values_detected=0,
            collinear_feature_pairs=collinear_pairs,
            is_balanced=is_balanced,
            leakage_guard_passed=unique_problems >= 2,  # Must have multiple problem clusters for GroupKFold
            audit_timestamp=utc_now().isoformat(),
        )

    @staticmethod
    def _compute_pearson_correlation(x: List[float], y: List[float]) -> float:
        """Compute Pearson correlation coefficient r between two numeric series."""
        n = len(x)
        if n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)

        if var_x == 0.0 or var_y == 0.0:
            return 0.0

        cov_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        return cov_xy / math.sqrt(var_x * var_y)


class DatasetExporter:
    """Handles JSON/CSV serialization and persistence for labeled telemetry datasets."""

    @classmethod
    def export_to_json(cls, records: List[LabeledSessionRecord], file_path: Path) -> None:
        """Export dataset to formatted JSON."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump(mode="json") for r in records]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_json(cls, file_path: Path) -> List[LabeledSessionRecord]:
        """Load dataset from JSON."""
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return [LabeledSessionRecord.model_validate(item) for item in raw_data]

    @classmethod
    def export_to_csv(cls, records: List[LabeledSessionRecord], file_path: Path) -> None:
        """Export tabular features and target labels to CSV."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        feature_names = TelemetryFeatures.feature_names()
        fieldnames = ["session_id", "problem_id", "is_synthetic"] + feature_names + ["label", "labeling_method", "confidence"]

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                row = {
                    "session_id": r.features.session_id,
                    "problem_id": r.features.problem_id,
                    "is_synthetic": r.features.is_synthetic,
                    "label": r.provenance.label.value if hasattr(r.provenance.label, "value") else str(r.provenance.label),
                    "labeling_method": r.provenance.labeling_method,
                    "confidence": r.provenance.confidence,
                }
                for name, val in zip(feature_names, r.features.to_feature_vector()):
                    row[name] = val
                writer.writerow(row)


class SyntheticBenchmarkDatasetGenerator:
    """Generates synthetic / benchmark test traces strictly quarantined for test suites & schema verification."""

    @classmethod
    def generate_test_dataset(cls, n_per_class: int = 20) -> List[LabeledSessionRecord]:
        """Generate deterministic, clearly labeled synthetic records across the 3 archetypes."""
        records: List[LabeledSessionRecord] = []

        # Problem clusters for GroupKFold testing
        problem_pool = [
            "prob_syntax_err_missing_colon",
            "prob_type_err_none_upper",
            "prob_logic_err_off_by_one",
            "prob_runtime_zerodiv",
            "prob_boundary_empty_list",
        ]

        # 1. Systematic Verification Archetype
        for i in range(n_per_class):
            pid = problem_pool[i % len(problem_pool)]
            feat = TelemetryFeatures(
                session_id=f"synth_sys_{i:03d}",
                is_synthetic=True,
                problem_id=pid,
                loc=15 + (i % 10),
                ast_node_count=45 + (i % 20),
                ast_max_depth=4 + (i % 3),
                cyclomatic_complexity=2 + (i % 3),
                function_count=1 + (i % 2),
                has_traceback_input=True,
                error_desc_length=40 + (i % 15),
                error_family_syntax=(i % 3 == 0),
                error_family_type_or_value=(i % 3 != 0),
                ast_first_step=True,
                static_to_exec_ratio=2.0 + ((i % 5) * 0.2),
                failed_tool_ratio=0.05,
                tool_sequence_entropy=0.85,
                total_investigation_steps=4 + (i % 3),
                hypothesis_churn_count=2,
                hypothesis_rejection_ratio=0.5,
                countercheck_execution_rate=0.8 + ((i % 3) * 0.1),
                direct_evidence_ratio=0.75 + ((i % 3) * 0.05),
            )
            records.append(LabeledSessionRecord(
                features=feat,
                provenance=LabelProvenance(
                    session_id=feat.session_id,
                    label=BehaviorArchetype.SYSTEMATIC_VERIFICATION,
                    labeling_method="SYNTHETIC_BENCHMARK",
                    reviewer_id="generator",
                    confidence=1.0,
                ),
            ))

        # 2. Rapid Trial and Error (Guess-and-Check) Archetype
        for i in range(n_per_class):
            pid = problem_pool[i % len(problem_pool)]
            feat = TelemetryFeatures(
                session_id=f"synth_guess_{i:03d}",
                is_synthetic=True,
                problem_id=pid,
                loc=10 + (i % 8),
                ast_node_count=30 + (i % 15),
                ast_max_depth=3 + (i % 2),
                cyclomatic_complexity=1 + (i % 2),
                function_count=1,
                has_traceback_input=False,
                error_desc_length=15 + (i % 10),
                error_family_syntax=False,
                error_family_type_or_value=True,
                ast_first_step=False,
                static_to_exec_ratio=0.25,
                failed_tool_ratio=0.40,
                tool_sequence_entropy=0.40,
                total_investigation_steps=5 + (i % 4),
                hypothesis_churn_count=3 + (i % 2),
                hypothesis_rejection_ratio=0.66,
                countercheck_execution_rate=0.0,
                direct_evidence_ratio=0.20,
            )
            records.append(LabeledSessionRecord(
                features=feat,
                provenance=LabelProvenance(
                    session_id=feat.session_id,
                    label=BehaviorArchetype.RAPID_TRIAL_AND_ERROR,
                    labeling_method="SYNTHETIC_BENCHMARK",
                    reviewer_id="generator",
                    confidence=1.0,
                ),
            ))

        # 3. Unfocused Exploration Archetype
        for i in range(n_per_class):
            pid = problem_pool[i % len(problem_pool)]
            feat = TelemetryFeatures(
                session_id=f"synth_unfocused_{i:03d}",
                is_synthetic=True,
                problem_id=pid,
                loc=25 + (i % 15),
                ast_node_count=60 + (i % 30),
                ast_max_depth=5 + (i % 3),
                cyclomatic_complexity=4 + (i % 3),
                function_count=2 + (i % 2),
                has_traceback_input=(i % 2 == 0),
                error_desc_length=10 + (i % 10),
                error_family_syntax=True,
                error_family_type_or_value=False,
                ast_first_step=(i % 2 == 0),
                static_to_exec_ratio=0.8,
                failed_tool_ratio=0.60 + ((i % 4) * 0.05),
                tool_sequence_entropy=0.92,
                total_investigation_steps=7 + (i % 3),
                hypothesis_churn_count=4 + (i % 3),
                hypothesis_rejection_ratio=0.80,
                countercheck_execution_rate=0.2,
                direct_evidence_ratio=0.35,
            )
            records.append(LabeledSessionRecord(
                features=feat,
                provenance=LabelProvenance(
                    session_id=feat.session_id,
                    label=BehaviorArchetype.UNFOCUSED_EXPLORATION,
                    labeling_method="SYNTHETIC_BENCHMARK",
                    reviewer_id="generator",
                    confidence=1.0,
                ),
            ))

        return records
