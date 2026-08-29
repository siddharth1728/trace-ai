"""Async Data Access Object (DAO) Repository for TRACE v0.3."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trace.core.state import AgentState, LifecycleState
from trace.db.models import (
    BehaviorLabelRecord,
    CodeRevisionRecord,
    CountercheckRecord,
    EvidenceRecord,
    HypothesisRecord,
    InteractionTurnRecord,
    ObservationRecord,
    PlanStepRecord,
    SessionEventRecord,
    SessionRecord,
    SessionTelemetryRecord,
    StudentHypothesisRecord,
    StudentTestInputRecord,
    utc_now,
)


class SessionRepository:
    """Repository handling database persistence and synchronization for TRACE sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        session_id: str,
        user_goal: str,
        source_code: str,
        title: Optional[str] = None,
        file_path: Optional[str] = None,
        error_description: Optional[str] = None,
        traceback_input: Optional[str] = None,
        mode: str = "GUIDED",
    ) -> SessionRecord:
        """Create and persist a new session record."""
        session_title = title or (user_goal[:60] if user_goal else "Untitled Investigation")
        record = SessionRecord(
            id=session_id,
            title=session_title,
            user_goal=user_goal,
            source_code=source_code,
            file_path=file_path,
            error_description=error_description,
            traceback_input=traceback_input,
            mode=mode,
            status="CREATED",
            confidence=0.0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(record)
        await self.session.commit()
        return await self.get_session(session_id)

    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Retrieve a session with all its child records eagerly loaded."""
        stmt = (
            select(SessionRecord)
            .where(SessionRecord.id == session_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(SessionRecord.plan_steps),
                selectinload(SessionRecord.observations),
                selectinload(SessionRecord.evidence),
                selectinload(SessionRecord.hypotheses),
                selectinload(SessionRecord.counterchecks),
                selectinload(SessionRecord.events),
                selectinload(SessionRecord.student_hypotheses),
                selectinload(SessionRecord.revisions),
                selectinload(SessionRecord.student_test_inputs),
                selectinload(SessionRecord.interaction_turns),
                selectinload(SessionRecord.telemetry),
                selectinload(SessionRecord.label),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionRecord]:
        """List sessions ordered by most recently updated."""
        stmt = (
            select(SessionRecord)
            .order_by(desc(SessionRecord.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        confidence: Optional[float] = None,
    ) -> Optional[SessionRecord]:
        """Update product-level status of a session."""
        record = await self.session.get(SessionRecord, session_id)
        if record:
            record.status = status
            if confidence is not None:
                record.confidence = confidence
            record.updated_at = utc_now()
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related records via cascade."""
        stmt = delete(SessionRecord).where(SessionRecord.id == session_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def add_session_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> SessionEventRecord:
        """Log an immutable investigation event."""
        event_record = SessionEventRecord(
            session_id=session_id,
            event_type=event_type,
            payload_json=json.dumps(payload),
            timestamp=utc_now(),
        )
        self.session.add(event_record)
        await self.session.commit()
        await self.session.refresh(event_record)
        return event_record

    async def get_session_events(self, session_id: str) -> List[SessionEventRecord]:
        """Get chronological log of events for a session."""
        stmt = (
            select(SessionEventRecord)
            .where(SessionEventRecord.session_id == session_id)
            .order_by(SessionEventRecord.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_full_agent_state(self, session_id: str, state: AgentState) -> None:
        """Synchronize complete internal AgentState into the relational database."""
        record = await self.get_session(session_id)
        if not record:
            return

        # Map internal lifecycle to product status
        if state.status == LifecycleState.COMPLETED:
            product_status = "COMPLETED"
        elif state.status == LifecycleState.BLOCKED:
            product_status = "BLOCKED"
        elif state.status == LifecycleState.FAILED:
            product_status = "FAILED"
        else:
            product_status = "RUNNING"

        record.status = product_status
        record.confidence = state.confidence
        record.updated_at = utc_now()

        # Diagnosis details
        if state.final_diagnosis:
            diag = state.final_diagnosis
            record.problem_statement = diag.problem_statement
            record.likely_root_cause = diag.likely_root_cause
            record.learning_point = diag.learning_point
            record.suggested_fix_guidance = diag.suggested_fix_guidance
            record.verified_hypothesis_id = diag.verified_hypothesis_id
            record.countercheck_summary = diag.countercheck_summary
            record.what_trace_checked = diag.what_trace_checked
            record.what_remains_uncertain = diag.what_remains_uncertain
            record.evidence_summary = diag.evidence_summary

        # Clean existing child relational records to avoid duplicates
        await self.session.execute(delete(PlanStepRecord).where(PlanStepRecord.session_id == session_id))
        await self.session.execute(delete(ObservationRecord).where(ObservationRecord.session_id == session_id))
        await self.session.execute(delete(EvidenceRecord).where(EvidenceRecord.session_id == session_id))
        await self.session.execute(delete(HypothesisRecord).where(HypothesisRecord.session_id == session_id))
        await self.session.execute(delete(CountercheckRecord).where(CountercheckRecord.session_id == session_id))

        # Insert Plan Steps
        if state.current_plan:
            for step in state.current_plan.steps:
                self.session.add(PlanStepRecord(
                    id=f"step_{session_id}_{step.step_id}",
                    session_id=session_id,
                    step_index=step.step_id,
                    title=step.title,
                    tool_name=step.tool_name,
                    tool_args_json=json.dumps(step.tool_args or {}),
                    expected_outcome=step.expected_outcome,
                    status=step.status.value,
                    observation_id=step.observation_id,
                ))

        # Insert Observations
        for idx, obs in enumerate(state.observations):
            obs_dt = utc_now()
            if hasattr(obs, "timestamp") and obs.timestamp:
                try:
                    obs_dt = datetime.fromisoformat(obs.timestamp)
                except Exception:
                    pass
            self.session.add(ObservationRecord(
                id=obs.id,
                session_id=session_id,
                step_index=idx + 1,
                tool_name=obs.tool_name,
                input_args_json=json.dumps(obs.input_args or {}),
                output_data_json=json.dumps(obs.output_data or {}),
                is_success=obs.is_success,
                summary=obs.summary,
                evidence_tags_json=json.dumps(obs.evidence_tags or []),
                created_at=obs_dt,
            ))

        # Insert Evidence Items
        for ev in state.evidence_store:
            ev_dt = utc_now()
            if hasattr(ev, "timestamp") and ev.timestamp:
                try:
                    ev_dt = datetime.fromisoformat(ev.timestamp)
                except Exception:
                    pass
            self.session.add(EvidenceRecord(
                id=ev.id,
                session_id=session_id,
                observation_id=ev.observation_id,
                target_hypothesis_id=ev.target_hypothesis_id,
                evidence_type=ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
                relation=ev.relation.value if hasattr(ev.relation, "value") else str(ev.relation),
                statement=ev.statement,
                raw_fact_json=json.dumps(ev.raw_fact or {}),
                confidence_weight=ev.confidence_weight,
                created_at=ev_dt,
            ))

        # Insert Hypotheses
        for hyp in state.hypotheses:
            self.session.add(HypothesisRecord(
                id=hyp.id,
                session_id=session_id,
                statement=hyp.statement,
                status=hyp.status.value if hasattr(hyp.status, "value") else str(hyp.status),
                confidence=hyp.confidence,
                rationale=hyp.rationale,
                falsification_condition=hyp.falsification_condition,
                supporting_observation_ids_json=json.dumps(hyp.supporting_observation_ids or []),
                contradictory_observation_ids_json=json.dumps(hyp.contradictory_observation_ids or []),
                supporting_evidence_ids_json=json.dumps(hyp.supporting_evidence_ids or []),
                contradictory_evidence_ids_json=json.dumps(hyp.contradictory_evidence_ids or []),
                counterexample_ids_json=json.dumps(hyp.counterexample_ids or []),
                created_at=utc_now(),
            ))

        await self.session.commit()

    # ========================================================================
    # Milestone v0.5 Interactive Student Artifact Operations
    # ========================================================================

    async def add_student_hypothesis(
        self,
        session_id: str,
        hypothesis_text: str,
        target_function_or_line: Optional[str] = None,
        student_confidence: Optional[float] = None,
        turn_number: int = 1,
        hypothesis_id: Optional[str] = None,
    ) -> StudentHypothesisRecord:
        """Persist a student-articulated hypothesis."""
        import uuid
        h_id = hypothesis_id or f"shyp_{uuid.uuid4().hex[:8]}"
        record = StudentHypothesisRecord(
            id=h_id,
            session_id=session_id,
            turn_number=turn_number,
            hypothesis_text=hypothesis_text,
            target_function_or_line=target_function_or_line,
            student_confidence=student_confidence,
            status="UNTESTED",
            created_at=utc_now(),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_student_hypotheses(self, session_id: str) -> List[StudentHypothesisRecord]:
        """List all student hypotheses for a session."""
        stmt = (
            select(StudentHypothesisRecord)
            .where(StudentHypothesisRecord.session_id == session_id)
            .order_by(StudentHypothesisRecord.turn_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_student_hypothesis_status(
        self,
        hypothesis_id: str,
        status: str,
        evaluation_observation_id: Optional[str] = None,
    ) -> Optional[StudentHypothesisRecord]:
        """Update evaluation status of a student hypothesis."""
        record = await self.session.get(StudentHypothesisRecord, hypothesis_id)
        if record:
            record.status = status
            if evaluation_observation_id:
                record.evaluation_observation_id = evaluation_observation_id
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def add_code_revision(
        self,
        session_id: str,
        source_code: str,
        intent_notes: Optional[str] = None,
        revision_number: Optional[int] = None,
        time_since_previous_sec: float = 0.0,
        lines_added: int = 0,
        lines_deleted: int = 0,
        lines_modified: int = 0,
        total_loc: int = 0,
        cyclomatic_complexity_delta: int = 0,
        modified_ast_nodes: Optional[List[str]] = None,
        modified_functions: Optional[List[str]] = None,
        execution_success: bool = False,
        runtime_error_type: Optional[str] = None,
        resolved_error: bool = False,
        revision_id: Optional[str] = None,
    ) -> CodeRevisionRecord:
        """Persist a student code revision attempt."""
        import uuid
        r_id = revision_id or f"rev_{uuid.uuid4().hex[:8]}"
        
        # Calculate auto revision number if not provided
        if revision_number is None:
            existing = await self.list_code_revisions(session_id)
            revision_number = len(existing) + 1

        record = CodeRevisionRecord(
            id=r_id,
            session_id=session_id,
            revision_number=revision_number,
            source_code=source_code,
            intent_notes=intent_notes,
            time_since_previous_sec=time_since_previous_sec,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            lines_modified=lines_modified,
            total_loc=total_loc,
            cyclomatic_complexity_delta=cyclomatic_complexity_delta,
            modified_ast_nodes_json=json.dumps(modified_ast_nodes or []),
            modified_functions_json=json.dumps(modified_functions or []),
            execution_success=execution_success,
            runtime_error_type=runtime_error_type,
            resolved_error=resolved_error,
            created_at=utc_now(),
        )
        self.session.add(record)
        
        # Also update the session's active source code
        sess = await self.session.get(SessionRecord, session_id)
        if sess:
            sess.source_code = source_code
            sess.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_code_revisions(self, session_id: str) -> List[CodeRevisionRecord]:
        """List all code revisions for a session in order."""
        stmt = (
            select(CodeRevisionRecord)
            .where(CodeRevisionRecord.session_id == session_id)
            .order_by(CodeRevisionRecord.revision_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest_code_revision(self, session_id: str) -> Optional[CodeRevisionRecord]:
        """Get the most recent code revision."""
        stmt = (
            select(CodeRevisionRecord)
            .where(CodeRevisionRecord.session_id == session_id)
            .order_by(desc(CodeRevisionRecord.revision_number))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def add_student_test_input(
        self,
        session_id: str,
        input_expression: str,
        student_rationale: Optional[str] = None,
        is_boundary_case: bool = False,
        turn_number: int = 1,
        test_id: Optional[str] = None,
    ) -> StudentTestInputRecord:
        """Persist a student proposed test input."""
        import uuid
        t_id = test_id or f"stest_{uuid.uuid4().hex[:8]}"
        record = StudentTestInputRecord(
            id=t_id,
            session_id=session_id,
            turn_number=turn_number,
            input_expression=input_expression,
            student_rationale=student_rationale,
            is_boundary_case=is_boundary_case,
            executed=False,
            execution_success=False,
            created_at=utc_now(),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_student_test_input_result(
        self,
        test_id: str,
        executed: bool,
        execution_success: bool,
        stdout: str,
        stderr: str,
        exception_type: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> Optional[StudentTestInputRecord]:
        """Update sandbox outcome of a student test input."""
        record = await self.session.get(StudentTestInputRecord, test_id)
        if record:
            record.executed = executed
            record.execution_success = execution_success
            record.stdout = stdout
            record.stderr = stderr
            record.exception_type = exception_type
            record.execution_time_ms = execution_time_ms
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def list_student_test_inputs(self, session_id: str) -> List[StudentTestInputRecord]:
        """List all student test inputs for a session."""
        stmt = (
            select(StudentTestInputRecord)
            .where(StudentTestInputRecord.session_id == session_id)
            .order_by(StudentTestInputRecord.turn_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add_interaction_turn(
        self,
        session_id: str,
        turn_number: int,
        speaker: str,
        action_type: str,
        content_text: str,
        referenced_entity_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> InteractionTurnRecord:
        """Record a sequential turn in the interactive timeline."""
        import uuid
        t_id = turn_id or f"turn_{uuid.uuid4().hex[:8]}"
        record = InteractionTurnRecord(
            id=t_id,
            session_id=session_id,
            turn_number=turn_number,
            speaker=speaker,
            action_type=action_type,
            content_text=content_text,
            referenced_entity_id=referenced_entity_id,
            created_at=utc_now(),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_interaction_turns(self, session_id: str) -> List[InteractionTurnRecord]:
        """List chronological interaction turns."""
        stmt = (
            select(InteractionTurnRecord)
            .where(InteractionTurnRecord.session_id == session_id)
            .order_by(InteractionTurnRecord.turn_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_telemetry(
        self,
        session_id: str,
        features_dict: Dict[str, Any],
        is_synthetic: bool = False,
        problem_id: str = "default",
        data_source: str = "REAL",
    ) -> SessionTelemetryRecord:
        """Upsert a session's extracted 18-feature telemetry record."""
        stmt = select(SessionTelemetryRecord).where(SessionTelemetryRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        scalar_fields = [
            "loc", "ast_node_count", "ast_max_depth", "cyclomatic_complexity", "function_count",
            "has_traceback_input", "error_desc_length", "error_family_syntax", "error_family_type_or_value",
            "ast_first_step", "static_to_exec_ratio", "failed_tool_ratio", "tool_sequence_entropy",
            "total_investigation_steps", "hypothesis_count", "hypothesis_rejection_ratio",
            "countercheck_execution_rate", "direct_evidence_ratio"
        ]

        if record is None:
            record = SessionTelemetryRecord(
                session_id=session_id,
                problem_id=problem_id,
                data_source=data_source,
                loc=features_dict.get("loc", 0),
                ast_node_count=features_dict.get("ast_node_count", 0),
                ast_max_depth=features_dict.get("ast_max_depth", 0),
                cyclomatic_complexity=features_dict.get("cyclomatic_complexity", 1),
                function_count=features_dict.get("function_count", 0),
                has_traceback_input=features_dict.get("has_traceback_input", False),
                error_desc_length=features_dict.get("error_desc_length", 0),
                error_family_syntax=features_dict.get("error_family_syntax", False),
                error_family_type_or_value=features_dict.get("error_family_type_or_value", False),
                ast_first_step=features_dict.get("ast_first_step", False),
                static_to_exec_ratio=features_dict.get("static_to_exec_ratio", 0.0),
                failed_tool_ratio=features_dict.get("failed_tool_ratio", 0.0),
                tool_sequence_entropy=features_dict.get("tool_sequence_entropy", 0.0),
                total_investigation_steps=features_dict.get("total_investigation_steps", 0),
                hypothesis_count=features_dict.get("hypothesis_count", 0),
                hypothesis_rejection_ratio=features_dict.get("hypothesis_rejection_ratio", 0.0),
                countercheck_execution_rate=features_dict.get("countercheck_execution_rate", 0.0),
                direct_evidence_ratio=features_dict.get("direct_evidence_ratio", 0.0),
                user_actions_json="{}",
                student_behavior_json="{}",
                code_properties_json="{}",
                investigation_context_json="{}",
                trace_agent_actions_json="{}",
                outcome_json="{}",
                created_at=utc_now(),
            )
            self.session.add(record)
        else:
            record.data_source = data_source
            record.problem_id = problem_id
            for k in scalar_fields:
                if k in features_dict:
                    setattr(record, k, features_dict[k])

        await self.session.commit()
        return record

    async def get_telemetry(self, session_id: str) -> Optional[SessionTelemetryRecord]:
        """Retrieve telemetry for a specific session."""
        stmt = select(SessionTelemetryRecord).where(SessionTelemetryRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all_telemetry(self, data_source: Optional[str] = None) -> List[SessionTelemetryRecord]:
        """List all telemetry records for dataset building and quality auditing."""
        stmt = select(SessionTelemetryRecord)
        if data_source:
            stmt = stmt.where(SessionTelemetryRecord.data_source == data_source)
        stmt = stmt.order_by(desc(SessionTelemetryRecord.created_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_label(
        self,
        session_id: str,
        proposed_label: Optional[str] = None,
        final_label: Optional[str] = None,
        labeling_method: str = "UNLABELED",
        reviewer_status: str = "UNREVIEWED",
        reviewer_notes: Optional[str] = None,
        confidence: float = 1.0,
        dataset_version: str = "v0.4-A",
    ) -> BehaviorLabelRecord:
        """Save or update candidate or confirmed behavior label for a session."""
        stmt = select(BehaviorLabelRecord).where(BehaviorLabelRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record is None:
            record = BehaviorLabelRecord(
                session_id=session_id,
                proposed_label=proposed_label,
                final_label=final_label,
                labeling_method=labeling_method,
                reviewer_status=reviewer_status,
                reviewer_notes=reviewer_notes,
                confidence=confidence,
                dataset_version=dataset_version,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.session.add(record)
        else:
            if proposed_label is not None:
                record.proposed_label = proposed_label
            if final_label is not None:
                record.final_label = final_label
            record.labeling_method = labeling_method
            record.reviewer_status = reviewer_status
            if reviewer_notes is not None:
                record.reviewer_notes = reviewer_notes
            record.confidence = confidence
            record.dataset_version = dataset_version
            record.updated_at = utc_now()

        await self.session.commit()
        return record

    async def get_label(self, session_id: str) -> Optional[BehaviorLabelRecord]:
        """Retrieve behavior label for a specific session."""
        stmt = select(BehaviorLabelRecord).where(BehaviorLabelRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all_labels(self, reviewer_status: Optional[str] = None) -> List[BehaviorLabelRecord]:
        """List all behavior labels."""
        stmt = select(BehaviorLabelRecord)
        if reviewer_status:
            stmt = stmt.where(BehaviorLabelRecord.reviewer_status == reviewer_status)
        stmt = stmt.order_by(desc(BehaviorLabelRecord.created_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


