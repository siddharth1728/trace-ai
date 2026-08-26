"""Transparent Deterministic Baseline Classifiers for TRACE v0.4-A Experimental Taxonomy.

Defines:
1. RuleBasedBehaviorClassifier (Documented heuristic decision engine across 4 archetypes)
2. MajorityClassBaseline (Theoretical empirical baseline)

IMPORTANT: These archetypes and rules are experimental engineering baselines.
They must NOT be represented as scientifically validated psychological facts.
"""

from typing import Dict, List, Optional, Tuple
from collections import Counter

from trace.ml.schemas import (
    BehaviorArchetype,
    FeatureVector,
    TelemetryRecord,
)


class RuleBasedBehaviorClassifier:
    """Documented deterministic heuristic classifier used as a transparent experimental baseline."""

    @classmethod
    def classify(cls, features: FeatureVector) -> Tuple[BehaviorArchetype, float, List[str]]:
        """Classify a FeatureVector using explicit, documented threshold rules.
        
        Returns:
            (predicted_archetype, confidence, rule_triggers)
        """
        triggers: List[str] = []

        # Rule Set 1: SYSTEMATIC_VERIFIER
        # Characteristics: Static AST inspection before run, traceback context provided, counterchecks executed, direct evidence gathered
        is_systematic = (
            features.ast_first_step
            and features.countercheck_execution_rate > 0.0
            and features.failed_tool_ratio <= 0.25
        )
        if is_systematic:
            triggers.append("Static AST analysis preceded execution")
            triggers.append(f"Countercheck disproof rate: {features.countercheck_execution_rate:.2f}")
            triggers.append(f"Low tool failure rate: {features.failed_tool_ratio:.2f}")
            return BehaviorArchetype.SYSTEMATIC_VERIFIER, 0.90, triggers

        # Rule Set 2: BLIND_TRIAL
        # Characteristics: High failed tool ratio, high replanning, unfocused execution
        is_blind_trial = (
            features.failed_tool_ratio > 0.40
            or (not features.ast_first_step and features.countercheck_execution_rate == 0.0 and features.failed_tool_ratio > 0.25)
        )
        if is_blind_trial:
            triggers.append(f"High tool failure ratio ({features.failed_tool_ratio:.2f})")
            triggers.append("Missing static analysis before execution")
            triggers.append("No countercheck disproof attempted")
            return BehaviorArchetype.BLIND_TRIAL, 0.85, triggers

        # Rule Set 3: SYMPTOM_FIXATED
        # Characteristics: Relies solely on traceback/error description without AST depth analysis or hypothesis testing
        is_symptom_fixated = (
            features.has_traceback_input
            and not features.ast_first_step
            and features.hypothesis_rejection_ratio <= 0.2
            and features.countercheck_execution_rate == 0.0
        )
        if is_symptom_fixated:
            triggers.append("Provided traceback but skipped static AST inspection")
            triggers.append("Low hypothesis exploration / single-symptom fixation")
            triggers.append("No countercheck verification executed")
            return BehaviorArchetype.SYMPTOM_FIXATED, 0.80, triggers

        # Rule Set 4: GUESS_AND_CHECK (Default fallback for rapid execution churn)
        # Characteristics: Execution-heavy, high hypothesis churn, missing disproof rigor
        triggers.append("Rapid execution cycles without structured verification")
        triggers.append(f"Static-to-execution ratio: {features.static_to_exec_ratio:.2f}")
        return BehaviorArchetype.GUESS_AND_CHECK, 0.75, triggers

    @classmethod
    def predict_one(cls, features: FeatureVector) -> BehaviorArchetype:
        """Convenience method returning single archetype prediction."""
        archetype, _, _ = cls.classify(features)
        return archetype


class MajorityClassBaseline:
    """Trivial empirical baseline always predicting the most frequent training class."""

    def __init__(self):
        self.majority_class: Optional[BehaviorArchetype] = None

    def fit(self, y: List[BehaviorArchetype]) -> "MajorityClassBaseline":
        if not y:
            self.majority_class = BehaviorArchetype.GUESS_AND_CHECK
            return self
        counts = Counter(y)
        self.majority_class = counts.most_common(1)[0][0]
        return self

    def predict(self, X: List[FeatureVector]) -> List[BehaviorArchetype]:
        cls_val = self.majority_class or BehaviorArchetype.GUESS_AND_CHECK
        return [cls_val for _ in X]


def compute_deterministic_habits(features_list: List[FeatureVector]) -> "DeterministicHabitStats":
    """Compute aggregate habit metrics from a list of FeatureVector objects."""
    from trace.ml.schemas import DeterministicHabitStats
    if not features_list:
        return DeterministicHabitStats()

    n = len(features_list)
    ast_first_cnt = sum(1 for f in features_list if getattr(f, "ast_first_step", False))
    tb_cnt = sum(1 for f in features_list if getattr(f, "has_traceback_input", False))
    cc_cnt = sum(1 for f in features_list if getattr(f, "countercheck_execution_rate", 0.0) > 0.0)
    steps_sum = sum(getattr(f, "total_investigation_steps", 0) for f in features_list)
    hyp_sum = sum(getattr(f, "hypothesis_count", getattr(f, "hypothesis_churn_count", 0)) for f in features_list)
    tool_fail_sum = sum(getattr(f, "failed_tool_ratio", 0.0) for f in features_list)

    return DeterministicHabitStats(
        total_sessions=n,
        ast_first_rate=round(ast_first_cnt / n, 2),
        traceback_provided_rate=round(tb_cnt / n, 2),
        countercheck_rigor_rate=round(cc_cnt / n, 2),
        avg_investigation_steps=round(steps_sum / n, 2),
        avg_hypotheses_per_session=round(hyp_sum / n, 2),
        tool_failure_rate=round(tool_fail_sum / n, 2),
    )


def generate_deterministic_strengths_and_growth(habits: "DeterministicHabitStats") -> Tuple[List[str], List[str]]:
    """Derive pedagogical strengths and growth feedback from deterministic habit stats."""
    strengths: List[str] = []
    growth: List[str] = []

    if habits.ast_first_rate >= 0.6:
        strengths.append("Consistently begins investigation with static code structure analysis")
    else:
        growth.append("Consider reviewing abstract syntax trees before jumping to execution")

    if habits.traceback_provided_rate >= 0.5:
        strengths.append("Regularly provides contextual Python runtime tracebacks")
    else:
        growth.append("Providing complete error tracebacks improves debugging speed and accuracy")

    if habits.countercheck_rigor_rate >= 0.4:
        strengths.append("High verification rigor with targeted countercheck disproof attempts")
    else:
        growth.append("Practice testing hypotheses with deliberate counterexample inputs")

    if habits.tool_failure_rate <= 0.2:
        strengths.append("Reliable and disciplined tool usage during investigations")
    else:
        growth.append("High tool error rate suggests unfocused or speculative testing")

    return strengths, growth
