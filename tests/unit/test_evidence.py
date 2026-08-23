"""Unit tests for TRACE v0.2 Evidence domain model and relationships."""

import pytest
from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import Hypothesis, HypothesisStatus
from trace.core.state import AgentState


def test_evidence_creation_direct_and_derived():
    """Test creating DIRECT and DERIVED evidence with proper type tags and weights."""
    direct_ev = Evidence(
        observation_id="obs_001",
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement="Execution failed with exit code 1: ZeroDivisionError",
        raw_fact={"exit_code": 1, "error": "ZeroDivisionError"},
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.SUPPORTS,
        confidence_weight=1.0,
    )
    assert direct_ev.is_direct() is True
    assert direct_ev.is_supporting() is True
    assert direct_ev.is_contradicting() is False

    derived_ev = Evidence(
        observation_id="obs_002",
        tool_name="ast_analyzer",
        evidence_type=EvidenceType.DERIVED,
        statement="Inference: Empty list input leads to len(scores) evaluating to 0",
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.DERIVED_FROM,
        confidence_weight=0.7,
    )
    assert derived_ev.is_direct() is False
    assert derived_ev.confidence_weight == 0.7


def test_evidence_linking_to_hypothesis_in_state():
    """Test adding evidence to AgentState links IDs to target hypothesis."""
    state = AgentState(
        user_goal="Test evidence linking",
        source_code="def f(x): return x",
    )
    hyp = Hypothesis(
        id="hyp_test_01",
        statement="A variable is None at runtime",
        status=HypothesisStatus.PROPOSED,
    )
    state.add_hypothesis(hyp)

    # Add supporting evidence
    ev_sup = Evidence(
        observation_id="obs_100",
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement="Reproduced AttributeError on NoneType",
        target_hypothesis_id="hyp_test_01",
        relation=EvidenceRelation.SUPPORTS,
    )
    state.add_evidence(ev_sup)

    # Add contradicting evidence
    ev_contra = Evidence(
        observation_id="obs_101",
        tool_name="ast_analyzer",
        evidence_type=EvidenceType.DIRECT,
        statement="Variable is explicitly initialized before use",
        target_hypothesis_id="hyp_test_01",
        relation=EvidenceRelation.CONTRADICTS,
    )
    state.add_evidence(ev_contra)

    updated_hyp = state.get_hypothesis("hyp_test_01")
    assert ev_sup.id in updated_hyp.supporting_evidence_ids
    assert ev_contra.id in updated_hyp.contradictory_evidence_ids

    direct_supporting = state.get_direct_supporting_evidence("hyp_test_01")
    assert len(direct_supporting) == 1
    assert direct_supporting[0].id == ev_sup.id

    contradicting = state.get_contradicting_evidence("hyp_test_01")
    assert len(contradicting) == 1
    assert contradicting[0].id == ev_contra.id
