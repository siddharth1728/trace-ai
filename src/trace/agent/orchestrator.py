"""Core Investigation Orchestrator driving the TRACE agent loop."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from trace.agent.evaluator import InvestigationEvaluator
from trace.agent.planner import InvestigationPlanner
from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.models import (
    FinalDiagnosis,
    HypothesisStatus,
    Observation,
    PlanStep,
    StepStatus,
)
from trace.core.state import AgentState, LifecycleState
from trace.llm.prompts import DIAGNOSIS_PROMPT_TEMPLATE, SYSTEM_INVESTIGATION_PROMPT
from trace.llm.provider import LLMProvider, LLMProviderFactory
from trace.llm.schemas import ActionType, DiagnosisSchema, NextActionDecision
from trace.tools.registry import ToolRegistry, create_default_registry


class InvestigationOrchestrator:
    """
    Main agent orchestrator executing the TRACE debugging investigation loop.
    Coordinates State, Planner, Evaluator, Tool Registry, and LLM Provider.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        registry: Optional[ToolRegistry] = None,
        workspace_root: Optional[str | Path] = None,
    ):
        self.provider = provider or LLMProviderFactory.create()
        self.registry = registry or create_default_registry(workspace_root=str(workspace_root) if workspace_root else None)
        self.planner = InvestigationPlanner(self.provider)
        self.evaluator = InvestigationEvaluator(self.provider)

    def _get_tools_summary(self) -> str:
        """Format a summary of registered tools for LLM prompts."""
        lines = []
        for tool_def in self.registry.list_tools():
            lines.append(f"- {tool_def.name}: {tool_def.description}")
        return "\n".join(lines)

    def investigate(
        self,
        source_code: str,
        user_goal: str,
        error_description: Optional[str] = None,
        traceback_input: Optional[str] = None,
        file_path: Optional[str] = None,
        max_iterations: int = 8,
    ) -> AgentState:
        """
        Execute an end-to-end evidence-driven debugging investigation session.
        """
        # 1. State Initialization
        state = AgentState(
            user_goal=user_goal,
            source_code=source_code,
            file_path=file_path,
            error_description=error_description,
            traceback_input=traceback_input,
            max_iterations=max_iterations,
        )

        global_event_bus.publish(
            TraceEvent(
                session_id=state.session_id,
                event_type=EventType.SESSION_STARTED,
                payload={"goal": user_goal, "file_path": file_path},
                message=f"Starting TRACE debugging investigation session for goal: '{user_goal}'",
            )
        )

        try:
            # 2. UNDERSTANDING
            state.transition_to(LifecycleState.UNDERSTANDING)
            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.STATE_TRANSITION,
                    payload={"new_state": LifecycleState.UNDERSTANDING.value},
                    message="Analyzing debugging goal, source code, and context.",
                )
            )

            # 3. PLANNING
            state.transition_to(LifecycleState.PLANNING)
            tools_summary = self._get_tools_summary()
            plan = self.planner.create_initial_plan(state, tools_summary)

            # 4. INVESTIGATING LOOP
            state.transition_to(LifecycleState.INVESTIGATING)

            while not state.is_terminal():
                # Check iteration limit
                can_continue = state.increment_iteration()
                
                # Pick current pending step from plan
                current_step: Optional[PlanStep] = None
                if state.current_plan:
                    for step in state.current_plan.steps:
                        if step.status == StepStatus.PENDING:
                            current_step = step
                            break

                if not current_step and not can_continue:
                    # Stopping condition met
                    break

                # Determine tool to execute
                tool_name: str
                tool_args: Dict[str, Any]

                if current_step:
                    current_step.status = StepStatus.IN_PROGRESS
                    tool_name = current_step.tool_name
                    tool_args = dict(current_step.tool_args)
                else:
                    tool_name = "python_executor"
                    tool_args = {"source_code": state.source_code}

                # Auto-populate missing arguments from state context
                self._populate_tool_args(tool_name, tool_args, state)

                # Emit step started
                global_event_bus.publish(
                    TraceEvent(
                        session_id=state.session_id,
                        event_type=EventType.STEP_STARTED,
                        payload={"step_title": current_step.title if current_step else f"Execute {tool_name}", "tool_name": tool_name},
                        message=f"Step {state.iteration_count}: {current_step.title if current_step else f'Run {tool_name}'}",
                    )
                )

                # Execute tool and record observation
                obs = self.registry.execute(tool_name, tool_args, state)
                
                if current_step:
                    current_step.status = StepStatus.DONE if obs.is_success else StepStatus.FAILED
                    current_step.observation_id = obs.id
                    state.completed_steps.append(current_step)

                # 5. EVALUATING
                state.transition_to(LifecycleState.EVALUATING)
                decision = self.evaluator.evaluate_step(state)

                # Check if replan requested
                if decision.action_type == ActionType.REPLAN or decision.should_replan:
                    state.transition_to(LifecycleState.REPLANNING)
                    self.planner.replan(
                        state,
                        reason=decision.replan_reason or decision.reasoning,
                        tools_summary=tools_summary,
                    )
                    state.transition_to(LifecycleState.INVESTIGATING)

                # Check termination conditions
                should_stop, stop_reason = self.evaluator.check_termination_condition(state, decision)
                if should_stop or not can_continue:
                    break
                else:
                    state.transition_to(LifecycleState.INVESTIGATING)

            # 6. DIAGNOSING
            state.transition_to(LifecycleState.DIAGNOSING)
            final_diagnosis = self._formulate_final_diagnosis(state)
            state.final_diagnosis = final_diagnosis
            state.confidence = final_diagnosis.confidence

            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.DIAGNOSIS_FORMED,
                    payload={"diagnosis": final_diagnosis.model_dump()},
                    message=f"Diagnosis formed: {final_diagnosis.likely_root_cause}",
                )
            )

            # 7. EXPLAINING & COMPLETED
            state.transition_to(LifecycleState.EXPLAINING)
            state.transition_to(LifecycleState.COMPLETED)

            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.SESSION_COMPLETED,
                    payload={"confidence": state.confidence, "iteration_count": state.iteration_count},
                    message=f"Investigation completed successfully in {state.iteration_count} iteration(s).",
                )
            )

        except Exception as ex:
            state.transition_to(LifecycleState.BLOCKED, reason=str(ex))
            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.SESSION_BLOCKED,
                    payload={"error": str(ex)},
                    message=f"Investigation blocked: {ex}",
                )
            )

        return state

    def _populate_tool_args(self, tool_name: str, args: Dict[str, Any], state: AgentState) -> None:
        """Inject appropriate state context into tool argument templates."""
        if tool_name in ("ast_analyzer", "python_executor"):
            if not args.get("source_code") and not args.get("file_path"):
                if state.file_path:
                    args["file_path"] = state.file_path
                else:
                    args["source_code"] = state.source_code
        elif tool_name == "traceback_parser":
            if not args.get("traceback_text"):
                args["traceback_text"] = state.traceback_input or ""
        elif tool_name == "file_reader":
            if not args.get("file_path") and state.file_path:
                args["file_path"] = state.file_path

    def _formulate_final_diagnosis(self, state: AgentState) -> FinalDiagnosis:
        """Call LLM provider and programmatically ground the final diagnosis against actual observations."""
        # 1. Format observations summary with explicit success/failure status tags
        obs_lines = []
        for obs in state.observations:
            status_tag = "SUCCESS" if obs.is_success else "FAILED"
            obs_lines.append(f"- [{obs.id}] [{status_tag}] ({obs.tool_name}): {obs.summary}")
        obs_summary = "\n".join(obs_lines) if obs_lines else "No observations recorded."

        hyp_lines = [
            f"- [{h.id}] Status: {h.status.value}, Confidence: {h.confidence:.2f} | Statement: '{h.statement}' | Rationale: {h.rationale}"
            for h in state.hypotheses
        ]
        hyp_summary = "\n".join(hyp_lines) if hyp_lines else "No hypotheses recorded."

        tool_lines = [
            f"- Call {t.tool_name} (success={t.success}, duration={t.execution_time_ms}ms)"
            for t in state.tool_history
        ]
        tool_summary = "\n".join(tool_lines) if tool_lines else "No tools recorded."

        prompt = DIAGNOSIS_PROMPT_TEMPLATE.format(
            user_goal=state.user_goal,
            source_code=state.source_code,
            observations_summary=obs_summary,
            hypotheses_summary=hyp_summary,
            tool_history_summary=tool_summary,
        )

        diag_schema: DiagnosisSchema = self.provider.generate_structured(
            prompt=prompt,
            response_model=DiagnosisSchema,
            system_prompt=SYSTEM_INVESTIGATION_PROMPT,
        )

        # 2. Programmatically construct what_trace_checked strictly from successful tool calls
        successful_tools = [t.tool_name for t in state.tool_history if t.success]
        tool_display_map = {
            "ast_analyzer": "Python AST Static Analysis (parsed syntax tree, functions, variable assignments, calls)",
            "python_executor": "Controlled Subprocess Sandbox Execution (captured exit code, stdout, stderr)",
            "traceback_parser": "Traceback Stack Frame Analysis (normalized error type and frame lines)",
            "file_reader": "Source Code File Inspector (read lines and structure)",
        }
        what_checked: List[str] = []
        seen_tools = set()
        for tool_name in successful_tools:
            if tool_name not in seen_tools:
                seen_tools.add(tool_name)
                what_checked.append(tool_display_map.get(tool_name, f"Tool execution: {tool_name}"))

        if not what_checked:
            what_checked = ["No tools executed successfully during the session."]

        # 3. Ground evidence_summary strictly in verified successful observations
        successful_obs = state.get_successful_observations()
        evidence_summary: List[str] = []
        if successful_obs:
            for obs in successful_obs:
                evidence_summary.append(f"[{obs.tool_name}] {obs.summary}")
        else:
            evidence_summary = ["No successful tool observations were collected during this investigation."]

        # 4. Calibrate confidence and uncertainties deterministically
        uncertainties = list(diag_schema.what_remains_uncertain)
        has_execution = any(t.tool_name == "python_executor" and t.success for t in state.tool_history)
        has_syntax_confirmed = any(
            h.status == HypothesisStatus.CONFIRMED and "syntax" in h.statement.lower()
            for h in state.hypotheses
        )
        has_supported_hyp = any(
            h.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED)
            for h in state.hypotheses
        )

        calibrated_confidence = float(diag_schema.confidence)

        if len(successful_obs) == 0:
            calibrated_confidence = min(calibrated_confidence, 0.25)
            uncertainty_msg = "Investigation lacked successful tool observations (dynamic execution and/or static analysis did not succeed)."
            if uncertainty_msg not in uncertainties:
                uncertainties.append(uncertainty_msg)
        elif not has_execution and not has_syntax_confirmed:
            calibrated_confidence = min(calibrated_confidence, 0.60)
            uncertainty_msg = "Dynamic runtime execution was not performed to verify runtime behavior."
            if uncertainty_msg not in uncertainties:
                uncertainties.append(uncertainty_msg)
        elif has_syntax_confirmed or (has_supported_hyp and has_execution):
            # Conclusively verified via AST syntax parser or sandbox execution reproduction
            calibrated_confidence = max(0.85, min(1.0, calibrated_confidence))
        elif has_supported_hyp and len(successful_obs) >= 2:
            calibrated_confidence = max(0.75, min(1.0, calibrated_confidence))
        else:
            calibrated_confidence = min(calibrated_confidence, 0.70)

        return FinalDiagnosis(
            problem_statement=diag_schema.problem_statement,
            investigation_summary=diag_schema.investigation_summary,
            likely_root_cause=diag_schema.likely_root_cause,
            evidence_summary=evidence_summary,
            confidence=round(calibrated_confidence, 2),
            what_trace_checked=what_checked,
            what_remains_uncertain=uncertainties,
            learning_point=diag_schema.learning_point,
            suggested_fix_guidance=diag_schema.suggested_fix_guidance,
        )
