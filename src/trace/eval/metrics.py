"""Evaluation metrics engine for TRACE v0.2 evidence quality and verification."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from trace.core.claim_validator import ClaimType, ClaimValidationResult, DiagnosisClaimValidator
from trace.core.models import HypothesisStatus
from trace.core.state import AgentState


class BenchmarkEvaluationResult(BaseModel):
    """Aggregate evaluation report measuring evidence quality across benchmark runs."""
    total_cases: int = 0
    passed_cases: int = 0
    evidence_grounding_rate: float = Field(default=100.0, description="% of factual claims backed by direct evidence")
    unsupported_claim_rate: float = Field(default=0.0, description="% of factual claims lacking evidence")
    hypothesis_verification_accuracy: float = Field(default=100.0, description="% of hypotheses correctly verified/disproven")
    counterexample_success_rate: float = Field(default=100.0, description="% of eligible cases with executed countercheck")
    premature_diagnosis_rate: float = Field(default=0.0, description="% of cases finalized prematurely")
    detailed_case_results: List[Dict[str, Any]] = Field(default_factory=list)


class MetricsCalculator:
    """
    Computes rigorous evidence quality, claim grounding, and verification metrics
    for TRACE benchmarks.
    """

    def __init__(self):
        self.validator = DiagnosisClaimValidator()

    def evaluate_session(
        self,
        state: AgentState,
        expected_status: Optional[HypothesisStatus] = None,
        expected_root_cause_keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute metrics for an individual completed investigation session."""
        diag = state.final_diagnosis
        if not diag:
            return {
                "success": False,
                "factual_claims_total": 0,
                "factual_claims_grounded": 0,
                "unsupported_claims": 0,
                "countercheck_executed": False,
                "is_premature": True,
                "verification_correct": False,
            }

        # Claim Validation Audit
        _, validation_results = self.validator.validate_and_ground_diagnosis(diag, state)
        factual_results = [r for r in validation_results if r.claim_type == ClaimType.FACTUAL]
        grounded_factual = [r for r in factual_results if r.is_grounded]
        unsupported_factual = [r for r in factual_results if not r.is_grounded]

        # Check Counterexample Execution
        counter_executed = (
            any(t.tool_name == "counterexample_engine" and t.success for t in state.tool_history)
            or any(e.tool_name == "counterexample_engine" for e in state.evidence_store)
        )
        is_syntax = (
            any("syntax" in (t.tool_name or "") for t in state.tool_history)
            or any("syntax" in e.statement.lower() for e in state.evidence_store)
            or "syntax" in state.user_goal.lower()
        )

        # Check Premature Termination
        is_premature = (len(state.get_successful_observations()) == 0)

        # Check Hypothesis Verification correctness
        top_hyp = next((h for h in state.hypotheses if h.status in (HypothesisStatus.VERIFIED, HypothesisStatus.CONFIRMED, HypothesisStatus.SUPPORTED)), None)
        verification_correct = True
        if expected_status and top_hyp:
            if expected_status == HypothesisStatus.VERIFIED:
                verification_correct = (top_hyp.status in (HypothesisStatus.VERIFIED, HypothesisStatus.CONFIRMED, HypothesisStatus.SUPPORTED))
            elif expected_status == HypothesisStatus.DISPROVEN:
                verification_correct = any(h.status == HypothesisStatus.DISPROVEN for h in state.hypotheses)

        # Check Root Cause Accuracy
        root_cause_matches = True
        if expected_root_cause_keywords:
            diag_text = (diag.likely_root_cause + " " + diag.problem_statement).lower()
            root_cause_matches = any(kw.lower() in diag_text for kw in expected_root_cause_keywords)

        case_passed = (len(unsupported_factual) == 0 and not is_premature and verification_correct and root_cause_matches)

        return {
            "success": case_passed,
            "factual_claims_total": len(factual_results),
            "factual_claims_grounded": len(grounded_factual),
            "unsupported_claims": len(unsupported_factual),
            "countercheck_executed": counter_executed or is_syntax,
            "is_premature": is_premature,
            "verification_correct": verification_correct,
            "root_cause_matches": root_cause_matches,
            "confidence": diag.confidence,
        }

    def aggregate_benchmark_results(self, case_reports: List[Dict[str, Any]]) -> BenchmarkEvaluationResult:
        """Aggregate session metrics across the complete benchmark suite."""
        total = len(case_reports)
        if total == 0:
            return BenchmarkEvaluationResult()

        passed = sum(1 for c in case_reports if c.get("success", False))
        total_factual = sum(c.get("factual_claims_total", 0) for c in case_reports)
        grounded_factual = sum(c.get("factual_claims_grounded", 0) for c in case_reports)
        unsupported_factual = sum(c.get("unsupported_claims", 0) for c in case_reports)

        egr = (grounded_factual / total_factual * 100.0) if total_factual > 0 else 100.0
        ucr = (unsupported_factual / total_factual * 100.0) if total_factual > 0 else 0.0

        correct_verifications = sum(1 for c in case_reports if c.get("verification_correct", False))
        hva = (correct_verifications / total * 100.0)

        counter_executed = sum(1 for c in case_reports if c.get("countercheck_executed", False))
        csr = (counter_executed / total * 100.0)

        premature_count = sum(1 for c in case_reports if c.get("is_premature", False))
        pdr = (premature_count / total * 100.0)

        return BenchmarkEvaluationResult(
            total_cases=total,
            passed_cases=passed,
            evidence_grounding_rate=round(egr, 1),
            unsupported_claim_rate=round(ucr, 1),
            hypothesis_verification_accuracy=round(hva, 1),
            counterexample_success_rate=round(csr, 1),
            premature_diagnosis_rate=round(pdr, 1),
            detailed_case_results=case_reports,
        )
