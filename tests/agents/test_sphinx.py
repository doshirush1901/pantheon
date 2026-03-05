"""
Tests for the Sphinx gatekeeper agent.

Covers: clarification detection, question generation, brief merging,
task type detection, and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_openai_response():
    """Factory for mocking OpenAI chat completions."""
    def _make(content: str):
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp
    return _make


class TestSphinxTaskTypeDetection:

    def test_detect_sales_task(self):
        from openclaw.agents.ira.src.agents.sphinx.agent import detect_task_type
        assert detect_task_type("I need a thermoforming machine for ABS") == "sales"

    def test_detect_email_task(self):
        from openclaw.agents.ira.src.agents.sphinx.agent import detect_task_type
        assert detect_task_type("Draft an email to the prospect") == "email"

    def test_detect_finance_task(self):
        from openclaw.agents.ira.src.agents.sphinx.agent import detect_task_type
        assert detect_task_type("What's our cashflow forecast?") == "finance"

    def test_detect_general_task(self):
        from openclaw.agents.ira.src.agents.sphinx.agent import detect_task_type
        result = detect_task_type("Tell me something interesting")
        assert result in ("general", "research")


class TestSphinxShouldClarify:

    @pytest.mark.asyncio
    async def test_vague_message_needs_clarification(self, mock_openai_response):
        from openclaw.agents.ira.src.agents.sphinx.agent import should_clarify

        mock_client = MagicMock()
        resp = mock_openai_response(json.dumps({"needs_clarification": True, "task_type": "sales"}))
        mock_client.chat.completions.create.return_value = resp

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = await should_clarify("Research that German company", "")

        assert result is True

    @pytest.mark.asyncio
    async def test_specific_message_no_clarification(self, mock_openai_response):
        from openclaw.agents.ira.src.agents.sphinx.agent import should_clarify

        mock_client = MagicMock()
        resp = mock_openai_response(json.dumps({"needs_clarification": False, "task_type": "sales"}))
        mock_client.chat.completions.create.return_value = resp

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = await should_clarify(
                "What is the price of PF1-C-2015 for 3mm ABS sheets?", ""
            )

        assert result is False


class TestSphinxGenerateQuestions:

    @pytest.mark.asyncio
    async def test_generates_questions_for_sales(self, mock_openai_response):
        from openclaw.agents.ira.src.agents.sphinx.agent import generate_questions

        questions = ["What material?", "What thickness?", "What application?"]
        mock_client = MagicMock()
        resp = mock_openai_response(json.dumps(questions))
        mock_client.chat.completions.create.return_value = resp

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = await generate_questions("I need a machine", "sales")

        assert isinstance(result, list)
        assert len(result) > 0


class TestSphinxMergeBrief:

    def test_merge_brief_combines_original_and_answers(self, mock_openai_response):
        from openclaw.agents.ira.src.agents.sphinx.agent import merge_brief

        mock_client = MagicMock()
        resp = mock_openai_response("TASK: Machine recommendation\nMATERIAL: ABS\nTHICKNESS: 3mm")
        mock_client.chat.completions.create.return_value = resp

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = merge_brief(
                original_message="I need a machine",
                questions=["What material?", "What thickness?"],
                answers="1. ABS\n2. 3mm",
            )

        assert isinstance(result, str)
        assert len(result) > 0


class TestSphinxErrorHandling:

    @pytest.mark.asyncio
    async def test_should_clarify_handles_llm_failure(self):
        from openclaw.agents.ira.src.agents.sphinx.agent import should_clarify

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("LLM down")

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = await should_clarify("test message", "")

        assert result is False

    @pytest.mark.asyncio
    async def test_generate_questions_handles_bad_json(self, mock_openai_response):
        from openclaw.agents.ira.src.agents.sphinx.agent import generate_questions

        mock_client = MagicMock()
        resp = mock_openai_response("not valid json at all")
        mock_client.chat.completions.create.return_value = resp

        with patch("openclaw.agents.ira.src.agents.sphinx.agent._get_client", return_value=mock_client):
            result = await generate_questions("test", "general")

        assert result == []
