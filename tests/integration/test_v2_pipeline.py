"""Integration test for the v2 pipeline."""

from unittest.mock import AsyncMock, patch

import pytest

from openclaw.agents.ira.src.core.unified_gateway import (
    GatewayRequest,
    UnifiedGateway,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unified_gateway_executes_full_pipeline():
    """
    Integration test: UnifiedGateway with real skills (or minimal mocks).
    Confirms the gateway can load and execute without mocking every component.
    """
    gateway = UnifiedGateway()

    async def mock_research(msg, ctx):
        return "Mock research output for PF1 specs."

    async def mock_write(msg, ctx):
        assert "research_output" in ctx
        return "Here is the draft based on research: " + str(ctx.get("research_output", ""))[:50]

    async def mock_verify(draft, msg, ctx):
        return draft

    with (
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_research", mock_research),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_write", mock_write),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_verify", mock_verify),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_iris_enrich", AsyncMock(return_value={})),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_identity_resolve", return_value=None),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_reflect", AsyncMock()),
    ):
        req = GatewayRequest(
            message="What are the PF1-C-2015 specifications?",
            channel="api",
            user_id="test-user",
        )
        resp = await gateway.process(req)

    assert resp.response
    assert "Mock research" in resp.response or "draft" in resp.response.lower()
    assert resp.intent in ("specs", "general", "recommendation")
