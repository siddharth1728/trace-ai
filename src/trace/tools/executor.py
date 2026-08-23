"""Controlled Python Execution Tool for TRACE investigation."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

from trace.safety.sandbox_limits import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    SafetyViolationError,
    sanitize_environment,
    truncate_output,
    validate_path_containment,
)
from trace.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolResult


class PythonExecutorTool(BaseTool):
    """Executes Python code in a controlled subprocess with timeout, output limits, and env scrubbing."""

    def __init__(self, workspace_root: Optional[str | Path] = None):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="python_executor",
            description="Executes Python source code in a controlled subprocess with strict timeouts and output capture.",
            parameters=[
                ToolParameter(
                    name="source_code",
                    type_name="string",
                    description="Python source code to execute.",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="file_path",
                    type_name="string",
                    description="Path to Python script file to execute.",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="args",
                    type_name="array",
                    description="Optional command-line arguments to pass to the script.",
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="stdin_input",
                    type_name="string",
                    description="Optional standard input to feed to the running program.",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="timeout_seconds",
                    type_name="number",
                    description=f"Execution timeout in seconds (default {DEFAULT_TIMEOUT_SECONDS}s, max {MAX_TIMEOUT_SECONDS}s).",
                    required=False,
                    default=DEFAULT_TIMEOUT_SECONDS,
                ),
            ],
            requires_execution=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        source_code = kwargs.get("source_code") or ""
        file_path = kwargs.get("file_path") or ""
        cmd_args = kwargs.get("args") or []
        stdin_input = kwargs.get("stdin_input")
        timeout = min(
            float(kwargs.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS),
            MAX_TIMEOUT_SECONDS
        )

        if not source_code and not file_path:
            return ToolResult(
                is_success=False,
                summary="Execution failed: Neither source_code nor file_path provided",
                error_message="Must provide either source_code or file_path to execute",
            )

        # Prepare target script path
        temp_dir: Optional[tempfile.TemporaryDirectory] = None
        target_script_path: Path

        try:
            if source_code:
                # Create a temporary directory for execution isolation
                temp_dir = tempfile.TemporaryDirectory(prefix="trace_exec_")
                target_script_path = Path(temp_dir.name) / "run_target.py"
                with open(target_script_path, "w", encoding="utf-8") as f:
                    f.write(source_code)
            else:
                # Validate existing file path containment
                target_script_path = validate_path_containment(
                    file_path,
                    allowed_root=self.workspace_root,
                    allow_temp=True,
                )
                if not target_script_path.exists():
                    return ToolResult(
                        is_success=False,
                        summary=f"Execution failed: Target file not found: {file_path}",
                        error_message=f"File does not exist: {target_script_path}",
                    )

            # Scrub environment variables
            safe_env = sanitize_environment()

            # Build command
            command = [sys.executable, str(target_script_path)] + [str(a) for a in cmd_args]
            cwd = str(target_script_path.parent)

            # Execute subprocess with timeout
            start_time = time.perf_counter()
            timed_out = False
            stdout_str = ""
            stderr_str = ""
            exit_code = 0

            try:
                proc = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE if stdin_input is not None else None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    env=safe_env,
                    text=True,
                )

                try:
                    stdout_str, stderr_str = proc.communicate(
                        input=stdin_input if stdin_input is not None else None,
                        timeout=timeout,
                    )
                    exit_code = proc.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    # Cleanly terminate process tree
                    self._kill_process_tree(proc)
                    try:
                        stdout_str, stderr_str = proc.communicate(timeout=1.0)
                    except Exception:
                        pass
                    exit_code = -1
            except Exception as proc_err:
                return ToolResult(
                    is_success=False,
                    summary=f"Failed to spawn execution process: {proc_err}",
                    error_message=str(proc_err),
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Output truncation
            stdout_clean = truncate_output(stdout_str)
            stderr_clean = truncate_output(stderr_str)

            has_error = (exit_code != 0) or timed_out or bool(stderr_clean.strip())

            result_data = {
                "exit_code": exit_code,
                "stdout": stdout_clean,
                "stderr": stderr_clean,
                "execution_time_ms": round(elapsed_ms, 2),
                "timed_out": timed_out,
                "has_error": has_error,
            }

            if timed_out:
                summary = f"Execution TIMED OUT after {timeout:.1f}s (Infinite loop or blocked I/O detected)"
                tags = ["execution", "timeout", "runtime_error"]
            elif exit_code != 0:
                # Extract first line of error or traceback summary
                err_first_line = stderr_clean.strip().splitlines()[-1] if stderr_clean.strip() else f"Exit code {exit_code}"
                summary = f"Execution FAILED (exit code {exit_code}): {err_first_line}"
                tags = ["execution", "runtime_error", "exit_failure"]
            else:
                summary = f"Execution SUCCEEDED (exit code 0 in {elapsed_ms:.1f}ms)"
                tags = ["execution", "success"]

            return ToolResult(
                is_success=not timed_out,  # Tool executed normally, even if script had runtime error
                data=result_data,
                summary=summary,
                error_message=stderr_clean if exit_code != 0 else None,
                evidence_tags=tags,
            )

        except SafetyViolationError as sve:
            return ToolResult(
                is_success=False,
                summary=f"Execution blocked by safety sandbox: {sve}",
                error_message=str(sve),
            )
        except Exception as ex:
            return ToolResult(
                is_success=False,
                summary=f"Unexpected error during execution: {ex}",
                error_message=str(ex),
            )
        finally:
            if temp_dir is not None:
                try:
                    temp_dir.cleanup()
                except Exception:
                    pass

    def _kill_process_tree(self, proc: subprocess.Popen) -> None:
        """Kill a subprocess and any children it may have spawned."""
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
