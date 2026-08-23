"""Unit tests for TRACE v0.2 VerificationEngine."""

import pytest
from trace.agent.verifier import VerificationEngine, VerificationStatus
from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import Hypothesis, HypothesisStatus
from trace.core.state import AgentState


def test_verifier_verified_with_countercheck():
    """Test hypothesis becomes VERIFIED when supported by direct evidence and passed countercheck."""
    state = AgentState(user_goal="Test verify", source_code="def f(): pass")
    hyp = Hypothesis(id="hyp_01", statement="Crash on NoneType argument")
    state.add_hypothesis(hyp)

    # Add 2 direct supporting items
    state.add_evidence(Evidence(
        observation_id="obs_01",
        tool_name="ast_analyzer",
        evidence_type=EvidenceType.DIRECT,
        statement="AST shows function format_user_display_name",
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.SUPPORTS,
    ))
    state.add_evidence(Evidence(
        observation_id="obs_02",
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement="Execution reproduced AttributeError on NoneType",
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.SUPPORTS,
    ))
    # Add passing countercheck evidence
    state.add_evidence(Evidence(
        observation_id="obs_03",
        tool_name="counterexample_engine",
        evidence_type=EvidenceType.DIRECT,
        statement="Countercheck passed with valid input",
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.VERIFIES,
    ))

    verifier = VerificationEngine()
    result = verifier.verify_hypothesis(hyp, state)

    assert result.status == VerificationStatus.VERIFIED
    assert result.calibrated_confidence >= 0.90
    assert result.countercheck_passed is True
    assert result.countercheck_disproved is False


def test_verifier_disproven_by_countercheck():
    """Test hypothesis becomes DISPROVEN when countercheck produces a direct disproof."""
    state = AgentState(user_goal="Test disproof", source_code="def f(): pass")
    hyp = Hypothesis(id="hyp_02", statement="Crash only on empty list")
    state.add_hypothesis(hyp)

    # Countercheck disproved
    state.add_evidence(Evidence(
        observation_id="obs_04",
        tool_name="counterexample_engine",
        evidence_type=EvidenceType.DIRECT,
        statement="Countercheck failed: non-empty input also crashed with ZeroDivisionError",
        target_hypothesis_id="hyp_02",
        relation=EvidenceRelation.DISPROVES,
    ))

    verifier = VerificationEngine()
    result = verifier.verify_hypothesis(hyp, state)

    assert result.status == VerificationStatus.DISPROVEN
    assert result.calibrated_confidence <= 0.25
    assert result.countercheck_disproved is True


def test_verifier_strongly_supported_when_countercheck_pending():
    """Test hypothesis is STRONGLY_SUPPORTED when multiple direct evidence items exist but countercheck is pending."""
    state = AgentState(user_goal="Test strong support", source_code="def f(): pass")
    hyp = Hypothesis(id="hyp_03", statement="Out of bounds indexing")
    state.add_hypothesis(hyp)

    state.add_evidence(Evidence(
        observation_id="obs_05",
        tool_name="ast_analyzer",
        evidence_type=EvidenceType.DIRECT,
        statement="AST shows array indexing inside loop",
        target_hypothesis_id="hyp_03",
        relation=EvidenceRelation.SUPPORTS,
    ))
    state.add_evidence(Evidence(
        observation_id="obs_06",
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement="Execution reproduced IndexError: list index out of range",
        target_hypothesis_id="hyp_03",
        relation=EvidenceRelation.SUPPORTS,
    ))

    verifier = VerificationEngine()
    result = verifier.verify_hypothesis(hyp, state)

    assert result.status == VerificationStatus.STRONGLY_SUPPORTED
    assert 0.65 <= result.calibrated_confidence <= 0.80


def test_verifier_deterministic_syntax_error():
    """Test deterministic AST syntax error is automatically VERIFIED with 0.95 confidence."""
    state = AgentState(user_goal="Fix syntax", source_code="def foo()")
    hyp = Hypothesis(id="hyp_04", statement="Missing colon causes syntax error")
    state.add_hypothesis(hyp)

    state.add_evidence(Evidence(
        observation_id="obs_07",
        tool_name="ast_analyzer",
        evidence_type=EvidenceType.DIRECT,
        statement="AST SyntaxError detected at line 1, col 9: expected ':'",
        target_hypothesis_id="hyp_04",
        relation=EvidenceRelation.SUPPORTS,
    ))

    verifier = VerificationEngine()
    result = verifier.verify_hypothesis(hyp, state)

    assert result.status == VerificationStatus.VERIFIED
    assert result.calibrated_confidence == 0.95
