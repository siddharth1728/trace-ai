"""Profile Service for TRACE v0.4: aggregates deterministic habits and manages behavior predictions."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from trace.db.repository import SessionRepository
from trace.ml.baselines import (
    compute_deterministic_habits,
    generate_deterministic_strengths_and_growth,
    RuleBasedBehaviorClassifier,
)
from trace.ml.explainer import BehaviorExplainer
from trace.ml.model import BehaviorClassifier
from trace.ml.schemas import (
    BehaviorArchetype,
    BehaviorPrediction,
    DeterministicHabitStats,
    FeatureContribution,
    StudentProfile,
    TelemetryFeatures,
    utc_now,
)
from trace.ml.telemetry import TelemetryExtractor


class ProfileService:
    """Service for managing student debugging profiles, telemetry extraction, and behavioral predictions."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or Path("models/v0.4")
        self.classifier = BehaviorClassifier.load(self.model_dir)

    async def get_student_profile(self, db_session: AsyncSession) -> StudentProfile:
        """Aggregate all recorded session telemetry into a comprehensive student debugging profile."""
        repo = SessionRepository(db_session)
        records = await repo.list_all_telemetry(include_synthetic=True)

        if not records:
            empty_habits = DeterministicHabitStats()
            strengths, growth = generate_deterministic_strengths_and_growth(empty_habits)
            return StudentProfile(
                deterministic_habits=empty_habits,
                latest_prediction=None,
                archetype_history={},
                key_strengths=strengths,
                growth_areas=growth,
                updated_at=utc_now(),
            )

        # Convert DB telemetry records into TelemetryFeatures
        feats_list: List[TelemetryFeatures] = []
        for r in records:
            feats_list.append(TelemetryFeatures(
                session_id=r.session_id,
                is_synthetic=r.is_synthetic,
                problem_id=r.problem_id,
                loc=r.loc,
                ast_node_count=r.ast_node_count,
                ast_max_depth=r.ast_max_depth,
                cyclomatic_complexity=r.cyclomatic_complexity,
                function_count=r.function_count,
                has_traceback_input=r.has_traceback_input,
                error_desc_length=r.error_desc_length,
                error_family_syntax=r.error_family_syntax,
                error_family_type_or_value=r.error_family_type_or_value,
                ast_first_step=r.ast_first_step,
                static_to_exec_ratio=r.static_to_exec_ratio,
                failed_tool_ratio=r.failed_tool_ratio,
                tool_sequence_entropy=r.tool_sequence_entropy,
                total_investigation_steps=r.total_investigation_steps,
                hypothesis_churn_count=r.hypothesis_churn_count,
                hypothesis_rejection_ratio=r.hypothesis_rejection_ratio,
                countercheck_execution_rate=r.countercheck_execution_rate,
                direct_evidence_ratio=r.direct_evidence_ratio,
            ))

        # 1. Compute Deterministic Habits (Factual Math)
        habits = compute_deterministic_habits(feats_list)
        strengths, growth = generate_deterministic_strengths_and_growth(habits)

        # 2. Retrieve Archetype Predictions
        recent_preds = await repo.list_recent_predictions(limit=50)
        archetype_history: Dict[str, int] = {}
        for p in recent_preds:
            archetype_history[p.predicted_archetype] = archetype_history.get(p.predicted_archetype, 0) + 1

        # 3. Latest Prediction
        latest_prediction: Optional[BehaviorPrediction] = None
        if recent_preds:
            p_rec = recent_preds[0]
            top_factors = [FeatureContribution(**f) for f in p_rec.top_factors] if p_rec.top_factors else []
            latest_prediction = BehaviorPrediction(
                session_id=p_rec.session_id,
                predicted_archetype=BehaviorArchetype(p_rec.predicted_archetype),
                confidence=p_rec.confidence,
                top_contributing_factors=top_factors,
                pedagogical_explanation=p_rec.pedagogical_explanation,
                model_type=p_rec.model_type,
                model_version=p_rec.model_version,
                created_at=p_rec.created_at,
            )
        elif feats_list:
            # Predict for most recent session if not already stored
            latest_feat = feats_list[0]
            latest_prediction = self._classify_features(latest_feat)

        return StudentProfile(
            deterministic_habits=habits,
            latest_prediction=latest_prediction,
            archetype_history=archetype_history,
            key_strengths=strengths,
            growth_areas=growth,
            updated_at=utc_now(),
        )

    async def process_and_save_session_telemetry(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> Tuple[Optional[TelemetryFeatures], Optional[BehaviorPrediction]]:
        """Extract 18-feature telemetry and behavior prediction for a completed session."""
        repo = SessionRepository(db_session)
        session_record = await repo.get_session(session_id)
        if not session_record:
            return None, None

        # 1. Extract 18 Features
        features = TelemetryExtractor.extract_from_session_record(
            session_record,
            problem_id=session_record.file_path or (session_record.title[:30] if session_record.title else "default"),
            is_synthetic=False,
        )

        # 2. Persist Telemetry
        await repo.save_telemetry(
            session_id=session_id,
            features_dict=features.model_dump(),
            is_synthetic=False,
            problem_id=features.problem_id or "default",
        )

        # 3. Classify Behavior & Generate Explanation
        prediction = self._classify_features(features)

        # 4. Persist Prediction
        pred_id = f"pred_{uuid.uuid4().hex[:8]}"
        await repo.save_prediction(
            prediction_id=pred_id,
            session_id=session_id,
            predicted_archetype=prediction.predicted_archetype.value,
            confidence=prediction.confidence,
            top_factors=[f.model_dump() for f in prediction.top_contributing_factors],
            pedagogical_explanation=prediction.pedagogical_explanation,
            model_type=prediction.model_type,
            model_version=prediction.model_version,
        )

        return features, prediction

    def _classify_features(self, features: TelemetryFeatures) -> BehaviorPrediction:
        """Classify features using Random Forest if fitted, otherwise fallback to Rule Baseline."""
        if self.classifier.is_fitted:
            archetype, conf = self.classifier.predict(features)
            top_factors, explanation = BehaviorExplainer.explain(features, archetype, conf, self.classifier)
            model_type = "RandomForest"
        else:
            archetype = RuleBasedBehaviorClassifier.predict_one(features)
            conf = 0.85
            top_factors, explanation = BehaviorExplainer.explain(features, archetype, conf)
            model_type = "RuleBaseline"

        return BehaviorPrediction(
            session_id=features.session_id,
            predicted_archetype=archetype,
            confidence=conf,
            top_contributing_factors=top_factors,
            pedagogical_explanation=explanation,
            model_type=model_type,
            model_version="v0.4",
            created_at=utc_now(),
        )
