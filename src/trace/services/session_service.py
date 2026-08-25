"""Session Service coordinating agent runs, persistence, and event delivery."""

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from trace.agent.orchestrator import InvestigationOrchestrator
from trace.api.schemas import (
    CountercheckDTO,
    CreateSessionRequest,
    EvidenceDTO,
    FinalDiagnosisDTO,
    HypothesisDTO,
    ObservationDTO,
    PlanStepDTO,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummaryDTO,
)
from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.state import LifecycleState
from trace.db.models import SessionRecord
from trace.db.repository import SessionRepository
from trace.db.session import get_session_factory
from trace.llm.mock_provider import MockLLMProvider
from trace.llm.provider import LLMProviderFactory
from trace.services.event_broadcaster import global_broadcaster

# Set of active investigation session IDs to prevent duplicate concurrent runs
_ACTIVE_INVESTIGATIONS: set[str] = set()


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal."""
    cleaned = re.sub(r"[^\w\.-]", "_", Path(filename).name)
    return cleaned if cleaned.endswith(".py") else f"{cleaned}.py"


def map_session_record_to_detail(record: SessionRecord) -> SessionDetailResponse:
    """Convert database SessionRecord into typed API DTO."""
    diag_dto = None
    if record.likely_root_cause or record.problem_statement:
        diag_dto = FinalDiagnosisDTO(
            problem_statement=record.problem_statement,
            likely_root_cause=record.likely_root_cause,
            learning_point=record.learning_point,
            suggested_fix_guidance=record.suggested_fix_guidance,
            confidence=record.confidence,
            verified_hypothesis_id=record.verified_hypothesis_id,
            countercheck_summary=record.countercheck_summary,
            what_trace_checked=record.what_trace_checked,
            what_remains_uncertain=record.what_remains_uncertain,
            evidence_summary=record.evidence_summary,
        )

    plan_dtos = [
        PlanStepDTO(
            id=p.id,
            step_index=p.step_index,
            title=p.title,
            tool_name=p.tool_name,
            status=p.status,
            expected_outcome=p.expected_outcome,
            observation_id=p.observation_id,
        )
        for p in record.plan_steps
    ]

    obs_dtos = [
        ObservationDTO(
            id=o.id,
            step_index=o.step_index,
            tool_name=o.tool_name,
            summary=o.summary,
            is_success=o.is_success,
            input_args=o.input_args,
            output_data=o.output_data,
            evidence_tags=o.evidence_tags,
            created_at=o.created_at.isoformat() if o.created_at else "",
        )
        for o in record.observations
    ]

    ev_dtos = [
        EvidenceDTO(
            id=e.id,
            observation_id=e.observation_id,
            target_hypothesis_id=e.target_hypothesis_id,
            evidence_type=e.evidence_type,
            relation=e.relation,
            statement=e.statement,
            confidence_weight=e.confidence_weight,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in record.evidence
    ]

    hyp_dtos = [
        HypothesisDTO(
            id=h.id,
            statement=h.statement,
            status=h.status,
            confidence=h.confidence,
            rationale=h.rationale,
            supporting_evidence_ids=h.supporting_evidence_ids,
            counterexample_ids=h.counterexample_ids,
        )
        for h in record.hypotheses
    ]

    c_dtos = [
        CountercheckDTO(
            id=c.id,
            hypothesis_id=c.hypothesis_id,
            strategy=c.strategy,
            description=c.description,
            harness_code=c.harness_code,
            executed=c.executed,
            passed=c.passed,
            disproved=c.disproved,
            actual_output=c.actual_output,
        )
        for c in record.counterchecks
    ]

    return SessionDetailResponse(
        id=record.id,
        title=record.title,
        user_goal=record.user_goal,
        source_code=record.source_code,
        file_path=record.file_path,
        error_description=record.error_description,
        traceback_input=record.traceback_input,
        status=record.status,
        confidence=record.confidence,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
        diagnosis=diag_dto,
        plan_steps=plan_dtos,
        observations=obs_dtos,
        evidence=ev_dtos,
        hypotheses=hyp_dtos,
        counterchecks=c_dtos,
    )


class SessionService:
    """Business logic coordinator managing sessions, execution, and persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SessionRepository(db)

    async def create_session(self, request: CreateSessionRequest) -> SessionDetailResponse:
        """Create a new debugging session from text payload."""
        session_id = f"trace_sess_{uuid.uuid4().hex[:10]}"
        record = await self.repo.create_session(
            session_id=session_id,
            user_goal=request.user_goal,
            source_code=request.source_code,
            title=request.title,
            error_description=request.error_description,
            traceback_input=request.traceback_input,
        )
        return map_session_record_to_detail(record)

    async def create_session_from_upload(
        self,
        filename: str,
        content_bytes: bytes,
        user_goal: str,
        error_description: Optional[str] = None,
        traceback_input: Optional[str] = None,
    ) -> SessionDetailResponse:
        """Validate and create session from uploaded Python file."""
        if not filename.endswith(".py"):
            raise ValueError("Invalid file extension. Only .py Python files are supported.")

        if len(content_bytes) > 256 * 1024:
            raise ValueError("File exceeds maximum allowed size of 256 KB.")

        try:
            source_code = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            source_code = content_bytes.decode("latin-1")

        safe_name = sanitize_filename(filename)
        session_id = f"trace_sess_{uuid.uuid4().hex[:10]}"

        # Write uploaded content to isolated temp file
        temp_dir = Path(tempfile.gettempdir()) / "trace_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        target_path = temp_dir / f"{session_id}_{safe_name}"
        target_path.write_text(source_code, encoding="utf-8")

        record = await self.repo.create_session(
            session_id=session_id,
            user_goal=user_goal,
            source_code=source_code,
            file_path=str(target_path),
            title=f"Investigation: {safe_name}",
            error_description=error_description,
            traceback_input=traceback_input,
        )
        return map_session_record_to_detail(record)

    async def get_session(self, session_id: str) -> Optional[SessionDetailResponse]:
        """Fetch session snapshot."""
        record = await self.repo.get_session(session_id)
        if not record:
            return None
        return map_session_record_to_detail(record)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> SessionListResponse:
        """List sessions with metadata."""
        records = await self.repo.list_sessions(limit=limit, offset=offset)
        summaries = [
            SessionSummaryDTO(
                id=r.id,
                title=r.title,
                user_goal=r.user_goal,
                status=r.status,
                confidence=r.confidence,
                likely_root_cause=r.likely_root_cause,
                created_at=r.created_at.isoformat() if r.created_at else "",
                updated_at=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in records
        ]
        return SessionListResponse(sessions=summaries, total=len(summaries))

    async def delete_session(self, session_id: str) -> bool:
        """Delete session and its associated data."""
        return await self.repo.delete_session(session_id)

    async def start_investigation(
        self,
        session_id: str,
        provider_name: str = "mock",
        max_iterations: int = 8,
    ) -> None:
        """Launch background investigation task."""
        record = await self.repo.get_session(session_id)
        if not record:
            raise KeyError(f"Session '{session_id}' not found.")

        if session_id in _ACTIVE_INVESTIGATIONS or record.status == "RUNNING":
            raise RuntimeError(f"Investigation for session '{session_id}' is already running.")

        _ACTIVE_INVESTIGATIONS.add(session_id)
        await self.repo.update_session_status(session_id, "RUNNING")

        # Spawn non-blocking background task
        asyncio.create_task(
            self._run_investigation_in_background(
                session_id=session_id,
                source_code=record.source_code,
                user_goal=record.user_goal,
                error_description=record.error_description,
                traceback_input=record.traceback_input,
                file_path=record.file_path,
                provider_name=provider_name,
                max_iterations=max_iterations,
            )
        )

    async def _run_investigation_in_background(
        self,
        session_id: str,
        source_code: str,
        user_goal: str,
        error_description: Optional[str],
        traceback_input: Optional[str],
        file_path: Optional[str],
        provider_name: str,
        max_iterations: int,
    ) -> None:
        """Execute the pure Python agent orchestrator in a background thread."""
        try:
            provider = MockLLMProvider() if provider_name == "mock" else LLMProviderFactory.create()
            orchestrator = InvestigationOrchestrator(provider=provider)

            # Run in worker thread to avoid blocking asyncio event loop
            state = await asyncio.to_thread(
                orchestrator.investigate,
                source_code=source_code,
                user_goal=user_goal,
                error_description=error_description,
                traceback_input=traceback_input,
                file_path=file_path,
                max_iterations=max_iterations,
            )

            # Persist state back to SQLite database using a fresh DB session
            factory = get_session_factory()
            async with factory() as db_session:
                repo = SessionRepository(db_session)
                await repo.save_full_agent_state(session_id, state)
                await repo.add_session_event(
                    session_id=session_id,
                    event_type="SESSION_COMPLETED",
                    payload={"status": "COMPLETED", "confidence": state.confidence},
                )
                try:
                    from trace.services.profile_service import ProfileService
                    profile_svc = ProfileService()
                    await profile_svc.process_and_save_session_telemetry(session_id, db_session)
                except Exception:
                    pass

            # Publish completed event
            global_event_bus.publish(
                TraceEvent(
                    session_id=session_id,
                    event_type=EventType.SESSION_COMPLETED,
                    payload={"status": "COMPLETED", "confidence": state.confidence},
                    message="Investigation successfully completed.",
                )
            )
        except Exception as exc:
            # Handle failure
            factory = get_session_factory()
            async with factory() as db_session:
                repo = SessionRepository(db_session)
                await repo.update_session_status(session_id, "FAILED")
                await repo.add_session_event(
                    session_id=session_id,
                    event_type="SESSION_FAILED",
                    payload={"error": str(exc)},
                )
            global_event_bus.publish(
                TraceEvent(
                    session_id=session_id,
                    event_type=EventType.SESSION_FAILED,
                    payload={"error": str(exc)},
                    message=f"Investigation failed: {str(exc)}",
                )
            )
        finally:
            _ACTIVE_INVESTIGATIONS.discard(session_id)
