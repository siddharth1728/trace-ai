"""AST Structural Diff Engine for TRACE v0.5 Code Revisions."""

import ast
import difflib
from typing import Any, Dict, List, Set, Tuple


class CodeDiffEngine:
    """Calculates structural, AST-level, and complexity diffs between Python code revisions."""

    @classmethod
    def calculate_diff(cls, old_code: str, new_code: str) -> Dict[str, Any]:
        """Compute unified line diffs, AST node replacements, and cyclomatic complexity changes."""
        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()

        # 1. Text-level line modifications
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        lines_added = 0
        lines_deleted = 0
        lines_modified = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                lines_added += (j2 - j1)
            elif tag == "delete":
                lines_deleted += (i2 - i1)
            elif tag == "replace":
                lines_modified += max(i2 - i1, j2 - j1)

        # 2. Non-empty, non-comment LOC for new code
        executable_lines = [l for l in new_lines if l.strip() and not l.strip().startswith("#")]
        total_loc = len(executable_lines)

        # 3. AST Complexity and Modified Nodes
        old_tree, old_syntax_ok = cls._safe_parse(old_code)
        new_tree, new_syntax_ok = cls._safe_parse(new_code)

        old_complexity = cls._compute_complexity(old_tree) if old_syntax_ok else 1
        new_complexity = cls._compute_complexity(new_tree) if new_syntax_ok else 1
        complexity_delta = new_complexity - old_complexity

        # 4. AST Modified Node Types and Functions
        modified_ast_nodes = cls._detect_modified_nodes(old_tree, new_tree)
        modified_functions = cls._detect_modified_functions(old_tree, new_tree, old_lines, new_lines)

        return {
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "lines_modified": lines_modified,
            "total_loc": total_loc,
            "cyclomatic_complexity_delta": complexity_delta,
            "modified_ast_nodes": modified_ast_nodes,
            "modified_functions": modified_functions,
            "is_syntax_valid": new_syntax_ok,
        }

    @staticmethod
    def _safe_parse(code: str) -> Tuple[Any, bool]:
        """Parse source code with syntax error resilience."""
        try:
            tree = ast.parse(code)
            return tree, True
        except (SyntaxError, IndentationError):
            return None, False

    @staticmethod
    def _compute_complexity(tree: Any) -> int:
        """Compute estimated cyclomatic complexity."""
        if tree is None:
            return 1
        branches = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert))
        )
        return max(1, branches + 1)

    @classmethod
    def _detect_modified_nodes(cls, old_tree: Any, new_tree: Any) -> List[str]:
        """Identify what structural AST node types were introduced or altered."""
        if old_tree is None or new_tree is None:
            return ["SyntaxChange"]

        old_node_types = {type(n).__name__ for n in ast.walk(old_tree)}
        new_node_types = {type(n).__name__ for n in ast.walk(new_tree)}

        # Structural changes
        added_types = new_node_types - old_node_types
        # Significant control flow nodes in new tree
        critical_types = {"If", "Return", "Raise", "Try", "ExceptHandler", "For", "While", "Subscript", "Call", "BinOp", "Compare"}
        present_critical = {type(n).__name__ for n in ast.walk(new_tree) if type(n).__name__ in critical_types}

        combined: Set[str] = added_types.union(present_critical)
        # Filter out trivial types like Module, Load, Store
        filtered = sorted([t for t in combined if t not in ("Module", "Load", "Store", "Expr", "Name", "Constant")])
        return filtered or ["Expression"]

    @classmethod
    def _detect_modified_functions(cls, old_tree: Any, new_tree: Any, old_lines: List[str], new_lines: List[str]) -> List[str]:
        """Identify which function definitions were modified."""
        if new_tree is None:
            return []

        funcs: List[str] = []
        for node in ast.walk(new_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append(node.name)

        return sorted(list(set(funcs)))
