"""State management and lifecycle transitions for TRACE."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field

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
        """Log a tool execution in the session's audit history."""
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

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a newly proposed hypothesis."""
        self.hypotheses.append(hypothesis)

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Lookup a hypothesis by its ID."""
        for hyp in self.hypotheses:
            if hyp.id == hypothesis_id:
                return hyp
        return None

    def update_hypothesis_status(
        self,
        hypothesis_id: str,
        new_status: HypothesisStatus,
        confidence: float,
        supporting_obs_id: Optional[str] = None,
        contradictory_obs_id: Optional[str] = None,
        rationale: str = "",
    ) -> None:
        """Update confidence, evidence links, and status of an existing hypothesis."""
        hyp = self.get_hypothesis(hypothesis_id)
        if not hyp:
            return
            
        hyp.status = new_status
        hyp.confidence = max(0.0, min(1.0, confidence))
        if supporting_obs_id and supporting_obs_id not in hyp.supporting_observation_ids:
            hyp.supporting_observation_ids.append(supporting_obs_id)
        if contradictory_obs_id and contradictory_obs_id not in hyp.contradictory_observation_ids:
            hyp.contradictory_observation_ids.append(contradictory_obs_id)
        if rationale:
            hyp.rationale = rationale

    def increment_iteration(self) -> bool:
        """Increment loop iteration. Returns False if max iterations exceeded."""
        self.iteration_count += 1
        if self.iteration_count >= self.max_iterations:
            return False
        return True
