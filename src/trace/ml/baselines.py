"""Deterministic Statistical Profiler and Rule-Based Baselines for TRACE v0.4.

Provides:
1. 100% Deterministic Habit Statistics (Factual percentages with zero ML).
2. Majority Class Dummy Baseline.
3. Explicit, Documented Rule-Based Behavior Classifier.
4. Grounded Pedagogical Strengths & Growth Area generator.
"""

from collections import Counter
from typing import Dict, List, Optional, Tuple

from trace.ml.schemas import (
    BehaviorArchetype,
    DeterministicHabitStats,
    TelemetryFeatures,
)


def compute_deterministic_habits(telemetry_list: List[TelemetryFeatures]) -> DeterministicHabitStats:
    """Calculate mathematically exact debugging habit statistics across a list of session telemetry items."""
    if not telemetry_list:
        return DeterministicHabitStats()

    total = len(telemetry_list)
    ast_first_count = sum(1 for t in telemetry_list if t.ast_first_step)
    tb_count = sum(1 for t in telemetry_list if t.has_traceback_input)
    countercheck_count = sum(1 for t in telemetry_list if t.countercheck_execution_rate > 0.0)

    total_steps = sum(t.total_investigation_steps for t in telemetry_list)
    total_hyps = sum(t.hypothesis_churn_count for t in telemetry_list)
    total_failures = sum(t.failed_tool_ratio for t in telemetry_list)

    return DeterministicHabitStats(
        total_sessions=total,
        ast_first_rate=round((ast_first_count / total) * 100, 1),
        traceback_provided_rate=round((tb_count / total) * 100, 1),
        countercheck_rigor_rate=round((countercheck_count / total) * 100, 1),
        avg_investigation_steps=round(total_steps / total, 1),
        avg_hypotheses_per_session=round(total_hyps / total, 1),
        tool_failure_rate=round((total_failures / total) * 100, 1),
    )


def generate_deterministic_strengths_and_growth(
    habits: DeterministicHabitStats,
) -> Tuple[List[str], List[str]]:
    """Derive grounded strengths and growth areas strictly from mathematical habit statistics."""
    strengths: List[str] = []
    growth_areas: List[str] = []

    if habits.total_sessions == 0:
        return (
            ["Begin debugging investigations in the studio to build your profile."],
            ["Practice inspecting stack traces and verifying code with AST tools."],
        )

    # Evaluate Strengths
    if habits.ast_first_rate >= 70.0:
        strengths.append(f"Strong static audit discipline: AST static analysis performed first in {habits.ast_first_rate}% of sessions.")
    if habits.traceback_provided_rate >= 60.0:
        strengths.append(f"Consistent error framing: Python tracebacks provided in {habits.traceback_provided_rate}% of investigations.")
    if habits.countercheck_rigor_rate >= 50.0:
        strengths.append(f"Grounded falsification: Disproof counterchecks executed in {habits.countercheck_rigor_rate}% of sessions.")
    if habits.tool_failure_rate <= 15.0:
        strengths.append("High tool precision: Low rate of failed tool executions.")

    if not strengths:
        strengths.append("Active debugging engagement: Consistently submitting code and error context for investigation.")

    # Evaluate Growth Areas
    if habits.ast_first_rate < 50.0:
        growth_areas.append(f"Inspect AST static structure before running code (currently {habits.ast_first_rate}%).")
    if habits.countercheck_rigor_rate < 40.0:
        growth_areas.append(f"Formulate explicit disproof tests before accepting a diagnosis (countercheck rate: {habits.countercheck_rigor_rate}%).")
    if habits.traceback_provided_rate < 40.0:
        growth_areas.append("Include Python stack traces when available to narrow the root cause search space.")
    if habits.tool_failure_rate > 30.0:
        growth_areas.append(f"High tool error rate ({habits.tool_failure_rate}%): verify syntax and file paths before running investigations.")

    if not growth_areas:
        growth_areas.append("Maintain your systematic debugging cadence across more complex multi-function algorithms.")

    return strengths, growth_areas


class MajorityClassBaseline:
    """Baseline A: Predicts the most frequent class in training data."""

    def __init__(self):
        self.majority_class: str = BehaviorArchetype.SYSTEMATIC_VERIFICATION.value

    def fit(self, y: List[str]) -> "MajorityClassBaseline":
        if y:
            counts = Counter(y)
            self.majority_class = counts.most_common(1)[0][0]
        return self

    def predict(self, X: List[List[float]]) -> List[str]:
        return [self.majority_class] * len(X)


class RuleBasedBehaviorClassifier:
    """Baseline B: Explicit, documented deterministic heuristic classifier."""

    @classmethod
    def predict_one(cls, row: TelemetryFeatures) -> BehaviorArchetype:
        """Classify a single telemetry feature record using documented decision rules."""
        # Rule 1: Systematic Verification
        # High static audit, disproof countercheck executed, traceback present or high direct evidence
        if (
            row.ast_first_step
            and row.countercheck_execution_rate >= 0.4
            and (row.has_traceback_input or row.direct_evidence_ratio >= 0.5)
            and row.failed_tool_ratio <= 0.35
        ):
            return BehaviorArchetype.SYSTEMATIC_VERIFICATION

        # Rule 2: Rapid Trial and Error (Guess-and-Check)
        # Execution-heavy, low static analysis, zero or minimal counterchecks
        if (
            (row.static_to_exec_ratio <= 0.5 or not row.ast_first_step)
            and row.countercheck_execution_rate == 0.0
            and row.hypothesis_churn_count >= 1
        ):
            return BehaviorArchetype.RAPID_TRIAL_AND_ERROR

        # Rule 3: Unfocused Exploration (Fallback)
        # High tool failure rate, high entropy, or missing structured cadence
        return BehaviorArchetype.UNFOCUSED_EXPLORATION

    @classmethod
    def predict(cls, features_list: List[TelemetryFeatures]) -> List[str]:
        """Classify a list of telemetry records."""
        return [cls.predict_one(feat).value for feat in features_list]
