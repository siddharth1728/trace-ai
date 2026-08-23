"""Core Investigation Orchestrator driving the TRACE v0.2 agent loop."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from trace.agent.counterexample import CounterexampleEngine
from trace.agent.evaluator import InvestigationEvaluator
from trace.agent.planner import InvestigationPlanner
from trace.agent.verifier import VerificationEngine, VerificationStatus
from trace.core.claim_validator import DiagnosisClaimValidator
from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import (
    FinalDiagnosis,
    Hypothesis,
    HypothesisStatus,
    Observation,
    PlanStep,
    StepStatus,
)
from trace.core.state import AgentState, LifecycleState
from trace.llm.prompts import DIAGNOSIS_PROMPT_TEMPLATE, SYSTEM_INVESTIGATION_PROMPT
from trace.llm.provider import LLMProvider, LLMProviderFactory
from trace.llm.schemas import ActionType, DiagnosisSchema
from trace.tools.registry import ToolRegistry, create_default_registry


class InvestigationOrchestrator:
    """
    Main agent orchestrator executing the TRACE v0.2 debugging investigation loop.
    Coordinates State, Planner, Evaluator, Verification Engine, Counterexample Engine,
    Claim Validator, and Tool Registry.
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
        self.verifier = VerificationEngine()
        self.counterexample_engine = CounterexampleEngine()
        self.claim_validator = DiagnosisClaimValidator()

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

                # Extract Direct Evidence from Observation
                self._extract_evidence_from_observation(obs, state)

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

            # 6. COUNTEREXAMPLE & VERIFICATION STAGE (v0.2)
            self._run_counterexample_and_verification_stage(state)

            # 7. DIAGNOSING & CLAIM VALIDATION
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

            # 8. EXPLAINING & COMPLETED
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

    def _extract_evidence_from_observation(self, obs: Observation, state: AgentState) -> None:
        """Extract atomic direct evidence items from a successful observation."""
        if not obs.is_success:
            return

        # Find target hypothesis (primary candidate matching observation characteristics)
        target_hyp = self._find_matching_hypothesis(obs, state)
        target_hyp_id = target_hyp.id if target_hyp else (state.hypotheses[0].id if state.hypotheses else "hyp_general")

        if target_hyp and obs.is_success:
            if obs.id not in target_hyp.supporting_observation_ids:
                target_hyp.supporting_observation_ids.append(obs.id)

        evidence_item = Evidence(
            observation_id=obs.id,
            tool_name=obs.tool_name,
            evidence_type=EvidenceType.DIRECT,
            statement=obs.summary,
            raw_fact=obs.output_data,
            target_hypothesis_id=target_hyp_id,
            relation=EvidenceRelation.SUPPORTS,
            confidence_weight=1.0,
        )
        state.add_evidence(evidence_item)

    def _find_matching_hypothesis(self, obs: Observation, state: AgentState) -> Optional[Hypothesis]:
        """Match an observation to the most relevant candidate hypothesis."""
        obs_text = obs.summary.lower()
        for hyp in state.hypotheses:
            hyp_text = hyp.statement.lower()
            if "syntax" in obs_text and "syntax" in hyp_text:
                return hyp
            if ("zerodivision" in obs_text or "division by zero" in obs_text) and ("zerodivision" in hyp_text or "empty" in hyp_text or "calculation" in hyp_text):
                return hyp
            if ("typeerror" in obs_text or "nonetype" in obs_text or "attributeerror" in obs_text) and ("none" in hyp_text or "type" in hyp_text):
                return hyp
            if "indexerror" in obs_text and ("index" in hyp_text or "bound" in hyp_text):
                return hyp
        return state.hypotheses[0] if state.hypotheses else None

    def _run_counterexample_and_verification_stage(self, state: AgentState) -> None:
        """
        Execute targeted countercheck experiments and run deterministic verification
        on candidate hypotheses before finalizing the diagnosis.
        """
        if not state.hypotheses:
            return

        # Find leading hypothesis
        leading_hyp = next(
            (h for h in state.hypotheses if h.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.CONFIRMED, HypothesisStatus.PROPOSED)),
            state.hypotheses[0]
        )

        # Check if leading hypothesis is already confirmed syntax error
        has_syntax_ast = any(
            e.tool_name == "ast_analyzer" and "syntax" in e.statement.lower()
            for e in state.get_direct_supporting_evidence(leading_hyp.id)
        )

        if not has_syntax_ast and leading_hyp:
            # Transition to VERIFICATION_PENDING
            leading_hyp.status = HypothesisStatus.VERIFICATION_PENDING
            
            # Generate and run targeted counterexample experiment
            experiment = self.counterexample_engine.generate_experiment(leading_hyp, state)
            if experiment:
                self.counterexample_engine.run_experiment(experiment, state)

        # Run Deterministic Verifier across all hypotheses
        verifications = self.verifier.verify_all_hypotheses(state)
        for ver in verifications:
            hyp = state.get_hypothesis(ver.hypothesis_id)
            if hyp:
                if ver.status == VerificationStatus.VERIFIED:
                    hyp.status = HypothesisStatus.VERIFIED
                    hyp.confidence = ver.calibrated_confidence
                    hyp.rationale = ver.rationale
                elif ver.status == VerificationStatus.DISPROVEN:
                    hyp.status = HypothesisStatus.DISPROVEN
                    hyp.confidence = ver.calibrated_confidence
                    hyp.rationale = ver.rationale
                elif ver.status == VerificationStatus.STRONGLY_SUPPORTED:
                    hyp.status = HypothesisStatus.SUPPORTED
                    hyp.confidence = ver.calibrated_confidence
                    hyp.rationale = ver.rationale
                elif ver.status == VerificationStatus.PLAUSIBLE:
                    hyp.status = HypothesisStatus.SUPPORTED
                    hyp.confidence = ver.calibrated_confidence
                    hyp.rationale = ver.rationale
                else:
                    hyp.status = HypothesisStatus.PROPOSED
                    hyp.confidence = ver.calibrated_confidence
                    hyp.rationale = ver.rationale

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
        """Call LLM provider and programmatically validate and ground all final claims."""
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

        # Identify top verified/supported hypothesis
        top_hyp = next(
            (h for h in state.hypotheses if h.status in (HypothesisStatus.VERIFIED, HypothesisStatus.CONFIRMED)),
            next((h for h in state.hypotheses if h.status == HypothesisStatus.SUPPORTED), None)
        )

        successful_obs = state.get_successful_observations()
        uncertainties = list(diag_schema.what_remains_uncertain)

        if len(successful_obs) == 0:
            calibrated_conf = 0.20
            unc_msg = "Investigation lacked successful tool observations (dynamic execution and/or static analysis did not succeed)."
            if unc_msg not in uncertainties:
                uncertainties.append(unc_msg)
        elif top_hyp:
            calibrated_conf = top_hyp.confidence
        else:
            calibrated_conf = 0.25

        # Countercheck summary
        counter_ev = next((e for e in state.evidence_store if e.tool_name == "counterexample_engine"), None)
        countercheck_summary = counter_ev.statement if counter_ev else None

        raw_diagnosis = FinalDiagnosis(
            problem_statement=diag_schema.problem_statement,
            investigation_summary=diag_schema.investigation_summary,
            likely_root_cause=diag_schema.likely_root_cause,
            evidence_summary=diag_schema.evidence_summary,
            confidence=round(calibrated_conf, 2),
            what_trace_checked=[],
            what_remains_uncertain=uncertainties,
            learning_point=diag_schema.learning_point,
            suggested_fix_guidance=diag_schema.suggested_fix_guidance,
            verified_hypothesis_id=top_hyp.id if top_hyp else None,
            countercheck_summary=countercheck_summary,
        )

        # Audit and ground diagnosis through Claim Validator
        grounded_diagnosis, _ = self.claim_validator.validate_and_ground_diagnosis(raw_diagnosis, state)
        return grounded_diagnosis
