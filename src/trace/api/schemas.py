"""Pydantic Data Transfer Objects (DTOs) for TRACE v0.3 REST API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request payload to create a new debugging session."""
    user_goal: str = Field(..., min_length=3, description="What the student wants to debug or understand")
    source_code: str = Field(..., min_length=1, description="Target Python source code to investigate")
    title: Optional[str] = Field(None, max_length=256, description="Short optional session title")
    error_description: Optional[str] = Field(None, description="Optional description of error observed")
    traceback_input: Optional[str] = Field(None, description="Optional raw Python traceback string")


class InvestigateRequest(BaseModel):
    """Request payload to trigger an investigation run."""
    provider: str = Field(default="mock", description="LLM provider name: 'mock' or 'openai'")
    max_iterations: int = Field(default=8, ge=1, le=15, description="Maximum agent tool iterations")


class PlanStepDTO(BaseModel):
    id: str
    step_index: int
    title: str
    tool_name: str
    status: str
    expected_outcome: str
    observation_id: Optional[str] = None


class ObservationDTO(BaseModel):
    id: str
    step_index: int
    tool_name: str
    summary: str
    is_success: bool
    input_args: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_tags: List[str] = Field(default_factory=list)
    created_at: str


class EvidenceDTO(BaseModel):
    id: str
    observation_id: Optional[str] = None
    target_hypothesis_id: Optional[str] = None
    evidence_type: str
    relation: str
    statement: str
    confidence_weight: float
    created_at: str


class HypothesisDTO(BaseModel):
    id: str
    statement: str
    status: str
    confidence: float
    rationale: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    counterexample_ids: List[str] = Field(default_factory=list)


class CountercheckDTO(BaseModel):
    id: str
    hypothesis_id: str
    strategy: str
    description: str
    harness_code: str
    executed: bool
    passed: bool
    disproved: bool
    actual_output: str


class FinalDiagnosisDTO(BaseModel):
    problem_statement: Optional[str] = None
    likely_root_cause: Optional[str] = None
    learning_point: Optional[str] = None
    suggested_fix_guidance: Optional[str] = None
    confidence: float = 0.0
    verified_hypothesis_id: Optional[str] = None
    countercheck_summary: Optional[str] = None
    what_trace_checked: List[str] = Field(default_factory=list)
    what_remains_uncertain: List[str] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)


class SessionSummaryDTO(BaseModel):
    """Condensed summary for session listing."""
    id: str
    title: str
    user_goal: str
    status: str
    confidence: float
    likely_root_cause: Optional[str] = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionSummaryDTO]
    total: int


class SessionDetailResponse(BaseModel):
    """Complete detail snapshot of an investigation session."""
    id: str
    title: str
    user_goal: str
    source_code: str
    file_path: Optional[str] = None
    error_description: Optional[str] = None
    traceback_input: Optional[str] = None
    status: str
    confidence: float
    created_at: str
    updated_at: str

    diagnosis: Optional[FinalDiagnosisDTO] = None
    plan_steps: List[PlanStepDTO] = Field(default_factory=list)
    observations: List[ObservationDTO] = Field(default_factory=list)
    evidence: List[EvidenceDTO] = Field(default_factory=list)
    hypotheses: List[HypothesisDTO] = Field(default_factory=list)
    counterchecks: List[CountercheckDTO] = Field(default_factory=list)


class InvestigationStartedResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
