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
            "description": "Search Machinecraft's knowledge base (Qdrant, Mem0, Neo4j, machine database). Use for product specs, customer history, order data, pricing, and any internal knowledge.",
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
            "name": "web_search",
            "description": "Search the web for external information. Use for company research, industry news, competitor analysis, market trends, or any information not in our internal knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "company": {"type": "string", "description": "Company name if researching a specific company"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "customer_lookup",
            "description": "Look up a customer or company in our CRM/memory. Returns relationship history, past orders, communication history, and preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Customer name, company name, or email to look up"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "Search Ira's long-term memory (Mem0) for stored facts, preferences, past conversations, and ingested data about customers, orders, or Machinecraft operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memory"},
                    "user_id": {"type": "string", "description": "Optional: specific user/category to search (e.g. 'machinecraft_customers', 'machinecraft_knowledge')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "writing_skill",
            "description": "Draft a response, email, or document based on research findings. Use after gathering information with other tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The original user query"},
                    "research_summary": {"type": "string", "description": "All research findings to base the draft on"},
                },
                "required": ["query", "research_summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fact_checking_skill",
            "description": "Verify a draft for accuracy against the machine database, AM series thickness rules, and pricing disclaimers. Always use before finalizing a response.",
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
            "name": "ask_user",
            "description": "Ask the user a clarifying question when you need more information to complete a task. Use this instead of guessing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question to ask the user"},
                },
                "required": ["question"],
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

    # Notify progress callback if available
    progress_fn = context.get("_progress_callback")
    if progress_fn:
        try:
            progress_fn(tool_name)
        except Exception:
            pass

    if tool_name == "research_skill":
        query = arguments.get("query", "")
        result = await invoke_research(query, context)
        return result or "(No results found in knowledge base)"

    elif tool_name == "web_search":
        query = arguments.get("query", "")
        company = arguments.get("company", "")
        try:
            from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
            iris_ctx = {"company": company or query, "query": query}
            iris_result = await iris_enrich(iris_ctx)
            if iris_result:
                parts = []
                for k, v in iris_result.items():
                    if v:
                        parts.append(f"{k}: {v}")
                return "\n".join(parts) if parts else "(No web results)"
        except Exception as e:
            logger.warning(f"Iris web search failed: {e}")
        try:
            import httpx
            resp = httpx.get(f"https://s.jina.ai/{query}", timeout=15, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                return resp.text[:3000]
        except Exception:
            pass
        return "(Web search unavailable)"

    elif tool_name == "customer_lookup":
        query = arguments.get("query", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            for uid in ["machinecraft_customers", "machinecraft_knowledge"]:
                memories = mem0.search(query, uid, limit=5)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Customer lookup Mem0 error: {e}")
        try:
            result = await invoke_research(f"customer {query}", context)
            if result:
                results.append(f"[knowledge_base] {result[:1000]}")
        except Exception:
            pass
        return "\n".join(results) if results else f"(No customer data found for '{query}')"

    elif tool_name == "memory_search":
        query = arguments.get("query", "")
        user_id = arguments.get("user_id", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            search_ids = [user_id] if user_id else [
                "machinecraft_knowledge", "machinecraft_customers",
                "machinecraft_pricing", "machinecraft_processes",
                "machinecraft_general",
            ]
            for uid in search_ids:
                memories = mem0.search(query, uid, limit=5)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Memory search error: {e}")
        return "\n".join(results) if results else f"(No memories found for '{query}')"

    elif tool_name == "writing_skill":
        query = arguments.get("query", "")
        research_summary = arguments.get("research_summary", "")
        ctx = dict(context)
        ctx["research_output"] = research_summary
        result = await invoke_write(query, ctx)
        return result or "(Draft empty)"

    elif tool_name == "fact_checking_skill":
        draft = arguments.get("draft", "")
        original_query = arguments.get("original_query", "")
        result = await invoke_verify(draft, original_query, context)
        return result or draft

    elif tool_name == "ask_user":
        question = arguments.get("question", "")
        return f"ASK_USER:{question}"

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
