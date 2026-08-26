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

from trace.agent.diff_engine import CodeDiffEngine
from trace.agent.orchestrator import InvestigationOrchestrator
from trace.api.schemas import (
    AnswerSocraticRequest,
    CodeRevisionDTO,
    CountercheckDTO,
    CreateCodeRevisionRequest,
    CreateSessionRequest,
    CreateStudentHypothesisRequest,
    CreateStudentTestInputRequest,
    EvidenceDTO,
    FinalDiagnosisDTO,
    HypothesisDTO,
    InteractiveTimelineResponse,
    InteractionTurnDTO,
    ObservationDTO,
    PlanStepDTO,
    RevisionsListResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummaryDTO,
    SocraticPromptDTO,
    StudentActivitySummaryDTO,
    StudentHypothesisDTO,
    StudentTestExecutionResponse,
    StudentTestInputDTO,
)
from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.state import LifecycleState
from trace.db.models import SessionRecord
from trace.db.repository import SessionRepository
from trace.db.session import get_session_factory
from trace.llm.mock_provider import MockLLMProvider
from trace.llm.provider import LLMProviderFactory
from trace.services.event_broadcaster import global_broadcaster
from trace.tools.executor import PythonExecutorTool

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

    # Milestone v0.5 Interactive Student Artifacts
    shyp_dtos = [
        StudentHypothesisDTO(
            id=sh.id,
            turn_number=sh.turn_number,
            hypothesis_text=sh.hypothesis_text,
            target_function_or_line=sh.target_function_or_line,
            student_confidence=sh.student_confidence,
            status=sh.status,
            evaluation_observation_id=sh.evaluation_observation_id,
            created_at=sh.created_at.isoformat() if sh.created_at else "",
        )
        for sh in getattr(record, "student_hypotheses", [])
    ]

    rev_dtos = [
        CodeRevisionDTO(
            id=rev.id,
            revision_number=rev.revision_number,
            source_code=rev.source_code,
            intent_notes=rev.intent_notes,
            time_since_previous_sec=rev.time_since_previous_sec,
            lines_added=rev.lines_added,
            lines_deleted=rev.lines_deleted,
            lines_modified=rev.lines_modified,
            total_loc=rev.total_loc,
            cyclomatic_complexity_delta=rev.cyclomatic_complexity_delta,
            modified_ast_nodes=rev.modified_ast_nodes,
            modified_functions=rev.modified_functions,
            execution_success=rev.execution_success,
            runtime_error_type=rev.runtime_error_type,
            resolved_error=rev.resolved_error,
            created_at=rev.created_at.isoformat() if rev.created_at else "",
        )
        for rev in getattr(record, "revisions", [])
    ]

    stest_dtos = [
        StudentTestInputDTO(
            id=st.id,
            turn_number=st.turn_number,
            input_expression=st.input_expression,
            student_rationale=st.student_rationale,
            is_boundary_case=st.is_boundary_case,
            executed=st.executed,
            execution_success=st.execution_success,
            stdout=st.stdout,
            stderr=st.stderr,
            exception_type=st.exception_type,
            execution_time_ms=st.execution_time_ms,
            created_at=st.created_at.isoformat() if st.created_at else "",
        )
        for st in getattr(record, "student_test_inputs", [])
    ]

    turn_dtos = [
        InteractionTurnDTO(
            id=t.id,
            turn_number=t.turn_number,
            speaker=t.speaker,
            action_type=t.action_type,
            content_text=t.content_text,
            referenced_entity_id=t.referenced_entity_id,
            created_at=t.created_at.isoformat() if t.created_at else "",
        )
        for t in getattr(record, "interaction_turns", [])
    ]

    activity_dto = StudentActivitySummaryDTO(
        revisions_count=len(rev_dtos),
        hypotheses_count=len(shyp_dtos),
        custom_tests_count=len(stest_dtos),
        boundary_tests_count=sum(1 for st in stest_dtos if st.is_boundary_case),
        socratic_questions_answered=sum(1 for t in turn_dtos if t.action_type == "ANSWER_SOCRATIC_PROMPT"),
        total_turns=len(turn_dtos),
    )

    return SessionDetailResponse(
        id=record.id,
        title=record.title,
        user_goal=record.user_goal,
        source_code=record.source_code,
        file_path=record.file_path,
        error_description=record.error_description,
        traceback_input=record.traceback_input,
        mode=getattr(record, "mode", "GUIDED") or "GUIDED",
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
        student_hypotheses=shyp_dtos,
        revisions=rev_dtos,
        student_test_inputs=stest_dtos,
        interaction_turns=turn_dtos,
        student_activity=activity_dto,
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
            mode=getattr(request, "mode", "GUIDED") or "GUIDED",
        )

        # Log initial turn
        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=1,
            speaker="STUDENT",
            action_type="SUBMIT_INITIAL_BUG",
            content_text=f"Submitted initial code for goal: '{request.user_goal}'",
        )

        # Create initial Revision 1
        diff_info = CodeDiffEngine.calculate_diff("", request.source_code)
        await self.repo.add_code_revision(
            session_id=session_id,
            source_code=request.source_code,
            intent_notes="Initial bug submission",
            revision_number=1,
            time_since_previous_sec=0.0,
            lines_added=diff_info["lines_added"],
            lines_deleted=diff_info["lines_deleted"],
            lines_modified=diff_info["lines_modified"],
            total_loc=diff_info["total_loc"],
            cyclomatic_complexity_delta=diff_info["cyclomatic_complexity_delta"],
            modified_ast_nodes=diff_info["modified_ast_nodes"],
            modified_functions=diff_info["modified_functions"],
            execution_success=False,
        )

        # Refresh session snapshot
        fresh_record = await self.repo.get_session(session_id)
        return map_session_record_to_detail(fresh_record or record)

    async def create_session_from_upload(
        self,
        filename: str,
        content_bytes: bytes,
        user_goal: str,
        error_description: Optional[str] = None,
        traceback_input: Optional[str] = None,
        mode: str = "GUIDED",
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
            mode=mode,
        )

        # Log initial turn and revision
        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=1,
            speaker="STUDENT",
            action_type="SUBMIT_INITIAL_BUG",
            content_text=f"Uploaded {safe_name} for goal: '{user_goal}'",
        )

        diff_info = CodeDiffEngine.calculate_diff("", source_code)
        await self.repo.add_code_revision(
            session_id=session_id,
            source_code=source_code,
            intent_notes=f"Uploaded file {safe_name}",
            revision_number=1,
            time_since_previous_sec=0.0,
            lines_added=diff_info["lines_added"],
            lines_deleted=diff_info["lines_deleted"],
            lines_modified=diff_info["lines_modified"],
            total_loc=diff_info["total_loc"],
            cyclomatic_complexity_delta=diff_info["cyclomatic_complexity_delta"],
            modified_ast_nodes=diff_info["modified_ast_nodes"],
            modified_functions=diff_info["modified_functions"],
        )

        fresh_record = await self.repo.get_session(session_id)
        return map_session_record_to_detail(fresh_record or record)

    # ========================================================================
    # Milestone v0.5 Interactive Student Action Handlers
    # ========================================================================

    async def submit_student_hypothesis(
        self,
        session_id: str,
        request: CreateStudentHypothesisRequest,
    ) -> StudentHypothesisDTO:
        """Record and broadcast a hypothesis articulated by the student."""
        session = await self.repo.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        turns = await self.repo.list_interaction_turns(session_id)
        next_turn = len(turns) + 1

        shyp_record = await self.repo.add_student_hypothesis(
            session_id=session_id,
            hypothesis_text=request.hypothesis_text,
            target_function_or_line=request.target_function_or_line,
            student_confidence=request.student_confidence,
            turn_number=next_turn,
        )

        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=next_turn,
            speaker="STUDENT",
            action_type="PROPOSE_HYPOTHESIS",
            content_text=request.hypothesis_text,
            referenced_entity_id=shyp_record.id,
        )

        # Broadcast SSE Event
        payload = {
            "session_id": session_id,
            "hypothesis_id": shyp_record.id,
            "hypothesis_text": request.hypothesis_text,
            "turn_number": next_turn,
        }
        await global_broadcaster.broadcast(session_id, {
            "event_type": EventType.STUDENT_ACTION_RECORDED.value,
            "payload": payload,
            "message": f"Student proposed hypothesis: '{request.hypothesis_text[:50]}...'",
        })

        return StudentHypothesisDTO(
            id=shyp_record.id,
            turn_number=shyp_record.turn_number,
            hypothesis_text=shyp_record.hypothesis_text,
            target_function_or_line=shyp_record.target_function_or_line,
            student_confidence=shyp_record.student_confidence,
            status=shyp_record.status,
            evaluation_observation_id=shyp_record.evaluation_observation_id,
            created_at=shyp_record.created_at.isoformat() if shyp_record.created_at else "",
        )

    async def submit_code_revision(
        self,
        session_id: str,
        request: CreateCodeRevisionRequest,
    ) -> CodeRevisionDTO:
        """Process, diff, and execute a student code revision attempt."""
        session = await self.repo.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        latest_rev = await self.repo.get_latest_code_revision(session_id)
        old_code = latest_rev.source_code if latest_rev else session.source_code

        # Calculate AST & structural diff
        diff = CodeDiffEngine.calculate_diff(old_code, request.source_code)

        # Test execution in sandbox
        executor = PythonExecutorTool()
        tool_res = executor.execute(source_code=request.source_code)
        
        exec_success = tool_res.success
        out_data = tool_res.output if isinstance(tool_res.output, dict) else {}
        err_type = out_data.get("exception_type")
        resolved = exec_success

        revisions = await self.repo.list_code_revisions(session_id)
        next_rev_num = len(revisions) + 1

        rev_record = await self.repo.add_code_revision(
            session_id=session_id,
            source_code=request.source_code,
            intent_notes=request.intent_notes,
            revision_number=next_rev_num,
            time_since_previous_sec=request.time_since_previous_sec,
            lines_added=diff["lines_added"],
            lines_deleted=diff["lines_deleted"],
            lines_modified=diff["lines_modified"],
            total_loc=diff["total_loc"],
            cyclomatic_complexity_delta=diff["cyclomatic_complexity_delta"],
            modified_ast_nodes=diff["modified_ast_nodes"],
            modified_functions=diff["modified_functions"],
            execution_success=exec_success,
            runtime_error_type=err_type,
            resolved_error=resolved,
        )

        turns = await self.repo.list_interaction_turns(session_id)
        next_turn = len(turns) + 1
        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=next_turn,
            speaker="STUDENT",
            action_type="SUBMIT_CODE_REVISION",
            content_text=f"Revision #{next_rev_num} submitted: {diff['lines_added']} added, {diff['lines_deleted']} deleted.",
            referenced_entity_id=rev_record.id,
        )

        # Broadcast SSE Event
        await global_broadcaster.broadcast(session_id, {
            "event_type": EventType.REVISION_ANALYZED.value,
            "payload": {
                "revision_id": rev_record.id,
                "revision_number": next_rev_num,
                "lines_added": diff["lines_added"],
                "lines_deleted": diff["lines_deleted"],
                "execution_success": exec_success,
                "resolved_error": resolved,
            },
            "message": f"Code Revision #{next_rev_num} analyzed: Execution {'succeeded' if exec_success else 'failed'}.",
        })

        return CodeRevisionDTO(
            id=rev_record.id,
            revision_number=rev_record.revision_number,
            source_code=rev_record.source_code,
            intent_notes=rev_record.intent_notes,
            time_since_previous_sec=rev_record.time_since_previous_sec,
            lines_added=rev_record.lines_added,
            lines_deleted=rev_record.lines_deleted,
            lines_modified=rev_record.lines_modified,
            total_loc=rev_record.total_loc,
            cyclomatic_complexity_delta=rev_record.cyclomatic_complexity_delta,
            modified_ast_nodes=rev_record.modified_ast_nodes,
            modified_functions=rev_record.modified_functions,
            execution_success=rev_record.execution_success,
            runtime_error_type=rev_record.runtime_error_type,
            resolved_error=rev_record.resolved_error,
            created_at=rev_record.created_at.isoformat() if rev_record.created_at else "",
        )

    async def submit_student_test_input(
        self,
        session_id: str,
        request: CreateStudentTestInputRequest,
    ) -> StudentTestExecutionResponse:
        """Capture and execute a student-proposed test input against the current code."""
        session = await self.repo.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        turns = await self.repo.list_interaction_turns(session_id)
        next_turn = len(turns) + 1

        test_record = await self.repo.add_student_test_input(
            session_id=session_id,
            input_expression=request.input_expression,
            student_rationale=request.student_rationale,
            is_boundary_case=request.is_boundary_case,
            turn_number=next_turn,
        )

        # Build test harness: append input expression to the session's active code
        harness = f"{session.source_code}\n\n# Student Test Input:\nprint({request.input_expression})\n"
        executor = PythonExecutorTool()
        tool_res = executor.execute(source_code=harness)

        out_data = tool_res.output if isinstance(tool_res.output, dict) else {}
        stdout_txt = out_data.get("stdout", "")
        stderr_txt = out_data.get("stderr", "")
        err_type = out_data.get("exception_type")
        exec_ms = float(out_data.get("execution_time_ms", 0.0))

        await self.repo.update_student_test_input_result(
            test_id=test_record.id,
            executed=True,
            execution_success=tool_res.success,
            stdout=stdout_txt,
            stderr=stderr_txt,
            exception_type=err_type,
            execution_time_ms=exec_ms,
        )

        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=next_turn,
            speaker="STUDENT",
            action_type="PROPOSE_TEST_INPUT",
            content_text=f"Tested: {request.input_expression} -> {'Success' if tool_res.success else err_type or 'Error'}",
            referenced_entity_id=test_record.id,
        )

        # Broadcast SSE Event
        await global_broadcaster.broadcast(session_id, {
            "event_type": EventType.TEST_INPUT_EXECUTED.value,
            "payload": {
                "test_id": test_record.id,
                "input_expression": request.input_expression,
                "execution_success": tool_res.success,
                "stdout": stdout_txt,
                "stderr": stderr_txt,
            },
            "message": f"Student test '{request.input_expression}' executed: {'Passed' if tool_res.success else 'Exception triggered'}.",
        })

        return StudentTestExecutionResponse(
            test_id=test_record.id,
            executed=True,
            execution_success=tool_res.success,
            stdout=stdout_txt,
            stderr=stderr_txt,
            exception_type=err_type,
            execution_time_ms=exec_ms,
        )

    async def answer_socratic_prompt(
        self,
        session_id: str,
        request: AnswerSocraticRequest,
    ) -> SessionDetailResponse:
        """Record response to or skip of a Socratic question."""
        session = await self.repo.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        turns = await self.repo.list_interaction_turns(session_id)
        next_turn = len(turns) + 1

        action_type = "SKIP_INTERACTION" if request.skip else "ANSWER_SOCRATIC_PROMPT"
        content = "Skipped question" if request.skip else (request.student_response or "Acknowledged")

        await self.repo.add_interaction_turn(
            session_id=session_id,
            turn_number=next_turn,
            speaker="STUDENT",
            action_type=action_type,
            content_text=content,
            referenced_entity_id=request.prompt_id,
        )

        fresh_session = await self.repo.get_session(session_id)
        return map_session_record_to_detail(fresh_session or session)

    async def list_revisions(self, session_id: str) -> RevisionsListResponse:
        """Get all code revisions for a session."""
        revs = await self.repo.list_code_revisions(session_id)
        dtos = [
            CodeRevisionDTO(
                id=r.id,
                revision_number=r.revision_number,
                source_code=r.source_code,
                intent_notes=r.intent_notes,
                time_since_previous_sec=r.time_since_previous_sec,
                lines_added=r.lines_added,
                lines_deleted=r.lines_deleted,
                lines_modified=r.lines_modified,
                total_loc=r.total_loc,
                cyclomatic_complexity_delta=r.cyclomatic_complexity_delta,
                modified_ast_nodes=r.modified_ast_nodes,
                modified_functions=r.modified_functions,
                execution_success=r.execution_success,
                runtime_error_type=r.runtime_error_type,
                resolved_error=r.resolved_error,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in revs
        ]
        return RevisionsListResponse(session_id=session_id, revisions=dtos, total=len(dtos))

    async def list_timeline(self, session_id: str) -> InteractiveTimelineResponse:
        """Get full chronological interaction turns for a session."""
        turns = await self.repo.list_interaction_turns(session_id)
        dtos = [
            InteractionTurnDTO(
                id=t.id,
                turn_number=t.turn_number,
                speaker=t.speaker,
                action_type=t.action_type,
                content_text=t.content_text,
                referenced_entity_id=t.referenced_entity_id,
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
            for t in turns
        ]
        return InteractiveTimelineResponse(session_id=session_id, turns=dtos, total_turns=len(dtos))

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
