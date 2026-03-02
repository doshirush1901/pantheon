"""Unit tests for StreamingGateway."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclaw.agents.ira.src.core.streaming import (
    StreamingGateway,
    create_streaming_routes,
    start_time,
    active_streams,
    SIMULATED_CHUNK_SIZE_WORDS,
    SIMULATED_CHUNK_DELAY_SECONDS,
)
from openclaw.agents.ira.src.core.unified_gateway import GatewayRequest


@pytest.fixture
def streaming_gateway():
    return StreamingGateway()


@pytest.mark.asyncio
async def test_stream_yields_progress_events_in_order(streaming_gateway):
    """Test stream() yields progress events in correct order."""
    async def mock_write_streaming(msg, ctx):
        yield "Token1 "
        yield "Token2"

    with (
        patch(
            "openclaw.agents.ira.src.agents.researcher.agent.research",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch(
            "openclaw.agents.ira.src.agents.iris_skill.iris_enrich",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch(
            "openclaw.agents.ira.src.agents.writer.agent.write_streaming",
            new=mock_write_streaming,
        ),
    ):
        req = GatewayRequest(message="Hi", channel="api")
        events = []
        async for event in streaming_gateway.stream(req, "stream-1"):
            events.append(event)
            if event.get("type") == "done":
                break

    stages = [e["stage"] for e in events if e.get("type") == "progress"]
    assert "intent_analysis" in stages
    assert "research" in stages
    assert "writing" in stages
    assert any(e.get("type") == "token" for e in events)
    assert events[-1].get("type") == "done"


@pytest.mark.asyncio
async def test_cancel_stops_generation(streaming_gateway):
    """Test cancel() stops the stream."""
    streaming_gateway._get_or_create_stream("stream-x")
    ok = streaming_gateway.cancel("stream-x")
    assert ok is True
    assert streaming_gateway._streams["stream-x"].cancelled is True


@pytest.mark.asyncio
async def test_steer_adds_command_to_context(streaming_gateway):
    """Test steer() adds command to stream context for pipeline steps."""
    streaming_gateway._get_or_create_stream("stream-2")
    ok = streaming_gateway.steer("stream-2", "make it shorter")
    assert ok is True
    assert streaming_gateway._streams["stream-2"].steering_command == "make it shorter"


def test_create_streaming_routes_health_endpoint():
    """Test create_streaming_routes returns router with health endpoint."""
    router = create_streaming_routes()
    if router is None:
        pytest.skip("FastAPI not installed")
    assert router is not None
    route_paths = [getattr(r, "path", str(r)) for r in router.routes]
    assert any("health" in str(p) for p in route_paths)


def test_simulated_chunk_constants():
    """Test magic numbers are extracted to named constants."""
    assert SIMULATED_CHUNK_SIZE_WORDS == 20
    assert SIMULATED_CHUNK_DELAY_SECONDS == 0.02
