"""Explainability and Pedagogical Explanation Engine for TRACE v0.4."""

from typing import List, Optional, Tuple
from trace.ml.model import BehaviorClassifier
from trace.ml.schemas import BehaviorArchetype, FeatureContribution, TelemetryFeatures


class BehaviorExplainer:
    """Translates model predictions and telemetry features into evidence-grounded pedagogical explanations."""

    @classmethod
    def explain(
        cls,
        features: TelemetryFeatures,
        predicted_archetype: BehaviorArchetype,
        confidence: float,
        classifier: Optional[BehaviorClassifier] = None,
    ) -> Tuple[List[FeatureContribution], str]:
        """Generate top contributing feature attributions and a natural-language pedagogical explanation."""
        contributions: List[FeatureContribution] = []

        # 1. Feature Attribution Extraction
        # Evaluate primary behavioral signals
        if features.ast_first_step:
            contributions.append(FeatureContribution(
                feature_name="ast_first_step",
                feature_value=1.0,
                contribution_weight=0.25,
                description="AST static analysis executed before code run",
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name="ast_first_step",
                feature_value=0.0,
                contribution_weight=-0.20,
                description="Code execution attempted before static AST inspection",
            ))

        if features.countercheck_execution_rate > 0.0:
            contributions.append(FeatureContribution(
                feature_name="countercheck_execution_rate",
                feature_value=features.countercheck_execution_rate,
                contribution_weight=0.30,
                description=f"Countercheck disproof rate of {int(features.countercheck_execution_rate * 100)}% across candidate hypotheses",
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name="countercheck_execution_rate",
                feature_value=0.0,
                contribution_weight=-0.25,
                description="Zero countercheck disproof experiments executed before confirming root cause",
            ))

        contributions.append(FeatureContribution(
            feature_name="static_to_exec_ratio",
            feature_value=features.static_to_exec_ratio,
            contribution_weight=0.20 if features.static_to_exec_ratio >= 1.0 else -0.15,
            description=f"Static-to-execution tool call balance ratio of {features.static_to_exec_ratio:.2f}",
        ))

        if features.has_traceback_input:
            contributions.append(FeatureContribution(
                feature_name="has_traceback_input",
                feature_value=1.0,
                contribution_weight=0.15,
                description="Python stack trace provided to frame exception scope",
            ))

        if features.failed_tool_ratio > 0.25:
            contributions.append(FeatureContribution(
                feature_name="failed_tool_ratio",
                feature_value=features.failed_tool_ratio,
                contribution_weight=-0.20,
                description=f"High tool execution failure rate ({int(features.failed_tool_ratio * 100)}%)",
            ))

        # Sort contributions by absolute weight
        contributions.sort(key=lambda x: abs(x.contribution_weight), reverse=True)
        top_factors = contributions[:4]

        # 2. Pedagogical Natural-Language Synthesis
        explanation = cls._synthesize_pedagogical_text(predicted_archetype, confidence, features)

        return top_factors, explanation

    @classmethod
    def _synthesize_pedagogical_text(
        cls,
        archetype: BehaviorArchetype,
        confidence: float,
        features: TelemetryFeatures,
    ) -> str:
        conf_pct = int(confidence * 100)

        if archetype == BehaviorArchetype.SYSTEMATIC_VERIFICATION:
            return (
                f"TRACE identified a Systematic Verification debugging cadence ({conf_pct}% confidence). "
                f"You inspected the AST static structure before running code, provided error context, "
                f"and validated hypotheses with countercheck disproof testing."
            )
        elif archetype == BehaviorArchetype.RAPID_TRIAL_AND_ERROR:
            return (
                f"TRACE identified a Rapid Trial-and-Error debugging pattern ({conf_pct}% confidence). "
                f"Multiple sandbox executions occurred before inspecting AST structure, with zero disproof experiments. "
                f"Recommendation: Inspect syntax trees and formulate an explicit falsification check before executing code modifications."
            )
        else:  # UNFOCUSED_EXPLORATION
            return (
                f"TRACE identified an Unfocused Exploration debugging pattern ({conf_pct}% confidence). "
                f"Investigation had a higher rate of failed tool executions ({int(features.failed_tool_ratio * 100)}%) or hypothesis churn. "
                f"Recommendation: Review the raw Python traceback to isolate the exact line and exception frame before testing hypotheses."
            )
