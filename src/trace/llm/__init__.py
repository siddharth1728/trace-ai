"""LLM abstraction and structured reasoning schemas for TRACE."""

from trace.llm.mock_provider import MockLLMProvider
from trace.llm.openai_provider import OpenAICompatibleProvider
from trace.llm.prompts import (
    DIAGNOSIS_PROMPT_TEMPLATE,
    PLANNING_PROMPT_TEMPLATE,
    STEP_EVALUATION_PROMPT_TEMPLATE,
    SYSTEM_INVESTIGATION_PROMPT,
)
from trace.llm.provider import LLMProvider, LLMProviderFactory
from trace.llm.schemas import (
    ActionType,
    DiagnosisSchema,
    HypothesisEvaluationItem,
    InitialPlanSchema,
    NextActionDecision,
    PlanStepSchema,
)

__all__ = [
    "LLMProvider",
    "LLMProviderFactory",
    "MockLLMProvider",
    "OpenAICompatibleProvider",
    "SYSTEM_INVESTIGATION_PROMPT",
    "PLANNING_PROMPT_TEMPLATE",
    "STEP_EVALUATION_PROMPT_TEMPLATE",
    "DIAGNOSIS_PROMPT_TEMPLATE",
    "ActionType",
    "PlanStepSchema",
    "InitialPlanSchema",
    "HypothesisEvaluationItem",
    "NextActionDecision",
    "DiagnosisSchema",
]
