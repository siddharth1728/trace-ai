"""Unit tests for PythonExecutorTool and Safety Sandbox controls."""

import os
from pathlib import Path
import pytest

from trace.safety.sandbox_limits import (
    MAX_OUTPUT_BYTES,
    SafetyViolationError,
    sanitize_environment,
    truncate_output,
    validate_path_containment,
)
from trace.tools.executor import PythonExecutorTool


def test_executor_successful_run():
    executor = PythonExecutorTool()
    code = "print('TRACE execution test: 42')"
    result = executor.execute(source_code=code)
    
    assert result.is_success
    assert result.data["exit_code"] == 0
    assert "TRACE execution test: 42" in result.data["stdout"]
    assert not result.data["timed_out"]
    assert not result.data["has_error"]


def test_executor_runtime_error():
    executor = PythonExecutorTool()
    code = """
def divide(a, b):
    return a / b

divide(10, 0)
"""
    result = executor.execute(source_code=code)
    
    assert result.data["exit_code"] != 0
    assert result.data["has_error"]
    assert "ZeroDivisionError" in result.data["stderr"]


def test_executor_timeout_infinite_loop():
    executor = PythonExecutorTool()
    # Code with infinite loop
    code = """
import time
while True:
    time.sleep(0.1)
"""
    # Run with 1 second timeout
    result = executor.execute(source_code=code, timeout_seconds=1.0)
    
    assert result.data["timed_out"] is True
    assert "TIMED OUT" in result.summary


def test_executor_output_truncation():
    executor = PythonExecutorTool()
    # Generate 50KB of output
    code = "print('X' * 50000)"
    result = executor.execute(source_code=code)
    
    stdout = result.data["stdout"]
    assert len(stdout.encode("utf-8")) <= MAX_OUTPUT_BYTES + 500  # allowing truncation note
    assert "[OUTPUT TRUNCATED:" in stdout


def test_executor_environment_sanitization(monkeypatch):
    # Set dummy sensitive environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-12345")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret-abc")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
    monkeypatch.setenv("NORMAL_APP_ENV", "testing")

    safe_env = sanitize_environment()
    assert "OPENAI_API_KEY" not in safe_env
    assert "AWS_SECRET_ACCESS_KEY" not in safe_env
    assert "DATABASE_URL" not in safe_env

    # Run executor and verify subprocess cannot access sensitive env
    executor = PythonExecutorTool()
    code = """
import os
import sys

has_openai = "OPENAI_API_KEY" in os.environ
has_aws = "AWS_SECRET_ACCESS_KEY" in os.environ
print(f"SECRET_DETECTED:{has_openai or has_aws}")
"""
    result = executor.execute(source_code=code)
    assert result.is_success
    assert "SECRET_DETECTED:False" in result.data["stdout"]


def test_path_containment_violation(tmp_path: Path):
    allowed_dir = tmp_path / "sandbox"
    allowed_dir.mkdir()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret")

    # Should raise safety violation for path outside allowed_dir
    with pytest.raises(SafetyViolationError):
        validate_path_containment(outside_file, allowed_root=allowed_dir, allow_temp=False)
