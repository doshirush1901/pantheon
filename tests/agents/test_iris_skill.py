"""Unit tests for iris_enrich skill."""

from unittest.mock import AsyncMock, patch

import pytest

from openclaw.agents.ira.src.agents.iris_skill import iris_enrich


@pytest.mark.asyncio
async def test_iris_enrich_returns_email_vars():
    """Test iris_enrich returns dict of email-ready variables."""
    mock_vars = {
        "news_hook": "Company announced expansion",
        "industry_hook": "EV boom drives demand",
        "timely_opener": "Congrats on the news!",
    }

    with patch(
        "agents.iris.agent.enrich_lead_for_email_async",
        new_callable=AsyncMock,
        return_value=mock_vars,
    ) as mock_enrich:
        result = await iris_enrich({
            "company": "Acme Corp",
            "lead_id": "lead-1",
            "country": "Germany",
            "industries": ["automotive"],
        })

    assert result == mock_vars
    mock_enrich.assert_called_once()
    call_kw = mock_enrich.call_args[1]
    assert call_kw["company"] == "Acme Corp"
    assert call_kw["country"] == "Germany"
    assert "automotive" in call_kw["industries"]


@pytest.mark.asyncio
async def test_iris_enrich_empty_when_no_company():
    """Test iris_enrich returns empty dict when company missing."""
    result = await iris_enrich({"lead_id": "x"})
    assert result == {}


@pytest.mark.asyncio
async def test_iris_enrich_handles_enrich_failure():
    """Test iris_enrich returns empty dict when Iris enrich call fails."""
    with patch(
        "agents.iris.agent.enrich_lead_for_email_async",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Iris API unavailable"),
    ):
        result = await iris_enrich({"company": "TestCo"})
    assert result == {}
