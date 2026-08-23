"""Deterministic Python AST Analysis Tool for TRACE."""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from trace.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolResult


class ASTInspector(ast.NodeVisitor):
    """AST visitor extracting structural properties from Python source code."""

    def __init__(self):
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []
        self.assignments: List[Dict[str, Any]] = []
        self.control_flow: List[Dict[str, Any]] = []
        self.node_count: int = 0
        self.branch_count: int = 0
        self._current_function: Optional[str] = None
        self._current_class: Optional[str] = None

    def visit(self, node: ast.AST) -> Any:
        self.node_count += 1
        return super().visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev_fn = self._current_function
        self._current_function = node.name

        args_list = [arg.arg for arg in node.args.args]
        fn_info = {
            "name": node.name,
            "class_name": self._current_class,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", node.lineno),
            "arguments": args_list,
            "has_vararg": node.args.vararg is not None,
            "has_kwarg": node.args.kwarg is not None,
            "is_async": False,
            "decorators": [self._get_name(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node),
        }
        self.functions.append(fn_info)

        self.generic_visit(node)
        self._current_function = prev_fn

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev_fn = self._current_function
        self._current_function = node.name

        args_list = [arg.arg for arg in node.args.args]
        fn_info = {
            "name": node.name,
            "class_name": self._current_class,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", node.lineno),
            "arguments": args_list,
            "is_async": True,
            "decorators": [self._get_name(d) for d in node.decorator_list],
            "docstring": ast.get_docstring(node),
        }
        self.functions.append(fn_info)

        self.generic_visit(node)
        self._current_function = prev_fn

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        prev_cls = self._current_class
        self._current_class = node.name

        cls_info = {
            "name": node.name,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", node.lineno),
            "bases": [self._get_name(b) for b in node.bases],
            "docstring": ast.get_docstring(node),
        }
        self.classes.append(cls_info)

        self.generic_visit(node)
        self._current_class = prev_cls

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                "type": "import",
                "module": alias.name,
                "asname": alias.asname,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "type": "from_import",
                "module": module,
                "name": alias.name,
                "asname": alias.asname,
                "line": node.lineno,
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._get_name(node.func)
        call_info = {
            "function": func_name,
            "line": node.lineno,
            "arg_count": len(node.args),
            "kwarg_count": len(node.keywords),
            "in_function": self._current_function,
            "is_recursive": (func_name == self._current_function and self._current_function is not None),
        }
        self.calls.append(call_info)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        targets: List[str] = []
        for t in node.targets:
            name = self._get_name(t)
            if name:
                targets.append(name)
        if targets:
            self.assignments.append({
                "targets": targets,
                "line": node.lineno,
                "in_function": self._current_function,
            })
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        target = self._get_name(node.target)
        if target:
            self.assignments.append({
                "targets": [target],
                "line": node.lineno,
                "is_augmented": True,
                "in_function": self._current_function,
            })
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.branch_count += 1
        self.control_flow.append({
            "type": "if",
            "line": node.lineno,
            "in_function": self._current_function,
        })
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.branch_count += 1
        self.control_flow.append({
            "type": "for_loop",
            "line": node.lineno,
            "target": self._get_name(node.target),
            "in_function": self._current_function,
        })
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.branch_count += 1
        self.control_flow.append({
            "type": "while_loop",
            "line": node.lineno,
            "in_function": self._current_function,
        })
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.branch_count += 1
        handlers = [self._get_name(h.type) if h.type else "Exception" for h in node.handlers]
        self.control_flow.append({
            "type": "try_except",
            "line": node.lineno,
            "handlers": handlers,
            "in_function": self._current_function,
        })
        self.generic_visit(node)

    def _get_name(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return type(node).__name__


class ASTAnalyzerTool(BaseTool):
    """Inspects Python source code deterministically using Python's abstract syntax tree."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ast_analyzer",
            description="Performs deterministic static analysis on Python source code via AST.",
            parameters=[
                ToolParameter(
                    name="source_code",
                    type_name="string",
                    description="Python source code to parse and analyze.",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="file_path",
                    type_name="string",
                    description="Optional file path to read source code from.",
                    required=False,
                    default="",
                ),
            ],
            requires_file_access=False,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        source_code = kwargs.get("source_code") or ""
        file_path = kwargs.get("file_path") or ""

        if not source_code and file_path:
            p = Path(file_path)
            if p.exists() and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        source_code = f.read()
                except Exception as ex:
                    return ToolResult(
                        is_success=False,
                        summary=f"Failed to read file for AST analysis: {ex}",
                        error_message=str(ex),
                    )
            else:
                return ToolResult(
                    is_success=False,
                    summary=f"File not found for AST analysis: {file_path}",
                    error_message=f"File path does not exist: {file_path}",
                )

        if not source_code.strip():
            return ToolResult(
                is_success=False,
                summary="AST analysis failed: Empty source code provided",
                error_message="No source code provided for analysis",
            )

        # Attempt to parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as se:
            # Report deterministic syntax error
            error_data = {
                "has_syntax_error": True,
                "syntax_error": {
                    "line": se.lineno,
                    "column": se.offset,
                    "error_type": "SyntaxError",
                    "message": se.msg,
                    "text": se.text.strip() if se.text else "",
                },
            }
            summary = f"SyntaxError detected at line {se.lineno}, col {se.offset}: {se.msg}"
            if se.text:
                summary += f" in line: '{se.text.strip()}'"
            return ToolResult(
                is_success=True,
                data=error_data,
                summary=summary,
                evidence_tags=["syntax_error", "static_analysis"],
            )

        # Inspect valid tree
        inspector = ASTInspector()
        inspector.visit(tree)

        # Check for recursive calls
        recursive_functions = [
            call["function"] for call in inspector.calls if call["is_recursive"]
        ]

        data = {
            "has_syntax_error": False,
            "functions": inspector.functions,
            "classes": inspector.classes,
            "imports": inspector.imports,
            "calls": inspector.calls,
            "assignments": inspector.assignments,
            "control_flow": inspector.control_flow,
            "metrics": {
                "total_nodes": inspector.node_count,
                "function_count": len(inspector.functions),
                "class_count": len(inspector.classes),
                "import_count": len(inspector.imports),
                "call_count": len(inspector.calls),
                "branch_count": inspector.branch_count,
            },
            "recursive_functions": list(set(recursive_functions)),
        }

        fn_names = [f["name"] for f in inspector.functions]
        cls_names = [c["name"] for c in inspector.classes]
        summary = (
            f"AST analysis succeeded: {len(fn_names)} function(s) {fn_names}, "
            f"{len(cls_names)} class(es) {cls_names}, {inspector.branch_count} branch point(s)."
        )

        return ToolResult(
            is_success=True,
            data=data,
            summary=summary,
            evidence_tags=["ast_structure", "static_analysis"],
        )
