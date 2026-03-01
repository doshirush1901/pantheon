"""
Streaming Gateway - Server-Sent Events for the Ira pipeline.

Provides real-time progress and token streaming with cancel/steer support.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("ira.streaming")

# Named constants for simulated streaming (Task 9 - replace with true LLM streaming)
SIMULATED_CHUNK_SIZE_WORDS = 20
SIMULATED_CHUNK_DELAY_SECONDS = 0.02

# Module-level for health check (Task 7)
start_time = time.time()
active_streams: Dict[str, Dict[str, Any]] = {}


@dataclass
class StreamState:
    """State for an active stream."""

    stream_id: str
    cancelled: bool = False
    steering_command: Optional[str] = None
    created_at: float = field(default_factory=time.time)


def _chunk_text(text: str, chunk_size: int = SIMULATED_CHUNK_SIZE_WORDS) -> list[str]:
    """Split text into word chunks (simulated streaming until true LLM stream)."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i : i + chunk_size]))
    return chunks


class StreamingGateway:
    """
    Gateway that yields SSE progress events and token chunks.
    Supports cancellation and mid-stream steering.
    """

    def __init__(self) -> None:
        self._gateway: Optional[Any] = None
        self._streams: Dict[str, StreamState] = {}

    def _get_gateway(self) -> Any:
        if self._gateway is None:
            from openclaw.agents.ira.src.core.unified_gateway import UnifiedGateway
            self._gateway = UnifiedGateway()
        return self._gateway

    def _get_or_create_stream(self, stream_id: str) -> StreamState:
        if stream_id not in self._streams:
            self._streams[stream_id] = StreamState(stream_id=stream_id)
            active_streams[stream_id] = {"created": time.time()}
        return self._streams[stream_id]

    def cancel(self, stream_id: str) -> bool:
        """Mark a stream as cancelled."""
        if stream_id in self._streams:
            self._streams[stream_id].cancelled = True
            return True
        return False

    def steer(self, stream_id: str, command: str) -> bool:
        """Add a steering command for the next pipeline steps."""
        if stream_id in self._streams:
            self._streams[stream_id].steering_command = command
            return True
        return False

    async def stream(
        self,
        request: Any,
        stream_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yield progress events then token events.
        Respects cancellation and applies steering to context.
        """
        stream_state = self._get_or_create_stream(stream_id)
        gateway = self._get_gateway()

        # Bind trace context for observability (correlates Athena→Clio→Vera logs)
        try:
            from openclaw.agents.ira.core.ira_logging import start_trace
            user_id = getattr(request, "user_id", "unknown")
            channel = getattr(request, "channel", "api")
            start_trace(channel=channel, user_id=user_id)
        except ImportError:
            pass

        # Build context from request
        from openclaw.agents.ira.src.core.unified_gateway import GatewayRequest
        if not isinstance(request, GatewayRequest):
            req = GatewayRequest(
                message=getattr(request, "message", str(request)),
                channel=getattr(request, "channel", "api"),
                user_id=getattr(request, "user_id", "unknown"),
            )
        else:
            req = request

        context: Dict[str, Any] = {
            "message": req.message,
            "channel": req.channel,
            "user_id": req.user_id,
            "intent": "general",
            "research_output": "",
            "iris_context": {},
            "steering": stream_state.steering_command,
        }

        # Progress: intent
        if stream_state.cancelled:
            yield {"type": "cancelled"}
            return
        yield {"type": "progress", "stage": "intent_analysis"}

        from openclaw.agents.ira.src.agents.chief_of_staff.agent import analyze_intent
        context["intent"] = analyze_intent(req.message)

        # Progress: research
        if stream_state.cancelled:
            yield {"type": "cancelled"}
            return
        yield {"type": "progress", "stage": "research"}

        from openclaw.agents.ira.src.skills.invocation import (
            invoke_iris_enrich,
            invoke_research,
            invoke_write_streaming,
        )

        try:
            context["research_output"] = await invoke_research(req.message, context)
        except Exception as e:
            logger.warning(f"Research failed: {e}")
            context["research_output"] = ""

        # Progress: iris
        if stream_state.cancelled:
            yield {"type": "cancelled"}
            return
        yield {"type": "progress", "stage": "iris"}

        try:
            context["iris_context"] = await invoke_iris_enrich(context)
        except Exception:
            context["iris_context"] = {}

        # Progress: writing
        if stream_state.cancelled:
            yield {"type": "cancelled"}
            return
        yield {"type": "progress", "stage": "writing"}

        # Apply steering to context for writer
        if stream_state.steering_command:
            context["steering"] = stream_state.steering_command

        # True LLM streaming via shared invocation
        try:
            async for token in invoke_write_streaming(req.message, context):
                if stream_state.cancelled:
                    yield {"type": "cancelled"}
                    return
                if token:
                    yield {"type": "token", "text": token}
        except Exception as e:
            logger.warning(f"Write streaming failed: {e}")
            yield {"type": "token", "text": "Error generating response."}

        yield {"type": "done"}

        # Cleanup
        if stream_id in self._streams:
            del self._streams[stream_id]
        if stream_id in active_streams:
            del active_streams[stream_id]


def create_streaming_routes() -> Any:
    """Create FastAPI router for streaming endpoints."""
    try:
        from fastapi import APIRouter
        from fastapi.responses import StreamingResponse
    except ImportError:
        return None

    router = APIRouter()
    gateway = StreamingGateway()

    @router.get("/api/v1/stream/health")
    async def get_health() -> Dict[str, Any]:
        """Health check for the streaming service (Task 7)."""
        return {
            "status": "ok",
            "active_streams": len(active_streams),
            "uptime_seconds": time.time() - start_time,
        }

    @router.post("/api/v1/stream/{stream_id}/cancel")
    async def cancel_stream(stream_id: str) -> Dict[str, Any]:
        """Cancel an active stream."""
        ok = gateway.cancel(stream_id)
        return {"cancelled": ok, "stream_id": stream_id}

    @router.post("/api/v1/stream/{stream_id}/steer")
    async def steer_stream(stream_id: str, body: Dict[str, str]) -> Dict[str, Any]:
        """Add steering command to stream context."""
        command = body.get("command", body.get("text", ""))
        ok = gateway.steer(stream_id, command)
        return {"steered": ok, "stream_id": stream_id}

    return router
