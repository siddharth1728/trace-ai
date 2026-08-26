"""Unit tests for AST structural and complexity diff engine in TRACE v0.5."""

from trace.agent.diff_engine import CodeDiffEngine


def test_diff_engine_identical_code():
    code = "def add(a, b):\n    return a + b\n"
    diff = CodeDiffEngine.calculate_diff(code, code)
    assert diff["lines_added"] == 0
    assert diff["lines_deleted"] == 0
    assert diff["lines_modified"] == 0
    assert diff["cyclomatic_complexity_delta"] == 0
    assert diff["is_syntax_valid"] is True


def test_diff_engine_line_additions_and_deletions():
    old_code = "def foo():\n    return 1\n"
    new_code = "def foo():\n    # Added check\n    if True:\n        return 2\n"
    diff = CodeDiffEngine.calculate_diff(old_code, new_code)
    assert diff["lines_added"] > 0
    assert diff["cyclomatic_complexity_delta"] >= 1
    assert "If" in diff["modified_ast_nodes"]
    assert "foo" in diff["modified_functions"]


def test_diff_engine_syntax_error_resilience():
    old_code = "def foo():\n    pass\n"
    broken_code = "def foo(:\n    pass"
    diff = CodeDiffEngine.calculate_diff(old_code, broken_code)
    assert diff["is_syntax_valid"] is False
    assert diff["lines_modified"] >= 1
