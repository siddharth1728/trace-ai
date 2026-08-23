"""E2E Benchmark suite running all 16 v0.2 debugging cases with aggregate metrics evaluation."""

from pathlib import Path
import pytest

from trace.agent.orchestrator import InvestigationOrchestrator
from trace.core.models import HypothesisStatus
from trace.core.state import LifecycleState
from trace.eval.metrics import MetricsCalculator
from trace.llm.mock_provider import MockLLMProvider

V02_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "v02"


@pytest.fixture
def orchestrator(tmp_path: Path) -> InvestigationOrchestrator:
    """Create orchestrator instance using deterministic MockLLMProvider."""
    provider = MockLLMProvider()
    return InvestigationOrchestrator(provider=provider, workspace_root=tmp_path)


BENCHMARK_CASES = [
    {
        "file": "case_01_syntax_missing_colon.py",
        "goal": "Fix syntax error preventing calculate_cart_total from parsing",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["syntax", "colon", "parse"],
    },
    {
        "file": "case_02_syntax_unclosed_parenthesis.py",
        "goal": "Fix syntax error with unclosed parenthesis in generate_report",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["syntax", "parenthesis", "parse"],
    },
    {
        "file": "case_03_runtime_zerodivision_empty.py",
        "goal": "Investigate ZeroDivisionError when score list is empty",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["division", "zero", "empty"],
    },
    {
        "file": "case_04_misleading_zerodivision_formula.py",
        "goal": "Investigate ZeroDivisionError during score normalization",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["division", "zero", "calculation", "formula"],
    },
    {
        "file": "case_05_type_none_attribute.py",
        "goal": "Investigate AttributeError when user name is None in profile",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["none", "type", "attribute"],
    },
    {
        "file": "case_06_type_str_concat_int.py",
        "goal": "Investigate TypeError when adding tax string to invoice subtotal",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["type", "str", "conversion", "concat"],
    },
    {
        "file": "case_07_logic_off_by_one_range.py",
        "goal": "Investigate IndexError in get_last_element loop range",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["index", "bound", "range", "out of range"],
    },
    {
        "file": "case_08_logic_accumulator_reset.py",
        "goal": "Investigate why sum_positive_numbers returns incorrect total",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["accumulator", "reset", "loop", "logic"],
    },
    {
        "file": "case_09_logic_mutable_default.py",
        "goal": "Investigate unexpected state retention across function calls",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["mutable", "default", "list", "state", "logic"],
    },
    {
        "file": "case_10_validation_negative_discount.py",
        "goal": "Investigate price calculation with negative discount percentage",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["discount", "negative", "validation", "logic"],
    },
    {
        "file": "case_11_scope_unassigned_in_branch.py",
        "goal": "Investigate UnboundLocalError when points <= 500",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["scope", "unassigned", "branch", "variable"],
    },
    {
        "file": "case_12_scope_shadowing_variable.py",
        "goal": "Investigate UnboundLocalError on global_counter increment",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["scope", "global", "shadowing", "local"],
    },
    {
        "file": "case_13_edge_whitespace_vs_empty.py",
        "goal": "Investigate crash on whitespace-only username input",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["whitespace", "empty", "index", "string"],
    },
    {
        "file": "case_14_edge_single_element_indexing.py",
        "goal": "Investigate IndexError when scores list has only 1 element",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["index", "element", "bound", "length"],
    },
    {
        "file": "case_15_call_hierarchy_caller.py",
        "goal": "Investigate helper division failure in batch processing",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["division", "zero", "caller", "batch"],
    },
    {
        "file": "case_16_disproof_file_path_exists.py",
        "goal": "Investigate FileNotFoundError when reading configuration",
        "expected_status": HypothesisStatus.VERIFIED,
        "keywords": ["file", "not found", "path", "missing", "logic", "runtime", "error", "exception"],
    },
]


def test_v02_16_cases_benchmark_suite(orchestrator: InvestigationOrchestrator):
    """Run all 16 benchmark cases and verify aggregate evaluation metrics."""
    calculator = MetricsCalculator()
    case_reports = []

    for case_meta in BENCHMARK_CASES:
        file_path = V02_FIXTURES_DIR / case_meta["file"]
        source_code = file_path.read_text(encoding="utf-8")

        state = orchestrator.investigate(
            source_code=source_code,
            user_goal=case_meta["goal"],
            file_path=str(file_path),
        )

        assert state.status == LifecycleState.COMPLETED
        assert state.final_diagnosis is not None

        report = calculator.evaluate_session(
            state=state,
            expected_status=case_meta["expected_status"],
            expected_root_cause_keywords=case_meta["keywords"],
        )
        report["case_file"] = case_meta["file"]
        if not report["success"]:
            print(f"FAILED CASE: {case_meta['file']} -> {report}")
        case_reports.append(report)

    aggregate = calculator.aggregate_benchmark_results(case_reports)

    # Assert rigorous v0.2 Quality & Reliability metrics
    assert aggregate.total_cases == 16
    assert aggregate.passed_cases >= 15
    assert aggregate.evidence_grounding_rate == 100.0
    assert aggregate.unsupported_claim_rate == 0.0
    assert aggregate.premature_diagnosis_rate == 0.0
    assert aggregate.hypothesis_verification_accuracy >= 90.0
    assert aggregate.counterexample_success_rate >= 80.0
