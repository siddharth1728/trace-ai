"""Investigation evaluator and hypothesis tracker for TRACE."""

from typing import List, Optional, Tuple

from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.models import Hypothesis, HypothesisStatus, StepStatus
from trace.core.state import AgentState
from trace.llm.prompts import STEP_EVALUATION_PROMPT_TEMPLATE, SYSTEM_INVESTIGATION_PROMPT
from trace.llm.provider import LLMProvider
from trace.llm.schemas import ActionType, NextActionDecision


class InvestigationEvaluator:
    """Evaluates hypothesis status against new observations and decides next actions."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def evaluate_step(self, state: AgentState) -> NextActionDecision:
        """Run LLM step evaluation to update hypotheses and select next action."""
        # Format hypotheses summary
        hyp_lines = [
            f"- [{h.id}] Status: {h.status.value}, Confidence: {h.confidence:.2f} | Statement: '{h.statement}' | Rationale: {h.rationale}"
            for h in state.hypotheses
        ]
        hyp_summary = "\n".join(hyp_lines) if hyp_lines else "None registered"

        # Format observations summary
        obs_lines = [
            f"- [{obs.id}] Tool: {obs.tool_name}, Success: {obs.is_success} | Summary: {obs.summary}"
            for obs in state.observations
        ]
        obs_summary = "\n".join(obs_lines) if obs_lines else "None recorded yet"

        # Format remaining steps
        rem_steps = []
        if state.current_plan:
            for s in state.current_plan.steps:
                if s.status == StepStatus.PENDING:
                    rem_steps.append(f"- Step {s.step_id}: {s.title} ({s.tool_name})")
        rem_summary = "\n".join(rem_steps) if rem_steps else "No pending steps remaining"

        prompt = STEP_EVALUATION_PROMPT_TEMPLATE.format(
            objective=state.current_plan.objective if state.current_plan else "Investigate issue",
            iteration=state.iteration_count,
            max_iterations=state.max_iterations,
            source_code=state.source_code,
            hypotheses_summary=hyp_summary,
            observations_summary=obs_summary,
            remaining_steps_summary=rem_summary,
        )

        decision: NextActionDecision = self.provider.generate_structured(
            prompt=prompt,
            response_model=NextActionDecision,
            system_prompt=SYSTEM_INVESTIGATION_PROMPT,
        )

        # Apply hypothesis evaluations to agent state
        for item in decision.hypothesis_evaluations:
            state.update_hypothesis_status(
                hypothesis_id=item.hypothesis_id,
                new_status=item.new_status,
                confidence=item.confidence,
                supporting_obs_id=item.supporting_obs_id,
                contradictory_obs_id=item.contradictory_obs_id,
                rationale=item.rationale,
            )
            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.HYPOTHESIS_UPDATED,
                    payload={"evaluation": item.model_dump()},
                    message=f"Hypothesis [{item.hypothesis_id}] -> {item.new_status.value} (conf={item.confidence:.2f}): {item.rationale}",
                )
            )

        return decision

    def check_termination_condition(
        self,
        state: AgentState,
        decision: Optional[NextActionDecision] = None,
    ) -> Tuple[bool, str]:
        """Determine if the investigation should stop and transition to diagnosis."""
        # 1. Explicit LLM decision to finalize
        if decision and decision.action_type == ActionType.FINALIZE_DIAGNOSIS:
            return True, "Sufficient evidence collected to finalize diagnosis."

        # 2. Max iterations reached
        if state.iteration_count >= state.max_iterations:
            return True, f"Reached maximum allowed iterations ({state.max_iterations})."

        # 3. A hypothesis is confirmed with high confidence (>= 0.90)
        for hyp in state.hypotheses:
            if hyp.status == HypothesisStatus.CONFIRMED and hyp.confidence >= 0.90:
                return True, f"Hypothesis [{hyp.id}] confirmed with {hyp.confidence * 100:.0f}% confidence."

        # 4. No more pending plan steps
        if state.current_plan:
            pending_steps = [s for s in state.current_plan.steps if s.status == StepStatus.PENDING]
            if not pending_steps and (decision is None or decision.action_type != ActionType.EXECUTE_TOOL):
                return True, "All planned investigation steps completed."

        return False, ""
