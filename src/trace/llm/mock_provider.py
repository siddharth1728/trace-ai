"""Deterministic Mock and Rule-based LLM Provider for reproducible testing."""

import re
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

from trace.core.models import HypothesisStatus
from trace.llm.provider import LLMProvider
from trace.llm.schemas import (
    ActionType,
    DiagnosisSchema,
    HypothesisEvaluationItem,
    InitialPlanSchema,
    NextActionDecision,
    PlanStepSchema,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Deterministic rule-based LLM provider for offline testing and evaluation.
    Inspects prompts using semantic heuristics to generate valid structured responses.
    """

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return "Deterministic Mock LLM Response."

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if issubclass(response_model, InitialPlanSchema):
            return self._plan_investigation(prompt)  # type: ignore
        elif issubclass(response_model, NextActionDecision):
            return self._decide_next_action(prompt)  # type: ignore
        elif issubclass(response_model, DiagnosisSchema):
            return self._formulate_diagnosis(prompt)  # type: ignore

        # Fallback to default instance
        return response_model.model_validate({})

    def _plan_investigation(self, prompt: str) -> InitialPlanSchema:
        """Formulate initial plan and candidate hypotheses based on prompt cues."""
        has_traceback = "TRACEBACK" in prompt and len(prompt.split("TRACEBACK (if available):")[1].split("SOURCE CODE:")[0].strip()) > 5
        has_syntax = "syntax" in prompt.lower() or "invalid syntax" in prompt.lower()
        has_type = "type" in prompt.lower() or "nonetype" in prompt.lower()
        has_zero_div = "zerodivision" in prompt.lower() or "division by zero" in prompt.lower() or "empty" in prompt.lower()
        has_index = "index" in prompt.lower() or "out of range" in prompt.lower() or "bound" in prompt.lower()

        # Step 1: Initial tool selection
        steps: List[PlanStepSchema] = []
        hypotheses: List[str] = []

        if has_traceback:
            hypotheses = [
                "The exception reported in traceback indicates an unhandled runtime edge case.",
                "A variable value becomes None or an unexpected data type at runtime.",
                "Input bounds or validation are missing before calculation.",
            ]
            steps = [
                PlanStepSchema(
                    step_id=1,
                    title="Parse traceback to extract failing frame and exception",
                    tool_name="traceback_parser",
                    tool_args={"traceback_text": ""},
                    expected_outcome="Extract exception type, file, line number, and stack context.",
                ),
                PlanStepSchema(
                    step_id=2,
                    title="Inspect AST structure of the failing code",
                    tool_name="ast_analyzer",
                    tool_args={"source_code": ""},
                    expected_outcome="Analyze variables, functions, and control flow around the error line.",
                ),
                PlanStepSchema(
                    step_id=3,
                    title="Execute code in controlled sandbox to reproduce error",
                    tool_name="python_executor",
                    tool_args={"source_code": ""},
                    expected_outcome="Confirm reproducible failure and stderr output.",
                ),
            ]
        elif has_syntax:
            hypotheses = [
                "The code has a syntax error such as a missing colon, bracket, or typo.",
                "An invalid token or unexpected indentation exists.",
                "An unclosed string or parenthesis extends across lines.",
            ]
            steps = [
                PlanStepSchema(
                    step_id=1,
                    title="Run AST analyzer to identify exact syntax error location",
                    tool_name="ast_analyzer",
                    tool_args={"source_code": ""},
                    expected_outcome="Locate exact line number and offset of syntax failure.",
                ),
                PlanStepSchema(
                    step_id=2,
                    title="Execute code to observe Python parser error message",
                    tool_name="python_executor",
                    tool_args={"source_code": ""},
                    expected_outcome="Confirm Python runtime parser error message.",
                ),
            ]
        else:
            hypotheses = [
                "The code fails due to an unexpected runtime exception on specific inputs.",
                "The logic contains a semantic calculation or boundary error.",
                "A variable is referenced before proper assignment or type conversion.",
            ]
            steps = [
                PlanStepSchema(
                    step_id=1,
                    title="Perform static AST analysis on code structure",
                    tool_name="ast_analyzer",
                    tool_args={"source_code": ""},
                    expected_outcome="Identify defined functions, variable assignments, and branches.",
                ),
                PlanStepSchema(
                    step_id=2,
                    title="Run code in controlled execution sandbox",
                    tool_name="python_executor",
                    tool_args={"source_code": ""},
                    expected_outcome="Observe actual runtime behavior, exit code, and stdout/stderr.",
                ),
            ]

        return InitialPlanSchema(
            objective="Systematically investigate the root cause of the reported issue using static analysis and controlled execution.",
            initial_hypotheses=hypotheses,
            steps=steps,
        )

    def _decide_next_action(self, prompt: str) -> NextActionDecision:
        """Decide the next action based on current observations and hypotheses in the prompt."""
        # Extract observations and hypotheses mentions from prompt
        evaluations: List[HypothesisEvaluationItem] = []

        has_syntax_obs = "syntaxerror" in prompt.lower()
        has_runtime_obs = "zerodivisionerror" in prompt.lower() or "typeerror" in prompt.lower() or "indexerror" in prompt.lower() or "runtime_error" in prompt.lower()
        has_exec_obs = "execution" in prompt.lower() or "exit code" in prompt.lower()
        has_ast_obs = "ast analysis" in prompt.lower()

        # Extract hypothesis IDs from prompt
        hyp_ids = re.findall(r"\[(hyp_[a-zA-Z0-9_]+)\]", prompt)
        if not hyp_ids:
            hyp_ids = re.findall(r"hyp_[a-zA-Z0-9_]+", prompt)

        if has_syntax_obs:
            for i, hid in enumerate(hyp_ids):
                if i == 0:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.CONFIRMED,
                            confidence=0.95,
                            rationale="AST parser and execution confirmed deterministic SyntaxError location.",
                        )
                    )
                else:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.REJECTED,
                            confidence=0.05,
                            rationale="Issue is purely syntactic, ruling out runtime type/logic hypotheses.",
                        )
                    )
            return NextActionDecision(
                reasoning="Sufficient deterministic evidence from AST analyzer confirms exact syntax error.",
                action_type=ActionType.FINALIZE_DIAGNOSIS,
                hypothesis_evaluations=evaluations,
            )

        if has_runtime_obs and has_exec_obs:
            for i, hid in enumerate(hyp_ids):
                if i == 0 or i == 1:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.SUPPORTED,
                            confidence=0.90,
                            rationale="Controlled execution and traceback confirmed exception type and failing frame.",
                        )
                    )
                else:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.WEAKENED,
                            confidence=0.20,
                            rationale="Evidence points specifically to runtime exception rather than generic logic issue.",
                        )
                    )
            return NextActionDecision(
                reasoning="Collected strong evidence from traceback and execution reproducing the runtime failure.",
                action_type=ActionType.FINALIZE_DIAGNOSIS,
                hypothesis_evaluations=evaluations,
            )

        # If we have only 1 observation and remaining steps, proceed to next tool
        return NextActionDecision(
            reasoning="Need additional dynamic evidence from execution to confirm hypothesis.",
            action_type=ActionType.EXECUTE_TOOL,
            tool_name="python_executor",
            tool_args={"source_code": ""},
            hypothesis_evaluations=evaluations,
        )

    def _formulate_diagnosis(self, prompt: str) -> DiagnosisSchema:
        """Formulate a student-oriented diagnosis backed by evidence."""
        prompt_lower = prompt.lower()

        if "syntaxerror" in prompt_lower or "syntax" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The Python interpreter encountered a SyntaxError and could not parse the file.",
                investigation_summary="TRACE performed AST static analysis and verified parser output in the sandbox.",
                likely_root_cause="A syntax error (e.g. missing colon, unbalanced parenthesis, or invalid keyword) prevents Python from parsing the code.",
                evidence_summary=[
                    "AST analyzer reported SyntaxError with line and column coordinates.",
                    "Subprocess execution exited with non-zero exit code during parsing phase.",
                ],
                confidence=0.95,
                what_trace_checked=[
                    "Python AST parsing",
                    "Syntax token positioning",
                    "Subprocess execution validation",
                ],
                what_remains_uncertain=["None. The syntax error was deterministically verified."],
                learning_point="In Python, Python code must be syntactically valid before any lines can run. Common syntax errors include missing colons ':' after 'def', 'if', 'for', 'while', or mismatched parentheses/brackets.",
                suggested_fix_guidance="Check the indicated line and the line directly above it for missing colons, unclosed brackets, or invalid syntax.",
            )

        if "zerodivisionerror" in prompt_lower or "division by zero" in prompt_lower or "average" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with a ZeroDivisionError when performing arithmetic division.",
                investigation_summary="TRACE parsed the traceback, verified the AST division operator, and reproduced the ZeroDivisionError in a sandbox.",
                likely_root_cause="The denominator in a division operation evaluates to zero (e.g., len(items) on an empty collection or an unhandled 0 value).",
                evidence_summary=[
                    "Execution raised ZeroDivisionError: division by zero.",
                    "AST analysis identified division node in the target function without a zero-check guard.",
                ],
                confidence=0.92,
                what_trace_checked=[
                    "Division operator operands in AST",
                    "Runtime execution on empty / zero inputs",
                    "Traceback frame stack",
                ],
                what_remains_uncertain=["Whether caller expected empty lists to return 0, None, or raise a custom exception."],
                learning_point="In Python, dividing any number by 0 raises a ZeroDivisionError. When computing averages or ratios, always verify that the divisor (such as len(numbers)) is greater than 0 before dividing.",
                suggested_fix_guidance="Add an input guard or conditional check (e.g., `if not numbers: return 0`) before performing the division.",
            )

        if "typeerror" in prompt_lower or "nonetype" in prompt_lower or "none" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with a TypeError due to an operation on an unexpected type (e.g., NoneType).",
                investigation_summary="TRACE traced variable assignments, inspected AST calls, and reproduced the TypeError in controlled execution.",
                likely_root_cause="A variable expected to be a collection or object evaluates to None (or an incompatible type) at runtime when a method or operator is invoked.",
                evidence_summary=[
                    "Subprocess execution produced a TypeError.",
                    "Traceback identified the exact line where the incompatible operation occurred.",
                ],
                confidence=0.90,
                what_trace_checked=[
                    "Traceback error line and exception type",
                    "Variable assignment flow in AST",
                    "Subprocess execution output",
                ],
                what_remains_uncertain=["Whether the upstream function returning None was intentional or itself buggy."],
                learning_point="Functions in Python return None by default if no return statement is executed. Attempting to access attributes, index, or iterate over None raises a TypeError.",
                suggested_fix_guidance="Check where the variable receives its value, and ensure default values or None-checks (e.g., `if value is None:`) are in place.",
            )

        if "indexerror" in prompt_lower or "out of range" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with an IndexError: list index out of range.",
                investigation_summary="TRACE analyzed list indexing operations and reproduced the out-of-bounds access in controlled execution.",
                likely_root_cause="An index accessed in a list, tuple, or string is equal to or greater than its length, or the collection is empty.",
                evidence_summary=[
                    "Execution produced IndexError: list index out of range.",
                    "Traceback pointed to indexing operation.",
                ],
                confidence=0.90,
                what_trace_checked=[
                    "List indexing operations in AST",
                    "Traceback frame",
                    "Execution with various collection lengths",
                ],
                what_remains_uncertain=["Intended collection size assumptions in the student's specification."],
                learning_point="Python lists are 0-indexed, meaning valid indices range from 0 to len(list) - 1. Accessing index len(list) will always raise an IndexError.",
                suggested_fix_guidance="Check boundary conditions in loops or check `if len(items) > index:` before direct indexing.",
            )

        # General / Logic Error fallback diagnosis
        return DiagnosisSchema(
            problem_statement="An issue was identified during code investigation.",
            investigation_summary="TRACE examined code structure with AST analyzer and executed the script in a controlled sandbox.",
            likely_root_cause="The code logic or control flow does not satisfy the required input/output conditions.",
            evidence_summary=[
                "Static AST analysis checked branches and variable assignments.",
                "Subprocess execution completed with observation logs.",
            ],
            confidence=0.85,
            what_trace_checked=[
                "Function definitions and control flow",
                "Subprocess execution output",
            ],
            what_remains_uncertain=["Exact expected domain specifications for all edge case inputs."],
            learning_point="Debugging requires matching expected state transitions at each step of execution against observed program state.",
            suggested_fix_guidance="Trace the variable values step by step through each conditional branch.",
        )
