"""
IRA Skills as OpenAI-Compatible Tools (P2 Remediation)

Exposes research_skill, writing_skill, fact_checking_skill as function-calling tools.
Enables LLM-driven orchestration: Athena (LLM) chooses which skills to call and in what order.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ira.tools.skills")

IRA_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "research_skill",
            "description": "Research the user's question. Search knowledge base, product specs, and memory. Use when you need to find information before answering.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The question or topic to research"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "writing_skill",
            "description": "Draft a response based on research. Use after research_skill when you have context. Handles emails, quotes, and general responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The original user query"},
                    "research_summary": {"type": "string", "description": "Research findings to base the draft on"},
                },
                "required": ["query", "research_summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fact_checking_skill",
            "description": "Verify a draft for accuracy, AM series thickness rules, and pricing disclaimers. Use before sending any response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft": {"type": "string", "description": "The draft response to verify"},
                    "original_query": {"type": "string", "description": "The original user question"},
                },
                "required": ["draft", "original_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "orchestrate_full_pipeline",
            "description": "Run the full pipeline: research -> write -> verify. Use for complex queries that need the complete workflow.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The user's question"}},
                "required": ["query"],
            },
        },
    },
]


def get_ira_tools_schema() -> List[Dict[str, Any]]:
    """Return OpenAI-compatible tools list for chat.completions.create(tools=...)."""
    return IRA_TOOLS_SCHEMA


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    """Execute an IRA skill by name. Called when LLM returns tool_calls."""
    try:
        from openclaw.agents.ira.src.skills.invocation import (
            invoke_research,
            invoke_verify,
            invoke_write,
        )
    except ImportError:
        return "Error: Skill invocation unavailable."

    if tool_name == "research_skill":
        query = arguments.get("query", "")
        result = await invoke_research(query, context)
        return result or "(No results found)"

    elif tool_name == "writing_skill":
        query = arguments.get("query", "")
        research_summary = arguments.get("research_summary", "")
        context = dict(context)
        context["research_output"] = research_summary
        result = await invoke_write(query, context)
        return result or "(Draft empty)"

    elif tool_name == "fact_checking_skill":
        draft = arguments.get("draft", "")
        original_query = arguments.get("original_query", "")
        result = await invoke_verify(draft, original_query, context)
        return result or draft

    elif tool_name == "orchestrate_full_pipeline":
        query = arguments.get("query", "")
        ctx = dict(context)
        research_output = await invoke_research(query, ctx)
        ctx["research_output"] = research_output
        draft = await invoke_write(query, ctx)
        verified = await invoke_verify(draft, query, ctx)
        return verified or draft

    return f"Error: Unknown tool '{tool_name}'"


def parse_tool_arguments(arguments: str) -> Dict[str, Any]:
    """Parse tool arguments from LLM response (JSON string)."""
    if not arguments or not arguments.strip():
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse tool arguments: %s", e)
        return {}
