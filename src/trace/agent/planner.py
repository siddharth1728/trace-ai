"""Investigation planner for TRACE."""

from typing import Any, Dict, List, Optional

from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.models import (
    Hypothesis,
    HypothesisStatus,
    InvestigationPlan,
    PlanStep,
    StepStatus,
)
from trace.core.state import AgentState
from trace.llm.prompts import PLANNING_PROMPT_TEMPLATE, SYSTEM_INVESTIGATION_PROMPT
from trace.llm.provider import LLMProvider
from trace.llm.schemas import InitialPlanSchema


class InvestigationPlanner:
    """Creates initial investigation plans and handles replanning when evidence contradicts hypotheses."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def create_initial_plan(self, state: AgentState, tools_summary: str) -> InvestigationPlan:
        """Formulate initial investigation plan and populate competing candidate hypotheses."""
        prompt = PLANNING_PROMPT_TEMPLATE.format(
            user_goal=state.user_goal,
            error_description=state.error_description or "None provided",
            traceback=state.traceback_input or "None provided",
            source_code=state.source_code,
            tools_summary=tools_summary,
        )

        plan_schema: InitialPlanSchema = self.provider.generate_structured(
            prompt=prompt,
            response_model=InitialPlanSchema,
            system_prompt=SYSTEM_INVESTIGATION_PROMPT,
        )

        # Register candidate hypotheses in state
        for statement in plan_schema.initial_hypotheses:
            hyp = Hypothesis(
                statement=statement,
                confidence=0.5,
                status=HypothesisStatus.PROPOSED,
                rationale="Proposed during initial investigation planning.",
            )
            state.add_hypothesis(hyp)
            global_event_bus.publish(
                TraceEvent(
                    session_id=state.session_id,
                    event_type=EventType.HYPOTHESIS_PROPOSED,
                    payload={"hypothesis": hyp.model_dump()},
                    message=f"Proposed Hypothesis [{hyp.id}]: {hyp.statement}",
                )
            )

        # Determine if valid traceback input exists
        has_valid_traceback = bool(
            state.traceback_input
            and state.traceback_input.strip()
            and state.traceback_input.strip() not in ("None provided", "None", "null")
        )

        # Convert to domain PlanStep models, gating tools by pre-conditions
        steps: List[PlanStep] = []
        for s in plan_schema.steps:
            # Pre-condition gate: Do not schedule traceback_parser if no traceback exists
            if s.tool_name == "traceback_parser" and not has_valid_traceback:
                continue

            steps.append(
                PlanStep(
                    step_id=len(steps) + 1,
                    title=s.title,
                    tool_name=s.tool_name,
                    tool_args=s.tool_args,
                    expected_outcome=s.expected_outcome,
                    status=StepStatus.PENDING,
                )
            )

        # If all steps were filtered out (or none created), ensure fallback investigation steps
        if not steps:
            steps = [
                PlanStep(
                    step_id=1,
                    title="Perform static AST analysis on code structure",
                    tool_name="ast_analyzer",
                    tool_args={"source_code": state.source_code},
                    expected_outcome="Analyze variables, functions, syntax, and control flow.",
                    status=StepStatus.PENDING,
                ),
                PlanStep(
                    step_id=2,
                    title="Execute code in controlled sandbox to observe runtime behavior",
                    tool_name="python_executor",
                    tool_args={"source_code": state.source_code},
                    expected_outcome="Observe runtime execution, exit code, and stdout/stderr.",
                    status=StepStatus.PENDING,
                ),
            ]

        plan = InvestigationPlan(
            objective=plan_schema.objective,
            steps=steps,
        )
        state.current_plan = plan

        global_event_bus.publish(
            TraceEvent(
                session_id=state.session_id,
                event_type=EventType.PLAN_CREATED,
                payload={"objective": plan.objective, "step_count": len(steps)},
                message=f"Investigation plan created with {len(steps)} steps: '{plan.objective}'",
            )
        )

        return plan

    def replan(self, state: AgentState, reason: str, tools_summary: str) -> InvestigationPlan:
        """Modify remaining investigation steps when new observations refute existing direction."""
        # Mark remaining pending steps as skipped
        if state.current_plan:
            for step in state.current_plan.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.SKIPPED
            state.current_plan.revision_count += 1

        # Propose fallback verification step
        new_step_id = len(state.current_plan.steps) + 1 if state.current_plan else 1
        replan_step = PlanStep(
            step_id=new_step_id,
            title="Execute targeted verification in controlled sandbox",
            tool_name="python_executor",
            tool_args={"source_code": state.source_code},
            expected_outcome="Collect additional execution telemetry following direction change.",
            status=StepStatus.PENDING,
        )

        if state.current_plan:
            state.current_plan.steps.append(replan_step)
            plan = state.current_plan
        else:
            plan = InvestigationPlan(
                objective="Replanned verification",
                steps=[replan_step],
                revision_count=1,
            )
            state.current_plan = plan

        global_event_bus.publish(
            TraceEvent(
                session_id=state.session_id,
                event_type=EventType.PLAN_REVISED,
                payload={"reason": reason, "new_step": replan_step.model_dump()},
                message=f"Plan revised (Reason: {reason})",
            )
        )

        return plan
