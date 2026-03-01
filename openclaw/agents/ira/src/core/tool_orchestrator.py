"""
Tool-Orchestrator Gateway (P2 Remediation)

LLM-driven pipeline: Athena (LLM) chooses which skills to call via tool use.
Alternative to the fixed research->write->verify sequence in UnifiedGateway.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("ira.tool_orchestrator")

# Max tool rounds to prevent infinite loops
MAX_TOOL_ROUNDS = 5


async def process_with_tools(
    message: str,
    channel: str = "api",
    user_id: str = "unknown",
    context: Dict[str, Any] = None,
) -> str:
    """
    Process a message using LLM + tool calls. The LLM decides when to call
    research_skill, writing_skill, fact_checking_skill, or orchestrate_full_pipeline.
    """
    import openai
    import os

    from openclaw.agents.ira.src.tools.ira_skills_tools import (
        execute_tool_call,
        get_ira_tools_schema,
        parse_tool_arguments,
    )

    api_key = os.environ.get("OPENAI_API_KEY") or getattr(
        __import__("openclaw.agents.ira.config", fromlist=["OPENAI_API_KEY"]),
        "OPENAI_API_KEY",
        "",
    )
    if not api_key:
        return "Error: OPENAI_API_KEY not set."

    context = context or {}
    context.setdefault("channel", channel)
    context.setdefault("user_id", user_id)

    system = """You are Athena, IRA's orchestrator. You have access to tools (skills):
- research_skill: Find information before answering
- writing_skill: Draft a response (needs research_summary)
- fact_checking_skill: Verify a draft before sending
- orchestrate_full_pipeline: Run research->write->verify for complex queries

Use tools to answer the user. For simple factual questions, you may research then respond.
For complex queries, use orchestrate_full_pipeline. Always verify before finalizing.
Respond with your final answer when done."""

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    tools = get_ira_tools_schema()

    client = openai.OpenAI(api_key=api_key)
    for round_num in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=1024,
            temperature=0.3,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            return (msg.content or "").strip()

        for tc in msg.tool_calls or []:
            fn = tc.function
            name = fn.name
            args = parse_tool_arguments(fn.arguments)
            result = await execute_tool_call(name, args, context)
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result[:8000],
            })

    return "Reached max tool rounds. Please try again."
