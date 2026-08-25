"""Asynchronous pub/sub event broadcaster for Server-Sent Events (SSE)."""

import asyncio
from collections import defaultdict
import json
from typing import Any, AsyncGenerator, Dict, Set
from trace.core.events import TraceEvent, global_event_bus


class EventBroadcaster:
    """
    Manages in-memory async queues for real-time SSE streaming to web clients.
    Subscribes to TRACE's global_event_bus and broadcasts events to connected session clients.
    """

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        # Register listener with global_event_bus
        global_event_bus.subscribe(self._handle_trace_event)

    def _handle_trace_event(self, event: TraceEvent) -> None:
        """Callback receiving events from global_event_bus."""
        session_id = event.session_id
        if session_id in self._subscribers and self._subscribers[session_id]:
            event_payload = {
                "event_id": event.event_id,
                "session_id": event.session_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "payload": event.payload,
                "message": event.message,
            }
            for queue in list(self._subscribers[session_id]):
                try:
                    queue.put_nowait(event_payload)
                except Exception:
                    pass

    async def broadcast_event(self, session_id: str, event_type: str, payload: Dict[str, Any], message: str = "") -> None:
        """Manually broadcast an event to subscribers of a session."""
        if session_id in self._subscribers:
            event_data = {
                "event_type": event_type,
                "session_id": session_id,
                "payload": payload,
                "message": message,
            }
            for queue in list(self._subscribers[session_id]):
                try:
                    await queue.put(event_data)
                except Exception:
                    pass

    async def subscribe(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe an async generator queue to a specific session's event stream.
        Yields event dictionaries until client disconnects or session completes.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[session_id].add(queue)

        try:
            while True:
                # Wait for next event or timeout check
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event_data
                    if event_data.get("event_type") in ("SESSION_COMPLETED", "SESSION_FAILED", "SESSION_BLOCKED"):
                        # Drain remaining and finish
                        break
                except asyncio.TimeoutError:
                    # Send periodic keep-alive ping comment
                    yield {"event_type": "PING", "session_id": session_id, "payload": {}}
        finally:
            if session_id in self._subscribers:
                self._subscribers[session_id].discard(queue)
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]


# Singleton broadcaster
global_broadcaster = EventBroadcaster()
