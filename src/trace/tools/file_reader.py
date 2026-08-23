"""Python source file reader tool with safety constraints."""

from pathlib import Path
from typing import Any, Dict, Optional

from trace.safety.sandbox_limits import (
    MAX_FILE_SIZE_BYTES,
    SafetyViolationError,
    validate_path_containment,
)
from trace.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolResult


class FileReaderTool(BaseTool):
    """Safely reads Python source files, enforcing size and path safety constraints."""

    def __init__(self, workspace_root: Optional[str | Path] = None):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_reader",
            description="Reads Python source code from a file with optional line slicing and safety checks.",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type_name="string",
                    description="Path to the Python source file to read.",
                    required=True,
                ),
                ToolParameter(
                    name="start_line",
                    type_name="integer",
                    description="1-based starting line number for slicing (inclusive).",
                    required=False,
                    default=1,
                ),
                ToolParameter(
                    name="end_line",
                    type_name="integer",
                    description="1-based ending line number for slicing (inclusive).",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="max_lines",
                    type_name="integer",
                    description="Maximum number of lines to return.",
                    required=False,
                    default=300,
                ),
            ],
            requires_file_access=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path_raw = kwargs.get("file_path")
        if not file_path_raw:
            return ToolResult(
                is_success=False,
                summary="File read failed: Missing file_path parameter",
                error_message="file_path is required",
            )

        start_line = kwargs.get("start_line", 1) or 1
        end_line = kwargs.get("end_line")
        max_lines = kwargs.get("max_lines", 300) or 300

        try:
            # 1. Path containment validation
            validated_path = validate_path_containment(
                file_path_raw,
                allowed_root=self.workspace_root,
                allow_temp=True,
            )

            # 2. File existence & type validation
            if not validated_path.exists():
                return ToolResult(
                    is_success=False,
                    summary=f"File not found: {file_path_raw}",
                    error_message=f"File does not exist: {validated_path}",
                )

            if not validated_path.is_file():
                return ToolResult(
                    is_success=False,
                    summary=f"Path is not a regular file: {file_path_raw}",
                    error_message=f"Expected file, got directory or special file: {validated_path}",
                )

            # 3. File size check
            file_size = validated_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return ToolResult(
                    is_success=False,
                    summary=f"File size exceeds safety limit ({file_size} > {MAX_FILE_SIZE_BYTES} bytes)",
                    error_message=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES} bytes",
                )

            # 4. Read content
            with open(validated_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            
            # Slicing (1-indexed)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line) if end_line else min(total_lines, start_idx + max_lines)
            
            selected_lines = all_lines[start_idx:end_idx]
            
            # Numbered source representation for student clarity
            numbered_content = "".join(
                f"{i + start_idx + 1:4d} | {line}"
                for i, line in enumerate(selected_lines)
            )
            raw_content = "".join(selected_lines)

            return ToolResult(
                is_success=True,
                data={
                    "file_path": str(validated_path),
                    "total_lines": total_lines,
                    "start_line": start_idx + 1,
                    "end_line": end_idx,
                    "line_count": len(selected_lines),
                    "content": raw_content,
                    "numbered_content": numbered_content,
                },
                summary=f"Read lines {start_idx + 1}-{end_idx} of {total_lines} total lines from '{validated_path.name}'",
                evidence_tags=["source_code", "file_inspect"],
            )

        except SafetyViolationError as sve:
            return ToolResult(
                is_success=False,
                summary=f"Security violation: {sve}",
                error_message=str(sve),
            )
        except Exception as ex:
            return ToolResult(
                is_success=False,
                summary=f"Failed to read file: {ex}",
                error_message=str(ex),
            )
