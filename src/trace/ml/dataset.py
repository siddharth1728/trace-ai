"""Dataset Builder, Exporter, and Labeling Workflow for TRACE v0.4-A.

Strictly enforces:
1. Zero raw code in dataset exports (only structured numerical/categorical features).
2. Explicit REAL vs. SYNTHETIC data source segregation.
3. Transparent labeling workflow (rule-assisted proposals, human review, ambiguous handling).
4. Export to standard JSON and CSV tabular formats with version metadata.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from trace.ml.baselines import RuleBasedBehaviorClassifier
from trace.ml.schemas import (
    BehaviorArchetype,
    BehaviorLabelRecord,
    DataSourceType,
    FeatureVector,
    TelemetryRecord,
    utc_now,
)


class DatasetExporter:
    """Exports structured telemetry features and behavioral labels into clean tabular datasets."""

    @classmethod
    def to_records(
        cls,
        features: List[FeatureVector],
        labels: Optional[Dict[str, BehaviorLabelRecord]] = None,
        dataset_version: str = "v0.4-A",
    ) -> List[Dict[str, Any]]:
        """Assemble structured dataset records with feature columns and explicit provenance."""
        labels = labels or {}
        rows: List[Dict[str, Any]] = []

        for f in features:
            label_rec = labels.get(f.session_id)
            final_label = label_rec.final_label if label_rec else None
            proposed_label = label_rec.proposed_label if label_rec else None
            method = label_rec.labeling_method if label_rec else "UNLABELED"
            reviewer_status = label_rec.reviewer_status if label_rec else "UNREVIEWED"

            row = {
                "session_id": f.session_id,
                "data_source": f.data_source.value if hasattr(f.data_source, "value") else str(f.data_source),
                "problem_id": f.problem_id,
                # 18 Features
                "loc": f.loc,
                "ast_node_count": f.ast_node_count,
                "ast_max_depth": f.ast_max_depth,
                "cyclomatic_complexity": f.cyclomatic_complexity,
                "function_count": f.function_count,
                "has_traceback_input": int(f.has_traceback_input),
                "error_desc_length": f.error_desc_length,
                "error_family_syntax": int(f.error_family_syntax),
                "error_family_type_or_value": int(f.error_family_type_or_value),
                "ast_first_step": int(f.ast_first_step),
                "static_to_exec_ratio": f.static_to_exec_ratio,
                "failed_tool_ratio": f.failed_tool_ratio,
                "tool_sequence_entropy": f.tool_sequence_entropy,
                "total_investigation_steps": f.total_investigation_steps,
                "hypothesis_count": f.hypothesis_count,
                "hypothesis_rejection_ratio": f.hypothesis_rejection_ratio,
                "countercheck_execution_rate": f.countercheck_execution_rate,
                "direct_evidence_ratio": f.direct_evidence_ratio,
                # Labeling Metadata
                "label": final_label.value if hasattr(final_label, "value") else final_label,
                "proposed_label": proposed_label.value if hasattr(proposed_label, "value") else proposed_label,
                "labeling_method": method,
                "reviewer_status": reviewer_status,
                "dataset_version": dataset_version,
            }
            rows.append(row)

        return rows

    @classmethod
    def export_json(
        cls,
        features: List[FeatureVector],
        labels: Optional[Dict[str, BehaviorLabelRecord]] = None,
        dataset_version: str = "v0.4-A",
    ) -> str:
        """Export dataset as formatted JSON string."""
        records = cls.to_records(features, labels, dataset_version)
        return json.dumps({
            "version": dataset_version,
            "record_count": len(records),
            "created_at": utc_now().isoformat(),
            "data": records,
        }, indent=2)

    @classmethod
    def export_csv(
        cls,
        features: List[FeatureVector],
        labels: Optional[Dict[str, BehaviorLabelRecord]] = None,
        dataset_version: str = "v0.4-A",
    ) -> str:
        """Export dataset as CSV text."""
        records = cls.to_records(features, labels, dataset_version)
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()


class LabelingWorkflow:
    """Manages rule-assisted candidate label generation and expert reviewer confirmation."""

    @classmethod
    def propose_rule_labels(
        cls,
        features_list: List[FeatureVector],
        dataset_version: str = "v0.4-A",
    ) -> List[BehaviorLabelRecord]:
        """Generate rule-assisted candidate labels using the deterministic rule baseline."""
        labels: List[BehaviorLabelRecord] = []
        for f in features_list:
            archetype, conf, triggers = RuleBasedBehaviorClassifier.classify(f)
            labels.append(BehaviorLabelRecord(
                session_id=f.session_id,
                proposed_label=archetype,
                final_label=None,  # Remains unconfirmed until human review
                labeling_method="RULE_ASSISTED",
                reviewer_status="UNREVIEWED",
                reviewer_notes=f"Triggers: {'; '.join(triggers)}",
                confidence=conf,
                dataset_version=dataset_version,
                created_at=utc_now(),
                updated_at=utc_now(),
            ))
        return labels

    @classmethod
    def review_label(
        cls,
        label_record: BehaviorLabelRecord,
        confirmed_label: Optional[BehaviorArchetype] = None,
        reviewer_notes: Optional[str] = None,
        is_ambiguous: bool = False,
    ) -> BehaviorLabelRecord:
        """Apply human expert confirmation or mark session as ambiguous."""
        if is_ambiguous:
            label_record.reviewer_status = "AMBIGUOUS"
            label_record.final_label = None
            label_record.reviewer_notes = reviewer_notes or "Marked as ambiguous by reviewer"
        elif confirmed_label is not None:
            if confirmed_label == label_record.proposed_label:
                label_record.reviewer_status = "CONFIRMED"
            else:
                label_record.reviewer_status = "OVERRIDDEN"
            label_record.final_label = confirmed_label
            label_record.labeling_method = "MANUAL_EXPERT"
            if reviewer_notes:
                label_record.reviewer_notes = reviewer_notes
        label_record.updated_at = utc_now()
        return label_record


class SyntheticBenchmarkQuarantine:
    """Generates synthetic traces strictly marked with data_source=SYNTHETIC for pipeline testing and edge cases."""

    @classmethod
    def generate_benchmark_traces(cls, count_per_archetype: int = 5) -> List[Tuple[FeatureVector, BehaviorArchetype]]:
        """Generate controlled test vectors across the 4 experimental archetypes."""
        records: List[Tuple[FeatureVector, BehaviorArchetype]] = []

        for i in range(count_per_archetype):
            # 1. Systematic Verifier
            f_sys = FeatureVector(
                session_id=f"syn_sys_{i+1:03d}",
                data_source=DataSourceType.SYNTHETIC,
                problem_id=f"benchmark_prob_{i % 5}",
                loc=25 + i * 3,
                ast_node_count=120 + i * 15,
                ast_max_depth=4,
                cyclomatic_complexity=3,
                function_count=2,
                has_traceback_input=True,
                error_desc_length=150,
                error_family_syntax=False,
                error_family_type_or_value=True,
                ast_first_step=True,
                static_to_exec_ratio=2.5,
                failed_tool_ratio=0.0,
                tool_sequence_entropy=0.82,
                total_investigation_steps=5,
                hypothesis_count=2,
                hypothesis_rejection_ratio=0.5,
                countercheck_execution_rate=1.0,
                direct_evidence_ratio=0.8,
            )
            records.append((f_sys, BehaviorArchetype.SYSTEMATIC_VERIFIER))

            # 2. Blind Trial
            f_blind = FeatureVector(
                session_id=f"syn_blind_{i+1:03d}",
                data_source=DataSourceType.SYNTHETIC,
                problem_id=f"benchmark_prob_{i % 5}",
                loc=15 + i * 2,
                ast_node_count=80 + i * 10,
                ast_max_depth=3,
                cyclomatic_complexity=2,
                function_count=1,
                has_traceback_input=False,
                error_desc_length=20,
                error_family_syntax=False,
                error_family_type_or_value=False,
                ast_first_step=False,
                static_to_exec_ratio=0.2,
                failed_tool_ratio=0.60,
                tool_sequence_entropy=0.35,
                total_investigation_steps=6,
                hypothesis_count=3,
                hypothesis_rejection_ratio=0.0,
                countercheck_execution_rate=0.0,
                direct_evidence_ratio=0.2,
            )
            records.append((f_blind, BehaviorArchetype.BLIND_TRIAL))

            # 3. Symptom Fixated
            f_symp = FeatureVector(
                session_id=f"syn_symp_{i+1:03d}",
                data_source=DataSourceType.SYNTHETIC,
                problem_id=f"benchmark_prob_{i % 5}",
                loc=18 + i * 2,
                ast_node_count=90 + i * 8,
                ast_max_depth=3,
                cyclomatic_complexity=2,
                function_count=1,
                has_traceback_input=True,
                error_desc_length=80,
                error_family_syntax=False,
                error_family_type_or_value=True,
                ast_first_step=False,
                static_to_exec_ratio=0.8,
                failed_tool_ratio=0.15,
                tool_sequence_entropy=0.55,
                total_investigation_steps=4,
                hypothesis_count=1,
                hypothesis_rejection_ratio=0.0,
                countercheck_execution_rate=0.0,
                direct_evidence_ratio=0.5,
            )
            records.append((f_symp, BehaviorArchetype.SYMPTOM_FIXATED))

            # 4. Guess and Check
            f_guess = FeatureVector(
                session_id=f"syn_guess_{i+1:03d}",
                data_source=DataSourceType.SYNTHETIC,
                problem_id=f"benchmark_prob_{i % 5}",
                loc=20 + i * 2,
                ast_node_count=100 + i * 10,
                ast_max_depth=3,
                cyclomatic_complexity=2,
                function_count=1,
                has_traceback_input=False,
                error_desc_length=40,
                error_family_syntax=True,
                error_family_type_or_value=False,
                ast_first_step=False,
                static_to_exec_ratio=0.4,
                failed_tool_ratio=0.20,
                tool_sequence_entropy=0.60,
                total_investigation_steps=7,
                hypothesis_count=4,
                hypothesis_rejection_ratio=0.75,
                countercheck_execution_rate=0.0,
                direct_evidence_ratio=0.3,
            )
            records.append((f_guess, BehaviorArchetype.GUESS_AND_CHECK))

        return records


# Compatibility Aliases
DatasetAuditor = LabelingWorkflow
SyntheticBenchmarkDatasetGenerator = SyntheticBenchmarkQuarantine
