"""Async Data Access Object (DAO) Repository for TRACE v0.3."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from trace.core.state import AgentState, LifecycleState
from trace.db.models import (
    CountercheckRecord,
    EvidenceRecord,
    HypothesisRecord,
    ObservationRecord,
    PlanStepRecord,
    SessionEventRecord,
    SessionRecord,
    SessionTelemetryRecord,
    BehaviorPredictionRecord,
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
            .options(
                selectinload(SessionRecord.plan_steps),
                selectinload(SessionRecord.observations),
                selectinload(SessionRecord.evidence),
                selectinload(SessionRecord.hypotheses),
                selectinload(SessionRecord.counterchecks),
                selectinload(SessionRecord.events),
                selectinload(SessionRecord.telemetry),
                selectinload(SessionRecord.prediction),
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

    async def save_telemetry(
        self,
        session_id: str,
        features_dict: Dict[str, Any],
        is_synthetic: bool = False,
        problem_id: str = "default",
    ) -> SessionTelemetryRecord:
        """Upsert a session's extracted 18-feature telemetry record."""
        stmt = select(SessionTelemetryRecord).where(SessionTelemetryRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record is None:
            record = SessionTelemetryRecord(
                session_id=session_id,
                is_synthetic=is_synthetic,
                problem_id=problem_id,
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
                hypothesis_churn_count=features_dict.get("hypothesis_churn_count", 0),
                hypothesis_rejection_ratio=features_dict.get("hypothesis_rejection_ratio", 0.0),
                countercheck_execution_rate=features_dict.get("countercheck_execution_rate", 0.0),
                direct_evidence_ratio=features_dict.get("direct_evidence_ratio", 0.0),
                created_at=utc_now(),
            )
            self.session.add(record)
        else:
            for k, v in features_dict.items():
                if hasattr(record, k):
                    setattr(record, k, v)
            record.is_synthetic = is_synthetic
            record.problem_id = problem_id

        await self.session.commit()
        return record

    async def get_telemetry(self, session_id: str) -> Optional[SessionTelemetryRecord]:
        """Retrieve telemetry for a specific session."""
        stmt = select(SessionTelemetryRecord).where(SessionTelemetryRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all_telemetry(self, include_synthetic: bool = True) -> List[SessionTelemetryRecord]:
        """List all telemetry records for dataset building and analysis."""
        stmt = select(SessionTelemetryRecord)
        if not include_synthetic:
            stmt = stmt.where(SessionTelemetryRecord.is_synthetic.is_(False))
        stmt = stmt.order_by(desc(SessionTelemetryRecord.created_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_prediction(
        self,
        prediction_id: str,
        session_id: str,
        predicted_archetype: str,
        confidence: float,
        top_factors: List[Dict[str, Any]],
        pedagogical_explanation: str = "",
        model_type: str = "RandomForest",
        model_version: str = "v0.4",
    ) -> BehaviorPredictionRecord:
        """Save a behavior prediction for a session."""
        stmt = select(BehaviorPredictionRecord).where(BehaviorPredictionRecord.session_id == session_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record is None:
            record = BehaviorPredictionRecord(
                id=prediction_id,
                session_id=session_id,
                predicted_archetype=predicted_archetype,
                confidence=confidence,
                top_factors_json=json.dumps(top_factors or []),
                pedagogical_explanation=pedagogical_explanation,
                model_type=model_type,
                model_version=model_version,
                created_at=utc_now(),
            )
            self.session.add(record)
        else:
            record.predicted_archetype = predicted_archetype
            record.confidence = confidence
            record.top_factors_json = json.dumps(top_factors or [])
            record.pedagogical_explanation = pedagogical_explanation
            record.model_type = model_type
            record.model_version = model_version

        await self.session.commit()
        return record

    async def list_recent_predictions(self, limit: int = 50) -> List[BehaviorPredictionRecord]:
        """List recent behavior predictions."""
        stmt = select(BehaviorPredictionRecord).order_by(desc(BehaviorPredictionRecord.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

