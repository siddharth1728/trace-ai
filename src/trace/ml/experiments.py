"""Comparative Experiment Runner for TRACE v0.4 (Stage v0.4-A Evaluation).

Performs strict, leakage-safe cross-validation comparisons across:
1. Majority Class Baseline
2. Documented Rule-Based Baseline
3. Logistic Regression (L2)
4. Decision Tree (max_depth=3)
5. Random Forest Classifier (n_estimators=50, max_depth=3)

Evaluates whether ML provides measurable advantage over deterministic rules before any model deployment.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from trace.ml.baselines import MajorityClassBaseline, RuleBasedBehaviorClassifier
from trace.ml.dataset import LabeledSessionRecord
from trace.ml.schemas import BehaviorArchetype, TelemetryFeatures, utc_now


class ModelMetrics(BaseModel):
    """Evaluation metrics for a single model across cross-validation folds."""
    model_name: str
    macro_precision: float
    macro_recall: float
    macro_f1: float
    accuracy: float
    fold_f1_scores: List[float]
    fold_f1_std: float  # Stability metric
    confusion_matrix_data: List[List[int]]
    classes: List[str]


class GateEvaluationReport(BaseModel):
    """Formal audit report determining whether v0.4-B ML progression is justified."""
    dataset_size: int
    num_folds: int
    baseline_rule_f1: float
    best_ml_model_name: str
    best_ml_model_f1: float
    improvement_over_rule_baseline: float
    is_gate_passed: bool
    gate_justification: str
    all_model_results: List[ModelMetrics]
    generated_at: str


class ExperimentRunner:
    """Runs leakage-safe, problem-disjoint cross-validation benchmarks across candidate models."""

    ARCHETYPES = [
        BehaviorArchetype.SYSTEMATIC_VERIFICATION.value,
        BehaviorArchetype.RAPID_TRIAL_AND_ERROR.value,
        BehaviorArchetype.UNFOCUSED_EXPLORATION.value,
    ]

    @classmethod
    def run_benchmark(
        cls,
        records: List[LabeledSessionRecord],
        n_splits: int = 5,
        random_state: int = 42,
    ) -> GateEvaluationReport:
        """Execute full comparative benchmark and generate gate evaluation report."""
        if len(records) < 15:
            raise ValueError(f"Insufficient samples ({len(records)}) to run 5-fold cross-validation. Minimum 15 required.")

        X_feats = [r.features for r in records]
        X = np.array([f.to_feature_vector() for f in X_feats])
        y = np.array([r.provenance.label.value if hasattr(r.provenance.label, "value") else str(r.provenance.label) for r in records])
        groups = np.array([r.features.problem_id or "default" for r in records])

        # Choose splitting strategy: GroupKFold if >= n_splits unique problem groups, else StratifiedKFold
        unique_groups = len(set(groups))
        if unique_groups >= n_splits:
            splitter = GroupKFold(n_splits=n_splits)
            splits = list(splitter.split(X, y, groups))
        else:
            splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
            splits = list(splitter.split(X, y))

        results: List[ModelMetrics] = []

        # 1. Majority Class Baseline
        results.append(cls._eval_majority_baseline(X, y, splits))

        # 2. Rule-Based Classifier Baseline
        results.append(cls._eval_rule_baseline(X_feats, y, splits))

        # 3. Logistic Regression
        results.append(cls._eval_sklearn_pipeline(
            name="Logistic Regression (L2)",
            model=LogisticRegression(C=1.0, max_iter=500, random_state=random_state),
            X=X,
            y=y,
            splits=splits,
        ))

        # 4. Decision Tree
        results.append(cls._eval_sklearn_pipeline(
            name="Decision Tree (d=3)",
            model=DecisionTreeClassifier(max_depth=3, random_state=random_state),
            X=X,
            y=y,
            splits=splits,
        ))

        # 5. Random Forest
        results.append(cls._eval_sklearn_pipeline(
            name="Random Forest (n=50, d=3)",
            model=RandomForestClassifier(n_estimators=50, max_depth=3, random_state=random_state),
            X=X,
            y=y,
            splits=splits,
        ))

        # Evaluate Gate Criteria
        rule_res = next(r for r in results if r.model_name == "Rule-Based Baseline")
        ml_candidates = [r for r in results if "Baseline" not in r.model_name]
        best_ml = max(ml_candidates, key=lambda m: m.macro_f1)

        delta = round(best_ml.macro_f1 - rule_res.macro_f1, 4)
        is_passed = (delta >= 0.05) and (best_ml.fold_f1_std <= 0.12)

        if is_passed:
            justification = (
                f"GATE PASSED: {best_ml.model_name} achieved Macro-F1 of {best_ml.macro_f1:.3f} "
                f"(+{delta * 100:.1f}% over Rule Baseline {rule_res.macro_f1:.3f}) with cross-fold stability sigma={best_ml.fold_f1_std:.3f}."
            )
        else:
            justification = (
                f"GATE NOT MET: Best ML model ({best_ml.model_name}, F1={best_ml.macro_f1:.3f}) did not achieve required +5% Macro-F1 improvement "
                f"over Rule Baseline ({rule_res.macro_f1:.3f}, delta={delta * 100:+.1f}%) or exhibited unstable cross-fold variance (sigma={best_ml.fold_f1_std:.3f}). "
                f"Recommend retaining deterministic behavioral analytics."
            )

        return GateEvaluationReport(
            dataset_size=len(records),
            num_folds=n_splits,
            baseline_rule_f1=rule_res.macro_f1,
            best_ml_model_name=best_ml.model_name,
            best_ml_model_f1=best_ml.macro_f1,
            improvement_over_rule_baseline=delta,
            is_gate_passed=is_passed,
            gate_justification=justification,
            all_model_results=results,
            generated_at=utc_now().isoformat(),
        )

    @classmethod
    def _eval_majority_baseline(cls, X: np.ndarray, y: np.ndarray, splits: List[Any]) -> ModelMetrics:
        all_preds: List[str] = []
        all_trues: List[str] = []
        fold_f1s: List[float] = []

        for train_idx, test_idx in splits:
            y_train, y_test = y[train_idx], y[test_idx]
            clf = MajorityClassBaseline().fit(list(y_train))
            preds = clf.predict([list(row) for row in X[test_idx]])

            all_preds.extend(preds)
            all_trues.extend(list(y_test))
            fold_f1s.append(f1_score(y_test, preds, average="macro", zero_division=0))

        return cls._compile_metrics("Majority Class Baseline", all_trues, all_preds, fold_f1s)

    @classmethod
    def _eval_rule_baseline(cls, X_feats: List[TelemetryFeatures], y: np.ndarray, splits: List[Any]) -> ModelMetrics:
        all_preds: List[str] = []
        all_trues: List[str] = []
        fold_f1s: List[float] = []

        for _, test_idx in splits:
            test_feats = [X_feats[i] for i in test_idx]
            y_test = y[test_idx]
            preds = RuleBasedBehaviorClassifier.predict(test_feats)

            all_preds.extend(preds)
            all_trues.extend(list(y_test))
            fold_f1s.append(f1_score(y_test, preds, average="macro", zero_division=0))

        return cls._compile_metrics("Rule-Based Baseline", all_trues, all_preds, fold_f1s)

    @classmethod
    def _eval_sklearn_pipeline(
        cls,
        name: str,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        splits: List[Any],
    ) -> ModelMetrics:
        all_preds: List[str] = []
        all_trues: List[str] = []
        fold_f1s: List[float] = []

        for train_idx, test_idx in splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            pipeline = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", model),
            ])
            pipeline.fit(X_train, y_train)
            preds = pipeline.predict(X_test)

            all_preds.extend(list(preds))
            all_trues.extend(list(y_test))
            fold_f1s.append(f1_score(y_test, preds, average="macro", zero_division=0))

        return cls._compile_metrics(name, all_trues, all_preds, fold_f1s)

    @classmethod
    def _compile_metrics(
        cls,
        model_name: str,
        y_true: List[str],
        y_pred: List[str],
        fold_f1s: List[float],
    ) -> ModelMetrics:
        p_macro = precision_score(y_true, y_pred, average="macro", zero_division=0)
        r_macro = recall_score(y_true, y_pred, average="macro", zero_division=0)
        f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
        acc = float(np.mean(np.array(y_true) == np.array(y_pred)))
        f1_std = float(np.std(fold_f1s))

        cm = confusion_matrix(y_true, y_pred, labels=cls.ARCHETYPES)

        return ModelMetrics(
            model_name=model_name,
            macro_precision=round(float(p_macro), 4),
            macro_recall=round(float(r_macro), 4),
            macro_f1=round(float(f1_macro), 4),
            accuracy=round(acc, 4),
            fold_f1_scores=[round(float(s), 4) for s in fold_f1s],
            fold_f1_std=round(f1_std, 4),
            confusion_matrix_data=[[int(val) for val in row] for row in cm],
            classes=cls.ARCHETYPES,
        )
