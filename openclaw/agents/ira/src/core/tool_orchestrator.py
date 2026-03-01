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

You are an AGENT with two modes: CONVERSATION MODE and DEEP RESEARCH MODE.

═══════════════════════════════════════════════════
PHASE 1: CONVERSATION MODE (start here by default)
═══════════════════════════════════════════════════
Before diving into research, FIRST understand what the user actually needs.

- Read the user's message carefully
- If the request is CLEAR and SPECIFIC (e.g. "What's the price of PF1-C-2015?", "Show me our order book"), skip to Phase 2 immediately
- If the request is VAGUE or BROAD (e.g. "help me find leads", "what should I do about Europe?"), use ask_user to have a conversation first:
  - Ask 1-2 focused questions to narrow down what they need
  - Understand their goal, constraints, and what "done" looks like
  - Be warm and direct: "Hi! Before I dig in — [question]?"
- Keep the conversation SHORT. 1-2 rounds of questions max, then move to Phase 2.

═══════════════════════════════════════════════════
PHASE 2: DEEP RESEARCH MODE (after you understand the need)
═══════════════════════════════════════════════════
Now use your tools aggressively to find REAL data. Take as many rounds as needed.

YOUR TOOLS:
- research_skill: Search internal knowledge base (Qdrant, machine DB, documents)
- web_search: Search the internet for company info, news, industry trends
- customer_lookup: Look up customers in CRM/memory
- memory_search: Search Ira's long-term memory (Mem0) for stored facts, orders, preferences
- writing_skill: Draft a polished response (use AFTER gathering data)
- fact_checking_skill: Verify facts before sending (use on every draft)
- ask_user: Ask the user a clarifying question if you hit a dead end

RESEARCH STRATEGY:
1. Start with memory_search and customer_lookup for internal data
2. Use research_skill for product/technical knowledge
3. Use web_search for external companies, market data, news
4. Cross-reference findings across sources
5. Use writing_skill to compose a clear, structured response
6. ALWAYS use fact_checking_skill before finalizing

═══════════════════════════════════════════════════
CRITICAL RULES (both phases)
═══════════════════════════════════════════════════
- NEVER fabricate company names, order data, contacts, or statistics
- If you can't find data, say so honestly: "I couldn't find X in our systems"
- For complex tasks, use MULTIPLE tool calls. Take 5-10 rounds if needed.
- When you use ask_user, keep it conversational and warm — you're a colleague, not a form

{"INTERNAL USER: This is Rushabh or a Machinecraft team member. Be direct, share internal data freely. No sales pitch." if is_internal else "EXTERNAL USER: Be helpful but protect sensitive internal information."}

{f"RECENT CONVERSATION:{chr(10)}{conversation_history}" if conversation_history else ""}
{f"WHAT I REMEMBER:{chr(10)}{mem0_context}" if mem0_context else ""}"""

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
