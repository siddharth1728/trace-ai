"""State management and lifecycle transitions for TRACE."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field

from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import (
    FinalDiagnosis,
    Hypothesis,
    HypothesisStatus,
    InvestigationPlan,
    Observation,
    PlanStep,
    StepStatus,
)


class LifecycleState(str, Enum):
    """Explicit lifecycle states for the investigation agent."""
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    INVESTIGATING = "INVESTIGATING"
    TESTING = "TESTING"
    EVALUATING = "EVALUATING"
    REPLANNING = "REPLANNING"
    DIAGNOSING = "DIAGNOSING"
    EXPLAINING = "EXPLAINING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


# Valid state transitions graph
VALID_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.CREATED: {LifecycleState.UNDERSTANDING, LifecycleState.BLOCKED},
    LifecycleState.UNDERSTANDING: {LifecycleState.PLANNING, LifecycleState.BLOCKED},
    LifecycleState.PLANNING: {LifecycleState.INVESTIGATING, LifecycleState.BLOCKED},
    LifecycleState.INVESTIGATING: {
        LifecycleState.TESTING,
        LifecycleState.EVALUATING,
        LifecycleState.REPLANNING,
        LifecycleState.DIAGNOSING,
        LifecycleState.BLOCKED,
    },
    LifecycleState.TESTING: {
        LifecycleState.EVALUATING,
        LifecycleState.INVESTIGATING,
        LifecycleState.BLOCKED,
    },
    LifecycleState.EVALUATING: {
        LifecycleState.INVESTIGATING,
        LifecycleState.TESTING,
        LifecycleState.REPLANNING,
        LifecycleState.DIAGNOSING,
        LifecycleState.BLOCKED,
    },
    LifecycleState.REPLANNING: {
        LifecycleState.INVESTIGATING,
        LifecycleState.DIAGNOSING,
        LifecycleState.BLOCKED,
    },
    LifecycleState.DIAGNOSING: {LifecycleState.EXPLAINING, LifecycleState.BLOCKED},
    LifecycleState.EXPLAINING: {LifecycleState.COMPLETED, LifecycleState.BLOCKED},
    LifecycleState.COMPLETED: set(),  # Terminal
    LifecycleState.BLOCKED: set(),    # Terminal
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal lifecycle transition is attempted."""
    def __init__(self, from_state: LifecycleState, to_state: LifecycleState):
        super().__init__(
            f"Invalid state transition: Cannot move from {from_state.value} to {to_state.value}"
        )
        self.from_state = from_state
        self.to_state = to_state


class ToolCallRecord(BaseModel):
    """Record of a tool invocation for audit and debugging."""
    call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool
    execution_time_ms: float
    observation_id: Optional[str] = None
    error: Optional[str] = None


class AgentState(BaseModel):
    """Complete, explicit agent state model for TRACE investigation sessions."""
    session_id: str = Field(default_factory=lambda: f"trace_sess_{uuid.uuid4().hex[:10]}")
    user_goal: str
    source_code: str
    file_path: Optional[str] = None
    error_description: Optional[str] = None
    traceback_input: Optional[str] = None
    
    current_plan: Optional[InvestigationPlan] = None
    current_step_index: int = 0
    completed_steps: List[PlanStep] = Field(default_factory=list)
    
    observations: List[Observation] = Field(default_factory=list)
    evidence_store: List[Evidence] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    tool_history: List[ToolCallRecord] = Field(default_factory=list)
    
    iteration_count: int = 0
    max_iterations: int = Field(default=8, ge=1, le=20)
    
    status: LifecycleState = LifecycleState.CREATED
    final_diagnosis: Optional[FinalDiagnosis] = None
    confidence: float = 0.0
    blocked_reason: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def transition_to(self, new_state: LifecycleState, reason: Optional[str] = None) -> None:
        """Enforce strict lifecycle state transition rules."""
        if new_state == self.status:
            return
            
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(self.status, new_state)
            
        self.status = new_state
        if new_state == LifecycleState.BLOCKED and reason:
            self.blocked_reason = reason

    def is_terminal(self) -> bool:
        """Check if the agent reached a terminal state."""
        return self.status in {LifecycleState.COMPLETED, LifecycleState.BLOCKED}

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        success: bool,
        execution_time_ms: float,
        observation_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> ToolCallRecord:
        """Audit log an executed tool call."""
        record = ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            success=success,
            execution_time_ms=execution_time_ms,
            observation_id=observation_id,
            error=error,
        )
        self.tool_history.append(record)
        return record

    def add_observation(self, observation: Observation) -> None:
        """Add an observation produced by a tool."""
        self.observations.append(observation)

    def add_evidence(self, evidence: Evidence) -> None:
        """Add an atomic evidence record and link to target hypothesis."""
        self.evidence_store.append(evidence)
        hyp = self.get_hypothesis(evidence.target_hypothesis_id)
        if hyp:
            if evidence.is_supporting():
                if evidence.id not in hyp.supporting_evidence_ids:
                    hyp.supporting_evidence_ids.append(evidence.id)
            elif evidence.is_contradicting():
                if evidence.id not in hyp.contradictory_evidence_ids:
                    hyp.contradictory_evidence_ids.append(evidence.id)

    def get_evidence_for_hypothesis(self, hypothesis_id: str) -> List[Evidence]:
        """Get all evidence linked to a specific hypothesis."""
        return [e for e in self.evidence_store if e.target_hypothesis_id == hypothesis_id]

    def get_direct_supporting_evidence(self, hypothesis_id: str) -> List[Evidence]:
        """Get all direct supporting evidence items for a hypothesis."""
        return [
            e for e in self.evidence_store
            if e.target_hypothesis_id == hypothesis_id and e.is_supporting() and e.is_direct()
        ]

    def get_contradicting_evidence(self, hypothesis_id: str) -> List[Evidence]:
        """Get all contradicting or disproving evidence items for a hypothesis."""
        return [
            e for e in self.evidence_store
            if e.target_hypothesis_id == hypothesis_id and e.is_contradicting()
        ]

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a newly proposed hypothesis."""
        self.hypotheses.append(hypothesis)

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Lookup a hypothesis by its ID."""
        for hyp in self.hypotheses:
            if hyp.id == hypothesis_id:
                return hyp
        return None

    def get_observation(self, observation_id: str) -> Optional[Observation]:
        """Lookup an observation by its ID."""
        for obs in self.observations:
            if obs.id == observation_id:
                return obs
        return None

    def get_successful_observations(self) -> List[Observation]:
        """Return all observations that executed successfully."""
        return [obs for obs in self.observations if obs.is_success]

    def update_hypothesis_status(
        self,
        hypothesis_id: str,
        new_status: HypothesisStatus,
        confidence: float,
        supporting_obs_id: Optional[str] = None,
        contradictory_obs_id: Optional[str] = None,
        rationale: str = "",
    ) -> None:
        """
        Update confidence, evidence links, and status of an existing hypothesis.
        Enforces strict domain-layer evidence grounding rules:
        - SUPPORTED / CONFIRMED / VERIFIED requires a verified, successful supporting observation.
        - Unsupported hypotheses are capped at <= 0.40 confidence and remain PROPOSED/WEAKENED.
        """
        hyp = self.get_hypothesis(hypothesis_id)
        if not hyp:
            return

        # Check supporting observation validity
        valid_supporting_obs = False
        if supporting_obs_id:
            obs = self.get_observation(supporting_obs_id)
            if obs and obs.is_success:
                valid_supporting_obs = True
                if supporting_obs_id not in hyp.supporting_observation_ids:
                    hyp.supporting_observation_ids.append(supporting_obs_id)

        # Check contradictory observation validity
        if contradictory_obs_id:
            c_obs = self.get_observation(contradictory_obs_id)
            if c_obs and c_obs.is_success:
                if contradictory_obs_id not in hyp.contradictory_observation_ids:
                    hyp.contradictory_observation_ids.append(contradictory_obs_id)

        # Evidence Grounding Gate
        if new_status in (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED, HypothesisStatus.VERIFIED):
            if not valid_supporting_obs and not hyp.supporting_observation_ids and not hyp.supporting_evidence_ids:
                # Disallow ungrounded high confidence/supported status
                hyp.status = HypothesisStatus.PROPOSED
                hyp.confidence = min(max(0.0, confidence), 0.40)
                hyp.rationale = rationale or "Awaiting successful supporting tool observation."
                return

        # If valid or other status (REJECTED/WEAKENED/PROPOSED/VERIFICATION_PENDING/DISPROVEN)
        hyp.status = new_status
        hyp.confidence = max(0.0, min(1.0, confidence))
        if rationale:
            hyp.rationale = rationale

    def increment_iteration(self) -> bool:
        """Increment loop iteration. Returns False if max iterations exceeded."""
        self.iteration_count += 1
        if self.iteration_count >= self.max_iterations:
            return False
        return True
