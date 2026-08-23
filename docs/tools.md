# TRACE Tool System Reference

TRACE tools are deterministic, testable software components that extract concrete facts about code without relying on LLM speculation.

---

## 1. Tool Summary

| Tool Name | Type | Purpose | Primary Evidence Generated |
| :--- | :--- | :--- | :--- |
| **`file_reader`** | Static / File System | Safe inspection of Python source files | Source lines, line count, file size validation |
| **`ast_analyzer`** | Static / AST | Deterministic Python AST parsing | Syntax errors, functions, calls, assignments, recursion |
| **`traceback_parser`** | Static / Log | Normalization of Python tracebacks | Exception type, message, frame stack, root cause line |
| **`python_executor`** | Dynamic / Subprocess | Controlled execution in isolated temporary directory | Exit code, stdout, stderr, execution duration, timeouts |

---

## 2. Tool Details

### `file_reader`
* **Input Parameters**: `file_path: str`, `start_line: int = 1`, `end_line: Optional[int]`, `max_lines: int = 300`
* **Safety Controls**: Enforces path containment within allowed workspace; rejects files $>256\text{ KB}$.
* **Returns**: Sliced content, line counts, numbered line display.

### `ast_analyzer`
* **Input Parameters**: `source_code: str`, `file_path: Optional[str]`
* **Capabilities**:
  * Catches `SyntaxError` and returns line, column, and exact invalid token text.
  * Traverses AST to map functions, classes, imports, variable assignments, calls, branch points, and recursive self-calls.
* **Returns**: Structured dictionary of code entities and complexity metrics.

### `traceback_parser`
* **Input Parameters**: `traceback_text: str`
* **Capabilities**:
  * Extracts exception class (e.g. `TypeError`, `ZeroDivisionError`, `IndexError`).
  * Parses individual stack frames (file, line, function, code line).
  * Identifies the primary failing frame.
* **Returns**: Structured frame array and root exception message.

### `python_executor`
* **Input Parameters**: `source_code: Optional[str]`, `file_path: Optional[str]`, `args: List[str]`, `stdin_input: Optional[str]`, `timeout_seconds: float = 5.0`
* **Safety Controls**:
  * Runs in dedicated temporary directory (`tempfile.TemporaryDirectory`).
  * Environment variable stripping (removes API keys and secrets).
  * Subprocess timeout with process tree termination.
  * Output truncated to $10\text{ KB}$ max to prevent memory exhaustion.
* **Returns**: Exit code, standard output, standard error, execution duration, timeout flag.
