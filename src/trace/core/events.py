"""Structured event system for TRACE agent observability and telemetry."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events emitted during an investigation session."""
    SESSION_STARTED = "SESSION_STARTED"
    STATE_TRANSITION = "STATE_TRANSITION"
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_REVISED = "PLAN_REVISED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    OBSERVATION_RECORDED = "OBSERVATION_RECORDED"
    EVIDENCE_EXTRACTED = "EVIDENCE_EXTRACTED"
    HYPOTHESIS_PROPOSED = "HYPOTHESIS_PROPOSED"
    HYPOTHESIS_UPDATED = "HYPOTHESIS_UPDATED"
    COUNTERCHECK_COMPLETED = "COUNTERCHECK_COMPLETED"
    DIAGNOSIS_FORMED = "DIAGNOSIS_FORMED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    SESSION_BLOCKED = "SESSION_BLOCKED"
    SESSION_FAILED = "SESSION_FAILED"


class TraceEvent(BaseModel):
    """Structured event record."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    session_id: str
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class EventBus:
    """Synchronous in-process event dispatcher for session observers and CLI renderers."""
    
    def __init__(self):
        self._listeners: List[Callable[[TraceEvent], None]] = []
        self._events: List[TraceEvent] = []

    def subscribe(self, listener: Callable[[TraceEvent], None]) -> None:
        """Add an event listener."""
        self._listeners.append(listener)

    def publish(self, event: TraceEvent) -> None:
        """Record and broadcast an event."""
        self._events.append(event)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass

    def get_events(self, session_id: Optional[str] = None) -> List[TraceEvent]:
        """Get all recorded events, optionally filtered by session_id."""
        if session_id:
            return [e for e in self._events if e.session_id == session_id]
        return list(self._events)

    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()


# Default global event bus instance
global_event_bus = EventBus()
