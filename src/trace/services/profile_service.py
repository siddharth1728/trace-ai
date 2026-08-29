"""Profile Service for TRACE v1.0: aggregates deterministic habits."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from trace.db.repository import SessionRepository
from trace.ml.baselines import (
    compute_deterministic_habits,
    generate_deterministic_strengths_and_growth,
)
from trace.ml.schemas import (
    DeterministicHabitStats,
    StudentProfile,
    TelemetryFeatures,
    utc_now,
)
from trace.ml.telemetry import TelemetryExtractor


class ProfileService:
    """Service for managing student debugging profiles and telemetry extraction."""

    def __init__(self, model_dir: Optional[Path] = None):
        pass

    async def get_student_profile(self, db_session: AsyncSession) -> StudentProfile:
        """Aggregate all recorded session telemetry into a deterministic student debugging profile."""
        repo = SessionRepository(db_session)
        records = await repo.list_all_telemetry()

        if not records:
            empty_habits = DeterministicHabitStats()
            strengths, growth = generate_deterministic_strengths_and_growth(empty_habits)
            return StudentProfile(
                deterministic_habits=empty_habits,
                key_strengths=strengths,
                growth_areas=growth,
                updated_at=utc_now().isoformat(),
            )

        # Convert DB telemetry records into TelemetryFeatures
        feats_list: List[TelemetryFeatures] = []
        for r in records:
            feats_list.append(TelemetryFeatures(
                session_id=r.session_id,
                data_source=r.data_source,
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
                hypothesis_count=r.hypothesis_count,
                hypothesis_rejection_ratio=r.hypothesis_rejection_ratio,
                countercheck_execution_rate=r.countercheck_execution_rate,
                direct_evidence_ratio=r.direct_evidence_ratio,
            ))

        # Compute Deterministic Habits (Factual Math)
        habits = compute_deterministic_habits(feats_list)
        strengths, growth = generate_deterministic_strengths_and_growth(habits)

        return StudentProfile(
            deterministic_habits=habits,
            key_strengths=strengths,
            growth_areas=growth,
            updated_at=utc_now().isoformat(),
        )

    async def process_and_save_session_telemetry(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> Tuple[Optional[TelemetryFeatures], None]:
        """Extract 18-feature telemetry for a completed session."""
        repo = SessionRepository(db_session)
        session_record = await repo.get_session(session_id)
        if not session_record:
            return None, None

        # Extract 18 Features
        from trace.ml.schemas import DataSourceType
        telemetry = TelemetryExtractor.extract_telemetry_record(
            session_record,
            problem_id=session_record.file_path or (session_record.title[:30] if session_record.title else "default"),
            data_source=DataSourceType.REAL,
        )
        features = TelemetryExtractor.extract_feature_vector(telemetry)

        # Persist Telemetry
        await repo.save_telemetry(
            session_id=session_id,
            features_dict=features.model_dump(),
            is_synthetic=False,
            problem_id=features.problem_id or "default",
        )

        return features, None

