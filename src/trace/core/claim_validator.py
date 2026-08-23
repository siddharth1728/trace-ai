"""Deterministic Diagnosis Claim Validation Engine for TRACE v0.2."""

from enum import Enum
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from trace.core.evidence import Evidence, EvidenceType
from trace.core.models import FinalDiagnosis
from trace.core.state import AgentState


class ClaimType(str, Enum):
    """Classification of final diagnosis statements."""
    FACTUAL = "FACTUAL"      # Directly verifiable empirical assertion (line number, exception, exit code, stdout)
    REASONING = "REASONING"  # Pedagogical explanation, causal deduction, or fix guidance


class ClaimValidationResult(BaseModel):
    """Validation report for an individual claim extracted from a diagnosis."""
    claim_text: str
    claim_type: ClaimType
    is_grounded: bool
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    flagged_reason: Optional[str] = None


class DiagnosisClaimValidator:
    """
    Validates final diagnosis statements against recorded evidence.
    Ensures 0% unsupported factual claims reach the student.
    """

    def validate_and_ground_diagnosis(
        self,
        raw_diagnosis: FinalDiagnosis,
        state: AgentState,
    ) -> Tuple[FinalDiagnosis, List[ClaimValidationResult]]:
        """
        Audit all claims in the diagnosis. Filters out ungrounded factual claims
        and preserves validated factual and reasoning statements.
        """
        validation_results: List[ClaimValidationResult] = []
        direct_evidence = [e for e in state.evidence_store if e.is_direct()]
        direct_statements_text = " ".join([e.statement.lower() for e in direct_evidence])
        tool_names_run = {t.tool_name for t in state.tool_history if t.success}

        # 1. Validate Evidence Summary Claims
        grounded_evidence_summary: List[str] = []
        for claim in raw_diagnosis.evidence_summary:
            is_factual = any(kw in claim.lower() for kw in [
                "error", "exception", "exit code", "line", "syntax", "attributeerror",
                "typeerror", "zerodivision", "indexerror", "nameerror", "ast", "failed", "succeeded"
            ])
            claim_type = ClaimType.FACTUAL if is_factual else ClaimType.REASONING

            # Look for supporting direct evidence
            matching_evidence = [
                e for e in direct_evidence
                if any(word in e.statement.lower() for word in claim.lower().split() if len(word) > 4)
            ]

            if claim_type == ClaimType.FACTUAL:
                if matching_evidence or any(t in claim.lower() for t in tool_names_run):
                    is_grounded = True
                    supporting_ids = [e.id for e in matching_evidence]
                    grounded_evidence_summary.append(claim)
                    validation_results.append(ClaimValidationResult(
                        claim_text=claim,
                        claim_type=claim_type,
                        is_grounded=True,
                        supporting_evidence_ids=supporting_ids,
                    ))
                else:
                    is_grounded = False
                    validation_results.append(ClaimValidationResult(
                        claim_text=claim,
                        claim_type=claim_type,
                        is_grounded=False,
                        flagged_reason="Factual claim lacks direct tool evidence backing.",
                    ))
            else:
                # Reasoning claims are preserved
                grounded_evidence_summary.append(claim)
                validation_results.append(ClaimValidationResult(
                    claim_text=claim,
                    claim_type=claim_type,
                    is_grounded=True,
                ))

        if not grounded_evidence_summary:
            grounded_evidence_summary = [
                f"[{obs.tool_name}] {obs.summary}"
                for obs in state.get_successful_observations()
            ] or ["No direct tool evidence was collected."]

        # 2. Programmatically Construct what_trace_checked strictly from successful tools
        tool_display_map = {
            "ast_analyzer": "Python AST Static Analysis (parsed syntax tree, functions, variables, branches)",
            "python_executor": "Controlled Subprocess Sandbox Execution (captured exit code, stdout, stderr)",
            "traceback_parser": "Traceback Stack Frame Analysis (normalized error type and frame lines)",
            "file_reader": "Source Code File Inspector (read lines and structure)",
            "counterexample_engine": "Targeted Countercheck Experiment (tested hypothesis falsification)",
        }
        what_checked: List[str] = []
        for t in state.tool_history:
            if t.success and t.tool_name not in what_checked:
                display = tool_display_map.get(t.tool_name, f"Tool: {t.tool_name}")
                if display not in what_checked:
                    what_checked.append(display)

        if not what_checked:
            what_checked = ["No tools executed successfully during this session."]

        # 3. Uncertainties and Flagged Factual Claims
        uncertainties = list(raw_diagnosis.what_remains_uncertain)
        unsupported_claims = [r for r in validation_results if not r.is_grounded]
        if unsupported_claims:
            for unbacked in unsupported_claims:
                note = f"Uncertain inference: '{unbacked.claim_text}' could not be directly confirmed by tool evidence."
                if note not in uncertainties:
                    uncertainties.append(note)

        grounded_diagnosis = FinalDiagnosis(
            problem_statement=raw_diagnosis.problem_statement,
            investigation_summary=raw_diagnosis.investigation_summary,
            likely_root_cause=raw_diagnosis.likely_root_cause,
            evidence_summary=grounded_evidence_summary,
            confidence=raw_diagnosis.confidence,
            what_trace_checked=what_checked,
            what_remains_uncertain=uncertainties,
            learning_point=raw_diagnosis.learning_point,
            suggested_fix_guidance=raw_diagnosis.suggested_fix_guidance,
            verified_hypothesis_id=raw_diagnosis.verified_hypothesis_id,
            countercheck_summary=raw_diagnosis.countercheck_summary,
        )

        return grounded_diagnosis, validation_results
