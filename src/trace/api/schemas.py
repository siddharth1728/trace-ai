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
    mode: str = Field(default="GUIDED", description="Investigation mode: 'GUIDED' or 'INTERACTIVE'")


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
    mode: str = "GUIDED"
    status: str
    confidence: float
    likely_root_cause: Optional[str] = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionSummaryDTO]
    total: int


# ============================================================================
# Milestone v0.5 Interactive Student Debugging DTOs
# ============================================================================

class StudentHypothesisDTO(BaseModel):
    id: str
    turn_number: int
    hypothesis_text: str
    target_function_or_line: Optional[str] = None
    student_confidence: Optional[float] = None
    status: str
    evaluation_observation_id: Optional[str] = None
    created_at: str


class CodeRevisionDTO(BaseModel):
    id: str
    revision_number: int
    source_code: str
    intent_notes: Optional[str] = None
    time_since_previous_sec: float
    lines_added: int
    lines_deleted: int
    lines_modified: int
    total_loc: int
    cyclomatic_complexity_delta: int
    modified_ast_nodes: List[str] = Field(default_factory=list)
    modified_functions: List[str] = Field(default_factory=list)
    execution_success: bool
    runtime_error_type: Optional[str] = None
    resolved_error: bool
    created_at: str


class StudentTestInputDTO(BaseModel):
    id: str
    turn_number: int
    input_expression: str
    student_rationale: Optional[str] = None
    is_boundary_case: bool
    executed: bool
    execution_success: bool
    stdout: str
    stderr: str
    exception_type: Optional[str] = None
    execution_time_ms: float
    created_at: str


class SocraticPromptDTO(BaseModel):
    id: str
    question_text: str
    focus_area: str
    target_code_snippet: Optional[str] = None
    suggested_options: List[str] = Field(default_factory=list)
    turn_number: int
    answered: bool = False
    student_response: Optional[str] = None
    skipped: bool = False


class InteractionTurnDTO(BaseModel):
    id: str
    turn_number: int
    speaker: str
    action_type: str
    content_text: str
    referenced_entity_id: Optional[str] = None
    created_at: str


class StudentActivitySummaryDTO(BaseModel):
    """Deterministic summary of student actions during a session."""
    revisions_count: int = 0
    hypotheses_count: int = 0
    custom_tests_count: int = 0
    boundary_tests_count: int = 0
    socratic_questions_answered: int = 0
    total_turns: int = 0


class SessionDetailResponse(BaseModel):
    """Complete detail snapshot of an investigation session."""
    id: str
    title: str
    user_goal: str
    source_code: str
    file_path: Optional[str] = None
    error_description: Optional[str] = None
    traceback_input: Optional[str] = None
    mode: str = "GUIDED"
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

    # v0.5 Interactive Student Artifacts
    student_hypotheses: List[StudentHypothesisDTO] = Field(default_factory=list)
    revisions: List[CodeRevisionDTO] = Field(default_factory=list)
    student_test_inputs: List[StudentTestInputDTO] = Field(default_factory=list)
    interaction_turns: List[InteractionTurnDTO] = Field(default_factory=list)
    active_socratic_prompt: Optional[SocraticPromptDTO] = None
    student_activity: Optional[StudentActivitySummaryDTO] = None


class CreateStudentHypothesisRequest(BaseModel):
    hypothesis_text: str = Field(..., min_length=2, description="Student's explanation of what is wrong")
    target_function_or_line: Optional[str] = None
    student_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class CreateCodeRevisionRequest(BaseModel):
    source_code: str = Field(..., min_length=1, description="Revised Python code snippet")
    intent_notes: Optional[str] = Field(None, description="What the student intended to change or fix")
    time_since_previous_sec: float = Field(default=0.0, ge=0.0)


class CreateStudentTestInputRequest(BaseModel):
    input_expression: str = Field(..., min_length=1, description="Python test call expression or variable setup")
    student_rationale: Optional[str] = None
    is_boundary_case: bool = False


class AnswerSocraticRequest(BaseModel):
    prompt_id: str
    student_response: Optional[str] = None
    skip: bool = False


class StudentTestExecutionResponse(BaseModel):
    test_id: str
    executed: bool
    execution_success: bool
    stdout: str
    stderr: str
    exception_type: Optional[str] = None
    execution_time_ms: float
    supports_student_hypothesis: Optional[bool] = None


class InteractiveTimelineResponse(BaseModel):
    session_id: str
    turns: List[InteractionTurnDTO]
    total_turns: int


class RevisionsListResponse(BaseModel):
    session_id: str
    revisions: List[CodeRevisionDTO]
    total: int


class InvestigationStartedResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
