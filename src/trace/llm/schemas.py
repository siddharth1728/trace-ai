"""Structured output schemas for LLM reasoning in TRACE."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from trace.core.models import HypothesisStatus


class ActionType(str, Enum):
    """Next action decided by the agent's reasoning loop."""
    EXECUTE_TOOL = "EXECUTE_TOOL"
    REPLAN = "REPLAN"
    FINALIZE_DIAGNOSIS = "FINALIZE_DIAGNOSIS"


class PlanStepSchema(BaseModel):
    """Schema for a proposed step in an investigation plan."""
    step_id: int
    title: str
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str


class InitialPlanSchema(BaseModel):
    """LLM structured output when formulating the initial investigation plan."""
    objective: str
    initial_hypotheses: List[str] = Field(
        default_factory=list,
        description="2-3 competing candidate hypotheses explaining the potential bug."
    )
    steps: List[PlanStepSchema] = Field(
        default_factory=list,
        description="Ordered list of investigation steps to collect evidence."
    )


class HypothesisEvaluationItem(BaseModel):
    """Evaluation update for an existing hypothesis based on new observation evidence."""
    hypothesis_id: str
    new_status: HypothesisStatus
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_obs_id: Optional[str] = None
    contradictory_obs_id: Optional[str] = None
    rationale: str


class NextActionDecision(BaseModel):
    """Agent decision for the next investigation step."""
    reasoning: str
    action_type: ActionType
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    hypothesis_evaluations: List[HypothesisEvaluationItem] = Field(default_factory=list)
    should_replan: bool = False
    replan_reason: Optional[str] = None


class DiagnosisSchema(BaseModel):
    """Structured LLM output for final evidence-grounded diagnosis."""
    problem_statement: str
    investigation_summary: str
    likely_root_cause: str
    evidence_summary: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    what_trace_checked: List[str] = Field(default_factory=list)
    what_remains_uncertain: List[str] = Field(default_factory=list)
    learning_point: str = Field(description="Student-friendly pedagogical takeaway explaining the concept.")
    suggested_fix_guidance: str = Field(description="Conceptual guidance on how to fix the issue without giving away raw replacement code.")
