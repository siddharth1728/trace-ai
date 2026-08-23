"""Targeted Counterexample & Disproof Engine for TRACE v0.2."""

import ast
import re
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import Hypothesis, Observation
from trace.core.state import AgentState
from trace.tools.executor import PythonExecutorTool


def extract_definitions_only(source_code: str) -> str:
    """
    Extract only function definitions, class definitions, and import statements
    from student code, removing crashing top-level script executions.
    """
    try:
        tree = ast.parse(source_code)
        def_lines = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
                segment = ast.get_source_segment(source_code, node)
                if segment:
                    def_lines.append(segment)
        if def_lines:
            return "\n\n".join(def_lines)
    except Exception:
        pass
    return source_code


class CounterexampleExperiment(BaseModel):
    """A targeted falsification experiment challenging a specific hypothesis."""
    id: str = Field(default_factory=lambda: f"cexp_{uuid.uuid4().hex[:6]}")
    hypothesis_id: str
    strategy: str
    description: str
    harness_code: str
    expected_exit_code: int = 0
    executed: bool = False
    passed: bool = False
    disproved: bool = False
    actual_output: str = ""
    evidence_id: Optional[str] = None


class CounterexampleEngine:
    """
    Generates and executes targeted minimal counterexample tests to challenge
    and verify debugging hypotheses in student code.
    """

    def __init__(self, executor: Optional[PythonExecutorTool] = None):
        self.executor = executor or PythonExecutorTool()

    def generate_experiment(
        self,
        hypothesis: Hypothesis,
        state: AgentState,
    ) -> Optional[CounterexampleExperiment]:
        """
        Generate a targeted minimal test harness to attempt disproof of a hypothesis.
        Uses signature inspection and template mutations based on common student bug patterns.
        """
        # Aggregate all diagnostic context
        obs_summaries = " ".join([o.summary for o in state.observations])
        context_text = f"{hypothesis.statement} {state.user_goal} {state.error_description or ''} {obs_summaries}".lower()
        code = state.source_code
        def_code = extract_definitions_only(code)

        # Parse AST to discover functions and their parameter counts
        func_info: List[Dict[str, Any]] = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    params = [a.arg for a in node.args.args]
                    func_info.append({"name": node.name, "params": params, "param_count": len(params)})
        except Exception:
            pass

        target = func_info[0] if func_info else None
        target_name = target["name"] if target else None
        param_count = target["param_count"] if target else 1

        # Strategy 1: NoneType / Missing Key / AttributeError
        if any(kw in context_text for kw in ["none", "typeerror", "attributeerror", "nonetype"]):
            if target_name:
                call_expr = f"{target_name}({{'id': 101, 'name': 'Alice', 'role': 'admin'}})" if param_count <= 1 else f"{target_name}({{'name': 'Alice'}}, 'extra')"
                harness = f"""{def_code}
# TRACE Automated Countercheck: Test with non-None valid dictionary value
try:
    res = {call_expr}
    print("COUNTERCHECK_PASS:", res)
except Exception as e:
    print("COUNTERCHECK_FAIL:", type(e).__name__, str(e))
    exit(1)
"""
                return CounterexampleExperiment(
                    hypothesis_id=hypothesis.id,
                    strategy="NON_NONE_VALID_INPUT",
                    description=f"Test '{target_name}' with valid non-None record to verify NoneType trigger.",
                    harness_code=harness,
                )

        # Strategy 2: ZeroDivision on Empty Collection / Formula
        if any(kw in context_text for kw in ["zerodivision", "empty", "division by zero", "division", "average", "percentage"]):
            if target_name:
                if param_count == 1:
                    call_expr = f"{target_name}([10.0, 20.0, 30.0])"
                elif param_count == 2:
                    call_expr = f"{target_name}(10.0, 20.0)"
                else:
                    call_expr = f"{target_name}([10.0, 20.0, 30.0])"

                harness = f"""{def_code}
# TRACE Automated Countercheck: Test with populated non-empty collection / valid divisor
try:
    res = {call_expr}
    print("COUNTERCHECK_PASS:", res)
except Exception as e:
    print("COUNTERCHECK_FAIL:", type(e).__name__, str(e))
    exit(1)
"""
                return CounterexampleExperiment(
                    hypothesis_id=hypothesis.id,
                    strategy="POPULATED_COLLECTION_INPUT",
                    description=f"Test '{target_name}' with valid arguments to test division trigger.",
                    harness_code=harness,
                )

        # Strategy 3: Boundary Index / IndexError
        if any(kw in context_text for kw in ["index", "out of range", "bound", "range", "element"]):
            if target_name:
                if param_count == 1:
                    call_expr = f"{target_name}(['item0', 'item1', 'item2', 'item3'])"
                elif param_count == 2:
                    call_expr = f"{target_name}(['item0', 'item1', 'item2', 'item3'], 1)"
                else:
                    call_expr = f"{target_name}(['item0', 'item1', 'item2', 'item3'])"

                harness = f"""{def_code}
# TRACE Automated Countercheck: Test with safe multi-element list
try:
    res = {call_expr}
    print("COUNTERCHECK_PASS:", res)
except Exception as e:
    print("COUNTERCHECK_FAIL:", type(e).__name__, str(e))
    exit(1)
"""
                return CounterexampleExperiment(
                    hypothesis_id=hypothesis.id,
                    strategy="SAFE_INDEX_INPUT",
                    description=f"Test '{target_name}' with safe multi-element list to verify index boundary assumption.",
                    harness_code=harness,
                )

        # Strategy 4: Negative Input / Discount / Validation
        if any(kw in context_text for kw in ["negative", "discount", "validation", "price"]):
            if target_name:
                call_expr = f"{target_name}(100.0, 20.0)" if param_count == 2 else f"{target_name}(100.0)"
                harness = f"""{def_code}
# TRACE Automated Countercheck: Test with valid standard positive arguments
try:
    res = {call_expr}
    print("COUNTERCHECK_PASS:", res)
except Exception as e:
    print("COUNTERCHECK_FAIL:", type(e).__name__, str(e))
    exit(1)
"""
                return CounterexampleExperiment(
                    hypothesis_id=hypothesis.id,
                    strategy="VALID_POSITIVE_INPUT",
                    description=f"Test '{target_name}' with standard valid positive parameters.",
                    harness_code=harness,
                )

        # Strategy 5: General Function Call with safe defaults
        if target_name:
            if param_count == 1:
                call_expr = f"{target_name}([10, 20, 30])"
            elif param_count == 2:
                call_expr = f"{target_name}(100.0, 10.0)"
            else:
                call_expr = f"{target_name}()"

            harness = f"""{def_code}
# TRACE Automated Countercheck: Verify code with safe input
try:
    res = {call_expr}
    print("COUNTERCHECK_PASS:", res)
except Exception as e:
    print("COUNTERCHECK_FAIL:", type(e).__name__, str(e))
    exit(1)
"""
            return CounterexampleExperiment(
                hypothesis_id=hypothesis.id,
                strategy="SAFE_EXECUTION_CHECK",
                description=f"Test '{target_name}' with safe arguments.",
                harness_code=harness,
            )

        # Fallback
        harness = f"""{def_code}
# TRACE Automated Countercheck: Verify code under standard execution
print("COUNTERCHECK_EXECUTION_COMPLETED")
"""
        return CounterexampleExperiment(
            hypothesis_id=hypothesis.id,
            strategy="STANDARD_EXECUTION_CHECK",
            description="Re-run student code structure in sandbox to check reproducibility.",
            harness_code=harness,
        )

    def run_experiment(
        self,
        experiment: CounterexampleExperiment,
        state: AgentState,
    ) -> Evidence:
        """
        Execute the counterexample experiment in the sandbox and record
        direct verification or disproof evidence.
        """
        result = self.executor.execute(source_code=experiment.harness_code)
        experiment.executed = True
        experiment.actual_output = result.data.get("stdout", "") + result.data.get("stderr", "")

        exit_code = result.data.get("exit_code", -1)
        experiment_passed = (exit_code == experiment.expected_exit_code and "COUNTERCHECK_FAIL" not in experiment.actual_output)
        experiment.passed = experiment_passed

        if not experiment_passed:
            experiment.disproved = True
            relation = EvidenceRelation.DISPROVES
            statement = f"Countercheck failed (exit code {exit_code}): Counter-experiment reproduced unexpected failure ({experiment.description})."
        else:
            experiment.disproved = False
            relation = EvidenceRelation.VERIFIES
            statement = f"Countercheck passed (exit code 0): Valid input test verified hypothesis ({experiment.description})."

        # Record observation
        obs = Observation(
            tool_name="counterexample_engine",
            input_args={"strategy": experiment.strategy, "description": experiment.description},
            output_data={"exit_code": exit_code, "stdout": experiment.actual_output},
            is_success=True,
            summary=statement,
            evidence_tags=["countercheck", experiment.strategy.lower()],
        )
        state.add_observation(obs)
        state.record_tool_call(
            tool_name="counterexample_engine",
            arguments={"strategy": experiment.strategy},
            success=True,
            execution_time_ms=15.0,
            observation_id=obs.id,
        )

        # Create Direct Evidence
        evidence = Evidence(
            observation_id=obs.id,
            tool_name="counterexample_engine",
            evidence_type=EvidenceType.DIRECT,
            statement=statement,
            raw_fact={"strategy": experiment.strategy, "exit_code": exit_code, "passed": experiment_passed},
            target_hypothesis_id=experiment.hypothesis_id,
            relation=relation,
            confidence_weight=1.0,
        )
        experiment.evidence_id = evidence.id
        state.add_evidence(evidence)

        # Link observation and experiment to hypothesis
        hyp = state.get_hypothesis(experiment.hypothesis_id)
        if hyp:
            if experiment.id not in hyp.counterexample_ids:
                hyp.counterexample_ids.append(experiment.id)
            if obs.id not in hyp.supporting_observation_ids and experiment_passed:
                hyp.supporting_observation_ids.append(obs.id)

        return evidence
