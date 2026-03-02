"""
IRA Skills as OpenAI-Compatible Tools

Exposes research_skill, writing_skill, fact_checking_skill, lead_intelligence
as function-calling tools for LLM-driven orchestration.
"""

import json
import logging
from typing import Any, Dict, List

from openclaw.agents.ira.src.core.company_config import get_config

logger = logging.getLogger("ira.tools.skills")


def _health(service: str, error: str) -> None:
    """Record a service failure in the health tracker (best-effort)."""
    try:
        from openclaw.agents.ira.src.core.service_health import record_failure
        record_failure(service, error)
    except Exception:
        pass


def _health_ok(service: str) -> None:
    try:
        from openclaw.agents.ira.src.core.service_health import record_success
        record_success(service)
    except Exception:
        pass


def _track_agent(context: Dict, agent_name: str) -> None:
    """Record which agent was invoked for accurate scoring later."""
    context.setdefault("agents_used", []).append(agent_name)


def _build_tools_schema(cfg) -> List[Dict[str, Any]]:
    """Build the tools schema with company-specific descriptions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "research_skill",
                "description": f"Search {cfg.company.name}'s knowledge base (Qdrant, Mem0, Neo4j, machine database). Use for product specs, customer history, order data, pricing, and any internal knowledge.",
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
                "description": "Search the web for external information. Use for general web queries, industry news, competitor analysis, or market trends.",
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
                "name": "lead_intelligence",
                "description": "Get intelligence on a company or lead: recent news, expansions, industry trends, website analysis. Use when preparing for outreach or researching a prospect.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string", "description": "Company name"},
                        "country": {"type": "string", "description": "Country (optional)"},
                        "industry": {"type": "string", "description": "Industry sector (optional)"},
                    },
                    "required": ["company"],
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
                "description": f"Search {cfg.company.agent_name}'s long-term memory (Mem0) for stored facts, preferences, past conversations, and ingested data about customers, orders, or {cfg.company.name} operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for in memory"},
                        "user_id": {"type": "string", "description": f"Optional: specific user/category to search (e.g. '{cfg.memory.customers}', '{cfg.memory.knowledge}')"},
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
                "description": "Verify a draft for accuracy against the machine database, product rules, and pricing disclaimers. Always use before finalizing a response.",
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
    cfg = get_config()
    return _build_tools_schema(cfg)


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    """Execute an IRA skill by name. Called when LLM returns tool_calls."""
    cfg = get_config()
    try:
        from openclaw.agents.ira.src.skills.invocation import (
            invoke_research,
            invoke_verify,
            invoke_write,
        )
    except ImportError:
        return "Error: Skill invocation unavailable."

    progress_fn = context.get("_progress_callback")
    if progress_fn:
        try:
            progress_fn(tool_name)
        except Exception:
            pass

    if tool_name == "research_skill":
        _track_agent(context, "clio")
        query = arguments.get("query", "")
        results_parts = []

        result = await invoke_research(query, context)
        if result:
            results_parts.append(f"[primary] {result}")

        if not result or len(result) < 100:
            try:
                from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve as qdrant_retrieve
                rag = qdrant_retrieve(query, top_k=8)
                _health_ok("qdrant")
                if hasattr(rag, 'citations') and rag.citations:
                    for c in rag.citations[:5]:
                        results_parts.append(f"[qdrant:{c.filename}] {c.text[:400]}")
            except Exception as e:
                _health("qdrant", str(e))

        return "\n\n".join(results_parts) if results_parts else "(No results found in knowledge base)"

    elif tool_name == "web_search":
        _track_agent(context, "iris")
        query = arguments.get("query", "")
        company = arguments.get("company", "")
        try:
            from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
            iris_ctx = {"company": company or query, "query": query}
            iris_result = await iris_enrich(iris_ctx)
            if iris_result:
                parts = [f"{k}: {v}" for k, v in iris_result.items() if v]
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

    elif tool_name == "lead_intelligence":
        _track_agent(context, "iris")
        company = arguments.get("company", "")
        country = arguments.get("country", "")
        industry = arguments.get("industry", "")
        try:
            from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
            iris_ctx = {
                "company": company,
                "country": country,
                "industries": [industry] if industry else [],
                "query": f"{company} {country} {industry}".strip(),
            }
            iris_result = await iris_enrich(iris_ctx)
            if iris_result:
                parts = [f"{k}: {v}" for k, v in iris_result.items() if v]
                return "\n".join(parts) if parts else f"(No intelligence found for {company})"
        except Exception as e:
            logger.warning(f"Lead intelligence failed: {e}")
        return f"(Lead intelligence unavailable for {company})"

    elif tool_name == "customer_lookup":
        _track_agent(context, "clio")
        query = arguments.get("query", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            _health_ok("mem0")
            for uid in [cfg.memory.customers, cfg.memory.knowledge]:
                memories = mem0.search(query, uid, limit=10)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Customer lookup Mem0 error: {e}")
            _health("mem0", str(e))
        try:
            result = await invoke_research(f"customer {query}", context)
            if result:
                results.append(f"[knowledge_base] {result[:2000]}")
        except Exception:
            pass
        if results:
            header = (
                "WARNING: These results come from memory and documents. "
                "Not every company mentioned is a CONFIRMED CUSTOMER. "
                "A company is only a confirmed customer if the data says they BOUGHT/ORDERED a machine. "
                "Companies that are agents, prospects, competitors, or just mentioned in passing are NOT customers. "
                "Label each as CONFIRMED CUSTOMER, PROSPECT, AGENT, or UNKNOWN based on the evidence.\n\n"
            )
            return header + "\n".join(results)
        return f"(No customer data found for '{query}')"

    elif tool_name == "memory_search":
        _track_agent(context, "clio")
        query = arguments.get("query", "")
        user_id = arguments.get("user_id", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            _health_ok("mem0")
            search_ids = [user_id] if user_id else cfg.memory.all_search_ids()
            for uid in search_ids:
                memories = mem0.search(query, uid, limit=10)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Memory search error: {e}")
            _health("mem0", str(e))
        return "\n".join(results) if results else f"(No memories found for '{query}')"

    elif tool_name == "writing_skill":
        _track_agent(context, "calliope")
        query = arguments.get("query", "")
        research_summary = arguments.get("research_summary", "")
        ctx = dict(context)
        ctx["research_output"] = research_summary
        result = await invoke_write(query, ctx)
        return result or "(Draft empty)"

    elif tool_name == "fact_checking_skill":
        _track_agent(context, "vera")
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
