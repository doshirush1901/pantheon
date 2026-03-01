"""Unit tests for UnifiedGateway."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclaw.agents.ira.src.core.unified_gateway import (
    GatewayRequest,
    GatewayResponse,
    UnifiedGateway,
)


@pytest.fixture
def gateway():
    return UnifiedGateway()


@pytest.mark.asyncio
async def test_process_pipeline_order(gateway):
    """Test pipeline executes in correct order: intent -> research -> iris -> write -> verify."""
    call_order = []

    async def mock_research(msg, ctx):
        call_order.append("research")
        return "researched"

    async def mock_write(msg, ctx):
        call_order.append("write")
        assert "research_output" in ctx
        assert "iris_context" in ctx
        return "draft"

    async def mock_verify(draft, msg, ctx):
        call_order.append("verify")
        return draft

    with (
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_research", mock_research),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_write", mock_write),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_verify", mock_verify),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_iris_enrich", AsyncMock(return_value={})),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_identity_resolve", return_value=None),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_reflect", AsyncMock()),
    ):
        req = GatewayRequest(message="What is the PF1 price?", channel="api")
        resp = await gateway.process(req)

    assert resp.response == "draft"
    assert call_order == ["research", "write", "verify"]


@pytest.mark.asyncio
async def test_process_telegram_formats_and_calls_process(gateway):
    """Test process_telegram formats GatewayRequest and returns response."""
    with patch.object(gateway, "process", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = GatewayResponse(response="Hi from Telegram", intent="general")
        resp = await gateway.process_telegram("Hello", user_id="tg-123")

    mock_process.assert_called_once()
    req = mock_process.call_args[0][0]
    assert req.message == "Hello"
    assert req.channel == "telegram"
    assert req.user_id == "tg-123"
    assert resp.response == "Hi from Telegram"


@pytest.mark.asyncio
async def test_process_email_formats_and_calls_process(gateway):
    """Test process_email formats GatewayRequest and returns response."""
    with patch.object(gateway, "process", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = GatewayResponse(response="Email draft", intent="email")
        resp = await gateway.process_email("Draft follow-up to Acme Corp", user_id="user-1")

    mock_process.assert_called_once()
    req = mock_process.call_args[0][0]
    assert req.channel == "email"
    assert resp.intent == "email"


@pytest.mark.asyncio
async def test_graceful_degradation_when_write_unavailable(gateway):
    """Test graceful degradation when write skill fails to load."""
    with (
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_research", AsyncMock(return_value="")),
        patch(
            "openclaw.agents.ira.src.core.unified_gateway.invoke_write",
            side_effect=RuntimeError("Write skill unavailable"),
        ),
        patch("openclaw.agents.ira.src.core.unified_gateway.invoke_iris_enrich", AsyncMock(return_value={})),
    ):
        req = GatewayRequest(message="Hello")
        resp = await gateway.process(req)

    assert "unavailable" in resp.response.lower()


@pytest.mark.asyncio
async def test_health_reports_skill_status(gateway):
    """Test health() returns status of each lazy-loaded skill."""
    result = await gateway.health()

    assert "status" in result
    assert result["status"] == "ok"
    assert "skills" in result
    assert "research" in result["skills"]
    assert "write" in result["skills"]
    assert "verify" in result["skills"]
    assert "iris_enrich" in result["skills"]
    assert result["skills"]["research"] in ("available", "unavailable")
