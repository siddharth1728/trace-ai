"""Pydantic Schemas for TRACE Telemetry, Features, Behavior Models & Profiles."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BehaviorArchetype(str, Enum):
    """Observable student debugging archetypes."""
    SYSTEMATIC_VERIFICATION = "SYSTEMATIC_VERIFICATION"
    RAPID_TRIAL_AND_ERROR = "RAPID_TRIAL_AND_ERROR"
    UNFOCUSED_EXPLORATION = "UNFOCUSED_EXPLORATION"


class TelemetryFeatures(BaseModel):
    """The 18-dimensional feature vector strictly representing student actions, code properties, and process dynamics."""
    session_id: str
    is_synthetic: bool = False
    problem_id: Optional[str] = "default"

    # [1-5] Code & Problem Complexity Context (Student's Starting Point)
    loc: int = Field(ge=0, description="Lines of code in submitted source")
    ast_node_count: int = Field(ge=0, description="Total AST structural elements")
    ast_max_depth: int = Field(ge=0, description="Maximum AST nesting depth")
    cyclomatic_complexity: int = Field(ge=1, description="Estimated branch decisions + 1")
    function_count: int = Field(ge=0, description="Number of function/method definitions")

    # [6-9] Student Input & Framing Quality (User Action Signals)
    has_traceback_input: bool = Field(description="Whether the student provided a raw stack trace")
    error_desc_length: int = Field(ge=0, description="Character length of problem/error description")
    error_family_syntax: bool = Field(description="Whether the bug is a SyntaxError")
    error_family_type_or_value: bool = Field(description="Whether the bug is a TypeError or ValueError")

    # [10-14] Investigation Process Cadence (How the Problem is Tackled)
    ast_first_step: bool = Field(description="Whether static analysis was executed before running")
    static_to_exec_ratio: float = Field(ge=0.0, description="Ratio of static inspection tool calls to execution tool calls")
    failed_tool_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of failed tool executions")
    tool_sequence_entropy: float = Field(ge=0.0, description="Normalized Shannon entropy of tool distribution")
    total_investigation_steps: int = Field(ge=0, description="Total distinct plan steps executed")

    # [15-18] Verification & Hypothesis Rigor (Grounded Scientific Method)
    hypothesis_churn_count: int = Field(ge=0, description="Total candidate hypotheses proposed")
    hypothesis_rejection_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of rejected hypotheses")
    countercheck_execution_rate: float = Field(ge=0.0, description="Executed counterchecks per hypothesis")
    direct_evidence_ratio: float = Field(ge=0.0, le=1.0, description="Direct evidence items / Total evidence items")

    def to_feature_vector(self) -> List[float]:
        """Convert features into an ordered 18-element float list for ML models."""
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
            float(self.hypothesis_churn_count),
            float(self.hypothesis_rejection_ratio),
            float(self.countercheck_execution_rate),
            float(self.direct_evidence_ratio),
        ]

    @classmethod
    def feature_names(cls) -> List[str]:
        """Return the canonical ordered list of feature names."""
        return [
            "loc",
            "ast_node_count",
            "ast_max_depth",
            "cyclomatic_complexity",
            "function_count",
            "has_traceback_input",
            "error_desc_length",
            "error_family_syntax",
            "error_family_type_or_value",
            "ast_first_step",
            "static_to_exec_ratio",
            "failed_tool_ratio",
            "tool_sequence_entropy",
            "total_investigation_steps",
            "hypothesis_churn_count",
            "hypothesis_rejection_ratio",
            "countercheck_execution_rate",
            "direct_evidence_ratio",
        ]


class LabelProvenance(BaseModel):
    """Metadata tracking human-verified or rule-assisted label provenance."""
    session_id: str
    label: BehaviorArchetype
    labeling_method: Literal["MANUAL_EXPERT", "HEURISTIC_VERIFIED", "CONSENSUS_AUDIT", "SYNTHETIC_BENCHMARK"]
    reviewer_id: str = "system"
    confidence: float = 1.0
    notes: Optional[str] = None
    dataset_version: str = "v0.4"
    created_at: datetime = Field(default_factory=utc_now)


class FeatureContribution(BaseModel):
    """Explains an individual feature's contribution to a model prediction."""
    feature_name: str
    feature_value: float
    contribution_weight: float
    description: str


class BehaviorPrediction(BaseModel):
    """Output of a behavior classification inference."""
    session_id: str
    predicted_archetype: BehaviorArchetype
    confidence: float = Field(ge=0.0, le=1.0)
    top_contributing_factors: List[FeatureContribution] = []
    pedagogical_explanation: str = ""
    model_type: str = "RandomForest"
    model_version: str = "v0.4"
    created_at: datetime = Field(default_factory=utc_now)


class DeterministicHabitStats(BaseModel):
    """100% deterministic, mathematically verifiable debugging habits across sessions."""
    total_sessions: int = 0
    ast_first_rate: float = 0.0  # Percentage of sessions where AST analysis preceded execution
    traceback_provided_rate: float = 0.0  # Percentage of sessions with stack traces
    countercheck_rigor_rate: float = 0.0  # Percentage of hypotheses tested with counterchecks
    avg_investigation_steps: float = 0.0
    avg_hypotheses_per_session: float = 0.0
    tool_failure_rate: float = 0.0


class StudentProfile(BaseModel):
    """Comprehensive debugging profile combining deterministic stats and AI detected patterns."""
    deterministic_habits: DeterministicHabitStats
    latest_prediction: Optional[BehaviorPrediction] = None
    archetype_history: Dict[str, int] = {}  # Archetype -> count of sessions
    key_strengths: List[str] = []
    growth_areas: List[str] = []
    updated_at: datetime = Field(default_factory=utc_now)
