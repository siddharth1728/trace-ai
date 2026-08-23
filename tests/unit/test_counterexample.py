"""Unit tests for TRACE v0.2 CounterexampleEngine."""

import pytest
from trace.agent.counterexample import CounterexampleEngine
from trace.core.evidence import EvidenceRelation
from trace.core.models import Hypothesis, HypothesisStatus
from trace.core.state import AgentState


def test_counterexample_generation_and_execution_none_type():
    """Test generating and executing a valid non-None countercheck test."""
    source_code = """
def format_user_display_name(user_record):
    raw_name = user_record.get("name")
    return raw_name.upper()

guest_user = {"id": 101, "name": None, "role": "guest"}
print(format_user_display_name(guest_user))
"""
    state = AgentState(user_goal="Investigate NoneType", source_code=source_code)
    hyp = Hypothesis(
        id="hyp_none_01",
        statement="Function crashes because user record name is None before .upper() is called",
        status=HypothesisStatus.SUPPORTED,
    )
    state.add_hypothesis(hyp)

    engine = CounterexampleEngine()
    experiment = engine.generate_experiment(hyp, state)

    assert experiment is not None
    assert "Alice" in experiment.harness_code
    assert experiment.strategy == "NON_NONE_VALID_INPUT"

    # Execute experiment in sandbox
    evidence = engine.run_experiment(experiment, state)

    assert experiment.executed is True
    assert experiment.passed is True
    assert experiment.disproved is False
    assert evidence.relation == EvidenceRelation.VERIFIES
    assert "Countercheck passed" in evidence.statement


def test_counterexample_execution_disproves_wrong_hypothesis():
    """Test that a flawed hypothesis is disproven when the counter-experiment reproduces failure on predicted-safe input."""
    source_code = """
def bad_divide(x):
    # Bug: Unconditionally divides by zero
    return x / 0

print(bad_divide(10))
"""
    state = AgentState(user_goal="Investigate division", source_code=source_code)
    # Incorrect hypothesis claiming the bug occurs only when input is negative
    hyp = Hypothesis(
        id="hyp_wrong_01",
        statement="ZeroDivisionError occurs only when input is negative",
        status=HypothesisStatus.SUPPORTED,
    )
    state.add_hypothesis(hyp)

    engine = CounterexampleEngine()
    experiment = engine.generate_experiment(hyp, state)
    assert experiment is not None

    # Run experiment: tests with positive input x = 100.0, which still crashes with ZeroDivisionError
    evidence = engine.run_experiment(experiment, state)
    assert experiment.executed is True
    assert experiment.disproved is True
    assert evidence.relation == EvidenceRelation.DISPROVES
