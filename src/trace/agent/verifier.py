"""Deterministic Verification Engine for TRACE v0.2."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import Hypothesis, HypothesisStatus
from trace.core.state import AgentState


class VerificationStatus(str, Enum):
    """Deterministic verification states for evaluating hypotheses."""
    VERIFIED = "VERIFIED"                      # Strong direct evidence + successful countercheck with 0 disproofs
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"  # Multiple direct supporting observations, countercheck pending
    PLAUSIBLE = "PLAUSIBLE"                    # Suggestive evidence exists, but verification is incomplete
    UNVERIFIED = "UNVERIFIED"                  # Lacks sufficient supporting evidence
    DISPROVEN = "DISPROVEN"                    # Targeted countercheck or direct observation refutes hypothesis


class HypothesisVerification(BaseModel):
    """Deterministic verification result for a single hypothesis."""
    hypothesis_id: str
    status: VerificationStatus
    calibrated_confidence: float = Field(ge=0.0, le=1.0)
    direct_supporting_count: int = 0
    derived_supporting_count: int = 0
    contradiction_count: int = 0
    countercheck_attempted: bool = False
    countercheck_passed: bool = False
    countercheck_disproved: bool = False
    rationale: str = ""


class VerificationEngine:
    """
    Evaluates evidence chains deterministically without relying on LLM self-assessment.
    Inspects direct vs derived evidence, contradiction counts, and countercheck outcomes.
    """

    def verify_hypothesis(
        self,
        hypothesis: Hypothesis,
        state: AgentState,
    ) -> HypothesisVerification:
        """Deterministically assess the verification state of a single hypothesis."""
        all_evidence = state.get_evidence_for_hypothesis(hypothesis.id)
        
        direct_supporting = [e for e in all_evidence if e.is_supporting() and e.is_direct()]
        derived_supporting = [e for e in all_evidence if e.is_supporting() and not e.is_direct()]
        contradictions = [e for e in all_evidence if e.is_contradicting()]

        counter_verifies = any(e.relation == EvidenceRelation.VERIFIES for e in all_evidence)
        counter_disproves = any(e.relation == EvidenceRelation.DISPROVES for e in all_evidence)
        counter_attempted = counter_verifies or counter_disproves

        n_direct = len(direct_supporting)
        n_derived = len(derived_supporting)
        n_contra = len(contradictions)

        # 1. Check if disproven
        if counter_disproves or n_contra > 0 and n_direct == 0:
            status = VerificationStatus.DISPROVEN
            confidence = max(0.05, min(0.25, 0.20 - 0.05 * n_contra))
            rationale = "Targeted countercheck or contradictory evidence directly disproved this hypothesis."
            return HypothesisVerification(
                hypothesis_id=hypothesis.id,
                status=status,
                calibrated_confidence=confidence,
                direct_supporting_count=n_direct,
                derived_supporting_count=n_derived,
                contradiction_count=n_contra,
                countercheck_attempted=counter_attempted,
                countercheck_passed=counter_verifies,
                countercheck_disproved=True,
                rationale=rationale,
            )

        # 2. Check deterministic syntax error
        is_syntax_hyp = "syntax" in hypothesis.statement.lower()
        has_syntax_ast = any(
            e.tool_name == "ast_analyzer" and "syntax" in e.statement.lower()
            for e in direct_supporting
        )
        if is_syntax_hyp and has_syntax_ast and n_contra == 0:
            status = VerificationStatus.VERIFIED
            confidence = 0.95
            rationale = "Conclusively verified via deterministic AST syntax error parsing coordinates."
            return HypothesisVerification(
                hypothesis_id=hypothesis.id,
                status=status,
                calibrated_confidence=confidence,
                direct_supporting_count=n_direct,
                derived_supporting_count=n_derived,
                contradiction_count=n_contra,
                countercheck_attempted=counter_attempted,
                countercheck_passed=True,
                countercheck_disproved=False,
                rationale=rationale,
            )

        # 3. Check VERIFIED (Strong direct evidence + passed countercheck)
        if n_direct >= 1 and counter_verifies and n_contra == 0:
            status = VerificationStatus.VERIFIED
            # Formula: min(0.95, 0.80 + 0.05 * min(n_direct, 3) + 0.10)
            confidence = min(0.95, 0.80 + 0.05 * min(n_direct, 3) + 0.10)
            rationale = f"Verified: {n_direct} direct evidence item(s) supported by successful countercheck experiment."
            return HypothesisVerification(
                hypothesis_id=hypothesis.id,
                status=status,
                calibrated_confidence=confidence,
                direct_supporting_count=n_direct,
                derived_supporting_count=n_derived,
                contradiction_count=n_contra,
                countercheck_attempted=True,
                countercheck_passed=True,
                countercheck_disproved=False,
                rationale=rationale,
            )

        # 4. Check STRONGLY_SUPPORTED (>= 2 direct supporting items, 0 contradictions)
        if n_direct >= 2 and n_contra == 0:
            status = VerificationStatus.STRONGLY_SUPPORTED
            # Formula: min(0.80, 0.65 + 0.05 * min(n_direct, 3))
            confidence = min(0.80, 0.65 + 0.05 * min(n_direct, 3))
            rationale = f"Strongly supported by {n_direct} direct observations; countercheck pending."
            return HypothesisVerification(
                hypothesis_id=hypothesis.id,
                status=status,
                calibrated_confidence=confidence,
                direct_supporting_count=n_direct,
                derived_supporting_count=n_derived,
                contradiction_count=n_contra,
                countercheck_attempted=counter_attempted,
                countercheck_passed=False,
                countercheck_disproved=False,
                rationale=rationale,
            )

        # 5. Check PLAUSIBLE (>= 1 direct or derived supporting item)
        if (n_direct >= 1 or n_derived >= 1) and n_contra == 0:
            status = VerificationStatus.PLAUSIBLE
            confidence = 0.50
            rationale = "Plausible: Single or derived observation evidence exists; further verification required."
            return HypothesisVerification(
                hypothesis_id=hypothesis.id,
                status=status,
                calibrated_confidence=confidence,
                direct_supporting_count=n_direct,
                derived_supporting_count=n_derived,
                contradiction_count=n_contra,
                countercheck_attempted=counter_attempted,
                countercheck_passed=False,
                countercheck_disproved=False,
                rationale=rationale,
            )

        # 6. Fallback: UNVERIFIED
        status = VerificationStatus.UNVERIFIED
        confidence = 0.20
        rationale = "Unverified: No successful supporting tool observations collected."
        return HypothesisVerification(
            hypothesis_id=hypothesis.id,
            status=status,
            calibrated_confidence=confidence,
            direct_supporting_count=n_direct,
            derived_supporting_count=n_derived,
            contradiction_count=n_contra,
            countercheck_attempted=counter_attempted,
            countercheck_passed=False,
            countercheck_disproved=False,
            rationale=rationale,
        )

    def verify_all_hypotheses(self, state: AgentState) -> List[HypothesisVerification]:
        """Run deterministic verification across all active hypotheses in state."""
        return [self.verify_hypothesis(hyp, state) for hyp in state.hypotheses]
