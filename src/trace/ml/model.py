"""Model Training, Serialization, and Inference Pipeline for TRACE v0.4."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from trace.ml.dataset import LabeledSessionRecord
from trace.ml.schemas import BehaviorArchetype, TelemetryFeatures, utc_now


class BehaviorClassifier:
    """Production Random Forest Behavior Classifier for TRACE v0.4."""

    ARCHETYPES = [
        BehaviorArchetype.SYSTEMATIC_VERIFICATION.value,
        BehaviorArchetype.RAPID_TRIAL_AND_ERROR.value,
        BehaviorArchetype.UNFOCUSED_EXPLORATION.value,
    ]

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 3,
        random_state: int = 42,
        version: str = "v0.4",
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.version = version

        self.pipeline: Optional[Pipeline] = None
        self.classes_: List[str] = list(self.ARCHETYPES)
        self.is_fitted: bool = False
        self.training_metadata: Dict[str, Any] = {}

    def fit(self, records: List[LabeledSessionRecord]) -> "BehaviorClassifier":
        """Fit the regularized Random Forest pipeline on labeled session records."""
        if not records:
            raise ValueError("Cannot fit BehaviorClassifier on empty records list.")

        X = np.array([r.features.to_feature_vector() for r in records])
        y = np.array([
            r.provenance.label.value if hasattr(r.provenance.label, "value") else str(r.provenance.label)
            for r in records
        ])

        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth,
                    random_state=self.random_state,
                    class_weight="balanced",
                ),
            ),
        ])

        self.pipeline.fit(X, y)
        self.is_fitted = True
        self.classes_ = list(self.pipeline.named_steps["rf"].classes_)

        self.training_metadata = {
            "n_samples": len(records),
            "version": self.version,
            "trained_at": utc_now().isoformat(),
            "classes": self.classes_,
        }
        return self

    def predict_proba(self, features: TelemetryFeatures) -> Dict[str, float]:
        """Return calibrated class probabilities for a single session telemetry record."""
        if not self.is_fitted or self.pipeline is None:
            # If not fitted, return uniform distribution
            return {arch: round(1.0 / len(self.classes_), 3) for arch in self.classes_}

        vec = np.array([features.to_feature_vector()])
        probs = self.pipeline.predict_proba(vec)[0]
        return {cls_name: round(float(prob), 3) for cls_name, prob in zip(self.classes_, probs)}

    def predict(self, features: TelemetryFeatures) -> Tuple[BehaviorArchetype, float]:
        """Predict the primary behavior archetype and associated model confidence."""
        probs = self.predict_proba(features)
        best_class = max(probs, key=probs.get)
        confidence = probs[best_class]

        return BehaviorArchetype(best_class), confidence

    def get_feature_importances(self) -> List[Tuple[str, float]]:
        """Return descending Mean Decrease in Impurity (GDI) feature importances."""
        if not self.is_fitted or self.pipeline is None:
            return []

        rf: RandomForestClassifier = self.pipeline.named_steps["rf"]
        importances = rf.feature_importances_
        names = TelemetryFeatures.feature_names()

        paired = list(zip(names, [round(float(imp), 4) for imp in importances]))
        return sorted(paired, key=lambda x: x[1], reverse=True)

    def save(self, model_dir: Path) -> None:
        """Serialize model artifact and metadata to disk."""
        model_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = model_dir / "behavior_classifier.joblib"
        metadata_path = model_dir / "metadata.json"

        joblib.dump(self.pipeline, artifact_path)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": self.version,
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "random_state": self.random_state,
                "classes": self.classes_,
                "is_fitted": self.is_fitted,
                "training_metadata": self.training_metadata,
            }, f, indent=2)

    @classmethod
    def load(cls, model_dir: Path) -> "BehaviorClassifier":
        """Load serialized model artifact and metadata from disk."""
        artifact_path = model_dir / "behavior_classifier.joblib"
        metadata_path = model_dir / "metadata.json"

        if not artifact_path.exists() or not metadata_path.exists():
            # Return fresh unfitted classifier
            return cls()

        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        instance = cls(
            n_estimators=meta.get("n_estimators", 50),
            max_depth=meta.get("max_depth", 3),
            random_state=meta.get("random_state", 42),
            version=meta.get("version", "v0.4"),
        )
        instance.pipeline = joblib.load(artifact_path)
        instance.classes_ = meta.get("classes", list(cls.ARCHETYPES))
        instance.is_fitted = meta.get("is_fitted", True)
        instance.training_metadata = meta.get("training_metadata", {})
        return instance
