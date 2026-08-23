"""Structured Python Traceback Parser Tool for TRACE."""

import re
from typing import Any, Dict, List, Optional

from trace.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolResult


class TracebackParserTool(BaseTool):
    """Parses and normalizes raw Python traceback strings into structured frames."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="traceback_parser",
            description="Parses standard Python traceback strings into structured frames, exception types, and root error lines.",
            parameters=[
                ToolParameter(
                    name="traceback_text",
                    type_name="string",
                    description="Raw traceback text from Python exception output.",
                    required=True,
                ),
            ],
            requires_file_access=False,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        tb_text = kwargs.get("traceback_text") or ""
        if not tb_text.strip():
            return ToolResult(
                is_success=False,
                summary="Traceback parsing failed: Empty traceback text provided",
                error_message="traceback_text is empty",
            )

        # Regex patterns for Python traceback parsing
        # Example frame line: File "example.py", line 14, in calculate_average
        frame_pattern = re.compile(
            r'File\s+["\'](?P<file>[^"\']+)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\n]+))?'
        )
        
        # Example exception line: ZeroDivisionError: division by zero
        # or CustomError: something happened
        exception_pattern = re.compile(
            r'^(?P<type>[a-zA-Z_][a-zA-Z0-9_\.]*(?:Error|Exception|Warning|Interrupt|Exit)?):\s*(?P<msg>.*)$'
        )

        lines = tb_text.strip().splitlines()
        frames: List[Dict[str, Any]] = []
        exception_type: Optional[str] = None
        exception_msg: str = ""

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            frame_match = frame_pattern.search(line)
            if frame_match:
                file_name = frame_match.group("file")
                line_num = int(frame_match.group("line"))
                func_name = frame_match.group("func") or "<module>"
                
                # Next line usually contains the code snippet
                code_snippet = ""
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('File "'):
                    code_snippet = lines[i + 1].strip()
                    i += 1
                
                frames.append({
                    "file": file_name,
                    "line": line_num,
                    "function": func_name.strip(),
                    "code": code_snippet,
                })
            else:
                # Check for exception line
                exc_match = exception_pattern.match(line)
                if exc_match:
                    exception_type = exc_match.group("type")
                    exception_msg = exc_match.group("msg").strip()
            i += 1

        # Fallback if standard exception pattern didn't match the last line
        if not exception_type and lines:
            last_line = lines[-1].strip()
            if ":" in last_line:
                parts = last_line.split(":", 1)
                if len(parts) == 2 and " " not in parts[0]:
                    exception_type = parts[0].strip()
                    exception_msg = parts[1].strip()
            elif last_line:
                exception_type = "Exception"
                exception_msg = last_line

        primary_frame = frames[-1] if frames else None

        data = {
            "exception_type": exception_type or "UnknownException",
            "exception_message": exception_msg,
            "stack_depth": len(frames),
            "frames": frames,
            "primary_frame": primary_frame,
            "has_frames": len(frames) > 0,
        }

        if primary_frame:
            summary = (
                f"Traceback parsed: {data['exception_type']} ('{data['exception_message']}') "
                f"at {primary_frame['file']}:{primary_frame['line']} in {primary_frame['function']}()"
            )
        else:
            summary = f"Traceback parsed: {data['exception_type']}: {data['exception_message']}"

        return ToolResult(
            is_success=True,
            data=data,
            summary=summary,
            evidence_tags=["traceback", "runtime_error"],
        )
