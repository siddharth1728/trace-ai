"""Telemetry Domain Model, Feature Provenance, and Labeling Schemas for TRACE v0.4-A.

Strictly defines:
1. 5 Telemetry Categories (User Actions, Code Properties, Investigation Context, TRACE Agent Actions, Outcome)
2. Feature Provenance Metadata (source, category, description)
3. Raw TelemetryRecord vs. Tabular FeatureVector
4. Experimental 4-Archetype Behavior Taxonomy
5. Label Record with Human Review & Provenance Tracking
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryCategory(str, Enum):
    """5 Formal categories partitioning all recorded debugging telemetry."""
    USER_ACTIONS = "USER_ACTIONS"                  # What the student actually provided / did
    CODE_PROPERTIES = "CODE_PROPERTIES"            # Deterministic AST / complexity characteristics of submitted code
    INVESTIGATION_CONTEXT = "INVESTIGATION_CONTEXT"# Problem / bug environment (exception type, error family)
    TRACE_AGENT_ACTIONS = "TRACE_AGENT_ACTIONS"    # What TRACE itself did (MUST NOT be confused with student behavior)
    OUTCOME = "OUTCOME"                            # Final resolution status, duration, and verification state


class BehaviorArchetype(str, Enum):
    """Initial experimental 4-archetype behavioral taxonomy for v0.4-A."""
    SYSTEMATIC_VERIFIER = "SYSTEMATIC_VERIFIER"
    GUESS_AND_CHECK = "GUESS_AND_CHECK"
    SYMPTOM_FIXATED = "SYMPTOM_FIXATED"
    BLIND_TRIAL = "BLIND_TRIAL"

    # Compatibility aliases
    SYSTEMATIC_VERIFICATION = "SYSTEMATIC_VERIFIER"
    RAPID_TRIAL_AND_ERROR = "GUESS_AND_CHECK"
    UNFOCUSED_EXPLORATION = "BLIND_TRIAL"


class DataSourceType(str, Enum):
    """Explicit provenance marker distinguishing real user sessions from synthetic benchmark traces."""
    REAL = "REAL"
    SYNTHETIC = "SYNTHETIC"


class FeatureProvenance(BaseModel):
    """Identifiable metadata tracking the exact origin and category of an extracted feature."""
    name: str
    category: TelemetryCategory
    source_component: str
    description: str
    is_student_facing: bool = True  # True if directly attributable to the student's problem/process


class UserActionsTelemetry(BaseModel):
    """Signals reflecting student input and submission framing."""
    has_traceback_input: bool = False
    error_desc_length: int = 0
    user_goal_length: int = 0
    submitted_file_name_present: bool = False


class StudentBehaviorTelemetry(BaseModel):
    """Milestone v0.5 authentic student debugging behavioral dynamics (strictly separated from agent metrics)."""
    student_hypothesis_count: int = 0
    hypotheses_revised_count: int = 0
    hypotheses_supported_ratio: float = 0.0
    student_test_input_count: int = 0
    boundary_tests_count: int = 0
    tested_before_editing: bool = False
    code_revision_count: int = 0
    avg_seconds_between_revisions: float = 0.0
    avg_lines_modified_per_revision: float = 0.0
    regression_occurred: bool = False
    socratic_questions_asked: int = 0
    socratic_questions_answered: int = 0
    socratic_skip_rate: float = 0.0
    changed_approach_after_counterevidence: bool = False
    requested_explanation: bool = False


class CodePropertiesTelemetry(BaseModel):
    """Structural properties of the submitted Python code."""
    loc: int = 0
    ast_node_count: int = 0
    ast_max_depth: int = 0
    cyclomatic_complexity: int = 1
    function_count: int = 0


class InvestigationContextTelemetry(BaseModel):
    """Contextual characteristics of the bug/problem."""
    error_family_syntax: bool = False
    error_family_type_or_value: bool = False
    error_family_runtime_other: bool = False
    exception_name: Optional[str] = None


class TraceAgentActionsTelemetry(BaseModel):
    """Metrics tracking TRACE agent actions (explicitly segregated from student actions)."""
    total_tool_calls: int = 0
    failed_tool_calls: int = 0
    failed_tool_ratio: float = 0.0
    ast_first_step: bool = False
    static_to_exec_ratio: float = 0.0
    tool_sequence_entropy: float = 0.0
    total_plan_steps: int = 0
    replan_count: int = 0
    hypothesis_count: int = 0
    rejected_hypothesis_count: int = 0
    hypothesis_rejection_ratio: float = 0.0
    counterchecks_executed: int = 0
    countercheck_execution_rate: float = 0.0
    direct_evidence_count: int = 0
    derived_evidence_count: int = 0
    direct_evidence_ratio: float = 0.0


class OutcomeTelemetry(BaseModel):
    """Outcome and termination metrics."""
    session_status: str = "CREATED"
    is_verified: bool = False
    calibrated_confidence: float = 0.0


class TelemetryRecord(BaseModel):
    """Complete, partitioned telemetry record containing raw structured measures across all categories."""
    session_id: str
    data_source: DataSourceType = DataSourceType.REAL
    problem_id: str = "default"
    created_at: datetime = Field(default_factory=utc_now)

    user_actions: UserActionsTelemetry = Field(default_factory=UserActionsTelemetry)
    student_behavior: StudentBehaviorTelemetry = Field(default_factory=StudentBehaviorTelemetry)
    code_properties: CodePropertiesTelemetry = Field(default_factory=CodePropertiesTelemetry)
    investigation_context: InvestigationContextTelemetry = Field(default_factory=InvestigationContextTelemetry)
    trace_agent_actions: TraceAgentActionsTelemetry = Field(default_factory=TraceAgentActionsTelemetry)
    outcome: OutcomeTelemetry = Field(default_factory=OutcomeTelemetry)


class FeatureVector(BaseModel):
    """Tabular feature representation derived from TelemetryRecord with zero raw source code strings."""
    session_id: str
    data_source: DataSourceType = DataSourceType.REAL
    problem_id: str = "default"

    # [1-5] Code Properties (Student's Starting Point)
    loc: int = Field(ge=0)
    ast_node_count: int = Field(ge=0)
    ast_max_depth: int = Field(ge=0)
    cyclomatic_complexity: int = Field(ge=1)
    function_count: int = Field(ge=0)

    # [6-9] User Actions & Context Framing
    has_traceback_input: bool
    error_desc_length: int = Field(ge=0)
    error_family_syntax: bool
    error_family_type_or_value: bool

    # [10-14] Process Dynamics (How Problem Was Investigated)
    ast_first_step: bool
    static_to_exec_ratio: float = Field(ge=0.0)
    failed_tool_ratio: float = Field(ge=0.0, le=1.0)
    tool_sequence_entropy: float = Field(ge=0.0)
    total_investigation_steps: int = Field(ge=0)

    # [15-18] Verification & Hypothesis Rigor
    hypothesis_count: int = Field(ge=0)
    hypothesis_rejection_ratio: float = Field(ge=0.0, le=1.0)
    countercheck_execution_rate: float = Field(ge=0.0)
    direct_evidence_ratio: float = Field(ge=0.0, le=1.0)

    def to_feature_list(self) -> List[float]:
        """Convert into ordered float vector for ML experiments."""
        return [
            float(self.loc),
            float(self.ast_node_count),
            float(self.ast_max_depth),
            float(self.cyclomatic_complexity),
            float(self.function_count),
            1.0 if self.has_traceback_input else 0.0,
            float(self.error_desc_length),
            1.0 if self.error_family_syntax else 0.0,
            1.0 if self.error_family_type_or_value else 0.0,
            1.0 if self.ast_first_step else 0.0,
            float(self.static_to_exec_ratio),
            float(self.failed_tool_ratio),
            float(self.tool_sequence_entropy),
            float(self.total_investigation_steps),
            float(self.hypothesis_count),
            float(self.hypothesis_rejection_ratio),
            float(self.countercheck_execution_rate),
            float(self.direct_evidence_ratio),
        ]

    @classmethod
    def get_feature_provenance_map(cls) -> Dict[str, FeatureProvenance]:
        """Returns the formal provenance metadata for every feature in the vector."""
        return {
            "loc": FeatureProvenance(
                name="loc",
                category=TelemetryCategory.CODE_PROPERTIES,
                source_component="ASTAnalyzerTool",
                description="Lines of code in submitted source (excluding blank lines)",
            ),
            "ast_node_count": FeatureProvenance(
                name="ast_node_count",
                category=TelemetryCategory.CODE_PROPERTIES,
                source_component="ASTAnalyzerTool",
                description="Total number of nodes in abstract syntax tree",
            ),
            "ast_max_depth": FeatureProvenance(
                name="ast_max_depth",
                category=TelemetryCategory.CODE_PROPERTIES,
                source_component="ASTAnalyzerTool",
                description="Maximum AST nesting depth (e.g. loops inside branches)",
            ),
            "cyclomatic_complexity": FeatureProvenance(
                name="cyclomatic_complexity",
                category=TelemetryCategory.CODE_PROPERTIES,
                source_component="ASTAnalyzerTool",
                description="Estimated decision branches + 1",
            ),
            "function_count": FeatureProvenance(
                name="function_count",
                category=TelemetryCategory.CODE_PROPERTIES,
                source_component="ASTAnalyzerTool",
                description="Number of function / method definitions",
            ),
            "has_traceback_input": FeatureProvenance(
                name="has_traceback_input",
                category=TelemetryCategory.USER_ACTIONS,
                source_component="UserSessionInput",
                description="Whether the student provided a Python stack trace",
            ),
            "error_desc_length": FeatureProvenance(
                name="error_desc_length",
                category=TelemetryCategory.USER_ACTIONS,
                source_component="UserSessionInput",
                description="Character count of user goal & error description",
            ),
            "error_family_syntax": FeatureProvenance(
                name="error_family_syntax",
                category=TelemetryCategory.INVESTIGATION_CONTEXT,
                source_component="TracebackParserTool",
                description="Whether the bug belongs to SyntaxError family",
            ),
            "error_family_type_or_value": FeatureProvenance(
                name="error_family_type_or_value",
                category=TelemetryCategory.INVESTIGATION_CONTEXT,
                source_component="TracebackParserTool",
                description="Whether the bug belongs to TypeError / ValueError family",
            ),
            "ast_first_step": FeatureProvenance(
                name="ast_first_step",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="OrchestratorPlan",
                description="Whether static AST analysis was executed before code run",
            ),
            "static_to_exec_ratio": FeatureProvenance(
                name="static_to_exec_ratio",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="ToolRegistry",
                description="Ratio of static inspection tool calls to execution calls",
            ),
            "failed_tool_ratio": FeatureProvenance(
                name="failed_tool_ratio",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="ToolRegistry",
                description="Ratio of tool execution failures to total invocations",
            ),
            "tool_sequence_entropy": FeatureProvenance(
                name="tool_sequence_entropy",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="ToolRegistry",
                description="Normalized Shannon entropy of tool distribution",
            ),
            "total_investigation_steps": FeatureProvenance(
                name="total_investigation_steps",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="OrchestratorPlan",
                description="Total planned and executed investigation steps",
            ),
            "hypothesis_count": FeatureProvenance(
                name="hypothesis_count",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="HypothesisStore",
                description="Total candidate hypotheses proposed during session",
            ),
            "hypothesis_rejection_ratio": FeatureProvenance(
                name="hypothesis_rejection_ratio",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="HypothesisStore",
                description="Ratio of hypotheses rejected or disproven",
            ),
            "countercheck_execution_rate": FeatureProvenance(
                name="countercheck_execution_rate",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="CounterexampleEngine",
                description="Executed countercheck experiments per hypothesis",
            ),
            "direct_evidence_ratio": FeatureProvenance(
                name="direct_evidence_ratio",
                category=TelemetryCategory.TRACE_AGENT_ACTIONS,
                source_component="EvidenceStore",
                description="Direct empirical facts / Total evidence items",
            ),
        }


class DeterministicHabitStats(BaseModel):
    total_sessions: int = 0
    ast_first_rate: float = 0.0
    traceback_provided_rate: float = 0.0
    countercheck_rigor_rate: float = 0.0
    avg_investigation_steps: float = 0.0
    avg_hypotheses_per_session: float = 0.0
    tool_failure_rate: float = 0.0


# Compatibility Aliases and Profile DTOs
TelemetryFeatures = FeatureVector

class StudentProfile(BaseModel):
    deterministic_habits: DeterministicHabitStats = Field(default_factory=DeterministicHabitStats)
    key_strengths: List[str] = Field(default_factory=list)
    growth_areas: List[str] = Field(default_factory=list)
    updated_at: str = ""

