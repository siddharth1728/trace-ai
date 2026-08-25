"""SQLAlchemy 2.0 ORM Models for TRACE Persistence."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all TRACE relational entities."""
    pass


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class SessionRecord(Base):
    """Represents a persistent debugging investigation session."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    title: Mapped[str] = mapped_column(String(256), default="Untitled Investigation")
    user_goal: Mapped[str] = mapped_column(Text, default="")
    source_code: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traceback_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Product status: CREATED, RUNNING, COMPLETED, FAILED, BLOCKED
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Final Diagnosis Fields
    problem_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    likely_root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    learning_point: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_fix_guidance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_hypothesis_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    countercheck_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON-encoded array fields
    what_trace_checked_json: Mapped[str] = mapped_column(Text, default="[]")
    what_remains_uncertain_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_summary_json: Mapped[str] = mapped_column(Text, default="[]")

    # Cascading Relational Children
    plan_steps: Mapped[List["PlanStepRecord"]] = relationship(
        "PlanStepRecord", back_populates="session", cascade="all, delete-orphan"
    )
    observations: Mapped[List["ObservationRecord"]] = relationship(
        "ObservationRecord", back_populates="session", cascade="all, delete-orphan"
    )
    evidence: Mapped[List["EvidenceRecord"]] = relationship(
        "EvidenceRecord", back_populates="session", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[List["HypothesisRecord"]] = relationship(
        "HypothesisRecord", back_populates="session", cascade="all, delete-orphan"
    )
    counterchecks: Mapped[List["CountercheckRecord"]] = relationship(
        "CountercheckRecord", back_populates="session", cascade="all, delete-orphan"
    )
    events: Mapped[List["SessionEventRecord"]] = relationship(
        "SessionEventRecord", back_populates="session", cascade="all, delete-orphan"
    )
    telemetry: Mapped[Optional["SessionTelemetryRecord"]] = relationship(
        "SessionTelemetryRecord", back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    prediction: Mapped[Optional["BehaviorPredictionRecord"]] = relationship(
        "BehaviorPredictionRecord", back_populates="session", cascade="all, delete-orphan", uselist=False
    )

    @property
    def what_trace_checked(self) -> List[str]:
        return json.loads(self.what_trace_checked_json or "[]")

    @what_trace_checked.setter
    def what_trace_checked(self, val: List[str]):
        self.what_trace_checked_json = json.dumps(val or [])

    @property
    def what_remains_uncertain(self) -> List[str]:
        return json.loads(self.what_remains_uncertain_json or "[]")

    @what_remains_uncertain.setter
    def what_remains_uncertain(self, val: List[str]):
        self.what_remains_uncertain_json = json.dumps(val or [])

    @property
    def evidence_summary(self) -> List[str]:
        return json.loads(self.evidence_summary_json or "[]")

    @evidence_summary.setter
    def evidence_summary(self, val: List[str]):
        self.evidence_summary_json = json.dumps(val or [])


class PlanStepRecord(Base):
    """Represents a planned investigative step."""
    __tablename__ = "plan_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(256))
    tool_name: Mapped[str] = mapped_column(String(64))
    tool_args_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_outcome: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    observation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="plan_steps")

    @property
    def tool_args(self) -> Dict[str, Any]:
        return json.loads(self.tool_args_json or "{}")

    @tool_args.setter
    def tool_args(self, val: Dict[str, Any]):
        self.tool_args_json = json.dumps(val or {})


class ObservationRecord(Base):
    """Represents an empirical observation produced by deterministic tools."""
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    tool_name: Mapped[str] = mapped_column(String(64))
    input_args_json: Mapped[str] = mapped_column(Text, default="{}")
    output_data_json: Mapped[str] = mapped_column(Text, default="{}")
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    evidence_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="observations")

    @property
    def input_args(self) -> Dict[str, Any]:
        return json.loads(self.input_args_json or "{}")

    @input_args.setter
    def input_args(self, val: Dict[str, Any]):
        self.input_args_json = json.dumps(val or {})

    @property
    def output_data(self) -> Dict[str, Any]:
        return json.loads(self.output_data_json or "{}")

    @output_data.setter
    def output_data(self, val: Dict[str, Any]):
        self.output_data_json = json.dumps(val or {})

    @property
    def evidence_tags(self) -> List[str]:
        return json.loads(self.evidence_tags_json or "[]")

    @evidence_tags.setter
    def evidence_tags(self, val: List[str]):
        self.evidence_tags_json = json.dumps(val or [])


class EvidenceRecord(Base):
    """Represents an atomic, structured evidence item linking observations to hypotheses."""
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    observation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_hypothesis_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(32), default="DIRECT")
    relation: Mapped[str] = mapped_column(String(32), default="SUPPORTS")
    statement: Mapped[str] = mapped_column(Text, default="")
    raw_fact_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence_weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="evidence")

    @property
    def raw_fact(self) -> Dict[str, Any]:
        return json.loads(self.raw_fact_json or "{}")

    @raw_fact.setter
    def raw_fact(self, val: Dict[str, Any]):
        self.raw_fact_json = json.dumps(val or {})


class HypothesisRecord(Base):
    """Represents a candidate explanation for a bug and its verified status."""
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")
    confidence: Mapped[float] = mapped_column(Float, default=0.20)
    rationale: Mapped[str] = mapped_column(Text, default="")
    falsification_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    supporting_observation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_observation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    counterexample_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="hypotheses")

    @property
    def supporting_observation_ids(self) -> List[str]:
        return json.loads(self.supporting_observation_ids_json or "[]")

    @supporting_observation_ids.setter
    def supporting_observation_ids(self, val: List[str]):
        self.supporting_observation_ids_json = json.dumps(val or [])

    @property
    def contradictory_observation_ids(self) -> List[str]:
        return json.loads(self.contradictory_observation_ids_json or "[]")

    @contradictory_observation_ids.setter
    def contradictory_observation_ids(self, val: List[str]):
        self.contradictory_observation_ids_json = json.dumps(val or [])

    @property
    def supporting_evidence_ids(self) -> List[str]:
        return json.loads(self.supporting_evidence_ids_json or "[]")

    @supporting_evidence_ids.setter
    def supporting_evidence_ids(self, val: List[str]):
        self.supporting_evidence_ids_json = json.dumps(val or [])

    @property
    def contradictory_evidence_ids(self) -> List[str]:
        return json.loads(self.contradictory_evidence_ids_json or "[]")

    @contradictory_evidence_ids.setter
    def contradictory_evidence_ids(self, val: List[str]):
        self.contradictory_evidence_ids_json = json.dumps(val or [])

    @property
    def counterexample_ids(self) -> List[str]:
        return json.loads(self.counterexample_ids_json or "[]")

    @counterexample_ids.setter
    def counterexample_ids(self, val: List[str]):
        self.counterexample_ids_json = json.dumps(val or [])


class CountercheckRecord(Base):
    """Represents a targeted sandbox falsification experiment."""
    __tablename__ = "counterchecks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    hypothesis_id: Mapped[str] = mapped_column(String(64), index=True)
    strategy: Mapped[str] = mapped_column(String(64), default="SAFE_EXECUTION_CHECK")
    description: Mapped[str] = mapped_column(Text, default="")
    harness_code: Mapped[str] = mapped_column(Text, default="")
    expected_exit_code: Mapped[int] = mapped_column(Integer, default=0)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    disproved: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_output: Mapped[str] = mapped_column(Text, default="")
    evidence_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="counterchecks")


class SessionEventRecord(Base):
    """Represents an immutable lifecycle event logged during an investigation."""
    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="events")

    @property
    def payload(self) -> Dict[str, Any]:
        return json.loads(self.payload_json or "{}")

    @payload.setter
    def payload(self, val: Dict[str, Any]):
        self.payload_json = json.dumps(val or {})


class SessionTelemetryRecord(Base):
    """Represents the 18-feature telemetry vector extracted from a session."""
    __tablename__ = "session_telemetry"

    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    problem_id: Mapped[str] = mapped_column(String(128), default="default", index=True)

    # 18 Telemetry Features
    loc: Mapped[int] = mapped_column(Integer, default=0)
    ast_node_count: Mapped[int] = mapped_column(Integer, default=0)
    ast_max_depth: Mapped[int] = mapped_column(Integer, default=0)
    cyclomatic_complexity: Mapped[int] = mapped_column(Integer, default=1)
    function_count: Mapped[int] = mapped_column(Integer, default=0)

    has_traceback_input: Mapped[bool] = mapped_column(Boolean, default=False)
    error_desc_length: Mapped[int] = mapped_column(Integer, default=0)
    error_family_syntax: Mapped[bool] = mapped_column(Boolean, default=False)
    error_family_type_or_value: Mapped[bool] = mapped_column(Boolean, default=False)

    ast_first_step: Mapped[bool] = mapped_column(Boolean, default=False)
    static_to_exec_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    failed_tool_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    tool_sequence_entropy: Mapped[float] = mapped_column(Float, default=0.0)
    total_investigation_steps: Mapped[int] = mapped_column(Integer, default=0)

    hypothesis_churn_count: Mapped[int] = mapped_column(Integer, default=0)
    hypothesis_rejection_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    countercheck_execution_rate: Mapped[float] = mapped_column(Float, default=0.0)
    direct_evidence_ratio: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="telemetry")


class BehaviorPredictionRecord(Base):
    """Represents a behavior archetype prediction for a session."""
    __tablename__ = "behavior_predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, index=True)
    predicted_archetype: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    top_factors_json: Mapped[str] = mapped_column(Text, default="[]")
    pedagogical_explanation: Mapped[str] = mapped_column(Text, default="")
    model_type: Mapped[str] = mapped_column(String(64), default="RandomForest")
    model_version: Mapped[str] = mapped_column(String(32), default="v0.4")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="prediction")

    @property
    def top_factors(self) -> List[Dict[str, Any]]:
        return json.loads(self.top_factors_json or "[]")

    @top_factors.setter
    def top_factors(self, val: List[Dict[str, Any]]):
        self.top_factors_json = json.dumps(val or [])
