"""Deterministic 5-Category Telemetry Extractor with Explicit Feature Provenance for TRACE v0.4-A."""

import ast
import math
from typing import Any, Dict, List, Optional

from trace.ml.schemas import (
    CodePropertiesTelemetry,
    DataSourceType,
    FeatureVector,
    InvestigationContextTelemetry,
    OutcomeTelemetry,
    TelemetryRecord,
    TraceAgentActionsTelemetry,
    UserActionsTelemetry,
)


class TelemetryExtractor:
    """Extracts raw 5-category telemetry and derived tabular feature vectors from agent states and session records."""

    @classmethod
    def extract_telemetry_record(
        cls,
        session_record: Any,
        state: Optional[Any] = None,
        data_source: DataSourceType = DataSourceType.REAL,
        problem_id: str = "default",
    ) -> TelemetryRecord:
        """Extract a structured TelemetryRecord partitioned into 5 explicit categories."""
        # 1. User Actions
        user_actions = cls._extract_user_actions(session_record)

        # 2. Code Properties
        source_code = getattr(session_record, "source_code", "") or ""
        code_props = cls._extract_code_properties(source_code)

        # 3. Investigation Context
        inv_context = cls._extract_investigation_context(session_record)

        # 4. TRACE Agent Actions (Segregated from user actions)
        agent_actions = cls._extract_agent_actions(session_record, state)

        # 5. Outcome
        outcome = cls._extract_outcome(session_record, state)

        resolved_problem_id = (
            problem_id
            if problem_id != "default"
            else getattr(session_record, "file_path", None)
            or (getattr(session_record, "title", "default")[:30])
        )
        
        session_id_val = str(getattr(session_record, "id", getattr(session_record, "session_id", "unknown")))

        return TelemetryRecord(
            session_id=session_id_val,
            data_source=data_source,
            problem_id=resolved_problem_id,
            user_actions=user_actions,
            code_properties=code_props,
            investigation_context=inv_context,
            trace_agent_actions=agent_actions,
            outcome=outcome,
        )

    @classmethod
    def extract_feature_vector(cls, telemetry: TelemetryRecord) -> FeatureVector:
        """Convert a TelemetryRecord into a clean numerical/categorical tabular FeatureVector (zero raw code)."""
        cp = telemetry.code_properties
        ua = telemetry.user_actions
        ic = telemetry.investigation_context
        ta = telemetry.trace_agent_actions

        return FeatureVector(
            session_id=telemetry.session_id,
            data_source=telemetry.data_source,
            problem_id=telemetry.problem_id,
            loc=cp.loc,
            ast_node_count=cp.ast_node_count,
            ast_max_depth=cp.ast_max_depth,
            cyclomatic_complexity=cp.cyclomatic_complexity,
            function_count=cp.function_count,
            has_traceback_input=ua.has_traceback_input,
            error_desc_length=ua.error_desc_length,
            error_family_syntax=ic.error_family_syntax,
            error_family_type_or_value=ic.error_family_type_or_value,
            ast_first_step=ta.ast_first_step,
            static_to_exec_ratio=ta.static_to_exec_ratio,
            failed_tool_ratio=ta.failed_tool_ratio,
            tool_sequence_entropy=ta.tool_sequence_entropy,
            total_investigation_steps=ta.total_plan_steps,
            hypothesis_count=ta.hypothesis_count,
            hypothesis_rejection_ratio=ta.hypothesis_rejection_ratio,
            countercheck_execution_rate=ta.countercheck_execution_rate,
            direct_evidence_ratio=ta.direct_evidence_ratio,
        )

    @classmethod
    def _extract_user_actions(cls, record: Any) -> UserActionsTelemetry:
        tb_input = getattr(record, "traceback_input", None)
        err_desc = getattr(record, "error_description", None) or ""
        user_goal = getattr(record, "user_goal", None) or ""
        file_path = getattr(record, "file_path", None)

        has_tb = bool(tb_input and len(str(tb_input).strip()) > 10)
        total_desc_len = len(err_desc.strip()) + len(user_goal.strip())

        return UserActionsTelemetry(
            has_traceback_input=has_tb,
            error_desc_length=total_desc_len,
            user_goal_length=len(user_goal.strip()),
            submitted_file_name_present=bool(file_path),
        )

    @classmethod
    def _extract_code_properties(cls, source_code: str) -> CodePropertiesTelemetry:
        if not source_code.strip():
            return CodePropertiesTelemetry()

        lines = [line for line in source_code.splitlines() if line.strip() and not line.strip().startswith("#")]
        loc = len(lines)

        try:
            tree = ast.parse(source_code)
            node_count = sum(1 for _ in ast.walk(tree))
            max_depth = cls._compute_ast_depth(tree)
            function_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))

            # Cyclomatic complexity estimation
            branches = sum(
                1 for n in ast.walk(tree)
                if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert))
            )
            complexity = max(1, branches + 1)

            return CodePropertiesTelemetry(
                loc=loc,
                ast_node_count=node_count,
                ast_max_depth=max_depth,
                cyclomatic_complexity=complexity,
                function_count=function_count,
            )
        except SyntaxError:
            # Fallback estimation for broken syntax
            return CodePropertiesTelemetry(
                loc=loc,
                ast_node_count=loc * 3,
                ast_max_depth=2,
                cyclomatic_complexity=1,
                function_count=source_code.count("def "),
            )

    @classmethod
    def _compute_ast_depth(cls, node: ast.AST, current_depth: int = 1) -> int:
        children = list(ast.iter_child_nodes(node))
        if not children:
            return current_depth
        return max(cls._compute_ast_depth(child, current_depth + 1) for child in children)

    @classmethod
    def _extract_investigation_context(cls, record: Any) -> InvestigationContextTelemetry:
        err_desc = (getattr(record, "error_description", "") or "").lower()
        tb_input = (getattr(record, "traceback_input", "") or "").lower()
        goal = (getattr(record, "user_goal", "") or "").lower()
        combined = f"{err_desc} {tb_input} {goal}"

        is_syntax = "syntaxerror" in combined or "indentationerror" in combined
        is_type_or_val = "typeerror" in combined or "valueerror" in combined or "attributeerror" in combined or "zerodivisionerror" in combined
        is_runtime_other = not is_syntax and not is_type_or_val

        exception_name = None
        for exc in ["SyntaxError", "IndentationError", "TypeError", "ValueError", "AttributeError", "ZeroDivisionError", "IndexError", "KeyError", "NameError"]:
            if exc.lower() in combined:
                exception_name = exc
                break

        return InvestigationContextTelemetry(
            error_family_syntax=is_syntax,
            error_family_type_or_value=is_type_or_val,
            error_family_runtime_other=is_runtime_other,
            exception_name=exception_name,
        )

    @classmethod
    def _extract_agent_actions(cls, record: Any, state: Optional[Any] = None) -> TraceAgentActionsTelemetry:
        observations = []
        plan_steps = []
        hypotheses = []
        evidence_list = []
        counterchecks = []

        if state is not None:
            observations = getattr(state, "observations", []) or []
            plan_steps = getattr(getattr(state, "current_plan", None), "steps", []) or []
            hypotheses = getattr(state, "hypotheses", []) or []
            evidence_list = getattr(state, "evidence_store", []) or []
            counterchecks = getattr(state, "counterchecks", []) or []
        else:
            observations = getattr(record, "observations", []) or []
            plan_steps = getattr(record, "plan_steps", []) or []
            hypotheses = getattr(record, "hypotheses", []) or []
            evidence_list = getattr(record, "evidence", []) or []
            counterchecks = getattr(record, "counterchecks", []) or []

        total_tool_calls = len(observations)
        failed_tool_calls = sum(1 for o in observations if not getattr(o, "is_success", True))
        failed_tool_ratio = (failed_tool_calls / total_tool_calls) if total_tool_calls > 0 else 0.0

        ast_first_step = False
        if observations:
            first_tool = getattr(observations[0], "tool_name", "")
            ast_first_step = (first_tool == "ast_analyzer")

        static_calls = sum(1 for o in observations if getattr(o, "tool_name", "") in ("ast_analyzer", "file_reader", "traceback_parser"))
        exec_calls = sum(1 for o in observations if getattr(o, "tool_name", "") in ("python_executor", "countercheck_executor"))
        static_to_exec_ratio = float(static_calls) if exec_calls == 0 else round(static_calls / exec_calls, 2)

        # Shannon Entropy of tool usage
        tool_counts: Dict[str, int] = {}
        for o in observations:
            tname = getattr(o, "tool_name", "unknown")
            tool_counts[tname] = tool_counts.get(tname, 0) + 1

        entropy = 0.0
        if total_tool_calls > 1:
            for count in tool_counts.values():
                p = count / total_tool_calls
                if p > 0:
                    entropy -= p * math.log2(p)
            max_entropy = math.log2(len(tool_counts)) if len(tool_counts) > 1 else 1.0
            entropy = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0

        # Hypotheses & Evidence stats
        hyp_count = len(hypotheses)
        rejected_count = sum(
            1 for h in hypotheses
            if str(getattr(h, "status", "")).upper() in ("REJECTED", "DISPROVEN", "WEAKENED")
        )
        hyp_rejection_ratio = round(rejected_count / hyp_count, 3) if hyp_count > 0 else 0.0

        executed_cc = sum(1 for c in counterchecks if getattr(c, "executed", False))
        cc_rate = round(executed_cc / hyp_count, 3) if hyp_count > 0 else 0.0

        direct_ev = sum(1 for e in evidence_list if "DIRECT" in str(getattr(e, "evidence_type", "")).upper())
        derived_ev = sum(1 for e in evidence_list if "DERIVED" in str(getattr(e, "evidence_type", "")).upper())
        total_ev = len(evidence_list)
        direct_ratio = round(direct_ev / total_ev, 3) if total_ev > 0 else 0.0

        return TraceAgentActionsTelemetry(
            total_tool_calls=total_tool_calls,
            failed_tool_calls=failed_tool_calls,
            failed_tool_ratio=failed_tool_ratio,
            ast_first_step=ast_first_step,
            static_to_exec_ratio=static_to_exec_ratio,
            tool_sequence_entropy=entropy,
            total_plan_steps=len(plan_steps),
            replan_count=getattr(state, "replan_count", 0) if state else 0,
            hypothesis_count=hyp_count,
            rejected_hypothesis_count=rejected_count,
            hypothesis_rejection_ratio=hyp_rejection_ratio,
            counterchecks_executed=executed_cc,
            countercheck_execution_rate=cc_rate,
            direct_evidence_count=direct_ev,
            derived_evidence_count=derived_ev,
            direct_evidence_ratio=direct_ratio,
        )

    @classmethod
    def _extract_outcome(cls, record: Any, state: Optional[Any] = None) -> OutcomeTelemetry:
        status_val = str(getattr(record, "status", "CREATED") or "CREATED")
        confidence_val = float(getattr(record, "confidence", 0.0) or 0.0)

        diag = getattr(record, "diagnosis", None)
        is_verified = bool(diag and getattr(diag, "verified_hypothesis_id", None))

        return OutcomeTelemetry(
            session_status=status_val,
            is_verified=is_verified,
            calibrated_confidence=confidence_val,
        )


def compute_ast_metrics(source_code: str) -> Dict[str, Any]:
    """Compute AST metrics dictionary for source code."""
    props = TelemetryExtractor._extract_code_properties(source_code)
    return {
        "loc": props.loc,
        "ast_node_count": props.ast_node_count,
        "ast_max_depth": props.ast_max_depth,
        "cyclomatic_complexity": props.cyclomatic_complexity,
        "function_count": props.function_count,
    }


def compute_tool_entropy(tool_names: List[str]) -> float:
    """Compute Shannon entropy of tool sequence."""
    if not tool_names:
        return 0.0
    tool_counts: Dict[str, int] = {}
    for t in tool_names:
        tool_counts[t] = tool_counts.get(t, 0) + 1
    total = len(tool_names)
    if total <= 1:
        return 0.0
    entropy = 0.0
    for count in tool_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    max_entropy = math.log2(len(tool_counts)) if len(tool_counts) > 1 else 1.0
    return round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0

