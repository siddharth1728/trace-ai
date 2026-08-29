"""FastAPI Routes for Student Debugging Profile, Telemetry, and Behavior Intelligence."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from trace.db.session import get_db_session
from trace.ml.schemas import (
    StudentProfile,
    TelemetryFeatures,
)
from trace.services.profile_service import ProfileService

router = APIRouter(prefix="/api", tags=["profile"])
profile_service = ProfileService()


@router.get("/profile", response_model=StudentProfile)
async def get_student_profile(db: AsyncSession = Depends(get_db_session)):
    """Retrieve the aggregated student debugging profile (deterministic habits + AI detected patterns)."""
    return await profile_service.get_student_profile(db)


@router.get("/sessions/{session_id}/telemetry", response_model=TelemetryFeatures)
async def get_session_telemetry(session_id: str, db: AsyncSession = Depends(get_db_session)):
    """Retrieve the 18-feature telemetry vector extracted for a specific session."""
    from trace.db.repository import SessionRepository
    repo = SessionRepository(db)
    record = await repo.get_telemetry(session_id)
    if not record:
        # If not already extracted, attempt on-demand extraction
        sess = await repo.get_session(session_id)
        if not sess:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found")
        features, _ = await profile_service.process_and_save_session_telemetry(session_id, db)
        if not features:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed to extract telemetry")
        return features

    return TelemetryFeatures(
        session_id=record.session_id,
        data_source=record.data_source,
        problem_id=record.problem_id,
        loc=record.loc,
        ast_node_count=record.ast_node_count,
        ast_max_depth=record.ast_max_depth,
        cyclomatic_complexity=record.cyclomatic_complexity,
        function_count=record.function_count,
        has_traceback_input=record.has_traceback_input,
        error_desc_length=record.error_desc_length,
        error_family_syntax=record.error_family_syntax,
        error_family_type_or_value=record.error_family_type_or_value,
        ast_first_step=record.ast_first_step,
        static_to_exec_ratio=record.static_to_exec_ratio,
        failed_tool_ratio=record.failed_tool_ratio,
        tool_sequence_entropy=record.tool_sequence_entropy,
        total_investigation_steps=record.total_investigation_steps,
        hypothesis_count=record.hypothesis_count,
        hypothesis_rejection_ratio=record.hypothesis_rejection_ratio,
        countercheck_execution_rate=record.countercheck_execution_rate,
        direct_evidence_ratio=record.direct_evidence_ratio,
    )
