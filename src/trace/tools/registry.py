"""Tool registry and execution controller for TRACE."""

import time
from typing import Any, Dict, List, Optional

from trace.core.events import EventType, TraceEvent, global_event_bus
from trace.core.models import Observation
from trace.core.state import AgentState
from trace.tools.base import BaseTool, ToolDefinition, ToolResult


class ToolNotFoundError(Exception):
    """Raised when an unregistered tool is requested."""
    pass


class ToolRegistry:
    """Central registry for discovering and safely executing TRACE tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name."""
        if name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{name}' is not registered. Available tools: {list(self._tools.keys())}"
            )
        return self._tools[name]

    def list_tools(self) -> List[ToolDefinition]:
        """Return definitions for all registered tools."""
        return [tool.definition for tool in self._tools.values()]

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        state: Optional[AgentState] = None,
    ) -> Observation:
        """
        Validate, execute the requested tool, measure execution time,
        generate an Observation, and log the execution event.
        """
        tool = self.get(tool_name)
        session_id = state.session_id if state else "no_session"

        # Emit tool started event
        global_event_bus.publish(
            TraceEvent(
                session_id=session_id,
                event_type=EventType.TOOL_STARTED,
                payload={"tool_name": tool_name, "arguments": arguments},
                message=f"Invoking tool '{tool_name}'",
            )
        )

        start_time = time.perf_counter()
        error_msg: Optional[str] = None
        tool_result: ToolResult

        try:
            validated_args = tool.validate_arguments(arguments)
            tool_result = tool.execute(**validated_args)
        except Exception as ex:
            error_msg = str(ex)
            tool_result = ToolResult(
                is_success=False,
                summary=f"Tool '{tool_name}' threw exception: {ex}",
                error_message=error_msg,
                evidence_tags=["tool_error"],
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Create observation
        observation = Observation(
            tool_name=tool_name,
            input_args=arguments,
            output_data=tool_result.data,
            is_success=tool_result.is_success,
            summary=tool_result.summary,
            evidence_tags=tool_result.evidence_tags,
            error_message=tool_result.error_message or error_msg,
        )

        # Record in agent state if provided
        if state:
            state.record_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                success=tool_result.is_success,
                execution_time_ms=round(duration_ms, 2),
                observation_id=observation.id,
                error=observation.error_message,
            )
            state.add_observation(observation)

        # Emit tool completed event
        global_event_bus.publish(
            TraceEvent(
                session_id=session_id,
                event_type=EventType.TOOL_COMPLETED,
                payload={
                    "tool_name": tool_name,
                    "observation_id": observation.id,
                    "is_success": observation.is_success,
                    "duration_ms": round(duration_ms, 2),
                },
                message=f"Tool '{tool_name}' finished in {duration_ms:.1f}ms: {observation.summary}",
            )
        )

        # Emit observation recorded event
        global_event_bus.publish(
            TraceEvent(
                session_id=session_id,
                event_type=EventType.OBSERVATION_RECORDED,
                payload={"observation": observation.model_dump()},
                message=f"Observation [{observation.id}]: {observation.summary}",
            )
        )

        return observation


def create_default_registry(workspace_root: Optional[str] = None) -> ToolRegistry:
    """Instantiate and register standard deterministic tools for TRACE v0.1."""
    from trace.tools.ast_analyzer import ASTAnalyzerTool
    from trace.tools.executor import PythonExecutorTool
    from trace.tools.file_reader import FileReaderTool
    from trace.tools.traceback_parser import TracebackParserTool

    registry = ToolRegistry()
    registry.register(FileReaderTool(workspace_root=workspace_root))
    registry.register(ASTAnalyzerTool())
    registry.register(TracebackParserTool())
    registry.register(PythonExecutorTool(workspace_root=workspace_root))
    return registry
