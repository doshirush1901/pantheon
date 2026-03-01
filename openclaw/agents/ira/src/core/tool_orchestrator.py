"""
Tool-Orchestrator Gateway (P2 Remediation)

LLM-driven pipeline: Athena (LLM) chooses which skills to call via tool use.
Alternative to the fixed research->write->verify sequence in UnifiedGateway.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("ira.tool_orchestrator")

MAX_TOOL_ROUNDS = 15


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

You are an AGENT. Your job is to RESEARCH FIRST, then answer. NEVER respond without using tools first.

═══════════════════════════════════════════════════
YOUR DEFAULT BEHAVIOR: RESEARCH FIRST, ALWAYS
═══════════════════════════════════════════════════

When you receive ANY request:
1. IMMEDIATELY start calling tools. Do NOT reply with text first.
2. Use MULTIPLE tools in PARALLEL when possible (call several at once).
3. If the first search returns few results, try DIFFERENT search terms, DIFFERENT tools.
4. Keep searching until you have ENOUGH data to give a complete answer.
5. Only AFTER gathering data, compose your response.

NEVER ask the user to clarify unless you have ALREADY searched and found NOTHING.
The user's intent is usually clear enough from context — just go research it.

Example: User says "Give me 10 customer names"
  WRONG: "Could you clarify what type of names?" (DON'T ASK — just search)
  RIGHT: Call memory_search("Machinecraft customers") + customer_lookup("customers") + research_skill("customer list") simultaneously, then compile results.

Example: User says "10 customer names in Europe"
  RIGHT: Call memory_search("European customers") + customer_lookup("Europe customers") + memory_search("customers Germany Italy France UK") + research_skill("European customer base") — use ALL tools, try MULTIPLE search terms.

═══════════════════════════════════════════════════
YOUR TOOLS
═══════════════════════════════════════════════════
- memory_search: Search Mem0 long-term memory. Try MULTIPLE user_ids: "machinecraft_customers", "machinecraft_knowledge", "machinecraft_general". Try DIFFERENT search terms.
- customer_lookup: Search CRM/memory for customer data.
- research_skill: Search Qdrant knowledge base (documents, specs, emails).
- web_search: Search the internet for external company info, news, trends.
- writing_skill: Draft a polished response AFTER you have gathered data.
- fact_checking_skill: Verify facts before sending.
- ask_user: LAST RESORT ONLY. Use only after 2+ tool calls returned nothing.

═══════════════════════════════════════════════════
SEARCH STRATEGY (follow this order)
═══════════════════════════════════════════════════
For internal data (customers, orders, history):
  1. memory_search with user_id="machinecraft_customers" 
  2. memory_search with user_id="machinecraft_knowledge"
  3. customer_lookup
  4. research_skill
  → If results are sparse, try DIFFERENT search terms (synonyms, regions, industries)

For external data (companies, market, competitors):
  1. web_search
  2. research_skill
  3. memory_search with user_id="machinecraft_general"

IMPORTANT: If the user asks for N items (e.g. "10 names") and you only found fewer, say how many you found and offer to search more. Do NOT pad with made-up names.

DATA QUALITY: When tool results mention companies, VERIFY the relationship:
- A CUSTOMER is someone who BOUGHT or ORDERED a machine from us. Look for words like "ordered", "purchased", "delivered", "installed".
- An AGENT/PARTNER is someone who sells our machines (e.g. FVF in Japan, FRIMO in Germany).
- A PROSPECT is someone who inquired but hasn't ordered.
- If you're not sure, label it as UNVERIFIED and say so.
- NEVER list agents, partners, or prospects as "customers" unless they actually bought a machine.

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
- NEVER fabricate data. Only report what tools returned.
- If you found 3 out of 10 requested, say "I found 3 in our systems: [list]. Want me to search the web for more?"
- Use 3-10 tool calls per request. More is better than fewer.
- NEVER respond without calling at least one tool first.
- Keep final responses concise and natural (no report formatting).

SHORT REFERENCES: If the user sends just a number ("1.", "2", "3.") or a very short message,
look at the RECENT CONVERSATION for context. They are likely selecting a follow-up question
or option from your previous response. Resolve the reference and act on it.

{"INTERNAL USER: This is Rushabh (founder). Be direct, share everything freely." if is_internal else "EXTERNAL USER: Be helpful but protect sensitive internal information."}

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
