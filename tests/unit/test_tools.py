"""Unit tests for TRACE tools and ToolRegistry."""

from pathlib import Path
import pytest

from trace.tools.ast_analyzer import ASTAnalyzerTool
from trace.tools.file_reader import FileReaderTool
from trace.tools.registry import ToolNotFoundError, ToolRegistry, create_default_registry
from trace.tools.traceback_parser import TracebackParserTool


def test_file_reader_tool(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    test_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    reader = FileReaderTool(workspace_root=str(tmp_path))
    
    # Read entire file
    res = reader.execute(file_path=str(test_file))
    assert res.is_success
    assert res.data["total_lines"] == 5
    assert "line 1" in res.data["content"]
    assert "   1 | line 1" in res.data["numbered_content"]

    # Slice lines 2 to 4
    res_slice = reader.execute(file_path=str(test_file), start_line=2, end_line=4)
    assert res_slice.is_success
    assert res_slice.data["start_line"] == 2
    assert res_slice.data["end_line"] == 4
    assert res_slice.data["line_count"] == 3


def test_file_reader_nonexistent_file(tmp_path: Path):
    reader = FileReaderTool(workspace_root=str(tmp_path))
    res = reader.execute(file_path=str(tmp_path / "missing.py"))
    assert not res.is_success
    assert "not found" in res.summary.lower()


def test_ast_analyzer_valid_code():
    code = """
import math

def calculate_hypotenuse(a, b):
    \"\"\"Calculate hypotenuse.\"\"\"
    if a <= 0 or b <= 0:
        return 0
    return math.sqrt(a**2 + b**2)

class GeometryCalculator:
    def __init__(self):
        self.history = []
"""
    analyzer = ASTAnalyzerTool()
    res = analyzer.execute(source_code=code)
    assert res.is_success
    assert not res.data["has_syntax_error"]
    
    # Functions check
    fn_names = [f["name"] for f in res.data["functions"]]
    assert "calculate_hypotenuse" in fn_names
    assert "__init__" in fn_names
    
    # Classes check
    cls_names = [c["name"] for c in res.data["classes"]]
    assert "GeometryCalculator" in cls_names
    
    # Imports check
    modules = [imp["module"] for imp in res.data["imports"]]
    assert "math" in modules
    
    # Branches check
    assert res.data["metrics"]["branch_count"] >= 1


def test_ast_analyzer_syntax_error():
    broken_code = "def broken_func(x, y\n    return x + y"
    analyzer = ASTAnalyzerTool()
    res = analyzer.execute(source_code=broken_code)
    assert res.is_success
    assert res.data["has_syntax_error"]
    syntax_err = res.data["syntax_error"]
    assert syntax_err["error_type"] == "SyntaxError"
    assert syntax_err["line"] is not None


def test_ast_analyzer_recursion_detection():
    recursive_code = """
def countdown(n):
    if n <= 0:
        return
    print(n)
    countdown(n - 1)
"""
    analyzer = ASTAnalyzerTool()
    res = analyzer.execute(source_code=recursive_code)
    assert res.is_success
    assert "countdown" in res.data["recursive_functions"]


def test_traceback_parser():
    raw_traceback = """Traceback (most recent call last):
  File "calculator.py", line 18, in <module>
    result = compute_metrics([1, 2, 0, 4])
  File "calculator.py", line 12, in compute_metrics
    val = process_item(x)
  File "calculator.py", line 6, in process_item
    return 100 / item
ZeroDivisionError: division by zero"""

    parser = TracebackParserTool()
    res = parser.execute(traceback_text=raw_traceback)
    assert res.is_success
    assert res.data["exception_type"] == "ZeroDivisionError"
    assert "division by zero" in res.data["exception_message"]
    assert res.data["stack_depth"] == 3
    
    primary = res.data["primary_frame"]
    assert primary["file"] == "calculator.py"
    assert primary["line"] == 6
    assert primary["function"] == "process_item"
    assert "return 100 / item" in primary["code"]


def test_tool_registry():
    registry = create_default_registry()
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "file_reader" in tool_names
    assert "ast_analyzer" in tool_names
    assert "traceback_parser" in tool_names
    assert "python_executor" in tool_names

    # Unknown tool raises error
    with pytest.raises(ToolNotFoundError):
        registry.get("non_existent_tool")
