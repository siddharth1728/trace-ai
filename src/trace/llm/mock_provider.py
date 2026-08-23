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
    Grounds all decisions, hypothesis evaluations, and actions strictly in verified observations.
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
        """Formulate initial plan and candidate hypotheses based on strictly validated inputs."""
        # Check if non-empty traceback exists in prompt
        has_traceback = False
        if "TRACEBACK (if available):" in prompt:
            tb_section = prompt.split("TRACEBACK (if available):")[1].split("SOURCE CODE:")[0].strip()
            if tb_section and tb_section not in ("None provided", "None", "null", ""):
                has_traceback = True

        has_syntax = "syntax" in prompt.lower() or "invalid syntax" in prompt.lower()

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
                    title="Execute code in controlled sandbox to observe parser error",
                    tool_name="python_executor",
                    tool_args={"source_code": ""},
                    expected_outcome="Observe Python runtime parser error message.",
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
        """
        Decide next action by parsing ONLY the 'OBSERVATIONS RECORDED SO FAR' section
        and considering only observations with Success: True.
        """
        # 1. Isolate the observations section strictly
        obs_section = ""
        if "OBSERVATIONS RECORDED SO FAR:" in prompt:
            parts = prompt.split("OBSERVATIONS RECORDED SO FAR:")[1]
            if "CURRENT PLAN REMAINING STEPS:" in parts:
                obs_section = parts.split("CURRENT PLAN REMAINING STEPS:")[0]
            else:
                obs_section = parts

        # 2. Parse individual successful observation lines
        obs_lines = obs_section.strip().splitlines()
        successful_observations: List[Dict[str, str]] = []
        
        for line in obs_lines:
            obs_match = re.search(r"-\s+\[(obs_[a-zA-Z0-9]+)\]\s+Tool:\s+([a-zA-Z0-9_]+),\s+Success:\s+(True|False)\s+\|\s+Summary:\s+(.*)", line)
            if obs_match:
                obs_id = obs_match.group(1)
                tool_name = obs_match.group(2)
                is_success = (obs_match.group(3) == "True")
                summary = obs_match.group(4)
                if is_success:
                    successful_observations.append({
                        "id": obs_id,
                        "tool": tool_name,
                        "summary": summary,
                    })

        # 3. Extract hypothesis IDs from prompt
        hyp_ids = re.findall(r"\[(hyp_[a-zA-Z0-9_]+)\]", prompt)
        if not hyp_ids:
            hyp_ids = re.findall(r"hyp_[a-zA-Z0-9_]+", prompt)

        evaluations: List[HypothesisEvaluationItem] = []

        # If NO successful observations exist yet, do not finalize and do not support hypotheses
        if not successful_observations:
            return NextActionDecision(
                reasoning="No successful observations collected yet; executing next tool step.",
                action_type=ActionType.EXECUTE_TOOL,
                tool_name="ast_analyzer",
                tool_args={"source_code": ""},
                hypothesis_evaluations=[],
            )

        # Check what facts are confirmed in successful observations
        syntax_obs = next((o for o in successful_observations if "syntaxerror" in o["summary"].lower()), None)
        runtime_err_obs = next((o for o in successful_observations if ("error" in o["summary"].lower() or "failed" in o["summary"].lower() or "exception" in o["summary"].lower())), None)
        exec_obs = next((o for o in successful_observations if o["tool"] == "python_executor"), None)
        ast_obs = next((o for o in successful_observations if o["tool"] == "ast_analyzer"), None)

        if syntax_obs:
            for i, hid in enumerate(hyp_ids):
                if i == 0:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.CONFIRMED,
                            confidence=0.95,
                            supporting_obs_id=syntax_obs["id"],
                            rationale=f"AST parser confirmed exact SyntaxError ({syntax_obs['summary']}).",
                        )
                    )
                else:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.REJECTED,
                            confidence=0.05,
                            contradictory_obs_id=syntax_obs["id"],
                            rationale="Issue is purely syntactic, ruling out runtime logic/type hypotheses.",
                        )
                    )
            return NextActionDecision(
                reasoning="Deterministic AST observation confirmed SyntaxError; finalizing diagnosis.",
                action_type=ActionType.FINALIZE_DIAGNOSIS,
                hypothesis_evaluations=evaluations,
            )

        if exec_obs and runtime_err_obs:
            for i, hid in enumerate(hyp_ids):
                if i == 0 or i == 1:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.SUPPORTED,
                            confidence=0.90,
                            supporting_obs_id=runtime_err_obs["id"],
                            rationale=f"Controlled execution reproduced failure ({runtime_err_obs['summary']}).",
                        )
                    )
                else:
                    evaluations.append(
                        HypothesisEvaluationItem(
                            hypothesis_id=hid,
                            new_status=HypothesisStatus.WEAKENED,
                            confidence=0.20,
                            rationale="Evidence points specifically to runtime exception.",
                        )
                    )
            return NextActionDecision(
                reasoning="Controlled execution produced concrete runtime error observation; finalizing diagnosis.",
                action_type=ActionType.FINALIZE_DIAGNOSIS,
                hypothesis_evaluations=evaluations,
            )

        # If execution has not run yet and it's not a confirmed syntax error, run execution to verify runtime behavior
        if not exec_obs and not syntax_obs:
            return NextActionDecision(
                reasoning="Static/traceback step completed; running code in sandbox to observe runtime behavior.",
                action_type=ActionType.EXECUTE_TOOL,
                tool_name="python_executor",
                tool_args={"source_code": ""},
                hypothesis_evaluations=evaluations,
            )

        return NextActionDecision(
            reasoning="Investigation steps completed; finalizing diagnosis.",
            action_type=ActionType.FINALIZE_DIAGNOSIS,
            hypothesis_evaluations=evaluations,
        )

    def _formulate_diagnosis(self, prompt: str) -> DiagnosisSchema:
        """Formulate student diagnosis grounded strictly in observation data."""
        # Isolate observations section in diagnosis prompt
        obs_text = ""
        if "ALL OBSERVATIONS COLLECTED:" in prompt:
            obs_text = prompt.split("ALL OBSERVATIONS COLLECTED:")[1].split("EVALUATED HYPOTHESES:")[0]

        obs_lower = obs_text.lower()
        prompt_lower = prompt.lower()

        if "syntaxerror" in obs_lower or "syntax" in obs_lower:
            return DiagnosisSchema(
                problem_statement="The Python interpreter encountered a SyntaxError and could not parse the file.",
                investigation_summary="TRACE performed AST static analysis and identified the syntax error location.",
                likely_root_cause="A syntax error (e.g. missing colon, unbalanced parenthesis, or invalid keyword) prevents Python from parsing the code.",
                evidence_summary=[
                    "AST analyzer reported SyntaxError coordinates.",
                ],
                confidence=0.95,
                what_trace_checked=[
                    "Python AST Static Analysis",
                ],
                what_remains_uncertain=["None. The syntax error was deterministically verified."],
                learning_point="In Python, code must be syntactically valid before any lines can run. Common syntax errors include missing colons ':' after 'def', 'if', 'for', 'while', or mismatched parentheses/brackets.",
                suggested_fix_guidance="Check the indicated line and the line directly above it for missing colons, unclosed brackets, or invalid syntax.",
            )

        if "zerodivisionerror" in obs_lower or "division by zero" in obs_lower or "zerodivision" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with a ZeroDivisionError when performing arithmetic division.",
                investigation_summary="TRACE analyzed the source structure and reproduced the ZeroDivisionError in a controlled execution sandbox.",
                likely_root_cause="The denominator in a division operation evaluates to zero (e.g., len(items) on an empty collection or an unhandled 0 value).",
                evidence_summary=[
                    "Execution raised ZeroDivisionError: division by zero.",
                ],
                confidence=0.90,
                what_trace_checked=[
                    "Controlled Subprocess Sandbox Execution",
                ],
                what_remains_uncertain=["Whether caller expected empty inputs to return 0, None, or raise a custom exception."],
                learning_point="In Python, dividing any number by 0 raises a ZeroDivisionError. When computing averages or ratios, always verify that the divisor (such as len(numbers)) is greater than 0 before dividing.",
                suggested_fix_guidance="Add an input guard or conditional check (e.g., `if not numbers: return 0`) before performing the division.",
            )

        if "typeerror" in obs_lower or "attributeerror" in obs_lower or "nonetype" in obs_lower or "nonetype" in prompt_lower or "none" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with a TypeError/AttributeError due to an operation on an unexpected None value.",
                investigation_summary="TRACE analyzed code structure and reproduced the exception in a controlled execution sandbox.",
                likely_root_cause="A variable expected to be a collection or string evaluates to None at runtime when a method or operator is invoked.",
                evidence_summary=[
                    "Subprocess execution produced TypeError / AttributeError on NoneType value.",
                ],
                confidence=0.90,
                what_trace_checked=[
                    "Controlled Subprocess Sandbox Execution",
                ],
                what_remains_uncertain=["Whether the upstream function returning None was intentional or itself buggy."],
                learning_point="Functions or dict lookups in Python return None if a key is missing or no return statement executes. Calling methods (like .upper()) on None raises an exception.",
                suggested_fix_guidance="Check where the variable receives its value, and ensure default values or None-checks (e.g., `if value is None:`) are in place.",
            )

        if "indexerror" in obs_lower or "out of range" in obs_lower or "index" in prompt_lower:
            return DiagnosisSchema(
                problem_statement="The program crashes with an IndexError: list index out of range.",
                investigation_summary="TRACE analyzed code indexing and reproduced the out-of-bounds access in controlled execution.",
                likely_root_cause="An index accessed in a list, tuple, or string is equal to or greater than its length.",
                evidence_summary=[
                    "Execution produced IndexError: list index out of range.",
                ],
                confidence=0.90,
                what_trace_checked=[
                    "Controlled Subprocess Sandbox Execution",
                ],
                what_remains_uncertain=["Intended collection size assumptions in the student's specification."],
                learning_point="Python lists are 0-indexed, meaning valid indices range from 0 to len(list) - 1. Accessing index len(list) will always raise an IndexError.",
                suggested_fix_guidance="Check boundary conditions in loops or check `if len(items) > index:` before direct indexing.",
            )

        # General fallback
        return DiagnosisSchema(
            problem_statement="An issue was investigated in the target Python script.",
            investigation_summary="TRACE examined code structure and executed the script in a controlled sandbox.",
            likely_root_cause="The code logic or control flow does not satisfy the required input/output conditions.",
            evidence_summary=[
                "Execution observation captured runtime behavior.",
            ],
            confidence=0.80,
            what_trace_checked=[
                "Controlled Subprocess Sandbox Execution",
            ],
            what_remains_uncertain=["Exact expected domain specifications for all edge case inputs."],
            learning_point="Debugging requires matching expected state transitions at each step of execution against observed program state.",
            suggested_fix_guidance="Trace the variable values step by step through each conditional branch.",
        )
