"""Base tool abstraction and schema definitions for TRACE."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Definition of a single parameter accepted by a tool."""
    name: str
    type_name: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Metadata describing a tool's capabilities, inputs, and output schema."""
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    requires_file_access: bool = False
    requires_execution: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert definition to dictionary for LLM tool schema inspection."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                p.name: {
                    "type": p.type_name,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in self.parameters
            },
        }


class ToolResult(BaseModel):
    """Structured output returned after executing a tool."""
    is_success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: str
    error_message: Optional[str] = None
    evidence_tags: List[str] = Field(default_factory=list)


class BaseTool(ABC):
    """Abstract base class for all deterministic debugging tools in TRACE."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool metadata definition."""
        pass

    @property
    def name(self) -> str:
        """Return tool name."""
        return self.definition.name

    def validate_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate passed arguments against the tool schema, applying defaults."""
        validated: Dict[str, Any] = {}
        for param in self.definition.parameters:
            if param.name in arguments:
                validated[param.name] = arguments[param.name]
            elif param.required:
                if param.default is not None:
                    validated[param.name] = param.default
                else:
                    raise ValueError(f"Missing required parameter '{param.name}' for tool '{self.name}'")
            else:
                validated[param.name] = param.default
                
        # Also preserve any extra arguments provided by LLM
        for key, val in arguments.items():
            if key not in validated:
                validated[key] = val
                
        return validated

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments and return a structured ToolResult."""
        pass
