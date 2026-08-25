"""Telemetry Extractor for TRACE v0.4.

Strictly extracts 18 defensible features reflecting:
1. Code & Problem Complexity Context (Student's Starting Point)
2. Student Input & Framing Quality (User Action Signals)
3. Investigation Process Cadence (How the Problem is Tackled)
4. Verification & Hypothesis Rigor (Grounded Scientific Method)

Excludes all internal agent mechanisms (prompt tokens, orchestrator retries, etc.).
"""

import ast
import math
from typing import Any, Dict, List, Optional

from trace.core.state import AgentState
from trace.db.models import SessionRecord
from trace.ml.schemas import TelemetryFeatures


def compute_ast_metrics(source_code: str) -> Dict[str, int]:
    """Deterministically parse Python source code into structural AST metrics."""
    if not source_code or not source_code.strip():
        return {
            "loc": 0,
            "ast_node_count": 0,
            "ast_max_depth": 0,
            "cyclomatic_complexity": 1,
            "function_count": 0,
        }

    loc = len([line for line in source_code.splitlines() if line.strip()])

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        # For unparseable syntax error code, return baseline structure
        return {
            "loc": loc,
            "ast_node_count": max(1, loc * 3),
            "ast_max_depth": 1,
            "cyclomatic_complexity": 1,
            "function_count": 0,
        }

    node_count = sum(1 for _ in ast.walk(tree))
    function_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))

    # Compute maximum AST depth
    def get_max_depth(node: ast.AST, current_depth: int = 1) -> int:
        children = list(ast.iter_child_nodes(node))
        if not children:
            return current_depth
        return max(get_max_depth(child, current_depth + 1) for child in children)

    max_depth = get_max_depth(tree)

    # Estimate cyclomatic complexity (branches + 1)
    branch_types = (
        ast.If,
        ast.For,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.Assert,
        ast.comprehension,
        ast.IfExp,
    )
    branch_count = sum(1 for node in ast.walk(tree) if isinstance(node, branch_types))
    cyclomatic_complexity = branch_count + 1

    return {
        "loc": loc,
        "ast_node_count": node_count,
        "ast_max_depth": max_depth,
        "cyclomatic_complexity": cyclomatic_complexity,
        "function_count": function_count,
    }


def compute_tool_entropy(tool_names: List[str]) -> float:
    """Compute normalized Shannon entropy of tool choice distribution."""
    if not tool_names:
        return 0.0

    counts: Dict[str, int] = {}
    for name in tool_names:
        counts[name] = counts.get(name, 0) + 1

    total = len(tool_names)
    num_unique = len(counts)
    if num_unique <= 1:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    # Normalize by log2(num_unique)
    max_entropy = math.log2(num_unique)
    return round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0


class TelemetryExtractor:
    """Extracts the 18-feature telemetry vector from an active AgentState or DB SessionRecord."""

    @classmethod
    def extract_from_state(
        cls,
        state: AgentState,
        problem_id: str = "default",
        is_synthetic: bool = False,
    ) -> TelemetryFeatures:
        """Extract features from in-memory AgentState."""
        ast_metrics = compute_ast_metrics(state.source_code)

        # Bug context & student framing
        error_text = f"{state.error_description or ''} {state.user_goal or ''} {state.traceback_input or ''}".lower()
        has_tb = bool(state.traceback_input and state.traceback_input.strip())
        error_desc_len = len((state.error_description or "") + (state.user_goal or ""))

        is_syntax = "syntaxerror" in error_text or "invalid syntax" in error_text
        is_type_val = any(err in error_text for err in ["typeerror", "valueerror", "attributeerror", "nonetype"])

        # Tool & process dynamics
        tool_names = [obs.tool_name for obs in state.observations]
        ast_first = bool(tool_names and tool_names[0] == "ast_analyzer")

        static_tools = sum(1 for t in tool_names if t in ["ast_analyzer", "traceback_parser", "file_reader"])
        exec_tools = sum(1 for t in tool_names if t in ["python_executor", "executor"])
        static_to_exec = round(static_tools / max(1, exec_tools), 4)

        failed_obs = sum(1 for obs in state.observations if not obs.is_success)
        total_obs = len(state.observations)
        failed_ratio = round(failed_obs / max(1, total_obs), 4)

        tool_entropy = compute_tool_entropy(tool_names)
        total_steps = len(state.current_plan.steps) if state.current_plan else len(state.observations)

        # Verification & hypothesis dynamics
        hyp_count = len(state.hypotheses)
        rejected_hyps = sum(
            1 for h in state.hypotheses if (hasattr(h.status, "value") and h.status.value in ["DISPROVEN", "REJECTED"]) or str(h.status) in ["DISPROVEN", "REJECTED"]
        )
        hyp_rejection_ratio = round(rejected_hyps / max(1, hyp_count), 4)

        # Counterchecks
        counterchecks = getattr(state, "counterchecks", [])
        executed_checks = sum(1 for c in counterchecks if getattr(c, "executed", False))
        countercheck_rate = round(executed_checks / max(1, hyp_count), 4)

        # Direct vs derived evidence
        evidence_list = state.evidence_store
        direct_ev = sum(
            1 for e in evidence_list if (hasattr(e.evidence_type, "value") and e.evidence_type.value == "DIRECT") or str(e.evidence_type) == "DIRECT"
        )
        direct_ratio = round(direct_ev / max(1, len(evidence_list)), 4)

        return TelemetryFeatures(
            session_id=state.session_id,
            is_synthetic=is_synthetic,
            problem_id=problem_id,
            loc=ast_metrics["loc"],
            ast_node_count=ast_metrics["ast_node_count"],
            ast_max_depth=ast_metrics["ast_max_depth"],
            cyclomatic_complexity=ast_metrics["cyclomatic_complexity"],
            function_count=ast_metrics["function_count"],
            has_traceback_input=has_tb,
            error_desc_length=error_desc_len,
            error_family_syntax=is_syntax,
            error_family_type_or_value=is_type_val,
            ast_first_step=ast_first,
            static_to_exec_ratio=static_to_exec,
            failed_tool_ratio=failed_ratio,
            tool_sequence_entropy=tool_entropy,
            total_investigation_steps=total_steps,
            hypothesis_churn_count=hyp_count,
            hypothesis_rejection_ratio=hyp_rejection_ratio,
            countercheck_execution_rate=countercheck_rate,
            direct_evidence_ratio=direct_ratio,
        )

    @classmethod
    def extract_from_session_record(
        self,
        record: SessionRecord,
        problem_id: Optional[str] = None,
        is_synthetic: bool = False,
    ) -> TelemetryFeatures:
        """Extract features from a persisted database SessionRecord."""
        ast_metrics = compute_ast_metrics(record.source_code or "")

        error_text = f"{record.error_description or ''} {record.user_goal or ''} {record.traceback_input or ''}".lower()
        has_tb = bool(record.traceback_input and record.traceback_input.strip())
        error_desc_len = len((record.error_description or "") + (record.user_goal or ""))

        is_syntax = "syntaxerror" in error_text or "invalid syntax" in error_text
        is_type_val = any(err in error_text for err in ["typeerror", "valueerror", "attributeerror", "nonetype"])

        tool_names = [obs.tool_name for obs in record.observations]
        ast_first = bool(tool_names and tool_names[0] == "ast_analyzer")

        static_tools = sum(1 for t in tool_names if t in ["ast_analyzer", "traceback_parser", "file_reader"])
        exec_tools = sum(1 for t in tool_names if t in ["python_executor", "executor"])
        static_to_exec = round(static_tools / max(1, exec_tools), 4)

        failed_obs = sum(1 for obs in record.observations if not obs.is_success)
        total_obs = len(record.observations)
        failed_ratio = round(failed_obs / max(1, total_obs), 4)

        tool_entropy = compute_tool_entropy(tool_names)
        total_steps = len(record.plan_steps) if record.plan_steps else len(record.observations)

        hyp_count = len(record.hypotheses)
        rejected_hyps = sum(1 for h in record.hypotheses if h.status in ["DISPROVEN", "REJECTED"])
        hyp_rejection_ratio = round(rejected_hyps / max(1, hyp_count), 4)

        counterchecks = record.counterchecks or []
        executed_checks = sum(1 for c in counterchecks if c.executed)
        countercheck_rate = round(executed_checks / max(1, hyp_count), 4)

        evidence_list = record.evidence or []
        direct_ev = sum(1 for e in evidence_list if e.evidence_type == "DIRECT")
        direct_ratio = round(direct_ev / max(1, len(evidence_list)), 4)

        resolved_problem_id = problem_id or record.file_path or (record.title[:30] if record.title else "default")

        return TelemetryFeatures(
            session_id=record.id,
            is_synthetic=is_synthetic,
            problem_id=resolved_problem_id,
            loc=ast_metrics["loc"],
            ast_node_count=ast_metrics["ast_node_count"],
            ast_max_depth=ast_metrics["ast_max_depth"],
            cyclomatic_complexity=ast_metrics["cyclomatic_complexity"],
            function_count=ast_metrics["function_count"],
            has_traceback_input=has_tb,
            error_desc_length=error_desc_len,
            error_family_syntax=is_syntax,
            error_family_type_or_value=is_type_val,
            ast_first_step=ast_first,
            static_to_exec_ratio=static_to_exec,
            failed_tool_ratio=failed_ratio,
            tool_sequence_entropy=tool_entropy,
            total_investigation_steps=total_steps,
            hypothesis_churn_count=hyp_count,
            hypothesis_rejection_ratio=hyp_rejection_ratio,
            countercheck_execution_rate=countercheck_rate,
            direct_evidence_ratio=direct_ratio,
        )
