"""Unit tests for TRACE v0.2 DiagnosisClaimValidator."""

import pytest
from trace.core.claim_validator import ClaimType, DiagnosisClaimValidator
from trace.core.evidence import Evidence, EvidenceRelation, EvidenceType
from trace.core.models import FinalDiagnosis
from trace.core.state import AgentState


def test_claim_validator_preserves_grounded_factual_claims():
    """Test validator preserves factual claims that match verified direct evidence."""
    state = AgentState(user_goal="Test grounding", source_code="print('hello')")
    state.add_evidence(Evidence(
        observation_id="obs_01",
        tool_name="python_executor",
        evidence_type=EvidenceType.DIRECT,
        statement="Execution FAILED (exit code 1): AttributeError: 'NoneType' object has no attribute 'upper'",
        target_hypothesis_id="hyp_01",
        relation=EvidenceRelation.SUPPORTS,
    ))
    state.record_tool_call(
        tool_name="python_executor",
        arguments={},
        success=True,
        execution_time_ms=12.0,
    )

    raw_diag = FinalDiagnosis(
        problem_statement="TypeError on NoneType operation",
        investigation_summary="Subprocess ran",
        likely_root_cause="A variable is None",
        evidence_summary=[
            "Subprocess execution produced AttributeError on NoneType operation",
        ],
        confidence=0.90,
        what_trace_checked=[],
        what_remains_uncertain=[],
        learning_point="Check for None before invoking methods.",
        suggested_fix_guidance="Add if var is None check.",
    )

    validator = DiagnosisClaimValidator()
    grounded_diag, results = validator.validate_and_ground_diagnosis(raw_diag, state)

    assert len(results) >= 1
    assert results[0].is_grounded is True
    assert "AttributeError" in grounded_diag.evidence_summary[0]
    assert "Controlled Subprocess Sandbox Execution" in grounded_diag.what_trace_checked[0]


def test_claim_validator_flags_unsupported_factual_claim():
    """Test validator flags factual claims claiming tools or errors that never occurred."""
    state = AgentState(user_goal="Test unbacked claim", source_code="print('hello')")
    # State has NO traceback evidence and traceback_parser never ran
    state.record_tool_call(
        tool_name="ast_analyzer",
        arguments={},
        success=True,
        execution_time_ms=5.0,
    )

    raw_diag = FinalDiagnosis(
        problem_statement="Test statement",
        investigation_summary="Investigated code",
        likely_root_cause="Syntax error",
        evidence_summary=[
            "Traceback parser identified line 45 as failing frame with ZeroDivisionError",
        ],
        confidence=0.50,
        what_trace_checked=[],
        what_remains_uncertain=[],
        learning_point="Check code syntax.",
        suggested_fix_guidance="Fix line.",
    )

    validator = DiagnosisClaimValidator()
    grounded_diag, results = validator.validate_and_ground_diagnosis(raw_diag, state)

    # The unbacked traceback claim should be flagged as ungrounded
    unsupported = [r for r in results if not r.is_grounded]
    assert len(unsupported) == 1
    assert "lacks direct tool evidence" in unsupported[0].flagged_reason
    assert any("could not be directly confirmed" in unc for unc in grounded_diag.what_remains_uncertain)
