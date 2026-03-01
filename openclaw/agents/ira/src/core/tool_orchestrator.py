"""
Tool-Orchestrator Gateway (P2 Remediation)

LLM-driven pipeline: Athena (LLM) chooses which skills to call via tool use.
Alternative to the fixed research->write->verify sequence in UnifiedGateway.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("ira.tool_orchestrator")

MAX_TOOL_ROUNDS = 10


async def process_with_tools(
    message: str,
    channel: str = "api",
    user_id: str = "unknown",
    context: Dict[str, Any] = None,
) -> str:
    """
    Agentic pipeline: Athena (LLM) decides which tools to call, in what order,
    and how many rounds to take. She can research, search the web, look up
    customers, query memory, draft responses, and verify facts -- all autonomously.
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

    conversation_history = context.get("conversation_history", "")
    is_internal = context.get("is_internal", False)
    mem0_context = context.get("mem0_context", "")

    system = f"""You are Athena, the Chief of Staff for Ira (Intelligent Revenue Assistant) at Machinecraft Technologies.

You are an AGENT, not a chatbot. You have tools and you MUST use them to find real data before answering.

YOUR TOOLS:
- research_skill: Search internal knowledge base (Qdrant, machine DB, documents)
- web_search: Search the internet for company info, news, industry trends
- customer_lookup: Look up customers in CRM/memory
- memory_search: Search Ira's long-term memory (Mem0) for stored facts, orders, preferences
- writing_skill: Draft a polished response (use AFTER gathering data)
- fact_checking_skill: Verify facts before sending (use on every draft)
- ask_user: Ask the user a clarifying question when you need more info

CRITICAL RULES:
1. ALWAYS use tools to find real data. NEVER fabricate company names, order data, or contacts.
2. If you can't find data, say so honestly. Don't make up plausible-sounding answers.
3. For complex tasks, use MULTIPLE tool calls in sequence. Take as many rounds as needed.
4. When asked about customers/orders, search memory_search first, then customer_lookup.
5. When asked about external companies, use web_search.
6. Always fact-check before finalizing.
7. If the user's request is unclear, use ask_user to clarify.

{"INTERNAL USER: This is a Machinecraft team member. Be direct, share internal data freely." if is_internal else "EXTERNAL USER: Be helpful but protect sensitive internal information."}

{f"CONVERSATION CONTEXT:{chr(10)}{conversation_history}" if conversation_history else ""}
{f"MEMORY CONTEXT:{chr(10)}{mem0_context}" if mem0_context else ""}

Think step by step. Use tools. Take your time. Get it right."""

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    tools = get_ira_tools_schema()

    client = openai.OpenAI(api_key=api_key)
    for round_num in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=2048,
            temperature=0.3,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            final = (msg.content or "").strip()
            if final.startswith("ASK_USER:"):
                return final[9:]
            return final

        messages.append(msg)
        for tc in msg.tool_calls or []:
            fn = tc.function
            name = fn.name
            args = parse_tool_arguments(fn.arguments)
            logger.info(f"[Athena] Round {round_num+1}: calling {name}({list(args.keys())})")
            result = await execute_tool_call(name, args, context)
            if result.startswith("ASK_USER:"):
                return result[9:]
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result[:8000],
            })

    return "I've been working on this but need more time. Let me summarize what I found so far and continue later."
